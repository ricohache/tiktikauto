import json, sqlite3, sys
from pathlib import Path

ROOT = Path(r'C:\TikTokHistoryFactory')
sys.path.insert(0, str(ROOT))

# We will run run_daily.py in a subprocess with mocked DB and catalogue
test_dir = ROOT / 'tests' / 'audit_run_daily'
import shutil
if test_dir.exists():
    shutil.rmtree(test_dir)
test_dir.mkdir(parents=True, exist_ok=True)
(test_dir / 'data' / 'catalogue').mkdir(parents=True, exist_ok=True)
(test_dir / 'data').mkdir(parents=True, exist_ok=True)

# Create a catalogue with 2 subjects
cat = {
    'subjects': [
        {'slug': 'subj-a-1900', 'title_en': 'A', 'title_fr': 'A', 'summary_en': '...', 'summary_fr': '...', 'event_date': '1900-01-01'},
        {'slug': 'subj-b-1901', 'title_en': 'B', 'title_fr': 'B', 'summary_en': '...', 'summary_fr': '...', 'event_date': '1901-01-01'},
    ]
}
(test_dir / 'data' / 'catalogue' / 'subjects.json').write_text(json.dumps(cat, ensure_ascii=False), encoding='utf-8')

# Create DB with auto_productions table
db_path = test_dir / 'data' / 'factory.db'
conn = sqlite3.connect(str(db_path))
c = conn.cursor()
c.execute('''
    CREATE TABLE IF NOT EXISTS auto_productions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        slug TEXT NOT NULL UNIQUE,
        title_en TEXT,
        title_fr TEXT,
        status TEXT DEFAULT 'pending',
        storyboard_path TEXT,
        output_dir TEXT,
        mp4_path TEXT,
        sha256 TEXT,
        started_at TEXT DEFAULT CURRENT_TIMESTAMP,
        completed_at TEXT,
        error TEXT,
        qc_passed INTEGER DEFAULT 0
    )
''')
conn.commit()
conn.close()

# Patch run_daily.py paths by importing and monkey-patching
import run_daily
run_daily.ROOT = test_dir
run_daily.DB = test_dir / 'data' / 'factory.db'
run_daily.CATALOGUE = test_dir / 'data' / 'catalogue' / 'subjects.json'

# Capture output
import io, contextlib
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    run_daily.main()

output = buf.getvalue()
print(output)
if 'BLOCKED: insufficient queue' in output:
    print('PASS: run_daily correctly blocked with insufficient queue')
else:
    print('FAIL: expected BLOCKED message not found')
