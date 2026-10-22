"""Isolated artistic A/B comparison; never changes production defaults or media."""
import argparse
import hashlib
import json
import shutil
import struct
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from acquire_pilot_assets import download
from tiktok_history_factory.pipeline.checkpoints import digest, exclusive_lock, save_json
from tiktok_history_factory.providers.comfyui_images import ComfyUIImageProvider

WORK = ROOT/'work/art-comparison-20261019-manga-ink'
REPO = 'strkyyy/manga-ink-screentone'
REVISION = '856ecac6ef6203faf52116dfc42c36f02bd93cbc'
FILENAME = 'manga-ink-screentone.safetensors'
SIZE = 93065304
SHA = 'e9fa7b9c4eb781d6cdf8329c6d056133e08c6cc72e730738575497d4ab3da6c9'
LORAS = ROOT/'ComfyUI/ComfyUI/models/loras'
SCENES = {
 'portrait': {'seed':19441204, 'description':
  'Tight three-quarter view of one adult West African tirailleur, short cropped hair, plain unadorned 1940s field shirt, tense brows and determined eyes, looking toward a comrade outside frame. Senegal 1944, rough plaster barracks wall behind him, expressive narrative composition.'},
 'camp': {'seed':19441201, 'description':
  'Transit camp near Dakar, Senegal, 1944. Two adult West African tirailleurs in plain unadorned cotton field shirts discussing a folded pay document. Low whitewashed plaster barracks, corrugated metal roofs, sandy courtyard. Medium wide narrative panel, expressive gestures, no weapons, no readable lettering.'}}
STYLE = 'black and white seinen manga panel, expressive ink contours, screentone dots, solid deep black shadows, drawn 2D faces'
NEGATIVE = ('photograph, photorealistic, studio portrait, camera photo, cinematic photography, skin pores, '
 '3D render, sepia, engraving, etching, pencil sketch, chibi, cute, glossy skin, color, '
 'gore, nudity, nsfw, modern camouflage, modern helmet, tactical vest, medals, fake insignia, '
 'pagoda, Japanese architecture, kimono, samurai, katana, watermark, text, letters, deformed hands, extra fingers')


def protected_files():
    paths = [ROOT/'.env', ROOT/'.env.example', ROOT/'tiktok_history_factory/config/settings.py',
             ROOT/'data/subjects/thiaroye-1944-v2.json']
    for folder in ('work/pilot-thiaroye-1944','work/pilot-thiaroye-1944-v2','output/review','output/ready'):
        paths += [p for p in (ROOT/folder).rglob('*') if p.is_file()]
    return {str(p.relative_to(ROOT)):digest(p) for p in paths if p.is_file()}


def acquire():
    WORK.mkdir(parents=True, exist_ok=True)
    if not (WORK/'protected-before.json').exists():
        save_json(WORK/'protected-before.json', protected_files())
    provider = ComfyUIImageProvider()
    queue = provider._request('/queue')
    if queue.get('queue_running') or queue.get('queue_pending'):
        raise RuntimeError('ComfyUI is busy; do not run concurrently')
    with urllib.request.urlopen(f'https://huggingface.co/api/models/{REPO}/revision/{REVISION}?blobs=true', timeout=30) as response:
        info = json.load(response)
    if info['sha'] != REVISION or info['cardData'].get('license') != 'openrail++' or info['cardData'].get('base_model') != 'stabilityai/stable-diffusion-xl-base-1.0':
        raise RuntimeError('Publisher metadata differs from audited SDXL/OpenRAIL++ contract')
    save_json(WORK/'publisher-metadata.json', info)
    item = next(x for x in info['siblings'] if x['rfilename'] == FILENAME)
    if item['size'] != SIZE or item['lfs']['sha256'] != SHA:
        raise RuntimeError('Published hash/size differs')
    licences = WORK/'licences'
    licences.mkdir(exist_ok=True)
    download(REPO, REVISION, 'README.md', licences/'manga-ink-screentone-README.md')
    shutil.copy2(ROOT/'assets/licenses/sdxl-LICENSE.md', licences/'SDXL-CreativeML-OpenRAIL++-M.md')
    shutil.copy2(ROOT/'assets/licenses/LineAniRedmondV2-README.md', licences/'LineAniRedmondV2-README.md')
    audit = {'checked_at':datetime.now(timezone.utc).isoformat(), 'publisher':'strkyyy (HF profile: Bogdan)',
      'url':f'https://huggingface.co/{REPO}/tree/{REVISION}', 'revision':REVISION,
      'declared_license':'openrail++', 'declared_base':'stabilityai/stable-diffusion-xl-base-1.0',
      'conditions':'Standard use restrictions apply; no NC-only or per-output royalty restriction stated. Historical respectful local comparison is consistent with declared terms. No publication authorized.',
      'provenance_limit':'Publisher and immutable commit verified; training dataset, training procedure and full chain of authorship not documented by publisher. No claim of exhaustive rights clearance.',
      'commercial_use':'No commercial-use exclusion stated in declared OpenRAIL++; outputs remain user responsibility. Model redistribution would require licence and restrictions notices.',
      'nsfw':'No NSFW training objective advertised in this model card; dataset content not independently audited.',
      'architecture':'SDXL LoRA declared; safetensors header and actual loading checked after hash verification.',
      'bytes':SIZE,'sha256':SHA,'disk_free_before':shutil.disk_usage(ROOT).free,
      'decision':'Proceed with bounded local comparison, record provenance limits; no production style acceptance.'}
    save_json(WORK/'licence-audit.json', audit)
    print('PREFLIGHT: publisher SDXL/OpenRAIL++ metadata archived; free GiB', round(shutil.disk_usage(ROOT).free/1024**3,1), flush=True)
    record = download(REPO, REVISION, FILENAME, LORAS/FILENAME, SIZE, SHA)
    shutil.copy2(LORAS/(FILENAME+'.provenance.json'), WORK/'B-model-provenance.json')
    with (LORAS/FILENAME).open('rb') as stream:
        length = struct.unpack('<Q',stream.read(8))[0]
        if not 0 < length < 16*1024**2:
            raise RuntimeError('Invalid safetensors header size')
        header = json.loads(stream.read(length))
    save_json(WORK/'B-safetensors-header.json',header)
    print('HEADER',json.dumps(header.get('__metadata__',{})), flush=True)
    print('TENSOR KEYS',list(header)[:8], flush=True)
    return record


def run():
    if not (WORK/'B-safetensors-header.json').exists():
        raise RuntimeError('Run acquisition and inspect actual tensor architecture first')
    runs = []
    with exclusive_lock(ROOT/'work/pilot.lock'):
        provider = ComfyUIImageProvider()
        for scene, spec in SCENES.items():
            for label, lora, trigger, strength in (
                ('A-LineAniRedmond', 'LineAniRedmondV2-Lineart-LineAniAF.safetensors','LineAniAF',1.0),
                ('B-MangaInk', FILENAME,'m4ng41nk',.85)):
                target = WORK/'images'/f'{scene}-{label}.png'
                prompt = f'{trigger}, {STYLE}. {spec["description"]}'
                result = provider.generate_image(prompt, width=768, height=1344, seed=spec['seed'],
                    checkpoint='sd_xl_base_1.0.safetensors',output_path=str(target),
                    negative_prompt=NEGATIVE,steps=28,lora=lora,strength=strength)
                if result.get('status') != 'SUCCESS':
                    save_json(WORK/'failed-result.json',result)
                    raise RuntimeError(result)
                entry={k:v for k,v in result.items() if k!='history'}
                entry.update(scene=scene, variant=label,trigger=trigger,strength_model=strength,strength_clip=strength)
                runs.append(entry)
                save_json(WORK/'comparison-manifest.json', {'status':'TECHNICAL_SUCCESS_ART_PENDING',
                    'controlled':'Same scenes, negative prompts, seeds, resolution, sampler/scheduler/CFG/steps; only LoRA, trigger and requested strength differ.',
                    'card_recommendation_note':'Publisher B suggests K-LMS around25 steps. Primary A/B retains DPM++2M/Karras28 to avoid confounding model and sampler.',
                    'runs':runs})
                print(scene,label,'SUCCESS',result.get('seconds'),flush=True)
        make_sheet()
    before=json.loads((WORK/'protected-before.json').read_text())
    changed=[name for name,h in before.items() if not (ROOT/name).is_file() or digest(ROOT/name)!=h]
    save_json(WORK/'preservation-check.json',{'protected_files':len(before),'changed':changed,'unchanged':not changed})
    if changed:
        raise RuntimeError('Existing production artifacts changed: '+str(changed))


def make_sheet():
    from PIL import Image,ImageDraw,ImageFont
    images=WORK/'images'
    # Full-resolution individual PNGs and 1:1 contact sheet; no AI editing or restyling.
    sheet=Image.new('RGB',(1536,2784),'#202020')
    draw=ImageDraw.Draw(sheet)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',25)
    for row,scene in enumerate(SCENES):
        for col,label in enumerate(('A-LineAniRedmond','B-MangaInk')):
            x,y=col*768,row*1392
            draw.text((x+14,y+10),f'{scene} | {label} | seed {SCENES[scene]["seed"]}',font=font,fill='white')
            with Image.open(images/f'{scene}-{label}.png') as img:
                sheet.paste(img.convert('RGB'),(x,y+48))
    sheet.save(WORK/'comparison-full.png')
    sheet.resize((768,1392)).save(WORK/'comparison-preview.jpg',quality=94)


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--acquire',action='store_true')
    args=parser.parse_args()
    acquire() if args.acquire else run()
