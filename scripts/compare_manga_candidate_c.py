"""Conditional third model trial after A/B visual inspection; no production changes."""
import argparse
import json
import shutil
import struct
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from compare_manga_ink import ROOT, WORK, LORAS, SCENES, STYLE, NEGATIVE, download, digest, save_json, exclusive_lock, ComfyUIImageProvider

REPO='Chan-Y/BoldLine-Manga'
REV='ebc3b45377f790c0e24d14289d32a92aba6d6d49'
FILENAME='boldlinemanga.safetensors'
SIZE=237421752
SHA='fd432e643cd3e85a5f1def9d654f0ed78fa696915c7c2f2528d0253b3bf16231'


def acquire():
    with urllib.request.urlopen(f'https://huggingface.co/api/models/{REPO}/revision/{REV}?blobs=true',timeout=30) as response:
        info=json.load(response)
    if info['sha'] != REV or info['cardData']['license'] != 'openrail++' or info['cardData']['base_model'] != 'stabilityai/stable-diffusion-xl-base-1.0':
        raise RuntimeError('Candidate C metadata differs from audited version')
    item=next(s for s in info['siblings'] if s['rfilename']==FILENAME)
    if item['size']!=SIZE or item['lfs']['sha256']!=SHA:
        raise RuntimeError('Published candidate C hash differs')
    save_json(WORK/'C-publisher-metadata.json',info)
    download(REPO,REV,'README.md',WORK/'licences/BoldLine-Manga-README.md')
    audit={'checked_at':datetime.now(timezone.utc).isoformat(),'publisher':'Chan-Y','repo':REPO,'revision':REV,
      'license':'openrail++ declared by publisher; no commercial exclusion in card',
      'compatibility':'SDXL Base LoRA explicitly documented for ComfyUI. Publisher says text encoder LoRA enabled. Existing 8GB SDXL workflow reused.',
      'trigger':'in the style of TOK','strength_model':1.0,'strength_clip':1.0,
      'provenance_limit':'Training script and hparams published; complete dataset rights/contents not independently documented or audited.',
      'decision':'Two bounded comparison images only; no final scene generation or production default change',
      'reason_for_C':'A/B actual images insufficient: weak expressiveness, generic etched/woodcut camp, unverified costumes and architecture.'}
    save_json(WORK/'C-licence-audit.json',audit)
    download(REPO,REV,FILENAME,LORAS/FILENAME,SIZE,SHA)
    shutil.copy2(LORAS/(FILENAME+'.provenance.json'),WORK/'C-model-provenance.json')
    with (LORAS/FILENAME).open('rb') as stream:
        length=struct.unpack('<Q',stream.read(8))[0]
        if not 0<length<16*1024**2:
            raise RuntimeError('Invalid C safetensors header')
        header=json.loads(stream.read(length))
    save_json(WORK/'C-safetensors-header.json',header)
    print('VERIFIED candidate C; tensors',len(header)-1,'text encoder tensors',sum('text_encoder' in k or 'lora_te' in k for k in header),flush=True)


def run():
    if not (WORK/'C-safetensors-header.json').exists():
        raise RuntimeError('Acquire and inspect candidate C first')
    runs=[]
    with exclusive_lock(ROOT/'work/pilot.lock'):
        provider=ComfyUIImageProvider()
        for scene,spec in SCENES.items():
            target=WORK/'images'/f'{scene}-C-BoldLineManga.png'
            prompt=f'in the style of TOK, {STYLE}. {spec["description"]}'
            result=provider.generate_image(prompt,width=768,height=1344,seed=spec['seed'],
                checkpoint='sd_xl_base_1.0.safetensors',output_path=str(target),
                negative_prompt=NEGATIVE,steps=28,lora=FILENAME,strength=1.0)
            if result.get('status')!='SUCCESS':
                save_json(WORK/'C-failed-result.json',result)
                raise RuntimeError(result)
            runs.append({**{k:v for k,v in result.items() if k!='history'},'scene':scene,'variant':'C-BoldLineManga'})
            save_json(WORK/'comparison-manifest-C.json',{'status':'TECHNICAL_SUCCESS_ART_PENDING','runs':runs})
            print(scene,'C-BoldLineManga SUCCESS',result.get('seconds'),flush=True)
    from PIL import Image,ImageDraw,ImageFont
    sheet=Image.new('RGB',(2304,2784),'#202020')
    draw=ImageDraw.Draw(sheet)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',25)
    for row,scene in enumerate(SCENES):
        for col,label in enumerate(('A-LineAniRedmond','B-MangaInk','C-BoldLineManga')):
            x,y=col*768,row*1392
            draw.text((x+12,y+10),f'{scene} | {label} | seed {SCENES[scene]["seed"]}',font=font,fill='white')
            with Image.open(WORK/'images'/f'{scene}-{label}.png') as image:
                sheet.paste(image.convert('RGB'),(x,y+48))
    sheet.save(WORK/'comparison-ABC-full.png')
    sheet.resize((1152,1392)).save(WORK/'comparison-ABC-preview.jpg',quality=95)
    before=json.loads((WORK/'protected-before.json').read_text())
    changed=[name for name,h in before.items() if not (ROOT/name).is_file() or digest(ROOT/name)!=h]
    save_json(WORK/'preservation-check.json',{'protected_files':len(before),'changed':changed,'unchanged':not changed})
    if changed:
        raise RuntimeError('Existing artifacts changed: '+str(changed))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--acquire',action='store_true')
    args=parser.parse_args()
    acquire() if args.acquire else run()
