"""One documented pilot, real media only, resumable stages, no publishing."""
import json
import math
import re
import shutil
import textwrap
import time
import urllib.parse
from pathlib import Path

from tiktok_history_factory.database.models import TaskStatus
from tiktok_history_factory.media.compositor import VideoCompositor
from tiktok_history_factory.media.prompts import build_image_prompt, build_negative_prompt
from tiktok_history_factory.media.subtitles import SubtitleSegment, SubtitleGenerator
from tiktok_history_factory.pipeline.checkpoints import Checkpoints, digest, exclusive_lock, save_json
from tiktok_history_factory.providers.comfyui_images import ComfyUIImageProvider
from tiktok_history_factory.providers.ffmpeg import FFmpegProvider
from tiktok_history_factory.providers.history_sources import HistoricalSourceProvider
from tiktok_history_factory.providers.ollama_cloud import OllamaCloudClient
from tiktok_history_factory.providers.piper_tts import PiperTTSProvider, inspect_wav


def visual_inputs(storyboard):
    return [{k:scene.get(k) for k in ('id','positive','negative','seed','image_revision')} for scene in storyboard]


def validate_dossier(dossier: dict) -> dict:
    if not isinstance(dossier, dict):
        raise ValueError('Dossier must be an object')
    if not re.fullmatch(r'[a-z0-9-]{1,100}', dossier.get('slug', '')):
        raise ValueError('Invalid subject slug')
    if dossier.get('language') not in ('fr', 'en') or not dossier.get('reviewed_at'):
        raise ValueError('A reviewed historical dossier is required')
    scenes = dossier.get('scenes', [])
    sources = {s['id'] for s in dossier.get('sources', [])}
    claims = {c['id']: c for c in dossier.get('claims', [])}
    if not 3 <= len(scenes) <= 6 or len(sources) < 2:
        raise ValueError('Need 3..6 scenes and at least two identifiable sources')
    if any(not re.fullmatch(r'[A-Za-z0-9_-]{1,32}', name) for name in sources):
        raise ValueError('Unsafe source ID')
    if len(sources) != len(dossier['sources']):
        raise ValueError('Duplicate source IDs')
    if len({s['id'] for s in scenes}) != len(scenes):
        raise ValueError('Duplicate scene IDs')
    for claim in claims.values():
        if not claim.get('sources') or not set(claim['sources']) <= sources:
            raise ValueError('Every claim must reference known sources')
    for scene in scenes:
        if not isinstance(scene['id'], int) or not 1 <= scene['id'] <= 6:
            raise ValueError('Invalid scene ID')
        if not isinstance(scene.get('narration'), str) or not isinstance(scene.get('visual'), str):
            raise ValueError('Scene text must be strings')
        if not scene.get('visual') or not scene.get('narration') or not scene.get('claims'):
            raise ValueError('Every scene needs narration, visual and claim references')
        if not set(scene['claims']) <= claims.keys():
            raise ValueError('Unknown claim reference')
    if dossier.get('language') == 'en':
        from tiktok_history_factory.pipeline.contracts import BilingualDossier
        BilingualDossier.model_validate(dossier)
        from tiktok_history_factory.media.bilingual_audio import caption_lines
        if dossier.get('audio_language') != 'en' or dossier.get('subtitle_language') != 'fr-FR':
            raise ValueError('English speech and French subtitle language must be explicit')
        for scene in scenes:
            if not scene.get('utterances'):
                raise ValueError('Bilingual utterances required')
            if ' '.join(u['en'] for u in scene['utterances']) != scene['narration']:
                raise ValueError('Utterances differ from English narration')
            if ' '.join(u['fr'] for u in scene['utterances']) != scene.get('translation_fr'):
                raise ValueError('French translation differs from subtitle utterances')
            for utterance in scene['utterances']:
                caption_lines(utterance['fr'])
    return dossier


class PilotRunner:
    def __init__(self, settings, db, task_id, dossier_path, work_dir=None):
        self.settings, self.db, self.task_id = settings, db, task_id
        self.dossier_path = Path(dossier_path)
        self.dossier = validate_dossier(json.loads(self.dossier_path.read_text(encoding='utf-8')))
        if self.dossier.get('language') == 'en':
            if settings.SPOKEN_LANGUAGE != self.dossier['spoken_language'] or settings.SUBTITLE_LANGUAGE != self.dossier['subtitle_language']:
                raise ValueError('Settings and bilingual dossier languages differ; cached media cannot override this contract')
        self.work = Path(work_dir or settings.PROJECT_ROOT / 'work' / ('pilot-' + self.dossier['slug'].removesuffix('-pilote'))).resolve()
        self.work.mkdir(parents=True, exist_ok=True)
        self.checkpoints = Checkpoints(self.work)
        self.ffmpeg = FFmpegProvider(settings.FFMPEG_PATH, settings.FFPROBE_PATH)
        self.manifest = {'subject': self.dossier['title'], 'slug': self.dossier['slug'],
                         'task_id': task_id, 'publication': 'DISABLED', 'stages': {}, 'schema_version': 2, 'audio_language': self.dossier.get('audio_language'), 'subtitle_language': self.dossier.get('subtitle_language'),
                         'disclosures': self.dossier['disclosures'], 'status': 'RUNNING'}
        provenance = []
        candidates = [Path(settings.PIPER_MODEL_PATH).with_suffix('.onnx.provenance.json')]
        model_root = Path(settings.COMFYUI_ROOT) / 'models'
        candidates += list(model_root.rglob('*.provenance.json'))
        for path in candidates:
            if path.is_file():
                data = json.loads(path.read_text(encoding='utf-8'))
                if data not in provenance:
                    provenance.append(data)
        import importlib.metadata
        import sys
        self.manifest['models'] = provenance
        self.manifest['runtime'] = {'python': sys.version, 'piper': importlib.metadata.version('piper-tts'),
                                    'pillow': importlib.metadata.version('Pillow')}
        self.manifest['dossier_sha256'] = digest(self.dossier_path)
        self.manifest['options'] = {'try_wan': settings.PILOT_TRY_WAN}

    def phase(self, name, status, inputs, action):
        print(f'PHASE {name}', flush=True)
        self.db.update_task_status(self.task_id, status)
        started = time.monotonic()
        try:
            result = self.checkpoints.run(name, inputs, action)
            self.manifest['stages'][name] = result
            self.db.record_phase(self.task_id, name, round((time.monotonic()-started)*1000), True)
            save_json(self.work / 'manifest.json', self.manifest)
            return result
        except Exception as exc:
            self.db.record_phase(self.task_id, name, round((time.monotonic()-started)*1000), False, str(exc))
            raise

    def research(self):
        provider = HistoricalSourceProvider(self.settings.WIKIPEDIA_USER_AGENT)
        hosts = {'questions.assemblee-nationale.fr', 'pur-editions.fr', 'fr.wikipedia.org'}
        records, files = [], []
        cached_path = self.work / 'research/research.json'
        cached = json.loads(cached_path.read_text(encoding='utf-8')) if cached_path.exists() else {}
        for source in self.dossier['sources']:
            path = self.work / 'research' / (source['id'] + '.source')
            old = next((r for r in cached.get('sources', []) if r['url'] == source['url']), {})
            record = old if path.is_file() and old.get('sha256') == digest(path) else provider.fetch(source['url'], path, hosts)
            text = path.read_text(encoding='utf-8', errors='replace')
            if 'thiaroye' not in text.lower():
                raise RuntimeError(f'Source content does not match subject: {source["id"]}')
            if source['id'] == 'WIKI':
                extracted = ' '.join(page.get('extract','') for page in json.loads(text)['query']['pages'].values())
            else:
                import html
                extracted = html.unescape(re.sub('<[^>]+>', '', text))
            extracted = ' '.join(extracted.split())
            excerpt = source.get('excerpt', '')
            if excerpt and excerpt not in extracted:
                raise RuntimeError(f'Quoted supporting excerpt not found in source: {source["id"]}')
            records.append({**source, **record, 'supporting_excerpt': excerpt})
            files.append(path)
        result = {'sources': records, 'claims': self.dossier['claims'],
                  'method': 'Curated claims cross-checked against identified sources; no claim of automatic proof',
                  'editorial_status': 'AWAITING_HUMAN_REVIEW',
                  'debates': 'Death toll and detailed circumstances disputed; no number asserted'}
        path = self.work / 'research/research.json'
        save_json(path, result)
        files.append(path)
        return result, files

    def script(self):
        approved = [scene['narration'] for scene in self.dossier['scenes']]
        client = OllamaCloudClient(self.settings.OLLAMA_BASE_URL, self.settings.OLLAMA_API_KEY,
                                   self.settings.OLLAMA_MODEL, timeout=120)
        prompt = ('Prépare le scénario anglais de ce pilote documentaire. Les phrases ont été vérifiées ; '
                  'ne les reformule pas, ne rajoute aucun fait. Retourne exclusivement un objet JSON '
                  'avec une clé narration contenant cette liste de phrases, dans le même ordre : '
                  + json.dumps(approved, ensure_ascii=False))
        cached = self.work / 'script/llm-response.json'
        result = json.loads(cached.read_text(encoding='utf-8')) if cached.exists() else {}
        try:
            valid_cached = result.get('status') == 'SUCCESS' and json.loads(result['message']['content']).get('narration') == approved
        except (KeyError, ValueError):
            valid_cached = False
        if not valid_cached:
            result = client.generate(prompt, temperature=0, max_tokens=900)
        save_json(self.work / 'script/llm-response.json', result)
        if result.get('status') != 'SUCCESS':
            raise RuntimeError('LLM unavailable: ' + str(result.get('error')))
        raw = result['message']['content'].strip()
        if raw.startswith('```'):
            raw = re.sub(r'^```(?:json)?\s*|\s*```$', '', raw)
        proposal = json.loads(raw)
        if proposal.get('narration') != approved:
            raise RuntimeError('LLM changed the reviewed wording; review llm-response.json before accepting')
        path = self.work / 'script/scenario.txt'
        path.write_text('\n\n'.join(approved), encoding='utf-8')
        board = []
        for scene in self.dossier['scenes']:
            # A shared character description is used only where a person appears.
            refs = self.dossier['character_sheet']['visual_prompt'] if scene['id'] in (2, 4) else ''
            board.append({**scene, 'positive': build_image_prompt(scene['visual'], refs),
                          'negative': build_negative_prompt(), 'seed': 19441204 if scene['id'] in (2,4) else 19441200 + scene['id']})
        (self.work/'script/translation-fr.txt').write_text('\n\n'.join(s.get('translation_fr','') for s in board), encoding='utf-8')
        save_json(self.work / 'script/storyboard.json', board)
        save_json(self.work / 'script/characters.json', self.dossier['character_sheet'])
        return {'narration': approved, 'storyboard': board, 'llm_model': result.get('model'),
                'token_usage': {k: result.get(k) for k in ('prompt_eval_count', 'eval_count')},
                'method': 'Source-locked English script with reviewed French translation formatted by LLM; new facts forbidden'}, [path,
                self.work / 'script/storyboard.json', self.work / 'script/characters.json', self.work / 'script/llm-response.json', self.work/'script/translation-fr.txt']

    def voice(self, script):
        from tiktok_history_factory.media.bilingual_audio import synthesize_bilingual
        return synthesize_bilingual(self.settings, self.dossier, self.work)

    def images(self, script):
        from PIL import Image, ImageStat
        provider = ComfyUIImageProvider(self.settings.COMFYUI_BASE_URL)
        paths, records = [], []
        for scene in script['storyboard']:
            revision = scene.get('image_revision', self.dossier.get('visual_revision', 2))
            path = self.work / f'media/scene-{scene["id"]:02d}-v{revision}.png'
            result = provider.generate_image(scene['positive'], seed=scene['seed'],
                        checkpoint=self.settings.COMFYUI_CHECKPOINT, output_path=str(path),
                        negative_prompt=scene['negative'], steps=28, lora=self.settings.COMFYUI_LORA, strength=self.settings.COMFYUI_LORA_STRENGTH)
            if result.get('status') != 'SUCCESS':
                raise RuntimeError('ComfyUI generation failed: ' + str(result))
            with Image.open(path) as image:
                if image.size != (768, 1344) or ImageStat.Stat(image.convert('L')).stddev[0] < 8:
                    raise RuntimeError('Invalid image dimensions or near-blank image')
                if 'prompt' not in image.info:
                    raise RuntimeError('PNG lacks actual ComfyUI generation metadata')
            records.append({k: v for k, v in result.items() if k != 'history'})
            paths.append(path)
        save_json(self.work / 'media/generation-manifest.json', records)
        return {'paths': [str(p) for p in paths], 'generations': records,
                'visual_qc': 'REQUIRES_HUMAN_REVIEW'}, paths + [self.work / 'media/generation-manifest.json']

    def animation(self, images):
        from tiktok_history_factory.providers.comfyui_wan import ComfyUIWanProvider
        result = {'status': 'FALLBACK_FFMPEG', 'mode': 'FFmpeg', 'reason': 'Optional Wan attempt not enabled'}
        files = [self.work / 'animation.json']
        if self.settings.PILOT_TRY_WAN:
            clip = self.work / 'wan/clip.mp4'
            attempt = ComfyUIWanProvider(self.settings.COMFYUI_BASE_URL).generate_clip(images['paths'][0],
                'Preserve the original monochrome ink drawing. Very slow camera push forward, subtle tree movement. No new objects, no people.',
                output_path=str(clip), timeout=600)
            if attempt.get('status') == 'SUCCESS':
                result = {'status': 'SUCCESS', 'mode': 'Wan+FFmpeg', 'clip': str(clip), 'attempt': attempt}
                files += [clip, clip.with_suffix('.wan.json')]
            else:
                result = {'status': 'FALLBACK_FFMPEG', 'mode': 'FFmpeg', 'attempt': attempt,
                          'reason': attempt.get('error', 'Wan unavailable')}
        save_json(files[0], result)
        return result, files

    def render(self, images, voice, animation):
        output = self.work / 'pilot.mp4'
        media = list(images['paths'])
        if animation.get('mode') == 'Wan+FFmpeg':
            media[0] = animation['clip']
        result = VideoCompositor(self.ffmpeg).compose_pilot(media, voice['paths'],
                    voice['subtitles'], str(output), str(self.work / 'render'))
        if result['status'] != 'SUCCESS':
            raise RuntimeError(str(result))
        return result, [output, self.work / 'render/narration.wav', self.work / 'render/ffmpeg-log.json']

    def qc(self, render):
        probe = self.ffmpeg.probe_file(render['output_path'])
        streams = probe.get('streams', [])
        videos = [s for s in streams if s['codec_type'] == 'video']
        audios = [s for s in streams if s['codec_type'] == 'audio']
        if len(videos) != 1 or len(audios) != 1:
            raise RuntimeError('Missing audio/video stream')
        video, audio = videos[0], audios[0]
        if (video['width'], video['height'], video['codec_name']) != (1080, 1920, 'h264'):
            raise RuntimeError('Wrong video format')
        duration = float(probe['format']['duration'])
        if not 15 <= duration <= 45 or abs(float(video['duration']) - float(audio['duration'])) > .15:
            raise RuntimeError('Video duration or A/V synchronization out of range')
        decode = self.ffmpeg._run(['-v', 'error', '-i', render['output_path'], '-f', 'null', '-'])
        if not decode['success'] or decode.get('stderr', '').strip():
            raise RuntimeError('Full FFmpeg decode failed')
        voice = inspect_wav(render['audio_path'])
        if voice['clipping_fraction'] > .001:
            raise RuntimeError('Narration contains excessive clipping')
        black = self.ffmpeg._run(['-hide_banner','-i',render['output_path'], '-vf',
            'blackdetect=d=0.04:pix_th=0.03:pic_th=0.98', '-an','-f','null','-'])
        if not black['success'] or 'black_start:' in black.get('stderr',''):
            raise RuntimeError('Black frames detected or blackdetect failed')
        language = json.loads((self.work/'audio/voice-manifest.json').read_text(encoding='utf-8'))
        if language['audio_language'] != 'en' or language['subtitle_language'] != 'fr-FR' or language['tempo_changed']:
            raise RuntimeError('Final language/tempo contract violated')
        if not 110 <= language['words_per_minute'] <= 150:
            raise RuntimeError('Narration pace unsuitable; rewrite rather than accelerate')
        report = {'status': 'TECHNICAL_PASS_AWAITING_EDITORIAL_REVIEW', 'duration': duration,
                  'probe': probe, 'decode': decode, 'voice': voice,
                  'blackdetect': black, 'language_contract':language,
                  'historical_qc': 'Curated references, debated claims labelled, no death toll asserted',
                  'limitations': ['Visual review required; illustrations are not documentary evidence',
                                 'No automatic proof of historical truth', 'No publication authorized']}
        path = self.work / 'qc.json'
        save_json(path, report)
        return report, [path]

    def run(self):
        with exclusive_lock(self.settings.PROJECT_ROOT / 'work/pilot.lock'):
            try:
                if shutil.disk_usage(self.work).free < 10 * 1024**3:
                    raise RuntimeError('Insufficient disk reserve for rendering')
                research = self.phase('research', TaskStatus.RESEARCHING, {'sources':self.dossier['sources'], 'claims':self.dossier['claims']}, self.research)
                script = self.phase('script', TaskStatus.SCRIPTING,
                    {'dossier':self.dossier, 'prompt_policy':build_image_prompt(''),
                     'negative_policy':build_negative_prompt()}, self.script)
                voice = self.phase('voice', TaskStatus.GENERATING_AUDIO,
                    {'narration': script['narration'], 'translation': [s.get('translation_fr') for s in self.dossier['scenes']], 'lexicon':self.dossier.get('pronunciation_lexicon'), 'scale':self.settings.TTS_LENGTH_SCALE, 'model': digest(self.settings.PIPER_MODEL_PATH), 'version': 3}, lambda: self.voice(script))
                images = self.phase('images', TaskStatus.GENERATING_IMAGES,
                    {'visuals': visual_inputs(script['storyboard']), 'checkpoint': self.settings.COMFYUI_CHECKPOINT, 'lora':self.settings.COMFYUI_LORA, 'strength':self.settings.COMFYUI_LORA_STRENGTH}, lambda: self.images(script))
                animation = self.phase('animation', TaskStatus.GENERATING_VIDEO,
                    {'reference': digest(images['paths'][0]), 'try_wan': self.settings.PILOT_TRY_WAN}, lambda: self.animation(images))
                self.manifest['animation'] = animation
                render = self.phase('render', TaskStatus.RENDERING, {'images': images, 'voice': voice, 'animation': animation, 'version': 4}, lambda: self.render(images, voice, animation))
                qc = self.phase('qc', TaskStatus.TECH_QC, {'video': digest(render['output_path']), 'version': 2}, lambda: self.qc(render))
                export_name = 'revision-' + str(self.dossier.get('export_revision', self.dossier.get('visual_revision', 2)))
                if self.settings.PILOT_TRY_WAN:
                    export_name += '-wan-attempt'
                exported = self.settings.PROJECT_ROOT / 'output/review' / self.dossier['slug'] / export_name
                exported.mkdir(parents=True, exist_ok=True)
                final = exported / 'pilot.mp4'
                if final.exists() and digest(final) != digest(render['output_path']):
                    raise RuntimeError('Different exported pilot exists; preserve it before new export')
                shutil.copy2(render['output_path'], final)
                self.manifest.update(status='AWAITING_REVIEW', output_path=str(final), qc_status=qc['status'])
                save_json(self.work / 'manifest.json', self.manifest)
                shutil.copy2(self.work / 'manifest.json', exported / 'manifest.json')
                credits = '\n'.join(self.dossier['disclosures']) + '\n\nSources :\n' + '\n'.join(s['title']+' : '+s['url'] for s in self.dossier['sources'])
                credits += '\nEnglish voice: Piper John, LibriVox public-domain training recordings. Model/runtime licences in assets/licenses. Manga: SDXL Base + LineAniRedmond V2, OpenRAIL licences.\n'
                (exported / 'CREDITS.txt').write_text(credits, encoding='utf-8')
                self.package(exported, images, script, research)
                self.db.save_production(self.task_id, research, '\n'.join(script['narration']), self.manifest)
                self.db.update_task_status(self.task_id, TaskStatus.AWAITING_REVIEW)
                return self.manifest
            except Exception as exc:
                self.manifest.update(status='BLOCKED', error=str(exc))
                save_json(self.work / 'manifest.json', self.manifest)
                self.db.update_task_status(self.task_id, TaskStatus.BLOCKED, str(exc))
                raise

    def package(self, exported, images, script, research):
        """Portable review dossier, contact sheet and cover; no external upload."""
        from PIL import Image, ImageDraw, ImageFont, ImageOps
        font_path = 'C:/Windows/Fonts/arial.ttf'
        font = ImageFont.truetype(font_path, 24)
        columns = min(4, len(images['paths']))
        rows = math.ceil(len(images['paths']) / columns)
        sheet = Image.new('RGB', (columns*288, rows*554), '#242424')
        draw = ImageDraw.Draw(sheet)
        for index, path in enumerate(images['paths']):
            x, y = (index % columns)*288, (index // columns)*554
            with Image.open(path) as image:
                sheet.paste(ImageOps.fit(image.convert('RGB'), (288, 504)), (x, y+40))
            draw.text((x+12, y+7), f'PLAN {index+1}', font=font, fill='white')
        sheet.save(exported / 'contact-sheet.jpg', quality=92)
        with Image.open(images['paths'][0]) as image:
            cover = ImageOps.fit(image.convert('RGB'), (1080,1920))
        draw = ImageDraw.Draw(cover)
        draw.rectangle((0,0,1080,260), fill='#1b1b1b')
        title = self.dossier['title'].split(',', 1)
        draw.text((60,45), title[0].upper(), font=ImageFont.truetype(font_path,80), fill='#f2e9d4')
        draw.text((60,170), title[1].strip() if len(title)>1 else '', font=ImageFont.truetype(font_path,46), fill='white')
        draw.text((40,1860), 'Reconstitution historique générée par IA', font=font, fill='white', stroke_width=2, stroke_fill='black')
        cover.save(exported / 'cover.jpg', quality=94)
        caption = (self.dossier['title'] + '\nReconstitution historique générée par IA. '
                   'Le bilan et des circonstances demeurent débattus ; aucun chiffre de victimes n’est affirmé. '
                   'Personnage composite fictif.\n#Histoire #Thiaroye #Mémoire\n\n' +
                   '\n'.join(source['title']+' — '+source['url'] for source in self.dossier['sources']))
        (exported / 'caption.txt').write_text(caption, encoding='utf-8')
        lines = ['# Dossier historique — ' + self.dossier['title'], '',
                 'Images illustratives et symboliques ; aucune photographie d’archive. Validation humaine avant diffusion.', '']
        for claim in research['claims']:
            lines += ['- ' + claim['id'] + ' : ' + claim['statement'] + ' [' + claim['certainty'] + '] — ' + ', '.join(claim['sources'])]
        for source in research['sources']:
            lines += ['', f"## {source['id']} — {source['title']}", source['url'],
                      'Consulté : ' + source['retrieved_at'], 'SHA-256 : ' + source['sha256'], source['role']]
        (exported / 'sources.md').write_text('\n'.join(lines), encoding='utf-8')
        for name in ('scenario.txt','translation-fr.txt','storyboard.json','characters.json','subtitles.srt'):
            shutil.copy2(self.work / 'script' / name, exported / name)
        shutil.copy2(self.work/'render/narration.wav', exported/'narration-en.wav')
        shutil.copy2(self.work/'audio/voice-manifest.json', exported/'voice-manifest.json')
        shutil.copy2(self.work / 'qc.json', exported / 'qc.json')
        shutil.copy2(self.work / 'render/captions.ass', exported / 'subtitles.ass')
        for path in images['paths']:
            (exported/'media').mkdir(exist_ok=True)
            shutil.copy2(path, exported/'media'/Path(path).name)
            metadata = Path(path).with_suffix('.generation.json')
            shutil.copy2(metadata, exported/'media'/metadata.name)
        for path in self.manifest['stages']['voice']['paths']:
            (exported/'audio').mkdir(exist_ok=True)
            shutil.copy2(path, exported/'audio'/Path(path).name)
        if self.manifest['animation'].get('mode') == 'Wan+FFmpeg':
            directory = exported/'animation'
            directory.mkdir(exist_ok=True)
            for source in (self.work/'wan').glob('*'):
                if source.suffix in ('.json','.mp4'):
                    shutil.copy2(source, directory/source.name)
        save_json(exported/'artifact_hashes.json', {str(p.relative_to(exported)): digest(p)
                  for p in exported.rglob('*') if p.is_file() and p.name != 'artifact_hashes.json'})
