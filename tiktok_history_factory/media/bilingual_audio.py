"""English utterance synthesis with French captions at actual WAV boundaries."""
import math
import json
import re
import textwrap
import wave
from pathlib import Path
from tiktok_history_factory.providers.piper_tts import PiperTTSProvider, inspect_wav
from tiktok_history_factory.media.subtitles import SubtitleGenerator, SubtitleSegment
from tiktok_history_factory.pipeline.checkpoints import digest, save_json


def caption_lines(text, width=40):
    lines = textwrap.wrap(text, width=width, break_long_words=False, break_on_hyphens=False)
    if not lines or len(lines) > 2 or any(len(line) > width for line in lines):
        raise ValueError('French subtitle must fit at most two 40-character lines; rewrite the utterance')
    return '\n'.join(lines)


def synthesize_bilingual(settings, dossier, work):
    if dossier.get('audio_language') != 'en' or dossier.get('subtitle_language') != 'fr-FR':
        raise ValueError('New pilot requires explicit English speech and French captions')
    if settings.SPOKEN_LANGUAGE not in ('en-US', 'en-GB') or settings.SUBTITLE_LANGUAGE != 'fr-FR':
        raise ValueError('Unsupported target language pair')
    provider = PiperTTSProvider(settings.PIPER_MODEL_PATH, expected_language=settings.SPOKEN_LANGUAGE)
    if not provider.available:
        raise RuntimeError('English TTS unavailable: ' + provider.error)
    if not 1 <= settings.TTS_LENGTH_SCALE <= 1.5:
        raise ValueError('TTS scale must be 1..1.5; acceleration prohibited')
    paths, records, segments, durations = [], [], [], []
    offset, word_count, speech_seconds = 0, 0, 0
    audio_dir = work/'audio'
    audio_dir.mkdir(parents=True, exist_ok=True)
    previous_path = audio_dir/'voice-manifest.json'
    previous = json.loads(previous_path.read_text(encoding='utf-8')) if previous_path.is_file() else {}
    model_hash = digest(settings.PIPER_MODEL_PATH)
    lexicon = dossier.get('pronunciation_lexicon', {})
    for scene in dossier['scenes']:
        path = audio_dir/f'scene-{scene["id"]:02d}.wav'
        with wave.open(str(path), 'wb') as out:
            out.setnchannels(1)
            out.setsampwidth(2)
            out.setframerate(22050)
            for index, utterance in enumerate(scene['utterances'], 1):
                audio_text = utterance['en']
                for name, pronunciation in lexicon.items():
                    audio_text = re.sub(r'\b'+re.escape(name)+r'\b', pronunciation, audio_text)
                chunk = audio_dir/f'utterance-{scene["id"]}-{index}.wav'
                old = next((r for r in previous.get('utterances', []) if r.get('audio_text') == audio_text
                    and r.get('output_path') == str(chunk) and r.get('parameters', {}).get('length_scale') == settings.TTS_LENGTH_SCALE), {})
                if previous.get('model_sha256') == model_hash and chunk.is_file() and old.get('wav_sha256') == digest(chunk):
                    result = old
                else:
                    result = provider.synthesize(audio_text, str(chunk), settings.TTS_LENGTH_SCALE)
                if result['status'] != 'SUCCESS':
                    raise RuntimeError(result)
                with wave.open(str(chunk), 'rb') as source:
                    frames = source.readframes(source.getnframes())
                duration = len(frames)/2/22050
                caption = caption_lines(utterance['fr'])
                segments.append(SubtitleSegment(round(offset*1000), round((offset+duration)*1000), caption))
                records.append({**result, 'scene_id':scene['id'], 'utterance_id':index,
                    'script_en':utterance['en'], 'audio_text':audio_text, 'translation_fr':utterance['fr'],
                    'start_seconds':offset, 'end_seconds':offset+duration,
                    'subtitle_characters_per_second':round(len(utterance['fr'])/duration,2)})
                word_count += len(re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", utterance['en']))
                speech_seconds += duration
                out.writeframes(frames)
                # A short natural pause, not a tempo alteration.
                pause_frames = round(.25*22050)
                out.writeframes(b'\0\0'*pause_frames)
                offset += duration + pause_frames/22050
        info = inspect_wav(path)
        rounded = math.ceil(info['duration']*30)/30
        offset += rounded-info['duration']
        durations.append(rounded)
        paths.append(path)
    total = sum(durations)
    if not 15 <= total <= 45:
        raise ValueError(f'Natural narration {total:.2f}s; rewrite script rather than speed it up')
    srt = work/'script/subtitles.srt'
    srt.write_text(SubtitleGenerator().to_srt(segments), encoding='utf-8')
    manifest = audio_dir/'voice-manifest.json'
    summary = {'utterances':records, 'model_sha256':model_hash, 'audio_language':'en', 'spoken_language':provider.language,
        'subtitle_language':'fr-FR', 'pronunciation_lexicon':lexicon, 'word_count':word_count,
        'speech_duration':speech_seconds, 'duration':total,
        'words_per_minute':round(word_count*60/speech_seconds,2),
        'tempo_changed':False, 'parameters':{'length_scale':settings.TTS_LENGTH_SCALE},
        'alignment':'Measured utterance WAV boundaries, 250ms pauses; no estimated word timing',
        'auditory_review':'Human listening required for intelligibility and proper names'}
    save_json(manifest, summary)
    return {'paths':[str(p) for p in paths], 'durations':durations, 'duration':total,
        'sha256':{str(p):digest(p) for p in paths}, 'subtitles':str(srt),
        'engine':'Piper', 'language':provider.language, **summary}, paths+[srt,manifest]+list(audio_dir.glob('utterance-*.wav'))
