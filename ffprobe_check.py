import subprocess, sys, json
from pathlib import Path
sys.path.insert(0, r'C:\TikTokHistoryFactory\src\v5_factory')
import finish_pilot as fp

ffprobe = fp.check_exe('ffprobe')

subjects = [
    ('maji-maji-rebellion-1905', 'auto-maji-maji-rebellion-1905-v5'),
    ('sharpeville-massacre-1960', 'auto-sharpeville-massacre-1960-v5'),
    ('chilembwe-uprising-1915', 'auto-chilembwe-uprising-1915-v5'),
]

for slug, outdir in subjects:
    mp4 = Path(r'C:\TikTokHistoryFactory\output') / outdir / (slug + '-v5-final.mp4')
    print('\n=== ' + slug + ' ===')
    if not mp4.exists():
        print('  MP4 NOT FOUND')
        continue
    
    r = subprocess.run([ffprobe, '-v', 'error', '-show_entries', 'format=duration,size,bit_rate', '-of', 'json', str(mp4)], capture_output=True, text=True)
    fmt = json.loads(r.stdout)
    print('  Format duration: ' + fmt['format']['duration'] + 's')
    print('  Size: ' + fmt['format']['size'] + ' bytes')
    print('  Bitrate: ' + fmt['format']['bit_rate'] + ' bps')
    
    r = subprocess.run([ffprobe, '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=duration,r_frame_rate,width,height', '-of', 'json', str(mp4)], capture_output=True, text=True)
    vid = json.loads(r.stdout)
    if vid.get('streams'):
        s = vid['streams'][0]
        print('  Video: ' + str(s['width']) + 'x' + str(s['height']) + ', ' + s['r_frame_rate'] + ' fps, duration=' + s.get('duration', 'N/A'))
    
    r = subprocess.run([ffprobe, '-v', 'error', '-select_streams', 'a:0', '-show_entries', 'stream=duration,sample_rate,channels', '-of', 'json', str(mp4)], capture_output=True, text=True)
    aud = json.loads(r.stdout)
    if aud.get('streams'):
        s = aud['streams'][0]
        print('  Audio: ' + s['sample_rate'] + ' Hz, ' + str(s['channels']) + ' ch, duration=' + s.get('duration', 'N/A'))
    
    r = subprocess.run([ffprobe, '-v', 'error', '-select_streams', 's:0', '-show_entries', 'stream=codec_name,index', '-of', 'json', str(mp4)], capture_output=True, text=True)
    sub = json.loads(r.stdout)
    if sub.get('streams'):
        s = sub['streams'][0]
        print('  Subtitle: codec=' + s['codec_name'] + ', index=' + str(s['index']))
    else:
        print('  Subtitle: NONE')
