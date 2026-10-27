import json, shutil, sqlite3, sys, time
from pathlib import Path

ROOT = Path(r'C:\TikTokHistoryFactory')
sys.path.insert(0, str(ROOT / 'src' / 'v5_factory'))

from discovery import HistoryDiscovery
from auto_engine import AutoProductionEngine

def main():
    # Setup isolated test env
    test_dir = ROOT / 'tests' / 'audit_real_no_template'
    if test_dir.exists():
        shutil.rmtree(test_dir)
    test_dir.mkdir(parents=True, exist_ok=True)
    (test_dir / 'data' / 'catalogue').mkdir(parents=True, exist_ok=True)
    (test_dir / 'data' / 'pre_sourced').mkdir(parents=True, exist_ok=True)
    (test_dir / 'work').mkdir(parents=True, exist_ok=True)
    (test_dir / 'output').mkdir(parents=True, exist_ok=True)

    cat = test_dir / 'data' / 'catalogue' / 'subjects.json'
    cat.write_text(json.dumps({'subjects': []}, ensure_ascii=False), encoding='utf-8')

    # Create a real new subject without template, with long summaries
    slug = 'test-real-subject-1960'
    ps_dir = test_dir / 'data' / 'pre_sourced' / slug
    ps_dir.mkdir(parents=True, exist_ok=True)
    summary_en = (
        'In nineteen sixty, a significant historical event changed the course of a nation. '
        'The people rose against colonial oppression with unprecedented courage and determination. '
        'Foreign powers attempted to suppress the movement through brutal military intervention. '
        'Thousands of civilians were displaced, yet the spirit of resistance remained unbroken. '
        'International observers documented widespread human rights violations committed by occupying forces. '
        'Diplomatic pressure gradually mounted as news of the atrocities reached global audiences. '
        'Humanitarian organizations provided essential aid to refugees fleeing the conflict zones. '
        'After months of struggle, negotiations began between colonial authorities and independence leaders. '
        'The eventual agreement granted limited autonomy, though full independence would take decades more. '
        'The legacy of this uprising inspired future generations to continue demanding justice and equality. '
        'Historians now recognize this period as a critical turning point in the decolonization process. '
        'The scars of that era remain visible in the collective memory of the affected population. '
        'Today, memorials stand as solemn reminders of the sacrifices made for freedom and dignity.'
    )
    summary_fr = (
        'En 1960, un evenement historique majeur changea le cours d une nation. '
        'Le peuple se souleva contre l oppression coloniale avec un courage et une determination sans precedent. '
        'Les puissances etrangeres tenterent d ecraser le mouvement par une intervention militaire brutale. '
        'Des milliers de civils furent deplaces, pourtant l esprit de resistance demeura intact. '
        'Des observateurs internationaux documenterent les violations des droits de l homme commises par les forces d occupation. '
        'La pression diplomatique s intensifia graduellement lorsque les nouvelles des atrocites parvinrent aux audiences mondiales. '
        'Des organisations humanitaires fournirent une aide essentielle aux refugies fuyant les zones de conflit. '
        'Apres des mois de lutte, des negociations s ouvrirent entre les autorites coloniales et les leaders independantistes. '
        'L accord final accorda une autonomie limitee, bien que l independance totale prendrait encore des decennies. '
        'L heritage de ce soulevement inspira les generations futures a continuer de reclamer justice et egalite. '
        'Les historiens reconnaissent aujourd hui cette periode comme un tournant critique du processus de decolonisation. '
        'Les cicatrices de cette epoque demeurent visibles dans la memoire collective de la population affectee. '
        'Aujourd hui, des memorials se dressent comme de solennels rappels des sacrifices consentis pour la liberte et la dignite.'
    )
    dossier = {
        'slug': slug,
        'title_en': 'The Forgotten Uprising of Nineteen Sixty',
        'title_fr': 'Le soulevement oublie de 1960',
        'summary_en': summary_en,
        'summary_fr': summary_fr,
        'event_date': '1960-01-01',
        'sources': [
            {'name': 'University Press Archive', 'url': 'https://example.com/archive', 'language': 'en'},
            {'name': 'Revue Historique Contemporaine', 'url': 'https://example.com/revue', 'language': 'fr'}
        ],
        'scenes': [],
        'wikipedia_url': '',
        'style_prompt': 'Japanese 2D seinen manga panel, bold expressive ink, weighted clean contours, solid black shadow shapes, halftone screentone dots, dramatic cinematic contrast, mature realistic anatomy, black and white with neutral gray, professional manga drawing, historical scene, no text, vertical composition'
    }
    (ps_dir / 'dossier.json').write_text(json.dumps(dossier, ensure_ascii=False, indent=2), encoding='utf-8')

    # Discover subject
    db_path = test_dir / 'data' / 'factory.db'
    disc = HistoryDiscovery(db_path, cat, test_dir / 'data' / 'pre_sourced')
    disc._test_network = lambda: False
    found = disc.discover(1)
    assert len(found) == 1, f'Expected 1 subject, got {len(found)}'
    assert found[0]['slug'] == slug
    slug_val = found[0]['slug']
    print(f'[TEST] Discovered subject: {slug_val}')

    # Verify catalogue + SQLite sync
    cat_data = json.loads(cat.read_text(encoding='utf-8'))
    assert any(s['slug'] == slug for s in cat_data['subjects']), 'Subject not in catalogue'
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    c.execute('SELECT slug FROM discovered_subjects WHERE slug=?', (slug,))
    assert c.fetchone(), 'Subject not in SQLite'
    conn.close()
    print('[TEST] Catalogue and SQLite sync: PASS')

    # Generate storyboard without template
    engine = AutoProductionEngine(test_dir)
    subject = found[0]
    work_dir = test_dir / 'work' / f'auto-{slug}'
    work_dir.mkdir(parents=True, exist_ok=True)
    sb_path = engine.generate_storyboard(subject, work_dir)
    sb = json.loads(sb_path.read_text(encoding='utf-8'))
    scenes = sb.get('scenes', [])
    num_scenes = len(scenes)
    num_shots = num_scenes * 2  # A + B per scene
    print(f'[TEST] Storyboard generated: {num_scenes} scenes = {num_shots} shots')
    assert 11 <= num_scenes <= 13, f'Expected 11-13 scenes, got {num_scenes}'
    assert 22 <= num_shots <= 26, f'Expected 22-26 shots, got {num_shots}'

    # Verify unique narrations
    en_texts = [s['narration_en'] for s in scenes]
    fr_texts = [s['narration_fr'] for s in scenes]
    assert len(en_texts) == len(set(en_texts)), 'Duplicate EN narrations'
    assert len(fr_texts) == len(set(fr_texts)), 'Duplicate FR narrations'
    print('[TEST] Unique narrations: PASS')

    # Verify no artificial pairing repetition (zip strict)
    for i, s in enumerate(scenes):
        if i > 0:
            assert s['narration_en'] != scenes[i-1]['narration_en'], 'Repeated EN sentence'
        if i > 0:
            assert s['narration_fr'] != scenes[i-1]['narration_fr'], 'Repeated FR sentence'
    print('[TEST] No repetition: PASS')

    print(f'\\n=== RESULT: REAL PASS ===')
    print(f'Subject: {slug}')
    print(f'Scenes: {num_scenes}')
    print(f'Shots: {num_shots}')
    print(f'Storyboard: {sb_path}')

if __name__ == '__main__':
    main()