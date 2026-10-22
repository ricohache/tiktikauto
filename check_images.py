import os
from pathlib import Path
import hashlib

def check_images(work_dir):
    img_dir = Path(work_dir) / 'images'
    if not img_dir.exists():
        return []
    files = sorted(img_dir.glob('*.png'))
    hashes = {}
    dups = []
    for f in files:
        h = hashlib.sha256(f.read_bytes()).hexdigest()[:16]
        if h in hashes:
            dups.append((f.name, hashes[h]))
        else:
            hashes[h] = f.name
    return dups

for slug in ['pende-revolt-1931', 'madagascar-revolt-1947', 'ruben-um-nyobe', 'tirailleurs-senegalais']:
    work = f'C:/TikTokHistoryFactory/work/auto-{slug}'
    dups = check_images(work)
    if dups:
        print(f'{slug}: {len(dups)} DUPLICATES detected')
        for dup, orig in dups:
            print(f'  {dup} == {orig}')
    else:
        print(f'{slug}: All images unique')
