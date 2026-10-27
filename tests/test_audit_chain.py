import json, os, shutil, sqlite3, sys, tempfile, traceback
from pathlib import Path

ROOT = Path(r'C:\TikTokHistoryFactory')
sys.path.insert(0, str(ROOT / 'src' / 'v5_factory'))

from discovery import HistoryDiscovery
from catalogue import SubjectCatalogue
from auto_engine import AutoProductionEngine

def setup_test_env():
    test_dir = ROOT / 'tests' / 'audit_isolated'
    if test_dir.exists():
        shutil.rmtree(test_dir)
    test_dir.mkdir(parents=True, exist_ok=True)
    (test_dir / 'data' / 'catalogue').mkdir(parents=True, exist_ok=True)
    (test_dir / 'data' / 'pre_sourced').mkdir(parents=True, exist_ok=True)
    (test_dir / 'work').mkdir(parents=True, exist_ok=True)
    (test_dir / 'output').mkdir(parents=True, exist_ok=True)
    catalogue = test_dir / 'data' / 'catalogue' / 'subjects.json'
    catalogue.write_text(json.dumps({"subjects": []}, ensure_ascii=False), encoding='utf-8')
    return test_dir

def create_pre_sourced(test_dir, slug, title_en, title_fr, summary_en, summary_fr, event_date, sources, scenes=None):
    ps_dir = test_dir / 'data' / 'pre_sourced' / slug
    ps_dir.mkdir(parents=True, exist_ok=True)
    dossier = {
        "slug": slug,
        "title_en": title_en,
        "title_fr": title_fr,
        "summary_en": summary_en,
        "summary_fr": summary_fr,
        "event_date": event_date,
        "sources": sources,
        "scenes": scenes or [],
        "wikipedia_url": "",
        "style_prompt": "Japanese 2D seinen manga panel, bold expressive ink, no text, vertical composition"
    }
    (ps_dir / 'dossier.json').write_text(json.dumps(dossier, ensure_ascii=False, indent=2), encoding='utf-8')

def test_discovery_catalogue_sync():
    print('\\n=== TEST 1: Discovery -> Catalogue sync ===')
    test_dir = setup_test_env()
    db_path = test_dir / 'data' / 'factory.db'
    cat_path = test_dir / 'data' / 'catalogue' / 'subjects.json'
    pre_dir = test_dir / 'data' / 'pre_sourced'
    
    create_pre_sourced(test_dir, 'berlin-wall-1989', 'Fall of the Berlin Wall', 'Chute du mur de Berlin',
        'In 1989, the Berlin Wall fell.', 'En 1989, le mur de Berlin est tombe.', '1989-11-09',
        [{"name": "Wikipedia EN", "url": "https://en.wikipedia.org/wiki/Berlin_Wall", "language": "en"},
         {"name": "Wikipedia FR", "url": "https://fr.wikipedia.org/wiki/Mur_de_Berlin", "language": "fr"}])
    
    disc = HistoryDiscovery(db_path, cat_path, pre_dir)
    disc._test_network = lambda: False
    found = disc.discover(1)
    
    assert len(found) == 1, f"Expected 1 found, got {len(found)}"
    assert found[0]['slug'] == 'berlin-wall-1989', f"Wrong slug: {found[0]['slug']}"
    
    # Verify SQLite
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    c.execute('SELECT slug FROM discovered_subjects')
    db_slugs = [r[0] for r in c.fetchall()]
    conn.close()
    assert 'berlin-wall-1989' in db_slugs, "Not in SQLite"
    
    # Verify catalogue
    cat = json.loads(cat_path.read_text(encoding='utf-8'))
    cat_slugs = [s['slug'] for s in cat['subjects']]
    assert 'berlin-wall-1989' in cat_slugs, "Not in catalogue"
    
    print('PASS: subject in SQLite and catalogue')
    return test_dir

def test_two_runs_no_dup():
    print('\\n=== TEST 2: Two runs without duplication ===')
    test_dir = setup_test_env()
    db_path = test_dir / 'data' / 'factory.db'
    cat_path = test_dir / 'data' / 'catalogue' / 'subjects.json'
    pre_dir = test_dir / 'data' / 'pre_sourced'
    
    create_pre_sourced(test_dir, 'subject-a-1900', 'Subject A', 'Sujet A', 'Summary A.', 'Resume A.', '1900-01-01',
        [{"name": "Source 1", "url": "http://example.com/a", "language": "en"},
         {"name": "Source 2", "url": "http://example.com/a-fr", "language": "fr"}])
    create_pre_sourced(test_dir, 'subject-b-1901', 'Subject B', 'Sujet B', 'Summary B.', 'Resume B.', '1901-01-01',
        [{"name": "Source 1", "url": "http://example.com/b", "language": "en"},
         {"name": "Source 2", "url": "http://example.com/b-fr", "language": "fr"}])
    
    disc = HistoryDiscovery(db_path, cat_path, pre_dir)
    disc._test_network = lambda: False
    found1 = disc.discover(3)  # asks for 3, only 2 available
    assert len(found1) == 2, f"First run: expected 2, got {len(found1)}"
    
    # Second run: same discovery instance (reloaded)
    disc2 = HistoryDiscovery(db_path, cat_path, pre_dir)
    disc2._test_network = lambda: False
    found2 = disc2.discover(3)
    assert len(found2) == 0, f"Second run: expected 0, got {len(found2)} (duplicates!)"
    
    print('PASS: no duplication on second run')

def test_exhausted_catalogue():
    print('\\n=== TEST 3: Exhausted catalogue ===')
    test_dir = setup_test_env()
    db_path = test_dir / 'data' / 'factory.db'
    cat_path = test_dir / 'data' / 'catalogue' / 'subjects.json'
    pre_dir = test_dir / 'data' / 'pre_sourced'
    
    create_pre_sourced(test_dir, 'single-subject-1900', 'Single Subject', 'Sujet Unique', 'Summary.', 'Resume.', '1900-01-01',
        [{"name": "S1", "url": "http://example.com", "language": "en"},
         {"name": "S2", "url": "http://example.com/fr", "language": "fr"}])
    
    disc = HistoryDiscovery(db_path, cat_path, pre_dir)
    disc._test_network = lambda: False
    found = disc.discover(3)
    assert len(found) == 1, f"Expected 1, got {len(found)}"
    
    disc2 = HistoryDiscovery(db_path, cat_path, pre_dir)
    disc2._test_network = lambda: False
    found2 = disc2.discover(3)
    assert len(found2) == 0, f"Expected 0 after exhaustion, got {len(found2)}"
    
    print('PASS: exhausted catalogue returns empty')

def test_storyboard_no_template():
    print('\\n=== TEST 4: Storyboard fallback without template ===')
    test_dir = setup_test_env()
    # Monkey-patch generate_images to avoid ComfyUI
    import auto_engine
    auto_engine.generate_images_for_scenes = lambda scenes, outdir, style: [{"scene": s["id"], "status": "success"} for s in scenes]
    
    # Create a subject with long summary but no template
    subject = {
        "slug": "test-no-template-1900",
        "title_en": "Test Subject",
        "title_fr": "Sujet Test",
        "summary_en": "In the early years of the twentieth century, a remarkable historical event unfolded that would reshape the destiny of an entire nation and inspire future generations across the continent. The struggle for independence began with peaceful demonstrations but quickly escalated into a full-scale confrontation with colonial authorities who refused to acknowledge the legitimate demands of the local population. Leaders emerged from diverse backgrounds, uniting people across ethnic and social lines in an unprecedented show of solidarity against foreign domination and exploitation. The movement faced brutal repression, with thousands imprisoned and hundreds killed, yet the spirit of resistance remained unbroken despite the overwhelming military superiority of the occupying forces. International attention eventually turned toward the conflict, bringing diplomatic pressure and humanitarian aid that sustained the morale of the resistance fighters during their darkest hours. After years of sacrifice and negotiation, the colonial power finally agreed to withdraw, marking the birth of a new nation determined to forge its own path toward democracy and prosperity. The legacy of this struggle continues to influence contemporary politics, reminding citizens that freedom requires vigilance and that authoritarianism must be challenged at every turn.",
        "summary_fr": "Dans les premieres annees du vingtieme siecle, un evenement historique remarquable se deroula et allait remodeler le destin d une nation entiere et inspirer les generations futures a travers le continent. La lutte pour l independance commenca par des manifestations pacifiques mais degenera rapidement en une confrontation a grande echelle avec les autorites coloniales qui refusaient de reconnaitre les demandes legitimes de la population locale. Des leaders emergerent de milieux divers, unissant les gens au-dela des lignes ethniques et sociales dans un spectacle sans precedent de solidarite contre la domination etrangere et l exploitation. Le mouvement fit face a une repression brutale, des milliers furent emprisonnes et des centaines tues, pourtant l esprit de resistance resta intact malgre la superiorite militaire ecrasante des forces d occupation. L attention internationale se tourna finalement vers le conflit, apportant une pression diplomatique et une aide humanitaire qui soutinrent le moral des combattants de la resistance pendant leurs heures les plus sombres. Apres des annees de sacrifice et de negociation, la puissance coloniale accepta finalement de se retirer, marquant la naissance d une nouvelle nation determinee a forger son propre chemin vers la democratie et la prosperite. L heritage de cette lutte continue d influencer la politique contemporaine, rappelant aux citoyens que la liberte exige de la vigilance et que l autoritarisme doit etre conteste a chaque tournant.",
        "event_date": "1900-01-01",
        "style_prompt": "Japanese 2D seinen manga panel, bold expressive ink, no text, vertical composition"
    }
    
    engine = AutoProductionEngine(test_dir)
    # Only test _build_scenes_from_subject
    scenes = engine._build_scenes_from_subject(subject)
    assert len(scenes) >= 6, f"Expected >=6 scenes, got {len(scenes)}"
    # Verify no repetition: all narration_en should be unique
    en_texts = [s['narration_en'] for s in scenes]
    assert len(en_texts) == len(set(en_texts)), "Repeated sentences detected in EN"
    fr_texts = [s['narration_fr'] for s in scenes]
    assert len(fr_texts) == len(set(fr_texts)), "Repeated sentences detected in FR"
    print(f'PASS: {len(scenes)} unique scenes generated without repetition')

def test_storyboard_no_template_short():
    print('\\n=== TEST 4b: Storyboard fallback with short summary must fail ===')
    test_dir = setup_test_env()
    subject = {
        "slug": "test-short-1900",
        "title_en": "Short Subject",
        "title_fr": "Sujet Court",
        "summary_en": "One sentence only.",
        "summary_fr": "Une seule phrase.",
        "event_date": "1900-01-01",
        "style_prompt": "test"
    }
    engine = AutoProductionEngine(test_dir)
    try:
        engine._build_scenes_from_subject(subject)
        assert False, "Should have raised RuntimeError"
    except RuntimeError as e:
        assert 'No template' in str(e), f"Wrong error: {e}"
        print('PASS: RuntimeError raised for short summary')

def test_sqlite_virgin_and_resume():
    print('\\n=== TEST 5: SQLite virgin init and resume ===')
    test_dir = setup_test_env()
    db_path = test_dir / 'data' / 'factory.db'
    cat_path = test_dir / 'data' / 'catalogue' / 'subjects.json'
    pre_dir = test_dir / 'data' / 'pre_sourced'
    
    # Virgin init
    assert not db_path.exists(), "DB should not exist initially"
    disc = HistoryDiscovery(db_path, cat_path, pre_dir)
    assert db_path.exists(), "DB should be created"
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='discovered_subjects'")
    assert c.fetchone(), "Table not created"
    conn.close()
    print('PASS: virgin SQLite init OK')
    
    # Simulate interruption: add a subject to DB but not catalogue, then verify recovery
    # Actually with current code _persist_discovery also adds to catalogue, so interruption
    # would be between discover and add. Let's test with raw DB insert.
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    c.execute('''INSERT INTO discovered_subjects (slug, title_en, event_date, sources_json)
                 VALUES (?,?,?,?)''', ('interrupted-subject-1900', 'Interrupted', '1900-01-01', '[]'))
    conn.commit()
    conn.close()
    
    disc2 = HistoryDiscovery(db_path, cat_path, pre_dir)
    assert 'interrupted-subject-1900' in disc2.existing_slugs, "Interrupted subject not recovered"
    
    # Now add it via pre_sourced - should be skipped as duplicate
    create_pre_sourced(test_dir, 'interrupted-subject-1900', 'Interrupted', 'Interrompu', 'Summary.', 'Resume.', '1900-01-01',
        [{"name": "S", "url": "http://example.com", "language": "en"},
         {"name": "S2", "url": "http://example.com/fr", "language": "fr"}])
    disc2._test_network = lambda: False
    found = disc2.discover(1)
    assert len(found) == 0, f"Should skip interrupted subject, found {len(found)}"
    print('PASS: resume after interruption (duplicate prevention) OK')

def main():
    results = []
    tests = [
        test_discovery_catalogue_sync,
        test_two_runs_no_dup,
        test_exhausted_catalogue,
        test_storyboard_no_template,
        test_storyboard_no_template_short,
        test_sqlite_virgin_and_resume,
    ]
    for t in tests:
        try:
            t()
            results.append((t.__name__, 'PASS'))
        except Exception as e:
            traceback.print_exc()
            results.append((t.__name__, f'BLOCKED: {e}'))
    
    print('\\n=== AUDIT RESULTS ===')
    for name, status in results:
        print(f'{name}: {status}')
    
    all_pass = all(s == 'PASS' for _, s in results)
    sys.exit(0 if all_pass else 1)

if __name__ == '__main__':
    main()
