#!/usr/bin/env python3
"""Menu de publication TikTok / Buffer — consultation uniquement, aucun upload reel."""
import json
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(r'C:\TikTokHistoryFactory')
sys.path.insert(0, str(ROOT / 'src' / 'v5_factory'))

from secure_credentials import CredentialStore

def get_queue():
    conn = sqlite3.connect(str(ROOT / 'data' / 'factory.db'))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""
        SELECT slug, title_fr, description_fr, hashtags, mp4_path, thumbnail_path,
               sources_json, mention_ia, status, scheduled_at, published_at, tiktok_video_id, error
        FROM tiktok_queue
        ORDER BY status, created_at
    """)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def show_ready():
    rows = get_queue()
    ready = [r for r in rows if r['status'] == 'pending']
    published = [r for r in rows if r['status'] == 'published']
    blocked = [r for r in rows if r['status'] not in ('pending', 'published')]
    
    print(f'\n=== FILE TIKTOK / BUFFER ===')
    print(f'Prets a publier: {len(ready)}')
    print(f'Deja publies: {len(published)}')
    print(f'Bloques/erreurs: {len(blocked)}')
    print(f'TOTAL: {len(rows)} episodes')
    
    print('\n--- EPISODES PRETS ---')
    for i, r in enumerate(ready, 1):
        mp4 = Path(r['mp4_path'])
        size_mb = round(mp4.stat().st_size / (1024*1024), 1) if mp4.exists() else 0
        thumb = 'OUI' if r['thumbnail_path'] and Path(r['thumbnail_path']).exists() else 'NON'
        sources = json.loads(r['sources_json']) if r['sources_json'] else []
        src_count = len(sources)
        print(f'{i}. {r["slug"]}')
        print(f'   Titre: {r["title_fr"]}')
        print(f'   MP4: {size_mb}MB | Miniature: {thumb} | Sources: {src_count}')
        print(f'   Hashtags: {r["hashtags"]}')
        print(f'   Mention IA: {r["mention_ia"]}')
    
    if published:
        print('\n--- EPISODES PUBLIES ---')
        for r in published:
            print(f'   {r["slug"]} | TikTok ID: {r["tiktok_video_id"]} | Date: {r["published_at"]}')
    
    if blocked:
        print('\n--- EPISODES BLOQUES ---')
        for r in blocked:
            print(f'   {r["slug"]} | Status: {r["status"]} | Erreur: {r["error"]}')

def show_api_status():
    print('\n=== ETAT API TIKTOK (OFFICIELLE) ===')
    print('Mode actuel: LOCAL_EXPORT (aucun appel API)')
    print('Content Posting API: NON CONFIGUREE')
    print('Eligibilite: necessite compte Developpeur TikTok approuve')
    print('')
    print('=== ETAT BUFFER ===')
    store = CredentialStore()
    has_token = store.has("buffer_access_token")
    print(f'Cle API Buffer stockee: {"OUI" if has_token else "NON"}')
    if has_token:
        print('Pour tester la connexion Buffer (lecture seule):')
        print('  C:\\TikTokHistoryFactory\\.venv\\Scripts\\python.exe C:\\TikTokHistoryFactory\\src\\v5_factory\\buffer_adapter.py')
        print('  (requiert la cle stockee via DPAPI)')
    else:
        print('Pour configurer la cle Buffer:')
        print('  Option 9 du menu PowerShell, ou:')
        print('  C:\\TikTokHistoryFactory\\.venv\\Scripts\\python.exe C:\\TikTokHistoryFactory\\src\\v5_factory\\buffer_config_cli.py')
    print('')
    print('Capacites Buffer pour TikTok (documentation officielle):')
    print('  ✓ Publication automatique (mode Automatic / Direct Publishing) disponible')
    print('  ✓ Programmation horaire supportee (dueAt + schedulingType=customScheduled)')
    print('  ✓ Signalement IA via aiAssisted + metadata.tiktok.isAiGenerated')
    print('  ✓ Mise en file automatique (mode=addToQueue)')
    print('  ✗ Upload direct de fichier MP4: NON — URL publique HTTPS requise')
    print('  ✗ Miniature depuis fichier local: NON — URL publique requise')
    print('')
    print('Options d\'hebergement video pour Buffer:')
    print('  1. Cloudinary (25 credits/mois gratuits, URL illimitee)')
    print('  2. Cloudflare R2 (10 Go/mois gratuits, necessite compte CF)')
    print('  3. Serveur perso avec HTTPS (controle total)')
    print('  4. Transfer.sh (ephemere, non recommande pour production)')
    print('')
    print('AUCUNE video n\'a ete uploadee. AUCUNE publication creee.')

def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--api-status':
        show_api_status()
        return
    show_ready()
    show_api_status()

if __name__ == '__main__':
    main()
