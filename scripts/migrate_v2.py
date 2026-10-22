"""One-time backed-up source migration to EN speech / FR captions."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace(path, old, new):
    p = ROOT/path
    text = p.read_text(encoding='utf-8')
    if old not in text:
        raise RuntimeError(f'Migration anchor missing in {path}: {old[:60]}')
    p.write_text(text.replace(old, new), encoding='utf-8')


p = 'tiktok_history_factory/config/settings.py'
replace(p, 'tools/piper/voices/fr_FR-siwis-medium.onnx', 'tools/piper/voices/en_US-john-medium.onnx')
replace(p, 'data/subjects/thiaroye-1944.json', 'data/subjects/thiaroye-1944-v2.json')
replace(p, '        self.COMFYUI_CHECKPOINT:', "        self.SPOKEN_LANGUAGE = os.getenv('SPOKEN_LANGUAGE', 'en-US')\n        self.SUBTITLE_LANGUAGE = os.getenv('SUBTITLE_LANGUAGE', 'fr-FR')\n        self.TRANSLATION_LOCALE = os.getenv('TRANSLATION_LOCALE', 'fr-FR')\n        self.TTS_LENGTH_SCALE = float(os.getenv('TTS_LENGTH_SCALE', '1.0'))\n        self.COMFYUI_LORA = os.getenv('COMFYUI_LORA', 'LineAniRedmondV2-Lineart-LineAniAF.safetensors')\n        self.COMFYUI_LORA_STRENGTH = float(os.getenv('COMFYUI_LORA_STRENGTH', '1.0'))\n        self.COMFYUI_CHECKPOINT:")
for path in ('.env', '.env.example'):
    p = ROOT/path
    text = p.read_text(encoding='utf-8')
    text = text.replace('fr_FR-siwis-medium.onnx', 'en_US-john-medium.onnx').replace('data/subjects/thiaroye-1944.json', 'data/subjects/thiaroye-1944-v2.json')
    text += '\n# V2: spoken English, French translation captions, no permanent AI overlay\nSPOKEN_LANGUAGE=en-US\nSUBTITLE_LANGUAGE=fr-FR\nTRANSLATION_LOCALE=fr-FR\nTTS_LENGTH_SCALE=1.0\nCOMFYUI_LORA=LineAniRedmondV2-Lineart-LineAniAF.safetensors\nCOMFYUI_LORA_STRENGTH=1.0\n'
    p.write_text(text, encoding='utf-8')

p = 'tiktok_history_factory/providers/ffmpeg.py'
text = (ROOT/p).read_text(encoding='utf-8')
start = text.index('            vf = ("ass=captions.ass,"')
end = text.index('            cmd = ', start)
text = text[:start] + "            vf = 'ass=captions.ass'\n" + text[end:]
# Do not manufacture fully black frames at each cut.
text = text.replace('f"fade=t=in:st=0:d=0.18,fade=t=out:st={max(0, duration-.18)}:d=0.18,format=yuv420p")', '"format=yuv420p")')
text = text.replace('f"tpad=stop_mode=clone:stop_duration={duration},fade=t=in:st=0:d=0.18,"\n                          f"fade=t=out:st={max(0,duration-.18)}:d=0.18,format=yuv420p")', 'f"tpad=stop_mode=clone:stop_duration={duration},format=yuv420p")')
text = text.replace('comment=Images IA non documentaires; voix Piper SIWIS CC-BY 4.0', 'comment=Reconstitution historique generee par IA; images non documentaires; narration EN; sous-titres FR')
(ROOT/p).write_text(text, encoding='utf-8')

d = json.loads((ROOT/'data/subjects/thiaroye-1944.json').read_text(encoding='utf-8'))
d.update(slug='thiaroye-1944-v2', language='en', audio_language='en', spoken_language='en-US', subtitle_language='fr-FR', translation_locale='fr-FR', visual_revision=1, export_revision=1, schema_version=2)
d['pronunciation_lexicon'] = {'Thiaroye': 'Tya-roy'}
d['disclosures'][-1] = 'English synthetic narration: Piper John; LibriVox public-domain recordings; no impersonation or new voice cloning.'
units = [
 [('December first, nineteen forty-four.', 'Le 1er décembre 1944.'), ('Thiaroye, near Dakar, Senegal.', 'À Thiaroye, près de Dakar, au Sénégal.')],
 [('African soldiers had returned from captivity in Europe.', "Des soldats africains rentraient de captivité en Europe."), ('They demanded their unpaid wages.', 'Ils réclamaient leurs soldes impayées.')],
 [('The French army opened fire.', "L’armée française a ouvert le feu."), ('Soldiers were killed.', 'Des soldats ont été tués.')],
 [('The death toll and the exact circumstances remain disputed.', 'Le bilan et les circonstances exactes restent débattus.'), ('Their memory endures.', 'Leur mémoire demeure.')]]
visuals = [
 'Wide cinematic manga establishing shot, an empty transit camp near Dakar in Senegal West Africa in 1944, low plain whitewashed plaster buildings with corrugated iron roofs, sandy ground, one distant baobab tree, dawn light, strong perspective, bold black shadow shapes, no people, no combat, no Japanese buildings. Leave lower quarter quiet for subtitles.',
 'Chest-up portrait of ONE dignified adult West African man, thirty years old, dark skin, long angular face, very short cropped black hair, plain unadorned 1940s khaki cotton shirt, no hat, no insignia. Senegal 1944. Serious determined expression, face in upper third, plain plaster wall behind him, cinematic side lighting, blank lower quarter for subtitles.',
 'Dramatic diagonal close composition of an EMPTY simple plaster barracks doorway, one abandoned plain enamel drinking cup on a wooden bench, heavy black shadows against white sunlight, Senegal 1944. Symbolic aftermath and absence, no people, no bodies, no weapons, no lettering. Leave lower quarter quiet for subtitles.',
 'Close portrait of ONE dignified adult West African man, thirty years old, dark skin, long angular face, very short cropped black hair, plain unadorned 1940s khaki cotton shirt, no hat, no insignia. Senegal 1944. Solemn eyes looking slightly away, face in upper third, neutral plaster wall, powerful black shadow shapes, blank lower quarter for subtitles.'
]
for scene, pairs, visual in zip(d['scenes'], units, visuals):
    scene.pop('image_revision', None)
    scene['narration'] = ' '.join(a for a,b in pairs)
    scene['translation_fr'] = ' '.join(b for a,b in pairs)
    scene['utterances'] = [{'en':a,'fr':b} for a,b in pairs]
    scene['visual'] = visual
(ROOT/'data/subjects/thiaroye-1944-v2.json').write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
(ROOT/'work/pilot-thiaroye-1944/DRAFT_REJECTED.json').write_text(json.dumps({'status':'DRAFT_REJECTED','reason':'Owner rejected French voice pace, engraving/sepia style and permanent AI overlay. Preserve all prior files.','replacement':'thiaroye-1944-v2'}, indent=2), encoding='utf-8')
print('V2 source defaults and new dossier prepared; V1 media preserved')
