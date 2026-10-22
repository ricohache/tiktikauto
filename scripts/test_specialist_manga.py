"""Bounded specialist-checkpoint trial. No production/video/default changes."""
import argparse
import json
import shutil
import struct
import subprocess
import sys
import threading
import time
import urllib.request
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from acquire_pilot_assets import download
from compare_manga_ink import protected_files
from tiktok_history_factory.pipeline.checkpoints import digest, save_json, exclusive_lock
from tiktok_history_factory.providers.comfyui_images import ComfyUIImageProvider

WORK=ROOT/'work/specialist-manga-emi2-20261019'
REPO='aipicasso/emi-2'
REV='a1aae09f044a1dfd4b674ff86c4c76acc5ff8c71'
FILENAME='emi-2.safetensors'
SIZE=6939227226
SHA='4a49a08efbca4b0e7f3b6bfd49e48f01d8684d29929f49adb0baf018dd7486db'
MODEL=ROOT/'ComfyUI/ComfyUI/models/checkpoints'/FILENAME
PROMPTS={
 'portrait':{'seed':19441204,'text':
  '(japanese manga:1.3), monochrome, black and white, seinen, ink, screentone, 1man, adult West African soldier, dark skin, very short curly black hair, angular face, (anguished expression:1.3), furrowed brows, clenched jaw, wide worried eyes, three-quarter view, close-up, looking offscreen, plain buttoned cotton field shirt, fully clothed, Senegal 1944, plaster wall, diagonal composition, dramatic black shadows'},
 'camp':{'seed':19441201,'text':
  '(japanese manga:1.3), monochrome, black and white, seinen, ink, screentone, 3men, adult West African soldiers, dark skin, very short curly black hair, plain cotton field shirts, fully clothed, (tense discussion:1.2), one man holding a folded pay document, two men listening with worried expressions, sandy courtyard, low white plaster barracks, corrugated iron roof, Thiaroye Senegal 1944, medium wide shot, strong perspective, dramatic black shadows'}}
NEGATIVE=('photo, photograph, photorealism, studio portrait, realism, skin pores, 3d, sepia, engraving, etching, '
 'pencil sketch, chibi, childish, color, low contrast, bad anatomy, bad hands, extra fingers, text, watermark, '
 'nsfw, nudity, naked, shirtless, underwear, sexual content, gore, blood, child, teenager, '
 'modern camouflage, tactical vest, modern weapons, helmet, fake insignia, medals, '
 'kimono, samurai, katana, pagoda, Japanese architecture, modern buildings, white background')


def get_json(url):
    with urllib.request.urlopen(url,timeout=30) as response:
        return json.load(response)


def fetch_text(url,target):
    if not target.exists():
        with urllib.request.urlopen(url,timeout=30) as response:
            blob=response.read(1024**2+1)
        if len(blob)>1024**2:
            raise RuntimeError('Source exceeds 1MiB')
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(blob)
    return target


def acquire():
    WORK.mkdir(parents=True,exist_ok=True)
    if not (WORK/'protected-before.json').exists():
        save_json(WORK/'protected-before.json',protected_files())
    provider=ComfyUIImageProvider()
    queue=provider._request('/queue')
    if queue.get('queue_running') or queue.get('queue_pending'):
        raise RuntimeError('Existing GPU work active; do not start trial')
    info=get_json(f'https://huggingface.co/api/models/{REPO}/revision/{REV}?blobs=true')
    if info['sha']!=REV or info.get('gated') or info['cardData']['license']!='openrail++':
        raise RuntimeError('Publisher metadata changed or gated access required')
    item=next(x for x in info['siblings'] if x['rfilename']==FILENAME)
    if item['size']!=SIZE or item['lfs']['sha256']!=SHA:
        raise RuntimeError('Publisher weight size/hash differs')
    save_json(WORK/'publisher-metadata.json',info)
    for name in ('README.md','scheduler/scheduler_config.json','unet/config.json','text_encoder/config.json','text_encoder_2/config.json'):
        fetch_text(f'https://huggingface.co/{REPO}/raw/{REV}/{name}',WORK/'sources'/name)
    shutil.copy2(ROOT/'assets/licenses/sdxl-LICENSE.md',WORK/'sources/CreativeML-OpenRAIL++-M.md')
    audit={
      'checked_at':datetime.now(timezone.utc).isoformat(),'publisher':'AI Picasso Inc.','repo':REPO,'revision':REV,
      'licence':'CreativeML OpenRAIL++-M declared; same standard as SDXL. Card intended uses explicitly include commercial and noncommercial illustration/manga/anime.',
      'monetisation':'No noncommercial-only or revenue threshold stated for Emi2. Preserve licence/notices for model redistribution. Generated drawings remain subject to applicable law and output responsibility; not authentic archives.',
      'provenance':'Complete specialized Emi2 checkpoint from publisher; publisher describes about3000 manually selected plus500000 automatically selected training images and exclusion of unauthorized Danbooru reposts. This is the publisher assertion, not an independent dataset audit.',
      'compatibility':'Card explicitly lists ComfyUI and standard SDXL safetensors loading. Existing native CheckpointLoaderSimple/CLIPTextEncode/KSampler/VAEDecode/SaveImage reused; no custom nodes, no LoRA, no system install.',
      '8gb_status_before_trial':'Plausible: SDXL-family graph already operated at768x1344 on this8GB GPU. Not yet a measured Emi2 success. Native ComfyUI memory management/offload, batch1, bounded inference900s.',
      'official_prompting':'Waifu-Diffusion-style tags or SD prompts; card example monochrome, black and white, japanese manga. New model-specific prompts; no living artist or copyrighted character target.',
      'official_sampling':'Card example uses EulerAncestralDiscreteScheduler,20 steps; repository scheduler JSON is EulerDiscreteScheduler. Trial follows card Euler ancestral20 with normal schedule, CFG7.5 (Diffusers default/example pipeline),768x1344 (~1MP).',
      'resolution_note':'Card itself gives no fixed dimensions; current publisher Emi-family demo uses768x1344 but now servesEmi2.5. We do not represent that newer demo as a pinned Emi2 benchmark.',
      'optional_features':'FreeU parameters documented by author; not used in first bounded baseline. Negative text inversion and hand LoRA not acquired because first trial must evaluate specialized checkpoint alone, with verified resources only.',
      'sfw':'Not marketed as an NSFW checkpoint; no guarantee or SFW-only certification is published. Fully clothed adult text prompts and NSFW/gore negatives are enforced in this trial, then actual images reviewed. Negatives are not a safety classifier or guarantee. No relaxation to an explicitly NSFW model authorized.',
      'disk_free_before':shutil.disk_usage(ROOT).free,'download_bytes':SIZE,'disk_reserve_bytes':15*1024**3,
      'decision':'Acquire this ONE checkpoint, then test TWO compositions. No production adoption, final-image generation or video render before owner approval.'}
    save_json(WORK/'preflight-and-licence-audit.json',audit)
    print('PREFLIGHT PASSED; ONE specialized checkpoint; sizeGiB',round(SIZE/1024**3,2),'freeGiB',round(shutil.disk_usage(ROOT).free/1024**3,1),flush=True)
    download(REPO,REV,FILENAME,MODEL,SIZE,SHA)
    with MODEL.open('rb') as stream:
        size=struct.unpack('<Q',stream.read(8))[0]
        if not 0<size<16*1024**2:
            raise RuntimeError('Invalid safetensors header')
        header=json.loads(stream.read(size))
    save_json(WORK/'safetensors-header.json',header)
    types={value['dtype'] for key,value in header.items() if key!='__metadata__'}
    print('VERIFIED Emi2; tensor types',sorted(types),'tensors',len(header)-1,flush=True)


class EmiProvider(ComfyUIImageProvider):
    @staticmethod
    def workflow(prompt,negative,checkpoint,width,height,seed,steps,lora='',strength=.85):
        if lora:
            raise ValueError('Specialist checkpoint trial forbids style LoRAs')
        graph=ComfyUIImageProvider.workflow(prompt,negative,checkpoint,width,height,seed,steps)
        graph['5']['inputs'].update(cfg=7.5,sampler_name='euler_ancestral',scheduler='normal')
        graph['7']['inputs']['filename_prefix']='history_factory/specialist_emi2_trial'
        return graph


def telemetry(stop,records):
    start=time.monotonic()
    while not stop.is_set():
        try:
            result=subprocess.run(['nvidia-smi','--query-gpu=memory.used,utilization.gpu,power.draw,temperature.gpu','--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=5)
            if result.returncode==0:
                records.append({'elapsed':round(time.monotonic()-start,2),'gpu':result.stdout.strip()})
        except Exception:
            pass
        stop.wait(2)


def run():
    if not MODEL.is_file() or not (WORK/'safetensors-header.json').exists():
        raise RuntimeError('Acquire and verify specialist checkpoint first')
    with exclusive_lock(ROOT/'work/pilot.lock'):
        provider=EmiProvider()
        save_json(WORK/'system-before-trials.json',provider._request('/system_stats'))
        results=[]
        for scene,spec in PROMPTS.items():
            samples=[]
            stop=threading.Event()
            thread=threading.Thread(target=telemetry,args=(stop,samples),daemon=True)
            thread.start()
            try:
                result=provider.generate_image(spec['text'],width=768,height=1344,seed=spec['seed'],
                    checkpoint=FILENAME,output_path=str(WORK/'images'/f'{scene}-Emi2.png'),
                    negative_prompt=NEGATIVE,steps=20,lora='')
            finally:
                stop.set(); thread.join(timeout=6)
            record={k:v for k,v in result.items() if k!='history'}
            record.update(scene=scene,telemetry=samples)
            record['system_after']=provider._request('/system_stats')
            results.append(record)
            save_json(WORK/'trial-results.json',{'status':'TRIALS_ONLY_AWAITING_REVIEW','results':results})
            print(scene,result.get('status'),result.get('seconds',result.get('error')),flush=True)
            if result.get('status')!='SUCCESS':
                raise RuntimeError('Bounded trial failed; stop without repeating: '+str(result))
    before=json.loads((WORK/'protected-before.json').read_text())
    changed=[p for p,h in before.items() if not (ROOT/p).is_file() or digest(ROOT/p)!=h]
    save_json(WORK/'preservation-check.json',{'protected_files':len(before),'changed':changed,'unchanged':not changed})
    if changed:
        raise RuntimeError('Existing protected artifact changed: '+str(changed))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--acquire',action='store_true')
    args=parser.parse_args()
    acquire() if args.acquire else run()
