#!/usr/bin/env python3
"""Orchestrateur autonome TikTokHistoryFactory V5.
Executable hors de Codex. Pipeline complet : selection -> storyboard -> images -> narration -> montage -> QC -> export.
Aucune publication TikTok activee par defaut.
"""
import argparse
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

_V5_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_V5_DIR))
sys.path.insert(0, str(_V5_DIR.parent.parent / 'TikTokHistoryFactory_finish_v5'))

from discovery import HistoryDiscovery
from auto_engine import AutoProductionEngine
from catalogue import SubjectCatalogue
from tiktok_queue import TikTokQueue

DEFAULT_ROOT = Path(r'C:\TikTokHistoryFactory')
TARGET_SECONDS = 90


class AutonomousFactory:
    def __init__(self, project: Path = DEFAULT_ROOT):
        self.project = project.resolve()
        self.db_path = self.project / 'data' / 'factory.db'
        self.catalogue_path = self.project / 'data' / 'catalogue' / 'subjects.json'
        self.pre_sourced_dir = self.project / 'data' / 'pre_sourced'
        self.output_dir = self.project / 'output'
        self.queue = TikTokQueue(self.db_path)
        self.engine = None

    def status(self):
        print('=== ETAT DE L USINE ===')
        cat = SubjectCatalogue(self.catalogue_path)
        total = len(cat.subjects)
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        try:
            c.execute('SELECT slug, status FROM auto_productions')
            produced = {r[0]: r[1] for r in c.fetchall()}
        except sqlite3.OperationalError:
            produced = {}
        conn.close()
        completed = [s for s, st in produced.items() if st == 'completed']
        print(f'Sujets catalogue: {total}')
        print(f'Productions: {len(produced)} | Terminees: {len(completed)}')
        gpu = self.queue.get_gpu_status()
        if gpu and gpu.get('locked'):
            print(f'GPU OCCUPEE par {gpu["slug"]} (PID {gpu["pid"]}) depuis {gpu["started_at"]}')
        else:
            print('GPU: disponible')
        pending = self.queue.list_pending()
        print(f'File TikTok: {len(pending)} episode(s) en attente')

    def discover_and_select(self, count: int = 3) -> List[Dict]:
        disc = HistoryDiscovery(self.db_path, self.catalogue_path, self.pre_sourced_dir)
        disc._test_network = self._test_network_real
        found = disc.discover(count)
        if not found:
            print('[FACTORY] BLOCKED: aucun nouveau sujet disponible.')
        return found

    def _test_network_real(self) -> bool:
        try:
            import urllib.request
            req = urllib.request.Request('https://en.wikipedia.org/api/rest_v1/page/summary/World_War_II',
                                           headers={'User-Agent': 'TikTokHistoryFactory/1.0'}, method='HEAD')
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status in (200, 204, 301, 302)
        except Exception:
            return False

    def produce_one(self, slug: str, run_id: str = "") -> Optional[Path]:
        if not self.engine:
            self.engine = AutoProductionEngine(self.project)
        gpu_ok = self.queue.acquire_gpu_lock(slug, os.getpid())
        if not gpu_ok:
            print(f'[FACTORY] BLOCKED: GPU occupee. Impossible de produire {slug} maintenant.')
            return None
        try:
            result = self.engine.produce_subject(slug, run_id=run_id)
            mp4 = result.get('mp4')
            if mp4:
                print(f'[FACTORY] Production terminee: {mp4}')
                return Path(mp4)
        except Exception as e:
            print(f'[FACTORY] ERREUR production {slug}: {e}')
        finally:
            self.queue.release_gpu_lock()
        return None

    def run_batch(self, count: int = 3):
        subjects = self.discover_and_select(count)
        if len(subjects) < count:
            print(f'[FACTORY] File insuffisante ({len(subjects)}/{count}). Pas de duplication.')
            return []
        results = []
        for subj in subjects:
            slug = subj['slug']
            print(f'\n=== PRODUCTION: {slug} ===')
            mp4 = self.produce_one(slug, run_id=args.run_id)
            if mp4:
                self._prepare_tiktok_queue(subj, mp4)
                results.append({'slug': slug, 'mp4': str(mp4), 'status': 'completed'})
            else:
                results.append({'slug': slug, 'status': 'failed'})
        return results

    def _prepare_tiktok_queue(self, subject: Dict, mp4_path: Path):
        title = subject.get('title_fr', subject['title_en'])
        desc = subject.get('summary_fr', subject['summary_en'])[:300]
        hashtags = '#Histoire #Afrique #Decolonisation #HistoireOubliee #TikTokHistoryFactory'
        thumb = self._generate_thumbnail(mp4_path)
        self.queue.add_episode(
            slug=subject['slug'],
            title_fr=title,
            description_fr=desc,
            hashtags=hashtags,
            mp4_path=str(mp4_path),
            thumbnail_path=str(thumb) if thumb else '',
            sources=subject.get('sources', [])
        )
        print(f'[TIKTOK QUEUE] {subject["slug"]} ajoute a la file de publication.')

    def _generate_thumbnail(self, mp4_path: Path) -> Optional[Path]:
        thumb = mp4_path.parent / (mp4_path.stem + '-thumbnail.jpg')
        ffmpeg = self.project / 'ffmpeg' / 'bin' / 'ffmpeg.exe'
        if not ffmpeg.exists():
            ffmpeg = 'ffmpeg'
        try:
            subprocess.run([str(ffmpeg), '-y', '-i', str(mp4_path), '-ss', '00:00:45',
                           '-vframes', '1', '-q:v', '2', str(thumb)],
                          check=True, capture_output=True)
            return thumb
        except Exception as e:
            print(f'[THUMB] Erreur miniature: {e}')
            return None

    def resume_interrupted(self):
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        try:
            c.execute("SELECT slug, status, output_dir FROM auto_productions WHERE status IN ('pending','storyboarding','storyboard_ready','rendering','failed')")
            rows = c.fetchall()
        except sqlite3.OperationalError:
            rows = []
        conn.close()
        if not rows:
            print('[FACTORY] Aucune production interrompue a reprendre.')
            return []
        results = []
        for slug, status, outdir in rows:
            print(f'[RESUME] Reprise de {slug} (status: {status})')
            mp4 = self.produce_one(slug, run_id="")
            if mp4:
                results.append({'slug': slug, 'mp4': str(mp4), 'status': 'completed'})
        return results

    def export_ready_episodes(self):
        ready = self.project / 'output' / 'ready'
        ready.mkdir(exist_ok=True)
        pending = self.queue.list_pending()
        for ep in pending:
            src = Path(ep['mp4_path'])
            if src.exists():
                dest = ready / (ep['slug'] + '.mp4')
                import shutil
                shutil.copy2(str(src), str(dest))
                meta = {
                    'slug': ep['slug'],
                    'title_fr': ep['title_fr'],
                    'description_fr': ep['description_fr'],
                    'hashtags': ep['hashtags'],
                    'sources': json.loads(ep['sources_json']) if ep['sources_json'] else [],
                    'mention_ia': ep['mention_ia']
                }
                (ready / (ep['slug'] + '.json')).write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding='utf-8')
                print(f'[EXPORT] {ep["slug"]} pret pour TikTok.')


def main():
    ap = argparse.ArgumentParser(description='TikTokHistoryFactory V5 - Usine autonome')
    ap.add_argument('--project', type=Path, default=DEFAULT_ROOT)
    ap.add_argument('--status', action='store_true', help='Afficher l etat')
    ap.add_argument('--batch', type=int, default=0, help='Produire N episodes')
    ap.add_argument('--resume', action='store_true', help='Reprendre les productions interrompues')
    ap.add_argument('--export', action='store_true', help='Exporter les episodes prets')
    ap.add_argument('--run-id', type=str, default='', help='Identifiant de run pour tracabilite')
    ap.add_argument('--subject', type=str, help='Produire un sujet specifique')
    args = ap.parse_args()

    factory = AutonomousFactory(args.project)

    if args.status:
        factory.status()
        return
    if args.resume:
        factory.resume_interrupted()
        return
    if args.export:
        factory.export_ready_episodes()
        return
    if args.subject:
        factory.produce_one(args.subject, run_id=args.run_id)
        return
    if args.batch > 0:
        factory.run_batch(args.batch)
        return

    print('Usage: autonomous_runner.py --status | --batch N | --resume | --export | --subject SLUG')


if __name__ == '__main__':
    main()
