"""Pinned official assets, size/hash validation, no global installation."""
import hashlib
import json
import shutil
import time
import urllib.request
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LICENSES = ROOT / 'assets' / 'licenses'
LICENSES.mkdir(parents=True, exist_ok=True)


def download(repo, revision, filename, target, size=None, sha256=None, url_override=None):
    url = url_override or f'https://huggingface.co/{repo}/resolve/{revision}/{filename}'
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    if size and shutil.disk_usage(ROOT).free < size + 15 * 1024**3:
        raise RuntimeError('Insufficient disk reserve')
    if not target.exists():
        part = target.with_suffix(target.suffix + '.part')
        offset = part.stat().st_size if part.exists() else 0
        headers = {'User-Agent': 'TikTokHistoryFactory/0.2 local-pilot'}
        if offset:
            headers['Range'] = f'bytes={offset}-'
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=90) as response:
            mode = 'ab' if offset and response.status == 206 else 'wb'
            if mode == 'wb':
                offset = 0
            total = offset
            last = time.monotonic()
            with part.open(mode) as stream:
                while chunk := response.read(4 * 1024**2):
                    stream.write(chunk)
                    total += len(chunk)
                    if time.monotonic() - last > 20:
                        print(f'{filename}: {total / 1024**3:.2f} GiB', flush=True)
                        last = time.monotonic()
        if size and part.stat().st_size != size:
            raise RuntimeError(f'Incomplete download {part}')
        if sha256 and hashlib.file_digest(part.open('rb'), 'sha256').hexdigest() != sha256:
            raise RuntimeError(f'Hash mismatch {part}')
        part.rename(target)
    digest = hashlib.file_digest(target.open('rb'), 'sha256').hexdigest()
    if size and target.stat().st_size != size or sha256 and digest != sha256:
        raise RuntimeError(f'Invalid installed asset {target}')
    record = {'repo': repo, 'revision': revision, 'url': url, 'path': str(target),
              'bytes': target.stat().st_size, 'sha256': digest}
    target.with_suffix(target.suffix + '.provenance.json').write_text(json.dumps(record, indent=2))
    print('VERIFIED', target, flush=True)
    return record


if __name__ == '__main__':
    sdxl = '462165984030d82259a11f4367a4eed129e94a7b'
    voice = 'c10ece1aade47bb51c153c893d14e5bf8e5b7117'
    for filename in ('README.md', 'LICENSE.md'):
        download('stabilityai/stable-diffusion-xl-base-1.0', sdxl, filename, LICENSES / ('sdxl-' + filename))
    download('rhasspy/piper-voices', voice, 'fr/fr_FR/siwis/medium/MODEL_CARD', LICENSES / 'siwis-MODEL_CARD.md')
    voice_dir = ROOT / 'tools' / 'piper' / 'voices'
    for filename in ('fr_FR-siwis-medium.onnx.json', 'fr_FR-siwis-medium.onnx'):
        download('rhasspy/piper-voices', voice, 'fr/fr_FR/siwis/medium/' + filename,
                 voice_dir / filename, 63201294 if filename.endswith('.onnx') else None,
                 '641d1ab097da2b81128c076810edb052b385decc8be3381814802a64a73baf99' if filename.endswith('.onnx') else None)
    download('stabilityai/stable-diffusion-xl-base-1.0', sdxl, 'sd_xl_base_1.0.safetensors',
             ROOT / 'ComfyUI/ComfyUI/models/checkpoints/sd_xl_base_1.0.safetensors',
             6938078334, '31e35c80fc4829d14f90153f4c74cd59c90b779f6afe05a74cd6120b893f7e5b')
    if '--wan' in sys.argv:
        repo = 'Comfy-Org/Wan_2.2_ComfyUI_Repackaged'
        revision = 'ee6f4a40737a995bf5818954cfce6d59443b0f04'
        download('Wan-Video/Wan2.2', 'main', 'LICENSE.txt', LICENSES / 'wan-Apache-2.0.txt',
                 url_override='https://raw.githubusercontent.com/Wan-Video/Wan2.2/main/LICENSE.txt')
        files = [
            ('diffusion_models/wan2.2_ti2v_5B_fp16.safetensors', 9999658848, '456f901338bd9eadbded3828b819109a9b68e8a525ca5cf8d0049a69fcfeca1e'),
            ('text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors', 6735906897, 'c3355d30191f1f066b26d93fba017ae9809dce6c627dda5f6a66eaa651204f68'),
            ('vae/wan2.2_vae.safetensors', 1409400960, 'e40321bd36b9709991dae2530eb4ac303dd168276980d3e9bc4b6e2b75fed156')]
        if shutil.disk_usage(ROOT).free < sum(item[1] for item in files) + 15*1024**3:
            raise RuntimeError('Insufficient space for complete Wan stack and reserve')
        for filename, size, checksum in files:
            download(repo, revision, 'split_files/' + filename, ROOT / 'ComfyUI/ComfyUI/models' / filename, size, checksum)
