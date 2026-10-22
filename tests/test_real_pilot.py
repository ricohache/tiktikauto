"""Opt-in integration verification of the actual generated pilot; no mock media."""
import json
import os
import unittest
from pathlib import Path

from PIL import Image, ImageStat
from tiktok_history_factory.config.settings import Settings
from tiktok_history_factory.pipeline.checkpoints import digest
from tiktok_history_factory.providers.ffmpeg import FFmpegProvider
from tiktok_history_factory.providers.piper_tts import inspect_wav


@unittest.skipUnless(os.getenv('THF_INTEGRATION') == '1', 'Set THF_INTEGRATION=1 after generating the real pilot')
class RealPilotIntegration(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]
        self.work = self.root/'work/pilot-thiaroye-1944-v2'
        self.manifest = json.loads((self.work/'manifest.json').read_text(encoding='utf-8'))

    def test_actual_checkpoint_files_are_unchanged(self):
        checkpoints = json.loads((self.work/'checkpoints.json').read_text(encoding='utf-8'))
        self.assertEqual(set(checkpoints), {'research', 'script', 'voice', 'images', 'animation', 'render', 'qc'})
        for stage in checkpoints.values():
            for path, expected in stage['files'].items():
                self.assertEqual(digest(path), expected)

    def test_real_diffusion_images_and_english_voice(self):
        images = self.manifest['stages']['images']
        self.assertTrue(3 <= len(images['paths']) <= 6)
        for path in images['paths']:
            with Image.open(path) as image:
                self.assertEqual(image.size, (768,1344))
                self.assertIn('prompt', image.info)
                self.assertGreater(ImageStat.Stat(image.convert('L')).stddev[0], 8)
        for path in self.manifest['stages']['voice']['paths']:
            info = inspect_wav(path)
            self.assertEqual(info['sample_rate'], 22050)
            self.assertGreater(info['rms'],20)
            self.assertEqual(digest(path), self.manifest['stages']['voice']['sha256'][path])
        voice_records = json.loads((self.work/'audio/voice-manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(voice_records['audio_language'], 'en')
        self.assertEqual(voice_records['subtitle_language'], 'fr-FR')
        self.assertTrue(all(r['parameters']['length_scale'] >= 1 for r in voice_records['utterances']))
        self.assertTrue(120 <= voice_records['words_per_minute'] <= 145)

    def test_export_and_full_decode(self):
        settings = Settings()
        provider = FFmpegProvider(settings.FFMPEG_PATH, settings.FFPROBE_PATH)
        output = self.manifest['output_path']
        probe = provider.probe_file(output)
        self.assertTrue(20 <= float(probe['format']['duration']) <= 30)
        result = provider._run(['-v','error','-i',output,'-f','null','-'])
        self.assertTrue(result['success'], result)
        self.assertFalse(result['stderr'].strip())

    def test_sqlite_requires_review_and_has_no_publication(self):
        import sqlite3
        with sqlite3.connect('file:' + (self.root/'data/factory.db').as_posix() + '?mode=ro', uri=True) as database:
            row = database.execute('SELECT status,tiktok_video_id,published_at FROM video_tasks WHERE id=?',
                                   (self.manifest['task_id'],)).fetchone()
        self.assertEqual(row[0], 'awaiting_review')
        self.assertFalse(row[1])
        self.assertFalse(row[2])

    def test_actual_ass_canvas_and_caption_bounds(self):
        ass = (self.work/'render/captions.ass').read_text(encoding='utf-8')
        self.assertIn('PlayResX: 1080', ass)
        self.assertIn('PlayResY: 1920', ass)
        self.assertIn('Style: Default,Arial,54,', ass)
        self.assertEqual(sum(line.startswith('Dialogue:') for line in ass.splitlines()), 8)
        for block in (self.work/'script/subtitles.srt').read_text(encoding='utf-8').strip().split('\n\n'):
            self.assertLessEqual(len(block.splitlines()[2:]), 2)
            self.assertTrue(all(len(line) <= 40 for line in block.splitlines()[2:]))

    def test_no_rejected_images_and_no_permanent_overlay(self):
        rejected = json.loads((self.root/'work/pilot-thiaroye-1944/manifest.json').read_text(encoding='utf-8'))
        old_hashes = {digest(p) for p in rejected['stages']['images']['paths']}
        for p in self.manifest['stages']['images']['paths']:
            self.assertNotIn(digest(p), old_hashes)
            graph = json.loads(Path(p).with_suffix('.generation.json').read_text())['workflow']
            self.assertEqual(graph['8']['inputs']['lora_name'], 'LineAniRedmondV2-Lineart-LineAniAF.safetensors')
            self.assertTrue(graph['2']['inputs']['text'].startswith('LineAniAF'))
        logs = json.loads((self.work/'render/ffmpeg-log.json').read_text())
        command = logs[-1]['command']
        self.assertEqual(command[command.index('-vf')+1], 'ass=captions.ass')
        self.assertIn('Reconstitution', ' '.join(command))

    def test_real_wan_clip_when_present(self):
        record_path = self.work/'wan/clip.wan.json'
        if not record_path.exists():
            self.skipTest('Optional Wan not attempted')
        record = json.loads(record_path.read_text(encoding='utf-8'))
        if record.get('status') != 'SUCCESS':
            self.skipTest('Optional Wan failed; FFmpeg fallback recorded')
        self.assertEqual(digest(record['output_path']), record['sha256'])
        video = record['probe']['streams'][0]
        self.assertEqual((video['width'],video['height'],int(video['nb_frames'])),(480,832,17))
        self.assertTrue(record['decode']['success'])
        self.assertTrue(record['telemetry'])

    def test_compositor_uses_the_actual_voice_pcm(self):
        import wave
        voice = self.manifest['stages']['voice']
        combined = self.manifest['stages']['render']['audio_path']
        with wave.open(combined, 'rb') as audio:
            self.assertEqual((audio.getframerate(), audio.getnchannels(), audio.getsampwidth()), (22050, 1, 2))
            pcm = audio.readframes(audio.getnframes())
        offset = 0
        for path, duration in zip(voice['paths'], voice['durations']):
            with wave.open(path, 'rb') as source:
                expected = source.readframes(source.getnframes())
            self.assertEqual(pcm[offset:offset+len(expected)], expected)
            offset += round(duration*22050)*2
