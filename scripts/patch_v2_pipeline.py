"""Apply scoped V2 migration after dated backup."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
p = root/'tiktok_history_factory/pipeline/pilot.py'
t = p.read_text(encoding='utf-8')
t = t.replace("dossier.get('language') != 'fr'", "dossier.get('language') not in ('fr', 'en')")
t = t.replace('A reviewed French historical dossier is required', 'A reviewed historical dossier is required')
anchor = "    return dossier\n"
extra = """    if dossier.get('language') == 'en':
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
"""
assert anchor in t
t = t.replace(anchor, extra)
t = t.replace("'stages': {},", "'stages': {}, 'schema_version': 2, 'audio_language': self.dossier.get('audio_language'), 'subtitle_language': self.dossier.get('subtitle_language'),")
t = t.replace('Prépare le scénario français', 'Prépare le scénario anglais')
t = t.replace('Source-locked French script', 'Source-locked English script with reviewed French translation')
t = t.replace("refs = self.dossier['character_sheet']['visual_prompt'] if scene['id'] == 4 else ''", "refs = self.dossier['character_sheet']['visual_prompt'] if scene['id'] in (2, 4) else ''")
t = t.replace("'seed': 19441200 + scene['id']", "'seed': 19441204 if scene['id'] in (2,4) else 19441200 + scene['id']")
t = t.replace("        save_json(self.work / 'script/storyboard.json', board)", "        (self.work/'script/translation-fr.txt').write_text('\\n\\n'.join(s.get('translation_fr','') for s in board), encoding='utf-8')\n        save_json(self.work / 'script/storyboard.json', board)")
t = t.replace("self.work / 'script/storyboard.json', self.work / 'script/characters.json', self.work / 'script/llm-response.json']", "self.work / 'script/storyboard.json', self.work / 'script/characters.json', self.work / 'script/llm-response.json', self.work/'script/translation-fr.txt']")
start = t.index('    def voice(self, script):')
end = t.index('    def images(self, script):', start)
t = t[:start] + """    def voice(self, script):
        from tiktok_history_factory.media.bilingual_audio import synthesize_bilingual
        return synthesize_bilingual(self.settings, self.dossier, self.work)

""" + t[end:]
t = t.replace("negative_prompt=scene['negative'], steps=28)", "negative_prompt=scene['negative'], steps=28, lora=self.settings.COMFYUI_LORA, strength=self.settings.COMFYUI_LORA_STRENGTH)")
t = t.replace('if not 20 <= duration <= 30', 'if not 15 <= duration <= 45')
t = t.replace("self.dossier, self.research)", "{'sources':self.dossier['sources'], 'claims':self.dossier['claims']}, self.research)")
t = t.replace("'model': digest(self.settings.PIPER_MODEL_PATH), 'version': 2", "'translation': [s.get('translation_fr') for s in self.dossier['scenes']], 'lexicon':self.dossier.get('pronunciation_lexicon'), 'scale':self.settings.TTS_LENGTH_SCALE, 'model': digest(self.settings.PIPER_MODEL_PATH), 'version': 3")
t = t.replace("'checkpoint': self.settings.COMFYUI_CHECKPOINT}", "'checkpoint': self.settings.COMFYUI_CHECKPOINT, 'lora':self.settings.COMFYUI_LORA, 'strength':self.settings.COMFYUI_LORA_STRENGTH}")
t = t.replace("'animation': animation, 'version': 3", "'animation': animation, 'version': 4")
t = t.replace("'video': digest(render['output_path']), 'version': 1", "'video': digest(render['output_path']), 'version': 2")
start=t.index("                credits += ('\\n\\nVoix :")
end=t.index("                (exported / 'CREDITS.txt')",start)
t=t[:start]+"                credits += '\\nEnglish voice: Piper John, LibriVox public-domain training recordings. Model/runtime licences in assets/licenses. Manga: SDXL Base + LineAniRedmond V2, OpenRAIL licences.\\n'\n"+t[end:]
t=t.replace("('scenario.txt','storyboard.json','characters.json','subtitles.srt')", "('scenario.txt','translation-fr.txt','storyboard.json','characters.json','subtitles.srt')")
t=t.replace("        shutil.copy2(self.work / 'qc.json', exported / 'qc.json')", "        shutil.copy2(self.work/'render/narration.wav', exported/'narration-en.wav')\n        shutil.copy2(self.work/'audio/voice-manifest.json', exported/'voice-manifest.json')\n        shutil.copy2(self.work / 'qc.json', exported / 'qc.json')")
p.write_text(t, encoding='utf-8')
p=root/'scripts/main.ps1'
t=p.read_text(encoding='utf-8').replace('voix francaise', 'voix anglaise et sous-titres francais')
t=t.replace('& $pythonExe scripts/acquire_pilot_assets.py\n        exit', '& $pythonExe scripts/acquire_pilot_assets.py\n        if ($LASTEXITCODE) { exit $LASTEXITCODE }\n        & $pythonExe scripts/acquire_v2_assets.py\n        exit')
p.write_text(t,encoding='utf-8')
p=root/'tiktok_history_factory/cli.py'
t=p.read_text(encoding='utf-8').replace("negative_prompt=build_negative_prompt(), steps=28)", "negative_prompt=build_negative_prompt(), steps=28, lora=settings.COMFYUI_LORA, strength=settings.COMFYUI_LORA_STRENGTH)")
t=t.replace("settings.PROJECT_ROOT / 'work/pilot-thiaroye-1944'", "settings.PROJECT_ROOT / 'work' / ('pilot-' + json.loads(Path(settings.PILOT_DOSSIER).read_text(encoding='utf-8'))['slug'].removesuffix('-pilote'))")
p.write_text(t,encoding='utf-8')
print('Bilingual runner, targeted fingerprints, compositor and commands updated')
