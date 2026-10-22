"""Tests sans réseau, sans coût, sans ComfyUI. Ne crée qu'un MP4 synthétique temporaire."""
import importlib.util
import math
import subprocess
import tempfile
from pathlib import Path
from PIL import Image, ImageDraw

here=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('finish_pilot',here/'finish_pilot.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def test_subtitles(tmp):
    scenes=[{'id':'SC01','narration_fr':"C'étaient des tirailleurs — des soldats d'Afrique de l'Ouest qui avaient combattu pour la France pendant la Seconde Guerre mondiale."},
            {'id':'SC02','narration_fr':"Thiaroye est une blessure dans l'histoire coloniale de la France — longtemps tus, enfin reconnue."}]
    count=m.generate_subtitles(scenes,[0,3],[2.7,2.7],6,tmp/'sub',fontsize=70)
    ass=(tmp/'sub'/'subtitles-fr.ass').read_text(encoding='utf-8-sig')
    assert count>=4
    assert 'passée' in ass and 'reconnue' in ass
    assert ass.count('Dialogue: ')==count
    assert r'\N\N' not in ass
    return count


def test_render(tmp):
    ffmpeg=m.check_exe('ffmpeg'); ffprobe=m.check_exe('ffprobe')
    for i in (1,2):
        im=Image.new('RGB',(768,1344),(175,175,175) if i==1 else (210,210,210))
        d=ImageDraw.Draw(im)
        d.rectangle((130,380,620,1240),outline='black',width=8)
        d.text((260,600),f'IMAGE {i}',fill='black')
        im.save(tmp/f'in{i}.png')
    enc=m.pick_ffmpeg_encoder(ffmpeg)
    shots=[]
    for i,frames in ((1,48),(2,42)):
        out=tmp/f'clip{i}.mp4'
        print('rendering sample video clip',i)
        m.render_shot(ffmpeg,tmp/f'in{i}.png',out,frames,enc,i)
        assert out.stat().st_size>1000
        shots.append(out)
    test_subtitles(tmp)
    m.generate_subtitles([
        {'id':'SC01','narration_fr':"Les soldats africains avaient servi la France pendant la guerre."},
        {'id':'SC02','narration_fr':"Ils réclamaient leur solde impayée et le respect."}],
        [0,1.5],[1.4,1.4],3,tmp/'qcsub',fontsize=70)
    audio=tmp/'voice.wav'
    m.run([ffmpeg,'-v','error','-f','lavfi','-i','sine=frequency=440:duration=3','-ar','48000','-ac','1','-c:a','pcm_s16le','-y',audio],quiet=True)
    final=tmp/'sample_output.mp4'
    print('rendering sample final with ASS subtitles')
    m.render_video(ffmpeg,shots,audio,tmp/'qcsub'/'subtitles-fr.ass',final,target=3)
    out=m.run([ffprobe,'-v','error','-show_entries','stream=codec_type','-of','csv=p=0',final],quiet=True)
    streams=out.stdout.splitlines()
    assert streams.count('video')==1 and streams.count('audio')==1, streams
    assert final.stat().st_size>10000
    from quality_v5 import check_final
    qc=check_final(ffmpeg,ffprobe,final,tmp/'qcsub'/'timings.json',tmp/'qcsub'/'subtitles-fr.ass',goal=3)
    assert qc['technical_checks_passed'] and qc['subtitles']['max_lines']<=2
    print('PASS rendered + full QC:',final,'bytes=',final.stat().st_size,
          'max_audio_dbfs=',qc['audio']['peak_dbfs'])


def test_helpers():
    parts=m.chunk_fr('De retour chez eux, ils réclamaient leurs soldes impayées et l’indemnisation promise.')
    assert all(len(p.split())<=7 for p in parts),parts
    for p in parts: assert len(m.wrap_caption(p))<=2
    f=m.allocate_frames([7.8,8.2,5,6,10,3,8,5,7,5,7],90)
    assert sum(f)==2700, sum(f)
    assert f[0]>=math.ceil(7.8*30)
    try:
        m.allocate_frames([95],90)
    except ValueError:pass
    else:raise AssertionError('oversized narration accepted')
    print('PASS helper tests')

if __name__=='__main__':
    test_helpers()
    with tempfile.TemporaryDirectory(prefix='tiktokfinish-') as d:
        test_render(Path(d))
    print('ALL TESTS PASS')
