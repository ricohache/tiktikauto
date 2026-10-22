import re

with open('src/v5_factory/auto_engine.py','r',encoding='utf-8') as f:
    content = f.read()

print('Taille initiale:', len(content))

# 1. Modifier _run_v5_production
old_run = """    def _run_v5_production(self, storyboard_path: Path, slug: str, output_dir: Path, work_dir: Path) -> Dict:
        \"\"\"Exécute le pipeline V5 sur le storyboard.\"\"\"
        # Copier les images placeholder pour test
        for i in range(1, 12):
            src = self.project / 'work' / 'pilot-thiaroye-1944-90s-v3' / 'images' / f'SC{i:02d}.png'
            dst = work_dir / 'images' / f'SC{i:02d}.png'
            if src.exists() and not dst.exists():
                shutil.copy2(src, dst)

        # Orchestrateur V5
        out = output_dir.resolve()
        out.mkdir(parents=True, exist_ok=True)
        for sub in ('images', 'audio', 'shots', 'metadata', 'subtitles', 'review'):
            (out / sub).mkdir(exist_ok=True)

        # Charger storyboard
        sb = json.loads(storyboard_path.read_text(encoding='utf-8-sig'))
        scenes = sb.get('scenes', [])

        # Images sources
        for s in scenes:
            ident = s['id']
            candidates = list((work_dir / 'images').glob(ident + '.*'))
            png = [p for p in candidates if p.suffix.lower() == '.png']
            if not png:
                raise FileNotFoundError(f'Image manquante: {ident}')
            s['source_image'] = str(png[0])"""

new_run = """    def _run_v5_production(self, scenes, storyboard_path: Path, slug: str, output_dir: Path, work_dir: Path) -> Dict:
        \"\"\"Exécute le pipeline V5 sur le storyboard.\"\"\"
        out = output_dir.resolve()
        out.mkdir(parents=True, exist_ok=True)
        for sub in ('images', 'audio', 'shots', 'metadata', 'subtitles', 'review'):
            (out / sub).mkdir(exist_ok=True)

        # Verifier images pre-generees
        for s in scenes:
            img = Path(s.get('source_image', ''))
            if not img.exists():
                raise FileNotFoundError(f'Image manquante pour {s["id"]}: {img}')"""

if old_run in content:
    content = content.replace(old_run, new_run)
    print('OK: _run_v5_production')
else:
    print('FAIL: _run_v5_production')

# 2. Remplacer sous-titres
old_subs = """        # Sous-titres
        fontpath = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts' / 'arialbd.ttf'
        nsubs = fp.generate_subtitles(scenes, starts, timings, goal, out / 'subtitles', fontsize=70, fontpath=fontpath)"""

new_subs = """        # Sous-titres alignes par duree phonetique reelle
        ass_path, timings_json, nsubs = self._generate_aligned_subtitles(
            scenes, timings, goal, out / 'subtitles'
        )"""

if old_subs in content:
    content = content.replace(old_subs, new_subs)
    print('OK: sous-titres')
else:
    print('FAIL: sous-titres')

# 3. Mettre a jour references aux fichiers de sous-titres
content = content.replace("out / 'subtitles' / 'subtitles-fr.ass'", "ass_path")
content = content.replace("out / 'subtitles' / 'timings.json'", "timings_json")
print('OK: references sous-titres')

with open('src/v5_factory/auto_engine.py','w',encoding='utf-8') as f:
    f.write(content)
print('Sauvegarde OK, taille:', len(content))
