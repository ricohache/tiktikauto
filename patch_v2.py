import json

with open('src/v5_factory/auto_engine.py','r',encoding='utf-8') as f:
    content = f.read()

print('Taille initiale:', len(content))

# 1. Ajouter imports
old = 'import finish_pilot as fp\nimport quality_v5 as qv'
new = 'import finish_pilot as fp\nimport quality_v5 as qv\nimport subtitle_aligner as sa\nfrom comfyui_client import generate_images_for_scenes'
if old in content:
    content = content.replace(old, new)
    print('OK: imports')
else:
    print('FAIL: imports')

# 2. MIN_SHOT_DURATION
old = 'TARGET_SECONDS = 90'
new = 'TARGET_SECONDS = 90\nMIN_SHOT_DURATION = 1.5'
if old in content:
    content = content.replace(old, new)
    print('OK: MIN_SHOT_DURATION')

# 3. produce_subject
old = '''    def produce_subject(self, slug: str) -> Dict:
        """Produit un épisode complet à partir d\'un sujet du catalogue."""
        start_time = time.time()
        subject = self.catalogue.get_by_slug(slug)
        if not subject:
            raise ValueError(f\'Sujet inconnu: {slug}\')

        self._db_insert(slug, subject[\'title_en\'], subject[\'title_fr\'])
        self._db_update(slug, \'storyboarding\')

        # Dossier de travail
        work_dir = self.project / \'work\' / f\'auto-{slug}\'
        work_dir.mkdir(parents=True, exist_ok=True)
        (work_dir / \'images\').mkdir(exist_ok=True)

        # 1. Storyboard
        storyboard_path = self.generate_storyboard(subject, work_dir)
        self._db_update(slug, \'storyboard_ready\', output_dir=str(work_dir))

        # 2. Production V5
        output_dir = self.project / \'output\' / f\'auto-{slug}-v5\'
        self._db_update(slug, \'rendering\', output_dir=str(output_dir))

        try:
            result = self._run_v5_production(storyboard_path, slug, output_dir, work_dir)'''

new = '''    def produce_subject(self, slug: str) -> Dict:
        """Produit un épisode complet à partir d\'un sujet du catalogue."""
        start_time = time.time()
        subject = self.catalogue.get_by_slug(slug)
        if not subject:
            raise ValueError(f\'Sujet inconnu: {slug}\')

        self._db_insert(slug, subject[\'title_en\'], subject[\'title_fr\'])
        self._db_update(slug, \'storyboarding\')

        # Dossier de travail
        work_dir = self.project / \'work\' / f\'auto-{slug}\'
        work_dir.mkdir(parents=True, exist_ok=True)
        (work_dir / \'images\').mkdir(exist_ok=True)

        # 1. Storyboard
        storyboard_path = self.generate_storyboard(subject, work_dir)
        sb = json.loads(storyboard_path.read_text(encoding=\'utf-8-sig\'))
        scenes = sb.get(\'scenes\', [])
        print(f\'[STORYBOARD] {len(scenes)} scenes generees\')

        # 2. Generation images reelles ComfyUI/Emi2
        print(f\'[IMAGES] Generation ComfyUI pour {slug}...\')
        img_results = generate_images_for_scenes(
            scenes, work_dir / \'images\', subject.get(\'style_prompt\', \'\')
        )
        success_imgs = sum(1 for r in img_results if r[\'status\'] in (\'success\', \'cached\'))
        print(f\'[IMAGES] {success_imgs}/{len(scenes)} images disponibles\')
        if success_imgs < len(scenes):
            missing = [r[\'scene\'] for r in img_results if r[\'status\'] not in (\'success\', \'cached\')]
            raise RuntimeError(f\'Images manquantes: {missing}\')

        for s in scenes:
            s[\'source_image\'] = str(work_dir / \'images\' / f"{s[\'id\']}.png")

        self._db_update(slug, \'storyboard_ready\', output_dir=str(work_dir))

        # 3. Production V5
        output_dir = self.project / \'output\' / f\'auto-{slug}-v5\'
        self._db_update(slug, \'rendering\', output_dir=str(output_dir))

        try:
            result = self._run_v5_production(scenes, storyboard_path, slug, output_dir, work_dir)'''

if old in content:
    content = content.replace(old, new)
    print('OK: produce_subject')
else:
    print('FAIL: produce_subject')

# Sauvegarder
with open('src/v5_factory/auto_engine.py','w',encoding='utf-8') as f:
    f.write(content)
print('Taille finale:', len(content))
