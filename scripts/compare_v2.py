"""Small controlled GPU and English voice auditions. Never publishes."""
import json
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tiktok_history_factory.providers.comfyui_images import ComfyUIImageProvider
from tiktok_history_factory.providers.piper_tts import PiperTTSProvider
from tiktok_history_factory.media.prompts import build_image_prompt, build_negative_prompt
from tiktok_history_factory.pipeline.checkpoints import save_json, exclusive_lock

ROOT = Path(__file__).resolve().parents[1]
work = ROOT/'work/v2-comparison-style-first'
work.mkdir(parents=True, exist_ok=True)
text = 'December first, nineteen forty-four. Thiaroye, near Dakar, Senegal. African soldiers demanded their unpaid wages. The death toll remains disputed.'
for name in ('john', 'kristin'):
    provider = PiperTTSProvider(str(ROOT/f'tools/piper/voices/en_US-{name}-medium.onnx'))
    record = provider.synthesize(text.replace('Thiaroye', 'Tya-roy'), str(work/f'{name}.wav'), length_scale=1.15)
    if record['status'] != 'SUCCESS':
        raise RuntimeError(record)
    record['words_per_minute'] = len(text.split())*60/record['duration']
    save_json(work/f'{name}.json', record)
    print(name, record['duration'], record['words_per_minute'], flush=True)
with exclusive_lock(ROOT/'work/pilot.lock'):
    provider = ComfyUIImageProvider()
    prompt = build_image_prompt('Close-up of a serious adult West African man, short black hair, plain cotton shirt, Senegal 1944, white plaster wall, face in upper half, no insignia.')
    records = []
    for name, strength in (('base', 0), ('lineani-070', .7), ('lineani-100', 1.0)):
        record = provider.generate_image(prompt, checkpoint='sd_xl_base_1.0.safetensors',
            width=768, height=1344, seed=19441204, steps=28, negative_prompt=build_negative_prompt(),
            output_path=str(work/f'{name}.png'),
            lora='LineAniRedmondV2-Lineart-LineAniAF.safetensors' if strength else '', strength=strength)
        records.append(record)
        save_json(work/'comparison.json', records)
        print(name, record.get('status'), record.get('error', record.get('seconds')), flush=True)
        if record['status'] != 'SUCCESS':
            raise RuntimeError(record)
    from PIL import Image, ImageDraw
    sheet = Image.new('RGB', (768, 488), 'white')
    draw = ImageDraw.Draw(sheet)
    for index, name in enumerate(('base', 'lineani-070', 'lineani-100')):
        with Image.open(work/f'{name}.png') as image:
            sheet.paste(image.convert('RGB').resize((256,448)), (index*256,40))
        draw.text((index*256+10,12), name, fill='black')
    sheet.save(work/'comparison.jpg')
