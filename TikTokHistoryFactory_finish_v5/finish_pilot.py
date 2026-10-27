#!/usr/bin/env python3
"""TikTokHistoryFactory pilot V4 finisher.

Safe defaults: works in a NEW versioned run directory, preserves the V3 assets,
uses Emi2+ComfyUI to generate complementary shots, Piper for English narration,
FFmpeg for a TikTok 90-second MP4, and ASS/Libass for short FR subtitles.

This tool is meant to run on the owner's Windows machine, where the complete
source assets and local services actually exist. It never posts to TikTok.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import wave
from quality_v5 import audio_signal, check_final, media_probe

DEFAULT_ROOT = Path(r'C:\TikTokHistoryFactory')
SAMPLE_RATE = 48000
FPS = 30
WIDTH, HEIGHT = 1080, 1920
TARGET_SECONDS = 90
NEW_IMAGE_PROMPTS = {
 'SC01': 'tight establishing view down an empty dusty walkway between simple whitewashed transit-camp buildings; crates, 1944 West Africa, colonial-era corrugated roof, no people, dramatic dawn shadows, cinematic historical black-and-white Japanese seinen manga ink and screentones, vertical composition',
 'SC02': 'close-up at waist and legs of adult West African soldiers marching in 1940s military trousers and shoes, dusty footsteps, historically plausible cut trousers, strong moving silhouettes, manga ink illustration, monochrome screentones, cinematic crop',
 'SC03': 'documentary symbolic scene, anonymous adult West African prisoners seen through barbed wire in a European World War Two detention compound, bare 1940s clothing, cold sky, restrained expression, manga black ink and monochrome screentones, no combat',
 'SC04': 'close-up of adult West African veteran hands holding a folded UNMARKED paper letter with blank surfaces, plain cotton buttoned shirt sleeves, simple wooden crate in 1944 Senegal military transit camp, black and white mature manga ink, no letters no symbols',
 'SC05': 'side-view of two adult West African veterans in plain buttoned 1940s cotton shirts talking seriously outdoors near whitewashed low military barracks in Dakar region, gesture of concern, no weapons, manga ink panel, cinematic close framing',
 'SC06': 'close up of a battered 1940s empty pay envelope on a wood table, adult West African soldier hands resting at each side, implied unpaid wages, black and white manga ink contrast, no readable words, no coins from other eras',
 'SC07': 'expressive close-up of adult West African World War Two veteran wearing plain buttoned cotton shirt, looking downward thoughtfully under a bare colonial transit-camp window, restrained grief, high-contrast seinen manga monochrome ink, no robe',
 'SC08': 'low perspective on boots and shadows of early 1940s uniformed military men approaching a low whitewashed transit barracks, dusty ground, tense stillness, no visible weapons, no violence, historically restrained Japanese manga monochrome ink',
 'SC09': 'solemn detail of an abandoned ordinary 1940s soldier cap and blank folded papers on a simple camp bench, empty space beyond, nonviolent remembrance, dramatic black-and-white ink seinen manga panel, no legible writing',
 'SC10': 'empty path between low whitewashed barracks of 1940s French colonial military transit camp near Dakar, long sunset shadows, contemplative solemn atmosphere, mature manga black ink, halftone screen texture, no Japanese buildings',
 'SC11': 'solemn wide African sunset horizon with anonymous adult West African veterans seen from behind in plain 1940s buttoned shirts and ordinary trousers, remembrance and dignity, sharp manga ink silhouettes, monochrome Japanese seinen illustration',
}
GLOBAL_NEGATIVE = ('photograph, photorealistic, engraving, etching, sepia, color, kimono, robe, '
 'samurai, pagoda, japanese building, japanese wooden interior, tatami, hakama, sandals, '
 'modern clothes, modern firearms, tactical vest, helmet, readable writing, text, logo, watermark, '
 'child, boys, teenager, blurry, deformed hands, extra fingers, gore, blood, explicit violence, nsfw')


def run(cmd, cwd=None, input_text=None, quiet=False):
    """Do not include large stdout in chat; save only concise process diagnostics."""
    result = subprocess.run([str(x) for x in cmd], cwd=cwd, input=input_text,
                            encoding='utf-8',
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, errors='replace')
    if result.returncode:
        err = (result.stderr or b'')
        if isinstance(err, bytes): err=err.decode('utf-8', 'replace')
        raise RuntimeError('Command failed: '+str(cmd[:3])+'\n'+err[-2500:])
    if not quiet: print('OK:', ' '.join(map(str,cmd[:3])))
    return result


def ffprobe_duration(ffprobe, path):
    p=run([ffprobe,'-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',path],quiet=True)
    return float(p.stdout.strip())


def check_exe(prog):
    path=shutil.which(prog)
    if not path:
        # Chercher dans les chemins connus du projet
        candidates = [
            Path(r'C:\TikTokHistoryFactory')/'ffmpeg'/'bin'/prog,
            Path(r'C:\TikTokHistoryFactory')/'ffmpeg'/'bin'/(prog+'.exe'),
        ]
        for c in candidates:
            if c.exists():
                return str(c)
        raise RuntimeError(f'{prog} not found in PATH or project ffmpeg/bin')
    return path


def canonical_text(value):
    return re.sub(r'\s+', ' ', value).strip()


def load_storyboard(project):
    p=project/'work'/'pilot-thiaroye-1944-90s-v3'/'script'/'storyboard.json'
    if not p.is_file(): raise FileNotFoundError(f'Missing storyboard: {p}')
    obj=json.loads(p.read_text(encoding='utf-8-sig'))
    scenes=obj.get('scenes', [])
    if len(scenes)<8: raise ValueError(f'Expected at least 8 scenes, found {len(scenes)}')
    for s in scenes:
        for k in ('id','narration_en','narration_fr','positive_prompt'):
            if not s.get(k): raise ValueError(f'Scene {s.get("id")}: missing {k}')
    return p,scenes


def safe_write(path, content):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        return
    path.write_text(content, encoding='utf-8')


def get_json(url, body=None, timeout=20):
    data=None if body is None else json.dumps(body).encode('utf-8')
    req=urllib.request.Request(url, data=data,headers={'Content-Type':'application/json'} if body is not None else {})
    with urllib.request.urlopen(req,timeout=timeout) as res:
        return json.load(res)


def check_comfy(url):
    stats=get_json(url+'/system_stats',timeout=5)
    return stats.get('system',{}).get('comfyui_version','unknown')


def generate_comfy(scene, dest, url, dry_run=False):
    ident=scene['id']
    prompt=NEW_IMAGE_PROMPTS.get(ident)
    if not prompt:
        prompt=('different camera viewpoint: '+scene['positive_prompt'])
    meta_file=dest.with_suffix('.json')
    if dest.exists() and dest.stat().st_size>20_000 and meta_file.exists():
        try:
            meta=json.loads(meta_file.read_text(encoding='utf-8'))
            if meta.get('positive')==prompt and meta.get('sha256')==hashlib.sha256(dest.read_bytes()).hexdigest():
                print('REUSE image:',dest.name)
                return 'reused'
        except (ValueError, OSError): pass
    wf={
       '1':{'class_type':'CheckpointLoaderSimple','inputs':{'ckpt_name':'emi-2.safetensors'}},
       '2':{'class_type':'CLIPTextEncode','inputs':{'text':prompt,'clip':['1',1]}},
       '3':{'class_type':'CLIPTextEncode','inputs':{'text':GLOBAL_NEGATIVE,'clip':['1',1]}},
       '4':{'class_type':'EmptyLatentImage','inputs':{'width':768,'height':1344,'batch_size':1}},
       '5':{'class_type':'KSampler','inputs':{'model':['1',0],'positive':['2',0],
            'negative':['3',0],'latent_image':['4',0],'seed':int(scene.get('seed',19441601))+90000,
            'steps':20,'cfg':7.5,'sampler_name':'euler_ancestral','scheduler':'normal','denoise':1.0}},
       '6':{'class_type':'VAEDecode','inputs':{'samples':['5',0],'vae':['1',2]}},
       '7':{'class_type':'SaveImage','inputs':{'images':['6',0], 'filename_prefix':'history_factory/v4_'+ident}},
    }
    if dry_run: return 'would-generate'
    reply=get_json(url+'/prompt',{'prompt':wf},timeout=30)
    if 'error' in reply: raise RuntimeError(f'ComfyUI rejected scene {ident}: {reply["error"]}')
    pid=reply.get('prompt_id')
    if not pid: raise RuntimeError(f'No prompt_id for scene {ident}: {reply}')
    deadline=time.time()+500
    while time.time()<deadline:
        obj=get_json(url+'/history/'+pid,timeout=20)
        if pid in obj:
            entry=obj[pid]
            if entry.get('status',{}).get('status_str')=='error':
                raise RuntimeError(f'ComfyUI error for {ident}: {entry.get("status")}')
            outs=entry.get('outputs',{}).get('7',{}).get('images',[])
            if outs:
                img=outs[0]
                query=urllib.parse.urlencode({'filename':img['filename'],
                   'subfolder':img.get('subfolder',''), 'type':img.get('type','output')})
                with urllib.request.urlopen(url+'/view?'+query,timeout=30) as res:
                    data=res.read()
                if len(data)<20_000: raise ValueError(f'Image suspiciously small: {ident}')
                dest.parent.mkdir(parents=True,exist_ok=True)
                dest.write_bytes(data)
                md={'scene':ident,'seed':wf['5']['inputs']['seed'],'positive':prompt,
                    'negative':GLOBAL_NEGATIVE,'prompt_id':pid,'sha256':hashlib.sha256(data).hexdigest(),
                    'workflow':wf}
                (dest.with_suffix('.json')).write_text(json.dumps(md,indent=2),encoding='utf-8')
                print('GENERATED image:',dest.name)
                return 'generated'
        time.sleep(2)
    raise TimeoutError(f'ComfyUI timeout for scene {ident}')


def detect_piper(root):
    cli=shutil.which('piper')
    roots=[root/'tools',root/'voices',root/'models',root/'piper',root/'.venv'/'Scripts']
    if not cli:
        for basedir in roots:
            if basedir.exists():
                matches=list(basedir.rglob('piper.exe'))[:1] if sys.platform=='win32' else list(basedir.rglob('piper'))[:1]
                if matches: cli=str(matches[0]); break
    voices=[]
    for basedir in roots:
        if basedir.exists():
            voices.extend(list(basedir.rglob('*.onnx')))
    voices=[p for p in voices if 'en_' in p.name.lower() or 'en-' in p.name.lower()]
    voices=sorted(voices, key=lambda p: ('john' not in p.name.lower() and 'kristin' not in p.name.lower(), str(p)))
    return cli, (voices[0] if voices else None)


def synthesize_voice(root, scenes, dest_audio, ffprobe, piper_cmd=None, piper_model=None, dry_run=False):
    cli, model=detect_piper(root)
    if piper_cmd: cli=str(piper_cmd)
    if piper_model: model=Path(piper_model)
    if not cli or not model:
        raise RuntimeError('Piper CLI/voice not detected. Existing project voices/provider may be used by Codex; '
           'specify --piper PATH and --voice PATH. Never substitute a silent audio track.')
    print('Piper executable:',cli)
    print('Piper voice model:',model.name)
    timings=[]
    for s in scenes:
        dest=dest_audio/(s['id']+'.wav')
        signature=hashlib.sha256((canonical_text(s['narration_en'])+'|'+str(model)+'|'+str(cli)).encode()).hexdigest()
        sig_file=dest.with_suffix('.source.sha256')
        valid=(dest.is_file() and dest.stat().st_size>1000 and sig_file.is_file() and
               sig_file.read_text(encoding='utf-8').strip()==signature)
        if not valid:
            if not dry_run:
                # official Piper CLI supports stdin, --model, --output_file.
                run([cli,'--model',model,'--output_file',dest],input_text=canonical_text(s['narration_en'])+'\n',quiet=True)
                sig_file.write_text(signature,encoding='utf-8')
                print('GENERATED narration:',dest.name)
        if dry_run:
            duration=float(s.get('duration_sec',8.0))
        else:
            duration=ffprobe_duration(ffprobe,dest)
            if duration<1.5: raise RuntimeError('Narration unexpectedly short: '+str(dest))
        timings.append(duration)
    return timings


def find_audio_clips(src, scenes, ffprobe):
    folder=src/'audio'
    if not folder.is_dir(): return None
    clips=[]
    for s in scenes:
        name=s['id']
        candidates=[folder/(name+'.wav'), folder/(name.lower()+'.wav')]
        f=next((p for p in candidates if p.is_file()),None)
        if not f:return None
        clips.append(f)
    if len(clips)==len(scenes): return [ffprobe_duration(ffprobe,p) for p in clips]
    return None


def detect_source_images(src, scenes):
    for s in scenes:
        ident=s['id']
        images=list((src/'images').glob(ident+'.*')) if (src/'images').is_dir() else []
        candidates=[p for p in images if p.suffix.lower() in ('.png','.jpg','.jpeg')]
        if not candidates:
            raise FileNotFoundError(f'Missing original {ident} image in {src/"images"} — cannot use burned subtitles video')
        s['source_image']=str(candidates[0])


def tokenize_words(t): return re.findall(r'\S+', t)


def chunk_fr(text, word_cap=7, char_cap=43, fontsize=70, fontpath=None):
    """Split French text into compact, physically measurable smartphone captions."""
    words=tokenize_words(canonical_text(text))
    chunks=[]; current=[]
    for word in words:
        proposed=' '.join(current+[word])
        would_overflow=False
        if current:
            try:
                wrap_caption(proposed,fontsize,fontpath)
            except ValueError:
                would_overflow=True
        if current and (len(current)>=word_cap or len(proposed)>char_cap or would_overflow):
            chunks.append(' '.join(current)); current=[]
        current.append(word)
    if current:chunks.append(' '.join(current))
    # Avoid orphan single-word caption by keeping the last short phrase where possible.
    if len(chunks)>1 and len(tokenize_words(chunks[-1]))<=2:
        last=chunks.pop(); previous=chunks.pop()
        combined=tokenize_words(previous+' '+last)
        split=max(2,math.ceil(len(combined)/2))
        first=' '.join(combined[:split]); second=' '.join(combined[split:])
        try:
            wrap_caption(first,fontsize,fontpath)
            wrap_caption(second,fontsize,fontpath)
            chunks.extend([first,second])
        except ValueError:
            chunks.extend([previous,last])
    return chunks


def check_caption_fit(line, fontsize=70, fontpath=None):
    """Measure caption using Pillow when available; fallback conservative estimation."""
    try:
        from PIL import ImageFont
        if fontpath and Path(fontpath).exists(): font=ImageFont.truetype(str(fontpath),fontsize)
        else:
            font=ImageFont.truetype('DejaVuSans-Bold.ttf',fontsize)
        return font.getlength(line)<=860
    except (ImportError,OSError):
        return len(line)<29


def wrap_caption(text,fontsize=70, fontpath=None):
    words=tokenize_words(text); lines=[]; current=[]
    for w in words:
        proposed=' '.join(current+[w])
        if current and not check_caption_fit(proposed, fontsize, fontpath):
            lines.append(' '.join(current)); current=[]
        current.append(w)
    if current:lines.append(' '.join(current))
    if len(lines)>2:
        raise ValueError(f'Subtitle exceeds 2 lines: {text!r}: {lines!r}')
    if any(not check_caption_fit(line,fontsize,fontpath) for line in lines):
        raise ValueError('Oversized subtitle: '+text)
    return lines


def ass_time(t):
    centis=max(0,round(t*100)); cs=centis%100; s=(centis//100)%60; m=(centis//6000)%60; h=centis//360000
    return f'{h}:{m:02d}:{s:02d}.{cs:02d}'


def srt_time(t):
    ms=max(0,round(t*1000)); return f'{ms//3600000:02}:{(ms//60000)%60:02}:{(ms//1000)%60:02},{ms%1000:03}'


def generate_subtitles(scenes, scene_starts, voice_durations, target, subtitle_dir, fontsize=70, fontpath=None):
    # libass: PlayResX/Y and margins below are in actual full-HD pixels.
    lines=["[Script Info]",'ScriptType: v4.00+','WrapStyle: 2',f'PlayResX: {WIDTH}',f'PlayResY: {HEIGHT}',
           'ScaledBorderAndShadow: yes','','[V4+ Styles]',
           'Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding',
           f'Style: TikTok,Arial,{fontsize},&H00FFFFFF,&H00FFFFFF,&H00000000,&H85000000,-1,0,0,0,100,100,0,0,1,5,2,2,110,110,360,1',
           '', '[Events]', 'Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text']
    srt=[]; idx=0; records=[]
    for j,s in enumerate(scenes):
        text=s['narration_fr']
        text=text.replace('longtemps tus, enfin reconnue','longtemps passée sous silence, aujourd’hui reconnue')
        chunks=chunk_fr(text,fontsize=fontsize,fontpath=fontpath)
        voice_sec=voice_durations[j]
        weights=[max(1,len(tokenize_words(part))) for part in chunks]
        total_weight=sum(weights)
        pos=scene_starts[j]; end_scene=pos+voice_sec
        for i,part in enumerate(chunks):
            duration=voice_sec*weights[i]/total_weight
            end=min(end_scene,pos+duration)
            wrapped=wrap_caption(part,fontsize,fontpath)
            if end-pos<0.28:raise ValueError(f'Too-fast subtitle segment: {s["id"]} {part!r}')
            ass_txt=r'\N'.join(w.replace('{','(').replace('}',')') for w in wrapped)
            lines.append(f'Dialogue: 0,{ass_time(pos)},{ass_time(end)},TikTok,,0,0,0,,{ass_txt}')
            idx+=1
            srt.append(f'{idx}\n{srt_time(pos)} --> {srt_time(end)}\n'+ '\n'.join(wrapped)+'\n')
            records.append({'scene':s['id'],'start':round(pos,3),'end':round(end,3),'text':part,'lines':wrapped})
            pos=end
    subtitle_dir.mkdir(parents=True,exist_ok=True)
    (subtitle_dir/'subtitles-fr.ass').write_text('\n'.join(lines)+'\n',encoding='utf-8-sig')
    (subtitle_dir/'subtitles-fr.srt').write_text('\n'.join(srt)+'\n',encoding='utf-8-sig')
    (subtitle_dir/'timings.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
    return len(records)


def allocate_frames(voice_durations, target=TARGET_SECONDS,fps=FPS):
    """Target EXACT video frames with enough per-beat room for every voice wav."""
    n=len(voice_durations)
    required=[math.ceil(d*fps)+2 for d in voice_durations]
    budget=target*fps-sum(required)
    if budget < -150:  # Tolerance 5s  # Tolérance 3 secondes pour variations de voix
        raise ValueError(f'Narration too long for {target}s by {-budget/fps:.2f}s. '
                         'Shorten text or accept up to 3s over target.')
    frames=required[:]
    for k in range(budget): frames[k%n]+=1
    return frames


def pick_ffmpeg_encoder(ffmpeg, prefer_nvenc=False):
    if not prefer_nvenc:return ['-c:v','libx264','-preset','veryfast','-crf','20']
    p=run([ffmpeg,'-hide_banner','-encoders'],quiet=True)
    if 'h264_nvenc' in p.stdout: return ['-c:v','h264_nvenc','-preset','p4','-cq','21']
    return ['-c:v','libx264','-preset','veryfast','-crf','20']


def render_shot(ffmpeg, inp, out, frames, encoder, index=0, framing=None):
    framing=framing or {'focus_x':0.5, 'focus_y':0.5, 'zoom_start':1.06, 'zoom_end':1.1}
    marker=out.with_suffix('.render.sha256')
    signature=hashlib.sha256((hashlib.sha256(Path(inp).read_bytes()).hexdigest()+
                             '|'+str(frames)+'|'+str(index)+'|'+str(encoder)+'|'+json.dumps(framing,sort_keys=True)).encode()).hexdigest()
    if out.exists() and marker.exists() and out.stat().st_size>25000:
        old=ffprobe_frames(ffmpeg, out)
        if old==frames and marker.read_text(encoding='utf-8').strip()==signature:
            return 'reused'
    # Subject-aware scene presets: progressive close framing while keeping aspect ratio.
    # User/Codex can refine individual focus values in framing-v5.json after viewing control frames.
    focus_x=float(framing['focus_x']); focus_y=float(framing['focus_y'])
    zoom_start=float(framing['zoom_start']); zoom_end=float(framing['zoom_end'])
    if not (0.0<=focus_x<=1.0 and 0.0<=focus_y<=1.0 and
            1.0<=zoom_start<=zoom_end<=1.3):
        raise ValueError('Invalid shot framing values: '+str(framing))
    inc=(zoom_end-zoom_start)/max(1,frames)
    z=f"min(max(zoom,{zoom_start:.6f})+{inc:.7f},{zoom_end:.6f})"
    filt=(f'scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,'
           f'crop={WIDTH}:{HEIGHT},'
           f"zoompan=z='{z}':x='(iw-iw/zoom)*{focus_x:.4f}':y='(ih-ih/zoom)*{focus_y:.4f}':d={frames}:s={WIDTH}x{HEIGHT}:fps={FPS},"
           'format=yuv420p,setsar=1')
    run([ffmpeg,'-hide_banner','-loglevel','error','-y','-loop','1','-framerate',str(FPS),
         '-i',inp,'-vf',filt,'-frames:v',str(frames),*encoder,'-pix_fmt','yuv420p',
         '-an','-movflags','+faststart',out],quiet=True)
    marker.write_text(signature,encoding='utf-8')
    return 'rendered'


def ffprobe_frames(ffmpeg, file):
    try:
        ffprobe=str(Path(ffmpeg).with_name('ffprobe'+('.exe' if os.name=='nt' else '')))
        if not Path(ffprobe).exists():ffprobe=check_exe('ffprobe')
        p=run([ffprobe,'-v','error','-count_frames','-select_streams','v:0',
               '-show_entries','stream=nb_read_frames','-of','default=nw=1:nk=1',file],quiet=True)
        return int(p.stdout.strip())
    except Exception:return 0


def ffconcat_escape(p):return str(p.resolve()).replace('\\','/').replace("'",r"'\''")


def merge_audio(ffmpeg, clips, frames, out, working):
    padded=[]
    for s, f, count in clips:
        dest=working/(s['id']+'_pad.wav')
        # Always rebuild small PCM: ensures synchronized scene padding after dialogue.
        run([ffmpeg,'-hide_banner','-loglevel','error','-y','-i',f,
             '-af','aresample=48000,apad','-ac','1', '-ar','48000','-t',f'{count/FPS:.6f}',
             '-c:a','pcm_s16le',dest],quiet=True)
        padded.append(dest)
    playlist=working/'audio.ffconcat'
    playlist.write_text('ffconcat version 1.0\n'+''.join("file '"+ffconcat_escape(p)+"'\n" for p in padded),encoding='utf-8')
    run([ffmpeg,'-hide_banner','-loglevel','error','-y','-safe','0','-f','concat','-i',playlist,
         '-ac','1','-ar','48000','-c:a','pcm_s16le',out],quiet=True)


def render_video(ffmpeg, shot_files, audio, assfile, dest, prefer_nvenc=False, target=TARGET_SECONDS):
    playlist=dest.parent/'video.ffconcat'
    playlist.write_text('ffconcat version 1.0\n'+''.join("file '"+ffconcat_escape(p)+"'\n" for p in shot_files),encoding='utf-8')
    enc=pick_ffmpeg_encoder(ffmpeg,prefer_nvenc)
    # Subtitle relative path avoids Windows drive-letter parsing by libass.
    subtitles_local=dest.parent/'captions-v4.ass'
    shutil.copyfile(assfile,subtitles_local)
    try:
        run([ffmpeg,'-hide_banner','-loglevel','error','-y','-safe','0','-f','concat','-i',playlist,
             '-i',audio,'-vf','ass=captions-v4.ass','-map','0:v:0','-map','1:a:0',
             *enc,'-r',str(FPS),'-pix_fmt','yuv420p','-c:a','aac','-b:a','192k',
             '-ar','48000','-t',str(target),'-movflags','+faststart',dest],cwd=dest.parent,quiet=True)
    except RuntimeError:
        if prefer_nvenc:
            print('NVENC encoding error, retrying CPU libx264')
            return render_video(ffmpeg,shot_files,audio,assfile,dest,False,target)
        raise

def generate_contact_sheet(shots, destination):
    """Lightweight local review only; do not inject full PNGs into Codex context."""
    try:
        from PIL import Image, ImageOps, ImageDraw
    except ImportError:
        print('Pillow not installed: skipping contact sheet')
        return
    columns=4; w=190; h=338; banner=30
    rows=math.ceil(len(shots)/columns)
    sheet=Image.new('RGB',(columns*w,rows*(h+banner)),(18,18,18))
    drawer=ImageDraw.Draw(sheet)
    for i,item in enumerate(shots):
        img=Image.open(item['image']).convert('RGB')
        thumb=ImageOps.fit(img,(w,h),method=Image.Resampling.LANCZOS)
        x=(i%columns)*w; y=(i//columns)*(h+banner)
        sheet.paste(thumb,(x,y+banner))
        drawer.text((x+8,y+6),Path(item['file']).stem,fill='white')
    sheet.save(destination,'JPEG',quality=76,optimize=True)


def generate_review_frames(ffmpeg, result, folder, target=TARGET_SECONDS):
    folder.mkdir(exist_ok=True,parents=True)
    for sec in (target*0.15,target*0.5,target*0.85):
        dest=folder/f'preview-{int(sec):03d}s.jpg'
        run([ffmpeg,'-v','error','-y','-ss',f'{sec:.3f}','-i',result,
             '-frames:v','1','-vf','scale=540:-2','-q:v','4',dest],quiet=True)


def validate_result(ffprobe, ffmpeg, result):
    p=run([ffprobe,'-v','error','-show_entries','format=duration:stream=codec_type,codec_name,width,height,r_frame_rate',
            '-of','json',result],quiet=True)
    d=json.loads(p.stdout)
    streams=d['streams']; vids=[s for s in streams if s['codec_type']=='video']; auds=[s for s in streams if s['codec_type']=='audio']
    dur=float(d['format']['duration'])
    if len(vids)!=1 or len(auds)!=1:raise ValueError('Final MP4 must have exactly one video + one audio stream')
    if (vids[0]['width'],vids[0]['height'])!=(WIDTH,HEIGHT): raise ValueError('Wrong resolution')
    if abs(dur-TARGET_SECONDS)>0.6:raise ValueError(f'Wrong final duration: {dur:.2f}s')
    run([ffmpeg,'-v','error','-i',result,'-f','null','-'],quiet=True)
    return {'duration_sec':round(dur,3),'width':WIDTH,'height':HEIGHT,
            'video_codec':vids[0]['codec_name'],'audio_codec':auds[0]['codec_name'],
            'video_fps':vids[0].get('r_frame_rate'), 'decoded_without_errors':True}


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument('--project',type=Path,default=DEFAULT_ROOT)
    ap.add_argument('--out',type=Path)
    ap.add_argument('--comfy',default='http://127.0.0.1:8188')
    ap.add_argument('--framing-config', type=Path, help='Optional shot framing JSON, defaults to bundled framing-v5.json')
    ap.add_argument('--piper',help='Path to installed Piper CLI')
    ap.add_argument('--narration-original',action='store_true',help='Keep exact V3 text instead of bundled V4 reviewed 189-word script')
    ap.add_argument('--voice',help='Path to English Piper voice ONNX')
    ap.add_argument('--preflight',action='store_true',help='Check prerequisites without generating any files')
    ap.add_argument('--skip-image-generation',action='store_true',help='Only for images already generated in V4')
    ap.add_argument('--nvenc',action='store_true',help='Attempt NVIDIA hardware encoding')
    ap.add_argument('--test',action='store_true',help='Use a two-scene smoke-test, never a final output')
    a=ap.parse_args(argv)
    root=a.project.resolve(); src=root/'work'/'pilot-thiaroye-1944-90s-v3'
    out=(a.out if a.out else root/'output'/'pilot-thiaroye-1944-90s-v5').resolve()
    sb, all_scenes=load_storyboard(root)
    scenes=all_scenes[:2] if a.test else all_scenes
    if not a.narration_original:
        override=Path(__file__).resolve().parent/'narration_v4.json'
        if override.is_file():
            texts=json.loads(override.read_text(encoding='utf-8'))['scenes']
            for s in scenes:
                if s['id'] in texts:
                    s['narration_en']=texts[s['id']]['en']
                    s['narration_fr']=texts[s['id']]['fr']
    detect_source_images(src,scenes)
    ffmpeg=check_exe('ffmpeg'); ffprobe=check_exe('ffprobe')
    cli,model=detect_piper(root)
    if a.piper:cli=a.piper
    if a.voice:model=Path(a.voice)
    print('Project:',root,'\nStoryboard:',sb,'\nScenes:',len(scenes))
    print('Output:',out,'\nPiper:',cli or '<not detected>','voice:',model or '<not detected>')
    if a.preflight:
        try:
            version = check_comfy(a.comfy)
            print('ComfyUI:', version)
            comfy_status = 'PASS'
        except Exception as e:
            print('ComfyUI unavailable:', e)
            comfy_status = 'BLOCKED'
        print('V3 original images OK:', len(scenes), '/', len(scenes))
        print('Preflight done — no media modified')
        if comfy_status == 'BLOCKED':
            print('PREFLIGHT RESULT: BLOCKED — ComfyUI is required for image generation')
            return 3
        print('PREFLIGHT RESULT: PASS')
        return 0
    if not cli or not model:
        raise RuntimeError('Cannot locate Piper/English voice. Pass --piper and --voice or use the existing TTS provider to create per-scene WAV files before continuing.')
    out.mkdir(parents=True,exist_ok=True)
    (out/'images').mkdir(exist_ok=True)
    (out/'audio').mkdir(exist_ok=True)
    (out/'shots').mkdir(exist_ok=True)
    (out/'metadata').mkdir(exist_ok=True)
    if not a.skip_image_generation: check_comfy(a.comfy)
    elif any(not (out/'images'/(s['id']+'_B.png')).exists() for s in scenes):
        raise FileNotFoundError('Missing V4 complementary images; cannot skip their generation')
    visual_report=[]
    for s in scenes:
        dest=out/'images'/(s['id']+'_B.png')
        status='reused' if a.skip_image_generation else generate_comfy(s,dest,a.comfy)
        visual_report.append({'scene':s['id'],'source':s['source_image'], 'new':str(dest),'status':status})
    timings=synthesize_voice(root,scenes,out/'audio',ffprobe,cli,model)
    goal=(max(6,math.ceil(sum(timings)+1)) if a.test else TARGET_SECONDS)
    frames=allocate_frames(timings,goal,FPS)
    starts=[]; t=0
    for count in frames: starts.append(t); t+=count/FPS
    nsubs=generate_subtitles(scenes,starts,timings,goal,out/'subtitles',fontsize=70,
                            fontpath=Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts'/'arialbd.ttf')
    enc=pick_ffmpeg_encoder(ffmpeg,a.nvenc)
    framing_path=a.framing_config or (Path(__file__).resolve().parent/'framing-v5.json')
    framing_spec=json.loads(framing_path.read_text(encoding='utf-8-sig'))
    shots=[]; shot_manifest=[]
    for j,s in enumerate(scenes):
        n=frames[j]
        first=max(1,round(n*0.48)); second=n-first
        for index,(img, shot_frames) in enumerate([(s['source_image'],first),(out/'images'/(s['id']+'_B.png'),second)]):
            dest=out/'shots'/f"{s['id']}_{'A' if index==0 else 'B'}.mp4"
            shot_label=f"{s['id']}_{'A' if index==0 else 'B'}"
            framing=dict(framing_spec['defaults']['A' if index==0 else 'B'])
            framing.update(framing_spec['shots'].get(shot_label,{}))
            status=render_shot(ffmpeg,img,dest,shot_frames,enc,index,framing=framing)
            shots.append(dest)
            shot_manifest.append({'scene':s['id'],'file':str(dest),'image':str(img),'frames':shot_frames,
                                  'duration_sec':round(shot_frames/FPS,3),'status':status,'framing':framing})
    wav=out/'audio'/'narration_english_v4.wav'
    merge_audio(ffmpeg,[(s,out/'audio'/(s['id']+'.wav'),frames[i]) for i,s in enumerate(scenes)],frames,wav,out/'audio')
    # Generate the 12-second control excerpt BEFORE attempting the full-length render.
    # It uses exactly the same source shots, audio, and ASS subtitles as the final.
    preview=out/'review'/'control-excerpt.mp4'
    preview.parent.mkdir(parents=True,exist_ok=True)
    render_video(ffmpeg,shots,wav,out/'subtitles'/'subtitles-fr.ass',preview,a.nvenc,target=min(12,goal))
    preview_media=media_probe(ffprobe,preview)
    preview_audio=audio_signal(ffmpeg,preview)
    if abs(preview_media['duration_sec']-min(12,goal))>0.6:
        raise ValueError('Control-excerpt length mismatch: '+str(preview_media['duration_sec']))
    generate_review_frames(ffmpeg,preview,out/'review'/'control-frames',target=min(12,goal))
    print('CONTROL excerpt PASS:',preview,'peak',preview_audio['peak_dbfs'],'dBFS')
    result=out/('smoke_test_v5.mp4' if a.test else 'thiaroye-1944-90s-v5-final.mp4')
    render_video(ffmpeg,shots,wav,out/'subtitles'/'subtitles-fr.ass',result,a.nvenc,target=goal)
    generate_contact_sheet(shot_manifest,out/'storyboard-v4.jpg')
    generate_review_frames(ffmpeg,result,out/'review',target=goal)
    if a.test:
        report={'test':True,'result':str(result),'shots':len(shots),'subtitles':nsubs,
                'control_excerpt':str(preview)}
    else:
        qc=check_final(ffmpeg,ffprobe,result,out/'subtitles'/'timings.json',
                       out/'subtitles'/'subtitles-fr.ass',goal=goal)
        report={'test':False,'result':str(result),'qc':qc,'shots':len(shots),'subtitles':nsubs,
                'images_old':len(scenes),'images_new':len(scenes),'frames':sum(frames),
                'control_excerpt':str(preview),'known_limitations':['Historical fidelity requires human review of newly generated images',
                                    'Subtitle timing within each narrated scene is proportional, not forced word-aligned',
                                    'The rendering scripts cannot automatically assess character visual consistency'],
                'source_video_not_reused':'concat_video_v2.mp4 has baked-in subtitles and no audio'}
    (out/'metadata'/'finish-report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    (out/'metadata'/'shots.json').write_text(json.dumps(shot_manifest,indent=2,ensure_ascii=False),encoding='utf-8')
    (out/'metadata'/'sources.json').write_text(json.dumps(visual_report,indent=2,ensure_ascii=False),encoding='utf-8')
    shutil.copyfile(framing_path,out/'metadata'/'framing-used.json')
    # One machine-readable, timestamped 22-shot storyboard for downstream videos.
    cursor=0.0
    storyboard_out=[]
    for shot in shot_manifest:
        ss=dict(shot)
        ss['start_sec']=round(cursor,3)
        cursor+=ss['duration_sec']
        ss['end_sec']=round(cursor,3)
        scene=next(x for x in scenes if x['id']==ss['scene'])
        ss['narration_en']=scene['narration_en']
        ss['narration_fr']=scene['narration_fr']
        storyboard_out.append(ss)
    (out/'storyboard-v5.json').write_text(json.dumps(storyboard_out,indent=2,ensure_ascii=False),encoding='utf-8')
    report_md=(f'# TikTokHistoryFactory V5 — Rapport de finalisation\n\n'
      f'- Fichier vidéo : `{result}`\n- Extrait contrôle : `{preview}`\n- Durée cible : {goal} secondes\n'
      f'- Nombre de plans : {len(shots)}\n- Sous-titres FR : {nsubs} segments\n'
      f'- Police : Arial Gras, taille 70 pixels, deux lignes maximum, marge basse 360 px\n'
      f'- Audio : narration anglaise Piper\n- Planche : `storyboard-v4.jpg`\n'
      f'- Aperçus de contrôle : `review/`\n\n'
      f'## Vérifications humaines indispensables\n'
      f'- Vérifier la justesse historique des nouveaux dessins.\n'
      f'- Écouter intégralement la voix et vérifier sa prononciation.\n'
      f'- Contrôler la correspondance des sous-titres avec les mots prononcés.\n'
      f'- Vérifier le confort de lecture sur un smartphone.\n'
      f'- Aucune publication TikTok effectuée.\n'
      f'\n## Résultats techniques\n'
      f'```json\n{json.dumps(report.get("qc", {"synthetic_test":True}), ensure_ascii=False, indent=2)}\n```\n')
    (out/'QC_REPORT.md').write_text(report_md,encoding='utf-8')
    print('DONE:',result,'\n',json.dumps(report,indent=2,ensure_ascii=False))
    return 0

if __name__=='__main__':
    try: sys.exit(main())
    except Exception as e:
        print('FAILED:',e,file=sys.stderr)
        sys.exit(1)

