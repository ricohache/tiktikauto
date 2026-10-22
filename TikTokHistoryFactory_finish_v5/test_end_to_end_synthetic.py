"""Full offline 2-scene fixture test with dummy images/synthesized BEEP voice.
Strictly a technical pipeline test, NEVER genuine historic documentary content.
No ComfyUI or publication and all generated media removed on exit.
"""
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from PIL import Image, ImageDraw
from quality_v5 import check_final

here=Path(__file__).resolve().parent
with tempfile.TemporaryDirectory(prefix='tiktok-v5-fixture-') as t:
    root=Path(t)
    source=root/'work'/'pilot-thiaroye-1944-90s-v3'
    (source/'script').mkdir(parents=True)
    (source/'images').mkdir()
    old=json.loads((here/'storyboard_reference_v3.json').read_text(encoding='utf-8-sig'))
    (source/'script'/'storyboard.json').write_text(json.dumps(old,ensure_ascii=False),encoding='utf-8')
    out=root/'output'/'pilot-thiaroye-1944-90s-v5'
    (out/'images').mkdir(parents=True)
    for scene in old['scenes'][:2]:
        for side,path in [('A',source/'images'/(scene['id']+'.png')),
                          ('B',out/'images'/(scene['id']+'_B.png'))]:
            im=Image.new('RGB',(768,1344),'white')
            painter=ImageDraw.Draw(im)
            painter.rectangle((90,300,640,1150),outline='black',width=14)
            painter.text((180,700),'SYNTHETIC '+scene['id']+side,fill='black')
            im.save(path)
    piper=root/'mock_piper.py'
    piper.write_text('''#!/usr/bin/env python3
import argparse,math,struct,sys,wave
p=argparse.ArgumentParser();p.add_argument('--model');p.add_argument('--output_file');a=p.parse_args()
text=sys.stdin.read();rate=24000;n=rate*4
with wave.open(a.output_file,'wb') as f:
 f.setnchannels(1);f.setsampwidth(2);f.setframerate(rate)
 for idx in range(n):
  sample=int(0.12*32767*math.sin(2*math.pi*340*idx/rate))
  f.writeframesraw(struct.pack('<h',sample))
''',encoding='utf-8')
    piper.chmod(0o755)
    voice=root/'en_US_mock.onnx';voice.write_bytes(b'SYNTHETIC-TEST-NOT-A-VOICE')
    cmd=[sys.executable,str(here/'finish_pilot.py'),'--project',str(root),
         '--piper',str(piper),'--voice',str(voice),'--skip-image-generation','--test']
    subprocess.run(cmd,check=True)
    result=out/'smoke_test_v5.mp4'
    assert (out/'review'/'control-excerpt.mp4').is_file()
    assert (out/'storyboard-v5.json').is_file()
    assert len(json.loads((out/'storyboard-v5.json').read_text()))==4
    qc=check_final('ffmpeg','ffprobe',result,out/'subtitles'/'timings.json',
                   out/'subtitles'/'subtitles-fr.ass',goal=9)
    print('PASS synthetic end-to-end:',result,'duration',qc['media']['duration_sec'],
          'signal peak',qc['audio']['peak_dbfs'],'dBFS')
print('PASS synthetic fixture cleaned up')
