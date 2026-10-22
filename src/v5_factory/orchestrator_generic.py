"""Orchestrateur générique V5 — production multi-sujets historiques TikTok.
Sans code hardcodé Thiaroye. Réutilise la logique V5.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time

# Ajouter le dossier V5 au path pour importer ses fonctions
_V5_DIR = Path(__file__).resolve().parent


# Imports depuis V5 (doivent être dans le même répertoire pour les imports relatifs de quality_v5)
import finish_pilot as fp
import quality_v5 as qv

DEFAULT_ROOT = Path(r'C:\TikTokHistoryFactory')
FPS = 30
WIDTH, HEIGHT = 1080, 1920
TARGET_SECONDS = 90


def produce_episode(project: Path, storyboard_path: Path, episode_slug: str,
                    output_dir: Path, piper_cmd=None, piper_model=None,
                    skip_images=False, nvenc=False) -> Path:
    """Produit un épisode générique à partir d'un storyboard JSON."""
    out = output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    for sub in ('images','audio','shots','metadata','subtitles','review'):
        (out / sub).mkdir(exist_ok=True)

    ffmpeg = fp.check_exe('ffmpeg')
    ffprobe = fp.check_exe('ffprobe')

    # Charger le storyboard
    sb = json.loads(storyboard_path.read_text(encoding='utf-8-sig'))
    scenes = sb.get('scenes', [])
    if len(scenes) < 8:
        raise ValueError(f'Need >=8 scenes, found {len(scenes)}')

    # Vérifier images sources A
    src_images = storyboard_path.parent.parent / 'images'
    for s in scenes:
        ident = s['id']
        candidates = list(src_images.glob(ident + '.*'))
        png = [p for p in candidates if p.suffix.lower() == '.png']
        if not png:
            raise FileNotFoundError(f'Missing source image {ident} in {src_images}')
        s['source_image'] = str(png[0])

    # Narration EN via Piper
    timings = fp.synthesize_voice(project, scenes, out / 'audio', ffprobe, piper_cmd, piper_model)
    goal = TARGET_SECONDS
    frames = fp.allocate_frames(timings, goal, FPS)
    starts = []
    t = 0.0
    for count in frames:
        starts.append(t)
        t += count / FPS

    # Sous-titres FR
    fontpath = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts' / 'arialbd.ttf'
    nsubs = fp.generate_subtitles(scenes, starts, timings, goal, out / 'subtitles', fontsize=70, fontpath=fontpath)

    # Rendu shots A+B avec cadrages V5
    enc = fp.pick_ffmpeg_encoder(ffmpeg, nvenc)
    framing_spec_path = _V5_DIR / 'framing-v5.json'
    framing_spec = json.loads(framing_spec_path.read_text(encoding='utf-8-sig'))
    shots = []
    shot_manifest = []
    for j, s in enumerate(scenes):
        n = frames[j]
        first = max(1, round(n * 0.48))
        second = n - first

        # Shot A (source)
        img_a = s['source_image']
        dest_a = out / 'shots' / f"{s['id']}_A.mp4"
        framing_a = dict(framing_spec['defaults']['A'])
        framing_a.update(framing_spec['shots'].get(f"{s['id']}_A", {}))
        status_a = fp.render_shot(ffmpeg, img_a, dest_a, first, enc, 0, framing=framing_a)
        shots.append(dest_a)
        shot_manifest.append({'scene': s['id'], 'file': str(dest_a), 'image': img_a, 'frames': first,
                               'duration_sec': round(first / FPS, 3), 'status': status_a, 'framing': framing_a})

        # Shot B (complément)
        img_b = out / 'images' / (s['id'] + '_B.png')
        if not img_b.exists():
            img_b = img_a
        dest_b = out / 'shots' / f"{s['id']}_B.mp4"
        framing_b = dict(framing_spec['defaults']['B'])
        framing_b.update(framing_spec['shots'].get(f"{s['id']}_B", {}))
        status_b = fp.render_shot(ffmpeg, str(img_b), dest_b, second, enc, 1, framing=framing_b)
        shots.append(dest_b)
        shot_manifest.append({'scene': s['id'], 'file': str(dest_b), 'image': str(img_b), 'frames': second,
                               'duration_sec': round(second / FPS, 3), 'status': status_b, 'framing': framing_b})

    # Audio final
    wav = out / 'audio' / 'narration.wav'
    fp.merge_audio(ffmpeg, [(s, out / 'audio' / (s['id'] + '.wav'), frames[i]) for i, s in enumerate(scenes)],
                    frames, wav, out / 'audio')

    # Extrait contrôle 12s
    preview = out / 'review' / 'control-excerpt.mp4'
    fp.render_video(ffmpeg, shots, wav, out / 'subtitles' / 'subtitles-fr.ass', preview, nvenc, target=min(12, goal))
    preview_media = qv.media_probe(ffprobe, preview)
    preview_audio = qv.audio_signal(ffmpeg, preview)
    fp.generate_review_frames(ffmpeg, preview, out / 'review' / 'control-frames', target=min(12, goal))
    print('CONTROL excerpt PASS:', preview, 'peak', preview_audio['peak_dbfs'], 'dBFS')

    # MP4 final
    result = out / f'{episode_slug}-v5-final.mp4'
    fp.render_video(ffmpeg, shots, wav, out / 'subtitles' / 'subtitles-fr.ass', result, nvenc, target=goal)
    fp.generate_contact_sheet(shot_manifest, out / 'storyboard.jpg')
    fp.generate_review_frames(ffmpeg, result, out / 'review', target=goal)

    # QC
    qc = qv.check_final(ffmpeg, ffprobe, result, out / 'subtitles' / 'timings.json',
                        out / 'subtitles' / 'subtitles-fr.ass', goal=goal)

    # Rapports
    report = {
        'episode': episode_slug, 'result': str(result), 'qc': qc,
        'shots': len(shots), 'subtitles': nsubs,
        'control_excerpt': str(preview),
        'technical_checks_passed': qc['technical_checks_passed']
    }
    (out / 'metadata' / 'finish-report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    (out / 'metadata' / 'shots.json').write_text(json.dumps(shot_manifest, indent=2, ensure_ascii=False), encoding='utf-8')

    # Storyboard horodaté
    cursor = 0.0
    storyboard_out = []
    for shot in shot_manifest:
        ss = dict(shot)
        ss['start_sec'] = round(cursor, 3)
        cursor += ss['duration_sec']
        ss['end_sec'] = round(cursor, 3)
        scene = next(x for x in scenes if x['id'] == ss['scene'])
        ss['narration_en'] = scene['narration_en']
        ss['narration_fr'] = scene['narration_fr']
        storyboard_out.append(ss)
    (out / 'storyboard.json').write_text(json.dumps(storyboard_out, indent=2, ensure_ascii=False), encoding='utf-8')

    # QC_REPORT.md
    report_md = (
        f'# TikTokHistoryFactory V5 — Rapport de finalisation\n\n'
        f'- Fichier vidéo : `{result}`\n'
        f'- Durée cible : {goal}s | Plans : {len(shots)} | Sous-titres FR : {nsubs} segments\n'
        f'- Audio : narration anglaise Piper\n'
        f'- SHA256 : `{qc["sha256"][:16]}...`\n'
        f'- Vérifications techniques : {"PASS" if qc["technical_checks_passed"] else "FAIL"}\n'
        f'- **Aucune publication TikTok effectuée.**\n\n'
        f'## Limitations connues\n'
        f'- Justesse historique à vérifier manuellement\n'
        f'- Timing sous-titres proportionnel (pas alignement phonétique)\n'
    )
    (out / 'QC_REPORT.md').write_text(report_md, encoding='utf-8')

    print('DONE:', result)
    return result


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='Orchestrateur générique V5')
    ap.add_argument('--project', type=Path, default=DEFAULT_ROOT)
    ap.add_argument('--storyboard', type=Path, required=True)
    ap.add_argument('--slug', type=str, required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--piper', help='Path to Piper CLI')
    ap.add_argument('--voice', help='Path to English voice ONNX')
    ap.add_argument('--nvenc', action='store_true')
    a = ap.parse_args()
    produce_episode(a.project, a.storyboard, a.slug, a.output, a.piper, a.voice, nvenc=a.nvenc)


