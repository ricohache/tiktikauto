import json, shutil, sqlite3, sys
from pathlib import Path

ROOT = Path(r'C:\TikTokHistoryFactory')
sys.path.insert(0, str(ROOT / 'src' / 'v5_factory'))
from discovery import HistoryDiscovery

def main():
    test_dir = ROOT / 'tests' / 'audit_recovery_v2'
    if test_dir.exists():
        shutil.rmtree(test_dir)
    test_dir.mkdir(parents=True, exist_ok=True)
    (test_dir / 'data' / 'catalogue').mkdir(parents=True, exist_ok=True)
    (test_dir / 'data' / 'pre_sourced').mkdir(parents=True, exist_ok=True)

    db_path = test_dir / 'data' / 'factory.db'
    cat_path = test_dir / 'data' / 'catalogue' / 'subjects.json'
    cat_path.write_text(json.dumps({'subjects': []}, ensure_ascii=False), encoding='utf-8')

    # Simulate interrupted discovery: subject in SQLite but NOT in catalogue
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS discovered_subjects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        slug TEXT NOT NULL UNIQUE,
        title_en TEXT,
        title_fr TEXT,
        summary_en TEXT,
        summary_fr TEXT,
        event_date TEXT,
        sources_json TEXT,
        network_available INTEGER DEFAULT 0,
        discovered_at TEXT DEFAULT CURRENT_TIMESTAMP,
        used INTEGER DEFAULT 0
    )''')
    c.execute('''INSERT OR IGNORE INTO discovered_subjects
        (slug, title_en, title_fr, summary_en, summary_fr, event_date, sources_json, network_available)
        VALUES (?,?,?,?,?,?,?,?)''',
        ('recovered-subject-1950', 'Recovered', 'Recupere', 'Summary EN.', 'Resume FR.', '1950-01-01',
         json.dumps([{'name': 'Test Source', 'url': 'http://example.com'}]), 0))
    conn.commit()
    conn.close()

    # Init discovery: should sync SQLite -> catalogue
    disc = HistoryDiscovery(db_path, cat_path, test_dir / 'data' / 'pre_sourced')
    disc._test_network = lambda: False

    cat = json.loads(cat_path.read_text(encoding='utf-8'))
    slugs = [s['slug'] for s in cat['subjects']]
    assert 'recovered-subject-1950' in slugs, 'Recovered subject not synced to catalogue'
    print('[RECOVERY] Synced SQLite -> catalogue: PASS')

    # Verify no duplicate when re-discovering
    found = disc.discover(1)
    assert len(found) == 0, f'Duplicate discovery: {len(found)}'
    print('[RECOVERY] Anti-duplicate after sync: PASS')

    # Verify that a pre_sourced with a DIFFERENT slug is accepted (semantic hash allows it)
    ps_dir = test_dir / 'data' / 'pre_sourced' / 'recovered-subject-1950-alt'
    ps_dir.mkdir(parents=True, exist_ok=True)
    dossier = {
        'slug': 'recovered-subject-1950-alt',
        'title_en': 'Recovered Alt',
        'title_fr': 'Recupere Alt',
        'summary_en': 'Summary EN alt.',
        'summary_fr': 'Resume FR alt.',
        'event_date': '1950-06-01',
        'sources': [{'name': 'S1', 'url': 'http://example.com/a', 'language': 'en'},
                    {'name': 'S2', 'url': 'http://example.com/b', 'language': 'fr'}],
        'scenes': [], 'wikipedia_url': '',
        'style_prompt': 'test'
    }
    (ps_dir / 'dossier.json').write_text(json.dumps(dossier, ensure_ascii=False, indent=2), encoding='utf-8')

    found2 = disc.discover(1)
    assert len(found2) == 1, f'Should accept different slug, found {len(found2)}'
    assert found2[0]['slug'] == 'recovered-subject-1950-alt'
    print('[RECOVERY] Different slug accepted: PASS')

    # Verify exact slug duplicate is blocked via existing_slugs
    assert 'recovered-subject-1950-alt' in disc.existing_slugs
    found3 = disc.discover(1)
    assert len(found3) == 0, f'Should block duplicate slug, found {len(found3)}'
    print('[RECOVERY] Exact slug dedup: PASS')

    print('\\n=== RECOVERY TEST: REAL PASS ===')

if __name__ == '__main__':
    main()
