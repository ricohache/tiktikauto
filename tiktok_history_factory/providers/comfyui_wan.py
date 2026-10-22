"""Official native Wan 2.2 TI2V 5B graph, one bounded I2V attempt."""
import json
import hashlib
import time
import urllib.parse
import urllib.request
from pathlib import Path

from tiktok_history_factory.pipeline.checkpoints import digest, save_json
from tiktok_history_factory.providers.comfyui_images import ComfyUIImageProvider
from tiktok_history_factory.providers.ffmpeg import FFmpegProvider


class ComfyUIWanProvider(ComfyUIImageProvider):
    MODEL = 'wan2.2_ti2v_5B_fp16.safetensors'
    CLIP = 'umt5_xxl_fp8_e4m3fn_scaled.safetensors'
    VAE = 'wan2.2_vae.safetensors'

    def list_wan_models(self):
        data = self._request('/object_info/UNETLoader')
        return [name for name in data['UNETLoader']['input']['required']['unet_name'][0] if self.MODEL in name]

    @staticmethod
    def native_workflow(image_name, prompt, frames=17, fps=8):
        # Same graph/classes/shift/sampler as the bundled official 5B TI2V template.
        return {
            '37': {'class_type': 'UNETLoader', 'inputs': {'unet_name': ComfyUIWanProvider.MODEL, 'weight_dtype': 'default'}},
            '38': {'class_type': 'CLIPLoader', 'inputs': {'clip_name': ComfyUIWanProvider.CLIP, 'type': 'wan', 'device': 'cpu'}},
            '39': {'class_type': 'VAELoader', 'inputs': {'vae_name': ComfyUIWanProvider.VAE}},
            '48': {'class_type': 'ModelSamplingSD3', 'inputs': {'model': ['37', 0], 'shift': 8.0}},
            '56': {'class_type': 'LoadImage', 'inputs': {'image': image_name}},
            '55': {'class_type': 'Wan22ImageToVideoLatent', 'inputs': {'vae': ['39', 0], 'width': 480, 'height': 832,
                    'length': frames, 'batch_size': 1, 'start_image': ['56', 0]}},
            '6': {'class_type': 'CLIPTextEncode', 'inputs': {'text': prompt, 'clip': ['38', 0]}},
            '7': {'class_type': 'CLIPTextEncode', 'inputs': {'text': 'color, photograph, distortion, text, watermark, gore, new people, flickering', 'clip': ['38', 0]}},
            '3': {'class_type': 'KSampler', 'inputs': {'model': ['48', 0], 'positive': ['6', 0], 'negative': ['7', 0],
                    'latent_image': ['55', 0], 'seed': 19441201, 'steps': 12, 'cfg': 5.0,
                    'sampler_name': 'uni_pc', 'scheduler': 'simple', 'denoise': 1.0}},
            '8': {'class_type': 'VAEDecode', 'inputs': {'samples': ['3', 0], 'vae': ['39', 0]}},
            '57': {'class_type': 'CreateVideo', 'inputs': {'images': ['8', 0], 'fps': fps}},
            '58': {'class_type': 'SaveVideo', 'inputs': {'video': ['57', 0], 'filename_prefix': 'history_factory/wan_pilot', 'format': 'auto', 'codec': 'auto'}}}

    def _upload(self, image_path):
        image_path = Path(image_path)
        name = 'thf-' + digest(image_path)[:16] + '.png'
        boundary = '----HistoryFactoryUploadBoundary'
        blob = image_path.read_bytes()
        if len(blob) > 20*1024**2:
            raise ValueError('Input image exceeds limit')
        body = (f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="{name}"\r\n'
                'Content-Type: image/png\r\n\r\n').encode() + blob + f'\r\n--{boundary}--\r\n'.encode()
        request = urllib.request.Request(self.base_url + '/upload/image', data=body,
                headers={'Content-Type': 'multipart/form-data; boundary=' + boundary})
        with urllib.request.urlopen(request, timeout=30) as response:
            uploaded = json.load(response)
        return (uploaded.get('subfolder', '') + '/' + uploaded['name']).lstrip('/')

    def generate_clip(self, image_path, prompt, frames=17, fps=8, output_path='', timeout=600):
        if frames < 5 or frames > 33 or (frames-1) % 4 or not 4 <= fps <= 16:
            return {'status': 'BLOCKED', 'error': 'Conservative test allows 4n+1 frames, max 33, fps 4..16'}
        if not output_path:
            return {'status': 'BLOCKED', 'error': 'Explicit output_path required'}
        target = Path(output_path).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        record_path = target.with_suffix('.wan.json')
        previous = json.loads(record_path.read_text(encoding='utf-8')) if record_path.exists() else {}
        fingerprint = hashlib.sha256(json.dumps({'image': digest(image_path), 'prompt': prompt, 'frames': frames, 'fps': fps, 'version': 1},sort_keys=True).encode()).hexdigest()
        if previous.get('fingerprint') == fingerprint and previous.get('status') == 'SUCCESS' and target.is_file() and previous.get('sha256') == digest(target):
            return {**previous, 'resumed': True}
        started = time.monotonic()
        job = previous.get('prompt_id') if previous.get('fingerprint') == fingerprint and previous.get('status') == 'RUNNING' else None
        try:
            if not self.list_wan_models():
                return {'status': 'BLOCKED', 'fallback': 'FFMPEG', 'error': 'Wan 5B weights missing'}
            queue = self._request('/queue')
            if not job and (queue.get('queue_running') or queue.get('queue_pending')):
                return {'status': 'BLOCKED', 'fallback': 'FFMPEG', 'error': 'GPU queue busy'}
            clip = self._request('/object_info/CLIPLoader')['CLIPLoader']['input']['required']['clip_name'][0]
            vae = self._request('/object_info/VAELoader')['VAELoader']['input']['required']['vae_name'][0]
            if self.CLIP not in clip or self.VAE not in vae:
                return {'status': 'BLOCKED', 'fallback': 'FFMPEG', 'error': 'Wan text encoder/VAE missing'}
            if target.exists() and previous.get('fingerprint') != fingerprint:
                raise RuntimeError('Different Wan output exists; choose a new path')
            if not job:
                graph = self.native_workflow(self._upload(image_path), prompt, frames, fps)
                save_json(target.with_suffix('.workflow.json'), graph)
                job = self._request('/prompt', {'prompt': graph, 'client_id': 'history-factory-wan-single-test'})['prompt_id']
            record = {'status': 'RUNNING', 'prompt_id': job, 'image_sha256': digest(image_path),
                      'width': 480, 'height': 832, 'frames': frames, 'fps': fps, 'steps': 12,
                      'offload': 'Native ComfyUI memory management; text encoder explicitly on CPU',
                      'output_path': str(target), 'fingerprint': fingerprint,
                      'system_before': self._request('/system_stats')}
            save_json(record_path, record)
            telemetry = []
            while time.monotonic() - started < timeout:
                history = self._request('/history/' + job)
                if job in history:
                    item = history[job]
                    if item.get('status', {}).get('status_str') == 'error':
                        raise RuntimeError(json.dumps(item['status']))
                    output = item.get('outputs', {}).get('58', {})
                    candidates = output.get('images', []) + output.get('videos', []) + output.get('gifs', [])
                    if candidates:
                        with urllib.request.urlopen(self.base_url + '/view?' + urllib.parse.urlencode(candidates[0]), timeout=90) as response:
                            data = response.read(200*1024**2 + 1)
                        if len(data) > 200*1024**2 or len(data) < 1000:
                            raise RuntimeError('Invalid clip size')
                        target.write_bytes(data)
                        ffmpeg = FFmpegProvider()
                        probe = ffmpeg.probe_file(str(target))
                        decode = ffmpeg._run(['-v','error','-i',str(target),'-f','null','-'])
                        if not probe.get('streams') or not decode['success']:
                            raise RuntimeError('Wan output failed ffprobe/decode')
                        result = {**record, 'status': 'SUCCESS', 'sha256': digest(target), 'history': item,
                                  'seconds': round(time.monotonic()-started,2), 'probe': probe,
                                  'decode': decode, 'telemetry': telemetry, 'visual_qc': 'AWAITING_REVIEW'}
                        save_json(record_path, result)
                        return result
                if len(telemetry) < 300:
                    import subprocess
                    try:
                        measurement = subprocess.run(['nvidia-smi','--query-gpu=memory.used,utilization.gpu,power.draw,temperature.gpu',
                                                      '--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=10)
                        telemetry.append({'elapsed': round(time.monotonic()-started,1), 'gpu': measurement.stdout.strip()})
                    except (OSError, subprocess.TimeoutExpired) as exc:
                        telemetry.append({'elapsed': round(time.monotonic()-started,1), 'gpu_unavailable': str(exc)})
                time.sleep(4)
            self._request('/api/jobs/' + job + '/cancel', {})
            raise TimeoutError('Wan deadline exceeded; only this job cancelled; select FFmpeg fallback')
        except Exception as exc:
            if job:
                try:
                    self._request('/api/jobs/' + job + '/cancel', {})
                except Exception:
                    pass  # Retain prompt_id in the report; never interrupt another job.
            error = str(exc)
            if hasattr(exc, 'read'):
                error += ' ' + exc.read(4096).decode(errors='replace')
            result = {'status': 'FAILED_FOR_SCENE', 'fallback': 'FFMPEG', 'prompt_id': job,
                      'seconds': round(time.monotonic()-started,2), 'error': error,
                      'telemetry': locals().get('telemetry', []), 'parameters': locals().get('record', {})}
            save_json(record_path, result)
            return result
