import re

with open('src/v5_factory/auto_engine.py','r',encoding='utf-8') as f:
    content = f.read()

print('Taille initiale:', len(content))

# === 1. AJOUTER IMPORTS ===
old_import = "import finish_pilot as fp\nimport quality_v5 as qv"
new_import = "import finish_pilot as fp\nimport quality_v5 as qv\nimport subtitle_aligner as sa\nfrom comfyui_client import generate_images_for_scenes"
content = content.replace(old_import, new_import)
print('Import ajoutes')

# === 2. AJOUTER MIN_SHOT_DURATION ===
old_const = "TARGET_SECONDS = 90"
new_const = "TARGET_SECONDS = 90\nMIN_SHOT_DURATION = 1.5"
content = content.replace(old_const, new_const)
print('MIN_SHOT_DURATION ajoute')

# === 3. MODIFIER produce_subject ===
old_produce = '''    def produce_subject(self, slug: str) -> Dict:
        \"\"\"Produit un épisode complet à partir d'un sujet du catalogue.\"\"\"
        start_time = time.time()
        subject = self.catalogue.get_by_slug(slug)
        if not subject:
            raise ValueError(f'Sujet inconnu: {slug}')

        self._db_insert(slug, subject['title_en'], subject['title_fr'])
        self._db_update(slug, 'storyboarding')

        # Dossier de travail
        work_dir = self.project / 'work' / f'auto-{slug}'
        work_dir.mkdir(parents=True, exist_ok=True)
        (work_dir / 'images').mkdir(exist_ok=True)

        # 1. Storyboard
        storyboard_path = self.generate_storyboard(subject, work_dir)
        self._db_update(slug, 'storyboard_ready', output_dir=str(work_dir))

        # 2. Production V5
        output_dir = self.project / 'output' / f'auto-{slug}-v5'
        self._db_update(slug, 'rendering', output_dir=str(output_dir))

        try:
            result = self._run_v5_production(storyboard_path, slug, output_dir, work_dir)'''

new_produce = '''    def produce_subject(self, slug: str) -> Dict:
        \"\"\"Produit un épisode complet à partir d'un sujet du catalogue.\"\"\"
        start_time = time.time()
        subject = self.catalogue.get_by_slug(slug)
        if not subject:
            raise ValueError(f'Sujet inconnu: {slug}')

        self._db_insert(slug, subject['title_en'], subject['title_fr'])
        self._db_update(slug, 'storyboarding')

        # Dossier de travail
        work_dir = self.project / 'work' / f'auto-{slug}'
        work_dir.mkdir(parents=True, exist_ok=True)
        (work_dir / 'images').mkdir(exist_ok=True)

        # 1. Storyboard
        storyboard_path = self.generate_storyboard(subject, work_dir)
        sb = json.loads(storyboard_path.read_text(encoding='utf-8-sig'))
        scenes = sb.get('scenes', [])
        print(f'[STORYBOARD] {len(scenes)} scenes generees')

        # 2. Generation images reelles ComfyUI/Emi2
        print(f'[IMAGES] Generation ComfyUI pour {slug}...')
        img_results = generate_images_for_scenes(
            scenes, work_dir / 'images', subject.get('style_prompt', '')
        )
        success_imgs = sum(1 for r in img_results if r['status'] in ('success', 'cached'))
        print(f'[IMAGES] {success_imgs}/{len(scenes)} images disponibles')
        if success_imgs < len(scenes):
            missing = [r['scene'] for r in img_results if r['status'] not in ('success', 'cached')]
            raise RuntimeError(f'Images manquantes: {missing}')

        for s in scenes:
            s['source_image'] = str(work_dir / 'images' / f"{s['id']}.png")

        self._db_update(slug, 'storyboard_ready', output_dir=str(work_dir))

        # 3. Production V5
        output_dir = self.project / 'output' / f'auto-{slug}-v5'
        self._db_update(slug, 'rendering', output_dir=str(output_dir))

        try:
            result = self._run_v5_production(scenes, storyboard_path, slug, output_dir, work_dir)'''

if old_produce in content:
    content = content.replace(old_produce, new_produce)
    print('produce_subject modifie')
else:
    print('ERREUR: produce_subject non trouve')

# === 4. MODIFIER _run_v5_production signature et debut ===
old_run = '''    def _run_v5_production(self, storyboard_path: Path, slug: str, output_dir: Path, work_dir: Path) -> Dict:
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
            s['source_image'] = str(png[0])'''

new_run = '''    def _run_v5_production(self, scenes, storyboard_path: Path, slug: str, output_dir: Path, work_dir: Path) -> Dict:
        \"\"\"Exécute le pipeline V5 sur le storyboard.\"\"\"
        out = output_dir.resolve()
        out.mkdir(parents=True, exist_ok=True)
        for sub in ('images', 'audio', 'shots', 'metadata', 'subtitles', 'review'):
            (out / sub).mkdir(exist_ok=True)

        # Verifier images pre-generees
        for s in scenes:
            img = Path(s.get('source_image', ''))
            if not img.exists():
                raise FileNotFoundError(f'Image manquante pour {s["id"]}: {img}')'''

if old_run in content:
    content = content.replace(old_run, new_run)
    print('_run_v5_production modifie')
else:
    print('ERREUR: _run_v5_production non trouve')

# === 5. REMPLACER generate_subtitles PAR _generate_aligned_subtitles ===
old_subs = '''        # Sous-titres
        fontpath = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts' / 'arialbd.ttf'
        nsubs = fp.generate_subtitles(scenes, starts, timings, goal, out / 'subtitles', fontsize=70, fontpath=fontpath)'''

new_subs = '''        # Sous-titres alignes par duree phonetique reelle
        ass_path, timings_json, nsubs = self._generate_aligned_subtitles(
            scenes, timings, goal, out / 'subtitles'
        )'''

if old_subs in content:
    content = content.replace(old_subs, new_subs)
    print('Sous-titres remplaces')
else:
    print('ERREUR: sous-titres non trouves')

# === 6. REMPLACER references aux sous-titres dans le rendu ===
content = content.replace("out / 'subtitles' / 'subtitles-fr.ass'", "ass_path")
content = content.replace("out / 'subtitles' / 'timings.json'", "timings_json")

print('References sous-titres mises a jour')

with open('src/v5_factory/auto_engine.py','w',encoding='utf-8') as f:
    f.write(content)
print('Sauvegarde OK, taille:', len(content))
