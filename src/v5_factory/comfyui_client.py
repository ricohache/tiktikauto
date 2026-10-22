"""Client ComfyUI pour génération d'images Emi2."""
import json
import urllib.request
import hashlib
import time
from pathlib import Path

BASE = 'http://127.0.0.1:8188'
NEGATIVE = "photograph, photorealistic, 3d render, chibi, cute, modern anime, neon colors, low quality, blurry, deformed hands, extra fingers, modern clothing, modern weapons, watermark, text, letters, nudity, nsfw, gore, blood, graphic violence, kimono, samurai, katana, pagoda, japanese architecture, bamboo, straw hat, conical hat, tactical vest, astronaut, spacesuit, face mask, modern helmet, nazi, swastika, medals, epaulettes, officer uniform"


def build_workflow(prompt, seed, width=768, height=1344, steps=20):
    return {
        '1': {'class_type': 'CheckpointLoaderSimple', 'inputs': {'ckpt_name': 'emi-2.safetensors'}},
        '2': {'class_type': 'CLIPTextEncode', 'inputs': {'text': prompt, 'clip': ['1', 1]}},
        '3': {'class_type': 'CLIPTextEncode', 'inputs': {'text': NEGATIVE, 'clip': ['1', 1]}},
        '4': {'class_type': 'EmptyLatentImage', 'inputs': {'width': width, 'height': height, 'batch_size': 1}},
        '5': {'class_type': 'KSampler', 'inputs': {
            'model': ['1', 0], 'positive': ['2', 0], 'negative': ['3', 0],
            'latent_image': ['4', 0], 'seed': seed, 'steps': steps, 'cfg': 7.5,
            'sampler_name': 'euler_ancestral', 'scheduler': 'normal', 'denoise': 1.0}},
        '6': {'class_type': 'VAEDecode', 'inputs': {'samples': ['5', 0], 'vae': ['1', 2]}},
        '7': {'class_type': 'SaveImage', 'inputs': {'images': ['6', 0], 'filename_prefix': f'history_factory/{seed}'}}
    }


def submit(wf):
    req = urllib.request.Request(f'{BASE}/prompt',
        data=json.dumps({'prompt': wf}).encode(),
        headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def poll(prompt_id, timeout=300):
    url = f'{BASE}/history/{prompt_id}'
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.load(resp)
                if prompt_id in data and data[prompt_id].get('outputs'):
                    return data[prompt_id]
        except Exception:
            pass
        time.sleep(2)
    return None


def fetch_image(filename, subfolder=''):
    url = f'{BASE}/view?filename={urllib.parse.quote(filename)}&subfolder={urllib.parse.quote(subfolder)}&type=output'
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def generate_single(prompt, seed, out_path: Path, timeout=300):
    """Génère une image et l'enregistre."""
    wf = build_workflow(prompt, seed)
    submit_resp = submit(wf)
    prompt_id = submit_resp.get('prompt_id')
    history = poll(prompt_id, timeout=timeout)
    if not history:
        raise TimeoutError(f'ComfyUI timeout pour prompt_id={prompt_id}')
    outputs = history.get('outputs', {})
    if not outputs:
        raise RuntimeError('Aucune sortie ComfyUI')
    img_node = list(outputs.values())[0]
    imgs = img_node.get('images', [{}])
    if not imgs or not imgs[0]:
        raise RuntimeError('Aucune image retournée')
    img_file = imgs[0].get('filename')
    img_sub = imgs[0].get('subfolder', '')
    img_data = fetch_image(img_file, img_sub)
    out_path.write_bytes(img_data)
    return {'path': str(out_path), 'sha256': hashlib.sha256(img_data).hexdigest(), 'bytes': len(img_data)}


def generate_images_for_scenes(scenes, images_dir: Path, style_prompt: str, timeout_per_image=300):
    """Génère les images pour une liste de scènes."""
    images_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for scene in scenes:
        scene_id = scene['id']
        seed = scene.get('seed', int(time.time() * 1000) % 2**32)
        prompt = scene.get('positive_prompt', style_prompt)
        out_path = images_dir / f'{scene_id}.png'
        if out_path.exists():
            print(f'[IMAGE] {scene_id} existe déjà, skip.')
            results.append({'scene': scene_id, 'path': str(out_path), 'status': 'cached'})
            continue
        print(f'[IMAGE] Génération {scene_id} seed={seed}...')
        try:
            info = generate_single(prompt, seed, out_path, timeout=timeout_per_image)
            results.append({'scene': scene_id, **info, 'status': 'success'})
            print(f'[IMAGE] {scene_id} OK ({info["bytes"]} bytes)')
        except Exception as e:
            print(f'[IMAGE] {scene_id} ERROR: {e}')
            results.append({'scene': scene_id, 'status': 'error', 'error': str(e)})
    return results


if __name__ == '__main__':
    # Test rapide
    print('Test ComfyUI...')
    req = urllib.request.Request(f'{BASE}/system_stats')
    with urllib.request.urlopen(req, timeout=5) as resp:
        stats = json.load(resp)
        print(f'ComfyUI OK: {stats.get("system",{}).get("comfyui_version","?")}')
