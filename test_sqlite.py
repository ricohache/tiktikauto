import sqlite3

db = sqlite3.connect(r'C:\TikTokHistoryFactory\data\factory.db')
c = db.cursor()

# Verifier les entrees pour les 3 nouveaux sujets
c.execute("SELECT slug, status, qc_passed, mp4_path FROM auto_productions WHERE slug IN ('maji-maji-rebellion-1905', 'sharpeville-massacre-1960', 'chilembwe-uprising-1915')")
rows = c.fetchall()
print('DB entries for new subjects:')
for row in rows:
    print(' ', row)

# Verifier le total
c.execute('SELECT COUNT(*) FROM auto_productions')
print('Total productions:', c.fetchone()[0])

# Tester anti-doublons : essayer d inserer un doublon
try:
    c.execute("INSERT INTO auto_productions (slug, title_en, title_fr) VALUES ('maji-maji-rebellion-1905', 'Test', 'Test')")
    db.commit()
    print('DUPLICATE INSERTED (BUG!)')
except sqlite3.IntegrityError as e:
    print('Anti-duplicate OK:', str(e))

db.close()
