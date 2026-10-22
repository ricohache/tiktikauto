"""Real ComfyUI API submission, bounded polling and reproducible PNG outputs."""
import hashlib
import json
import secrets
import struct
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


class ComfyUIImageProvider:
    def __init__(self, base_url='http://127.0.0.1:8188', timeout=900):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.available = self._check_health()

    def _request(self, path, payload=None):
        request = urllib.request.Request(self.base_url + path,
            data=json.dumps(payload).encode() if payload is not None else None,
            headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)

    def _check_health(self):
        try:
            return bool(self._request('/system_stats').get('devices'))
        except Exception:
            return False

    def list_checkpoints(self):
        data = self._request('/object_info/CheckpointLoaderSimple')
        return data['CheckpointLoaderSimple']['input']['required']['ckpt_name'][0]

    @staticmethod
    def workflow(prompt, negative, checkpoint, width, height, seed, steps, lora='', strength=.85):
        graph = {
            '1': {'class_type': 'CheckpointLoaderSimple', 'inputs': {'ckpt_name': checkpoint}},
            '2': {'class_type': 'CLIPTextEncode', 'inputs': {'text': prompt, 'clip': ['1', 1]}},
            '3': {'class_type': 'CLIPTextEncode', 'inputs': {'text': negative, 'clip': ['1', 1]}},
            '4': {'class_type': 'EmptyLatentImage', 'inputs': {'width': width, 'height': height, 'batch_size': 1}},
            '5': {'class_type': 'KSampler', 'inputs': {'model': ['1', 0], 'positive': ['2', 0],
                  'negative': ['3', 0], 'latent_image': ['4', 0], 'seed': seed, 'steps': steps,
                  'cfg': 7.0, 'sampler_name': 'dpmpp_2m', 'scheduler': 'karras', 'denoise': 1.0}},
            '6': {'class_type': 'VAEDecode', 'inputs': {'samples': ['5', 0], 'vae': ['1', 2]}},
            '7': {'class_type': 'SaveImage', 'inputs': {'images': ['6', 0], 'filename_prefix': 'history_factory/pilot'}}}
        if lora:
            graph['8'] = {'class_type': 'LoraLoader', 'inputs': {'model': ['1', 0], 'clip': ['1', 1],
                'lora_name': lora, 'strength_model': strength, 'strength_clip': strength}}
            graph['2']['inputs']['clip'] = ['8', 1]
            graph['3']['inputs']['clip'] = ['8', 1]
            graph['5']['inputs']['model'] = ['8', 0]
        return graph

    def generate_image(self, prompt, width=768, height=1344, seed=-1, checkpoint='',
                       output_path='', negative_prompt='', steps=24, lora='', strength=.85):
        if not output_path:
            return {'status': 'BLOCKED', 'error': 'An explicit output_path is required'}
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        record_path = target.with_suffix('.generation.json')
        if width % 64 or height % 64 or not 256 <= width <= 1536 or not 256 <= height <= 1536:
            return {'status': 'FAILED', 'error': 'Dimensions must be 256..1536 and divisible by 64'}
        if not 1 <= steps <= 50:
            return {'status': 'FAILED', 'error': 'steps must be 1..50'}
        try:
            checkpoints = self.list_checkpoints()
            checkpoint = checkpoint or (checkpoints[0] if checkpoints else '')
            if checkpoint not in checkpoints:
                return {'status': 'BLOCKED', 'error': 'Requested checkpoint is not installed'}
            previous = json.loads(record_path.read_text()) if record_path.exists() else {}
            if seed < 0:
                seed = previous.get('seed', secrets.randbits(32))
            if not 0 <= strength <= 1.5:
                raise ValueError('LoRA strength outside 0..1.5')
            graph = self.workflow(prompt, negative_prompt, checkpoint, width, height, seed, steps, lora, strength)
            fingerprint = hashlib.sha256(json.dumps(graph, sort_keys=True).encode()).hexdigest()
            if previous.get('fingerprint') == fingerprint and previous.get('status') == 'SUCCESS' and target.exists():
                if hashlib.sha256(target.read_bytes()).hexdigest() == previous.get('sha256'):
                    return {**previous, 'resumed': True}
            if target.exists() and previous.get('fingerprint') != fingerprint:
                raise RuntimeError('Output belongs to another generation; choose a new path')
            started = time.monotonic()
            job = previous.get('prompt_id') if previous.get('fingerprint') == fingerprint else None
            if not job:
                queue = self._request('/queue')
                if queue.get('queue_running') or queue.get('queue_pending'):
                    return {'status': 'BLOCKED', 'error': 'GPU queue busy; retry after current job'}
                submission = self._request('/prompt', {'prompt': graph, 'client_id': 'history-factory-pilot'})
                if submission.get('node_errors'):
                    raise RuntimeError(json.dumps(submission['node_errors']))
                job = submission['prompt_id']
                previous = {'status': 'RUNNING', 'prompt_id': job, 'fingerprint': fingerprint,
                            'seed': seed, 'checkpoint': checkpoint, 'workflow': graph,
                            'width': width, 'height': height, 'output_path': str(target)}
                record_path.write_text(json.dumps(previous, indent=2), encoding='utf-8')
            while time.monotonic() - started < self.timeout:
                history = self._request('/history/' + urllib.parse.quote(job))
                if job in history:
                    item = history[job]
                    messages = item.get('status', {})
                    if messages.get('status_str') == 'error':
                        raise RuntimeError(json.dumps(messages))
                    images = item.get('outputs', {}).get('7', {}).get('images', [])
                    if images:
                        with urllib.request.urlopen(self.base_url + '/view?' + urllib.parse.urlencode(images[0]), timeout=60) as response:
                            blob = response.read(32 * 1024**2 + 1)
                        if len(blob) > 32 * 1024**2 or blob[:8] != b'\x89PNG\r\n\x1a\n':
                            raise RuntimeError('Invalid or oversized PNG')
                        if struct.unpack('>II', blob[16:24]) != (width, height):
                            raise RuntimeError('Unexpected PNG dimensions')
                        target.write_bytes(blob)
                        result = {**previous, 'status': 'SUCCESS', 'sha256': hashlib.sha256(blob).hexdigest(),
                                  'seconds': round(time.monotonic() - started, 2), 'history': item,
                                  'device': self._request('/system_stats')['devices']}
                        record_path.write_text(json.dumps(result, indent=2), encoding='utf-8')
                        return result
                time.sleep(2)
            return {**previous, 'status': 'BLOCKED', 'error': 'Timeout; job retained for resume without duplicate'}
        except Exception as exc:
            error = str(exc)
            if isinstance(exc, urllib.error.HTTPError):
                error += ' ' + exc.read(4096).decode(errors='replace')
            return {'status': 'FAILED', 'error': error,
                    'out_of_memory': any(x in error.lower() for x in ('out of memory', 'outofmemory'))}
