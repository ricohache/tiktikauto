"""Unit checks for invalid data, real-file checkpoint reuse and API contracts."""
import io
import json
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from tiktok_history_factory.pipeline.checkpoints import Checkpoints
from tiktok_history_factory.pipeline.pilot import validate_dossier
from tiktok_history_factory.providers.ollama_cloud import OllamaCloudClient
from tiktok_history_factory.providers.piper_tts import PiperTTSProvider, inspect_wav
from tiktok_history_factory.media.subtitles import SubtitleGenerator
from tiktok_history_factory.providers.comfyui_images import ComfyUIImageProvider
from tiktok_history_factory.providers.history_sources import HistoricalSourceProvider


class PilotContracts(unittest.TestCase):
    def test_resume_rechecks_actual_content_and_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'artifact.txt'
            calls = []
            def action():
                calls.append(1)
                output.write_text('verified')
                return {'output': str(output)}, [output]
            cp = Checkpoints(directory)
            first = cp.run('stage', {'version': 1}, action)
            self.assertEqual(first, cp.run('stage', {'version': 1}, action))
            self.assertEqual(len(calls), 1)
            output.write_text('corrupt')
            cp.run('stage', {'version': 1}, action)
            cp.run('stage', {'version': 2}, action)
            self.assertEqual(len(calls), 3)

    def test_missing_artifact_never_commits_success(self):
        with tempfile.TemporaryDirectory() as directory:
            cp = Checkpoints(directory)
            with self.assertRaises(RuntimeError):
                cp.run('missing', {}, lambda: ({'status': 'SUCCESS'}, [Path(directory)/'absent']))
            self.assertNotIn('missing', cp.records)

    def test_reject_unreferenced_claim(self):
        root = Path(__file__).resolve().parents[1]
        dossier = json.loads((root/'data/subjects/thiaroye-1944.json').read_text(encoding='utf-8'))
        dossier['scenes'][0]['claims'] = ['INVENTED']
        with self.assertRaises(ValueError):
            validate_dossier(dossier)

    def test_piper_not_available_without_model(self):
        self.assertFalse(PiperTTSProvider('').available)

    def test_reject_silent_wav(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'silent.wav'
            with wave.open(str(path), 'wb') as stream:
                stream.setnchannels(1); stream.setsampwidth(2); stream.setframerate(22050)
                stream.writeframes(b'\x00\x00'*22050)
            with self.assertRaises(ValueError):
                inspect_wav(path)

    def test_subtitle_remainder_has_positive_duration(self):
        result = SubtitleGenerator().split_into_segments('un deux trois quatre cinq six sept', 7000)
        self.assertEqual(result[-1].end_ms, 7000)
        self.assertTrue(all(s.end_ms > s.start_ms for s in result))

    def test_mock_native_and_openai_api_routes(self):
        for base, route in [('http://localhost:11434/api', '/api/chat'), ('https://ollama.com/v1', '/v1/chat/completions')]:
            payload = {'message': {'content': 'OK'}} if base.endswith('/api') else {'choices': [{'message': {'content': 'OK'}}]}
            with patch('urllib.request.urlopen', return_value=io.BytesIO(json.dumps(payload).encode())) as request:
                response = OllamaCloudClient(base, '', 'test-model').generate('test')
                self.assertEqual(response['status'], 'SUCCESS')
                req = request.call_args.args[0]
                self.assertTrue(req.full_url.endswith(route))
                data = json.loads(req.data)
                self.assertEqual('options' in data, base.endswith('/api'))

    def test_source_rejects_unapproved_url_without_network(self):
        with self.assertRaises(ValueError):
            HistoricalSourceProvider().fetch('http://127.0.0.1/private', 'unused', {'example.org'})

    def test_mock_comfy_oom_is_not_success(self):
        provider = ComfyUIImageProvider.__new__(ComfyUIImageProvider)
        provider.base_url, provider.timeout = 'http://mock.invalid', 10
        def request(path, payload=None):
            if path.startswith('/object_info'):
                return {'CheckpointLoaderSimple': {'input': {'required': {'ckpt_name': [['test.safetensors']]}}}}
            if path == '/queue': return {'queue_running': [], 'queue_pending': []}
            if path == '/prompt': return {'prompt_id': 'unit-job'}
            return {'unit-job': {'status': {'status_str': 'error', 'messages': ['CUDA out of memory']}}}
        with tempfile.TemporaryDirectory() as directory, patch.object(provider, '_request', side_effect=request):
            output = Path(directory)/'image.png'
            result = provider.generate_image('unit simulation', seed=1, output_path=str(output))
            self.assertEqual(result['status'], 'FAILED')
            self.assertTrue(result['out_of_memory'])
            self.assertFalse(output.exists())

    def test_mock_timeout_resume_never_duplicates_submission(self):
        provider = ComfyUIImageProvider.__new__(ComfyUIImageProvider)
        provider.base_url, provider.timeout = 'http://mock.invalid', 0
        submissions = []
        def request(path, payload=None):
            if path.startswith('/object_info'):
                return {'CheckpointLoaderSimple': {'input': {'required': {'ckpt_name': [['test.safetensors']]}}}}
            if path == '/queue': return {'queue_running': [], 'queue_pending': []}
            if path == '/prompt':
                submissions.append(payload)
                return {'prompt_id': 'unit-job'}
            return {}
        with tempfile.TemporaryDirectory() as directory, patch.object(provider, '_request', side_effect=request):
            output = str(Path(directory)/'image.png')
            for _ in range(2):
                self.assertEqual(provider.generate_image('unit simulation', seed=1, output_path=output)['status'], 'BLOCKED')
            self.assertEqual(len(submissions), 1)
