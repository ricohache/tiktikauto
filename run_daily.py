#!/usr/bin/env python3
# Script autonome: production de 3 episodes par jour sans Codex
import json, random, subprocess, sys, sqlite3
from pathlib import Path

ROOT = Path(r'C:\TikTokHistoryFactory')
ENGINE = ROOT / 'src' / 'v5_factory' / 'auto_engine.py'
DB = ROOT / 'data' / 'factory.db'
CATALOGUE = ROOT / 'data' / 'catalogue' / 'subjects.json'

def main():
    # Discovery: enrich catalogue with pre_sourced or online subjects
    disc_script = ROOT / 'src' / 'v5_factory' / 'discovery.py'
    if disc_script.exists():
        subprocess.run([sys.executable, str(disc_script)], check=False)
    # Charger les sujets
    cat = json.load(open(CATALOGUE, 'r', encoding='utf-8'))
    subjects = [s['slug'] for s in cat['subjects']]
    
    # Verifier les deja produits
    conn = sqlite3.connect(str(DB))
    c = conn.cursor()
    produced = set()
    c.execute('SELECT slug FROM auto_productions WHERE qc_passed=1')
    for row in c.fetchall():
        produced.add(row[0])
    conn.close()
    
    # Selectionner 3 sujets non encore produits
    available = [s for s in subjects if s not in produced]
    if len(available) < 3:
        print(f"[RUN DAILY] BLOCKED: insufficient queue ({len(available)} new subjects available, need 3). No duplication allowed.")
        return
    
    selected = random.sample(available, 3)
    print('=== TIKTOK HISTORY FACTORY - RUN DAILY ===')
    print('Selected:', selected)
    
    for slug in selected:
        print('Producing:', slug)
        subprocess.run([sys.executable, str(ENGINE), '--subject', slug], check=True)
    
    print('Done. Produced', len(selected), 'episodes.')

if __name__ == '__main__':
    main()

