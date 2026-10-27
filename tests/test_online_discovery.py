import json, shutil, sys
from pathlib import Path

ROOT = Path(r'C:\TikTokHistoryFactory')
sys.path.insert(0, str(ROOT / 'src' / 'v5_factory'))
from discovery import HistoryDiscovery

def main():
    test_dir = ROOT / 'tests' / 'audit_online_discovery'
    if test_dir.exists():
        shutil.rmtree(test_dir)
    test_dir.mkdir(parents=True, exist_ok=True)
    (test_dir / 'data' / 'catalogue').mkdir(parents=True, exist_ok=True)
    (test_dir / 'data' / 'pre_sourced').mkdir(parents=True, exist_ok=True)

    db_path = test_dir / 'data' / 'factory.db'
    cat_path = test_dir / 'data' / 'catalogue' / 'subjects.json'
    cat_path.write_text(json.dumps({'subjects': []}, ensure_ascii=False), encoding='utf-8')

    disc = HistoryDiscovery(db_path, cat_path, test_dir / 'data' / 'pre_sourced')
    # Do NOT mock network: let it try real network
    found = disc.discover(1)
    if found:
        slug_val = found[0]['slug']; print(f'[ONLINE] Found: {slug_val}')
        print('=== RESULT: REAL PASS ===')
    else:
        print('=== RESULT: BLOCKED - no online subject discovered ===')

if __name__ == '__main__':
    main()
