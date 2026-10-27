import re
src_path = r'C:\TikTokHistoryFactory\src\v5_factory\auto_engine.py'
dst_path = r'C:\\TikTokHistoryFactory\\src\\v5_factory\\auto_engine.py'
src = open(src_path, 'r', encoding='utf-8').read()

old_block = """        slug = subject['slug']
        tmpl = templates.get(slug)
        if not tmpl:
            raise RuntimeError(f'Aucun template de storyboard pour: {slug}. Le catalogue doit être enrichi.')"""

new_block = """        slug = subject['slug']
        tmpl = templates.get(slug)
        if not tmpl:
            # Tentative: dossier pre_sourced avec scenes detaillees
            pre_path = self.project / 'data' / 'pre_sourced' / slug / 'dossier.json'
            if pre_path.exists():
                dossier = json.loads(pre_path.read_text(encoding='utf-8'))
                scenes_data = dossier.get('scenes', [])
                if len(scenes_data) >= 6:
                    tmpl = {'scenes': [(s['narration_en'], s['narration_fr']) for s in scenes_data]}
                    print(f'[STORYBOARD] Using pre_sourced scenes for {slug}')
                else:
                    print(f'[STORYBOARD] pre_sourced dossier for {slug} has only {len(scenes_data)} scenes, need at least 6')
        if not tmpl:
            # Tentative: generation automatique a partir du resume detaille
            summary_en = subject.get('summary_en', '')
            summary_fr = subject.get('summary_fr', '')
            if len(summary_en) < 300 or len(summary_fr) < 300:
                raise RuntimeError(
                    f'No template for {slug} and summary too short ({len(summary_en)} EN / {len(summary_fr)} FR chars). '
                    f'Provide a template, a pre_sourced dossier with scenes, or a detailed summary (min 300 chars each).'
                )
            sentences_en = [s.strip() for s in re.split(r'(?<=[.!?])\s+', summary_en) if len(s.strip()) > 10]
            sentences_fr = [s.strip() for s in re.split(r'(?<=[.!?])\s+', summary_fr) if len(s.strip()) > 10]
            if len(sentences_en) < 6 or len(sentences_fr) < 6:
                raise RuntimeError(
                    f'No template for {slug} and not enough sentences in summary ({len(sentences_en)} EN / {len(sentences_fr)} FR). '
                    f'Need at least 6 sentences per language for auto-generation.'
                )
            scenes = []
            for i in range(min(11, max(len(sentences_en), len(sentences_fr)))):
                en = sentences_en[i] if i < len(sentences_en) else sentences_en[-1]
                fr = sentences_fr[i] if i < len(sentences_fr) else sentences_fr[-1]
                scenes.append((en, fr))
            tmpl = {'scenes': scenes}
            print(f'[STORYBOARD] Auto-generated scenes from summary for {slug} ({len(scenes)} scenes)')"""

if old_block not in src:
    print('ERROR: old block not found')
    exit(1)

new_src = src.replace(old_block, new_block)
open(dst_path, 'w', encoding='utf-8').write(new_src)
print('Patched auto_engine.py written to', dst_path)
print('Size:', len(new_src))

