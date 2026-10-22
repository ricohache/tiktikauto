"""Portable, non-destructive post-render checks for TikTokHistoryFactory.
No remote services; never treats an intermediate silent video as a final.
"""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess


def _run(args):
    return subprocess.run([str(x) for x in args], stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, encoding='utf-8', errors='replace', check=True)


def media_probe(ffprobe, mp4):
    p = _run([ffprobe, '-v','error','-show_entries',
              'format=duration,size:stream=index,codec_type,codec_name,width,height,r_frame_rate,duration,channels,sample_rate',
              '-of','json',mp4])
    data=json.loads(p.stdout)
    v=[s for s in data.get('streams',[]) if s.get('codec_type')=='video']
    a=[s for s in data.get('streams',[]) if s.get('codec_type')=='audio']
    if len(v)!=1 or len(a)!=1:
        raise ValueError('Expected exactly one video and one audible audio track')
    if (v[0].get('width'),v[0].get('height'))!=(1080,1920):
        raise ValueError('Incorrect dimensions: '+str(v[0]))
    if v[0].get('r_frame_rate')!='30/1':
        raise ValueError('Expected 30 FPS, got '+str(v[0].get('r_frame_rate')))
    return {'duration_sec':float(data['format']['duration']),
            'size_bytes':int(data['format']['size']),
            'video':v[0], 'audio':a[0]}


def audio_signal(ffmpeg, mp4):
    p=_run([ffmpeg,'-hide_banner','-i',mp4,'-map','0:a:0',
            '-af','volumedetect','-f','null','-'])
    log=p.stderr
    def vol(which):
        match=re.search(r'\b'+which+r':\s*(-?(?:\d+(?:\.\d+)?|inf))\s*dB',log)
        if not match:raise ValueError('volumedetect did not return '+which)
        return float(match.group(1))
    mean,maxv=vol('mean_volume'),vol('max_volume')
    if not math.isfinite(mean) or not math.isfinite(maxv) or maxv < -38 or mean < -51:
        raise ValueError(f'Audio track silent or extremely quiet: mean={mean} dBFS, peak={maxv} dBFS')
    return {'mean_dbfs':mean,'peak_dbfs':maxv,'audible_signal_detected':True,
            'warning':'Signal level alone cannot certify correct English speech or intelligibility'}


def captions_qc(subs, ass, expected_end, font_size=70):
    captions=json.loads(Path(subs).read_text(encoding='utf-8'))
    if not captions:raise ValueError('No French subtitle segments')
    last=-1.0
    for i,cue in enumerate(captions,1):
        lines=cue['lines']
        if not (1<=len(lines)<=2) or any(not line.strip() for line in lines):
            raise ValueError(f'Cue {i} does not respect two-line limit')
        t0=float(cue['start']); t1=float(cue['end'])
        if t0 < last-0.02 or t1<=t0 or t1>expected_end+0.05:
            raise ValueError(f'Cue {i} invalid/out-of-order: {t0} to {t1}')
        last=t1
    ass_text=Path(ass).read_text(encoding='utf-8-sig')
    if ass_text.count('Dialogue: ')!=len(captions):
        raise ValueError('ASS and timing manifest disagree')
    style=next((s for s in ass_text.splitlines() if s.startswith('Style: TikTok,')), '')
    if not style:raise ValueError('Required ASS TikTok style missing')
    values=style.split(',')
    # Style Format: Name, Fontname, Fontsize, [four colours], Bold... BorderStyle index 15.
    if len(values)<22 or values[2].strip()!=str(font_size) or values[15].strip()!='1':
        raise ValueError('Wrong ASS font size or subtitle border style')
    if values[21].strip()!='360':
        raise ValueError('Subtitle safe-area margin has changed')
    return {'caption_count':len(captions),'max_lines':max(len(c['lines']) for c in captions),
            'last_caption_end_sec':last, 'font_px':font_size,'bottom_margin_px':360,
            'box_background':False, 'visually_checked':False}


def check_final(ffmpeg, ffprobe, mp4, subs, ass, goal=90):
    mp4=Path(mp4)
    if not mp4.is_file() or mp4.stat().st_size<100_000:
        raise ValueError('Missing/suspiciously small MP4')
    media=media_probe(ffprobe,mp4)
    if abs(media['duration_sec']-goal)>0.6:
        raise ValueError(f'Wrong duration: {media["duration_sec"]:.3f}s, target={goal}s')
    if media['video'].get('codec_name')!='h264' or media['audio'].get('codec_name')!='aac':
        raise ValueError('Expected H.264/AAC')
    audio=audio_signal(ffmpeg,mp4)
    captions=captions_qc(subs,ass,goal)
    _run([ffmpeg,'-v','error','-i',mp4,'-f','null','-'])
    return {'file':str(mp4),'sha256':hashlib.sha256(mp4.read_bytes()).hexdigest(),
            'media':media,'audio':audio,'subtitles':captions,
            'decode_errors':0,'technical_checks_passed':True,
            'limitations':['Piper enunciation and French translation must be checked at listening speed',
                           'Frame-to-story narrative match and period accuracy need visual human review',
                           'Subtitle visibility behind UI overlays depends on each TikTok app revision']}
