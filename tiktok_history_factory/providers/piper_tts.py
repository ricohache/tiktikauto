"""Local Piper CLI, French voice validation and non-silence checks."""
import array
import hashlib
import json
import math
import shutil
import subprocess
import sys
import wave
from pathlib import Path


def inspect_wav(path):
    with wave.open(str(path), 'rb') as audio:
        if audio.getsampwidth() != 2:
            raise ValueError('Expected 16-bit PCM')
        samples = array.array('h', audio.readframes(audio.getnframes()))
        if sys.byteorder != 'little':
            samples.byteswap()
        rms = math.sqrt(sum(v * v for v in samples) / max(1, len(samples)))
        duration = audio.getnframes() / audio.getframerate()
        if duration < .25 or rms < 20:
            raise ValueError('Empty or silent voice audio')
        peak = max(abs(v) for v in samples)
        clipped = sum(abs(v) >= 32760 for v in samples)
        return {'duration': duration, 'sample_rate': audio.getframerate(),
                'channels': audio.getnchannels(), 'rms': round(rms, 2),
                'peak': peak, 'peak_dbfs': round(20*math.log10(max(1,peak)/32768),2),
                'clipped_samples': clipped, 'clipping_fraction': clipped/max(1,len(samples))}


class PiperTTSProvider:
    def __init__(self, model_path='', piper_binary='piper', expected_language='en'):
        self.model_path = model_path
        local = Path(__file__).resolve().parents[2] / '.venv/Scripts/piper.exe'
        self.piper_binary = str(local) if piper_binary == 'piper' and local.is_file() else (shutil.which(piper_binary) or '')
        if Path(piper_binary).is_file():
            self.piper_binary = str(Path(piper_binary).resolve())
        config = Path(model_path + '.json')
        self.available = bool(self.piper_binary and model_path and Path(model_path).is_file() and config.is_file())
        self.error = ''
        if self.available:
            data = json.loads(config.read_text(encoding='utf-8'))
            self.language = data.get('language', {}).get('code', '')
            actual = self.language.replace('_', '-')
            expected = expected_language.replace('_', '-')
            self.available = actual == expected if '-' in expected else actual.split('-')[0] == expected
            if not self.available:
                self.error = f'A {expected_language} voice is required; found {self.language}'

    def synthesize(self, text, output_path, length_scale=1.0):
        if not self.available:
            return {'status': 'BLOCKED', 'error': self.error or 'Piper executable or fr_FR model/config missing'}
        if not text.strip():
            return {'status': 'FAILED', 'error': 'Empty narration'}
        if length_scale < 1:
            return {'status': 'BLOCKED', 'error': 'Artificial narration acceleration is prohibited'}
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        try:
            result = subprocess.run([self.piper_binary, '--model', self.model_path, '--output_file', output_path,
                                     '--length-scale', str(length_scale), '--noise-scale', '0.667', '--noise-w-scale', '0.8'], input=text,
                                    capture_output=True, encoding='utf-8', timeout=120)
            if result.returncode:
                return {'status': 'FAILED', 'returncode': result.returncode, 'error': result.stderr[-2000:]}
            return {'status': 'SUCCESS', 'output_path': output_path, 'returncode': 0,
                    'engine': 'piper', 'model': self.model_path,
                    'parameters': {'length_scale': length_scale, 'noise_scale': 0.667, 'noise_w_scale': 0.8},
                    'text_sha256': hashlib.sha256(text.encode('utf-8')).hexdigest(),
                    'wav_sha256': hashlib.sha256(Path(output_path).read_bytes()).hexdigest(),
                    **inspect_wav(output_path)}
        except Exception as exc:
            return {'status': 'FAILED', 'error': str(exc)}
