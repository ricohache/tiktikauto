import json, sqlite3
from pathlib import Path

# Creer un sujet test pour la reprise
cat = json.load(open(r'C:\TikTokHistoryFactory\data\catalogue\subjects.json', 'r', encoding='utf-8'))
test_subject = {
    'slug': 'test-resume-2026',
    'title_en': 'Test Resume Subject',
    'title_fr': 'Sujet test reprise',
    'summary_en': 'This is a test subject for resume capability verification.',
    'summary_fr': 'Ceci est un sujet de test pour verifier la reprise.',
    'event_date': '2026-01-01',
    'style_prompt': 'Japanese 2D seinen manga panel, bold expressive ink, dramatic contrast, black and white, no text, vertical composition'
}
cat['subjects'].append(test_subject)
with open(r'C:\TikTokHistoryFactory\data\catalogue\subjects.json', 'w', encoding='utf-8') as f:
    json.dump(cat, f, indent=2, ensure_ascii=False)

# Inserer dans la DB avec status pending (simuler une interruption)
db = sqlite3.connect(r'C:\TikTokHistoryFactory\data\factory.db')
c = db.cursor()
c.execute(\"INSERT OR REPLACE INTO auto_productions (slug, title_en, title_fr, status) VALUES ('test-resume-2026', 'Test Resume Subject', 'Sujet test reprise', 'pending')\")
db.commit()

# Verifier que run_daily.py le selectionnera (car qc_passed=0)
c.execute(\"SELECT slug, status, qc_passed FROM auto_productions WHERE slug='test-resume-2026'\")
row = c.fetchone()
print('Test subject DB entry:', row)
db.close()

print('Test subject created for resume test')
