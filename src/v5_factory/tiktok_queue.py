"""Gestionnaire de file de publication TikTok via SQLite.
Aucune publication reelle n'est effectuee sans activation explicite.
"""
import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

DB_SCHEMA = '''
CREATE TABLE IF NOT EXISTS tiktok_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT NOT NULL UNIQUE,
    title_fr TEXT,
    description_fr TEXT,
    hashtags TEXT,
    mp4_path TEXT,
    thumbnail_path TEXT,
    sources_json TEXT,
    mention_ia TEXT DEFAULT 'Images generees par IA. Scenario historique base sur des sources academiques.',
    status TEXT DEFAULT 'pending',
    scheduled_at TEXT,
    published_at TEXT,
    tiktok_video_id TEXT,
    error TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS production_state (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS gpu_lock (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    locked INTEGER DEFAULT 0,
    slug TEXT,
    started_at TEXT,
    pid INTEGER
);
'''

class TikTokQueue:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path))
        conn.executescript(DB_SCHEMA)
        conn.commit()
        conn.close()

    def add_episode(self, slug: str, title_fr: str, description_fr: str, hashtags: str,
                    mp4_path: str, thumbnail_path: str, sources: List[Dict]):
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute('''
            INSERT OR IGNORE INTO tiktok_queue
            (slug, title_fr, description_fr, hashtags, mp4_path, thumbnail_path, sources_json, status)
            VALUES (?,?,?,?,?,?,?,?)
        ''', (slug, title_fr, description_fr, hashtags, mp4_path, thumbnail_path,
              json.dumps(sources, ensure_ascii=False), 'pending'))
        conn.commit()
        conn.close()

    def list_pending(self) -> List[Dict]:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM tiktok_queue WHERE status='pending' ORDER BY created_at")
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        return rows

    def list_all(self) -> List[Dict]:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM tiktok_queue ORDER BY created_at")
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        return rows

    def update_status(self, slug: str, status: str, error: str = None, tiktok_video_id: str = None):
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute('''
            UPDATE tiktok_queue SET status=?, error=?, tiktok_video_id=? WHERE slug=?''',
            (status, error, tiktok_video_id, slug))
        conn.commit()
        conn.close()

    def acquire_gpu_lock(self, slug: str, pid: int) -> bool:
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute("SELECT locked FROM gpu_lock WHERE id=1")
        row = c.fetchone()
        if row and row[0]:
            conn.close()
            return False
        if not row:
            c.execute("INSERT INTO gpu_lock (id, locked, slug, started_at, pid) VALUES (1,1,?,?,?)",
                      (slug, datetime.now().isoformat(), pid))
        else:
            c.execute("UPDATE gpu_lock SET locked=1, slug=?, started_at=?, pid=? WHERE id=1",
                      (slug, datetime.now().isoformat(), pid))
        conn.commit()
        conn.close()
        return True

    def release_gpu_lock(self) -> bool:
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute("UPDATE gpu_lock SET locked=0, slug=NULL, started_at=NULL, pid=NULL WHERE id=1")
        conn.commit()
        conn.close()
        return True

    def get_gpu_status(self) -> Optional[Dict]:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM gpu_lock WHERE id=1")
        row = c.fetchone()
        conn.close()
        return dict(row) if row else None

    def set_state(self, key: str, value: str):
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO production_state (key, value, updated_at)
                       VALUES (?, ?, ?)''', (key, value, datetime.now().isoformat()))
        conn.commit()
        conn.close()

    def get_state(self, key: str, default: str = '') -> str:
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute("SELECT value FROM production_state WHERE key=?", (key,))
        row = c.fetchone()
        conn.close()
        return row[0] if row else default

if __name__ == '__main__':
    q = TikTokQueue(Path(r'C:\TikTokHistoryFactory\data\factory.db'))
    print('TikTokQueue initialized. GPU status:', q.get_gpu_status())
