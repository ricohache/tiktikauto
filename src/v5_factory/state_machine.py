"""SQLite state machine for TikTokHistoryFactory pipeline.

Transitions:
    DISCOVERED => PRODUCING => PRODUCED => QC_PASSED => R2_UPLOADING => R2_VERIFIED
    => BUFFER_SUBMITTED => PUBLICATION_CONFIRMED

Errors produce FAILED at the current step with explicit diagnostic.
"""
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

VALID_TRANSITIONS = {
    'DISCOVERED': ['PRODUCING', 'FAILED'],
    'PRODUCING': ['PRODUCED', 'FAILED'],
    'PRODUCED': ['QC_PASSED', 'QC_FAILED', 'FAILED'],
    'QC_PASSED': ['R2_UPLOADING', 'R2_FAILED', 'FAILED'],
    'R2_UPLOADING': ['R2_VERIFIED', 'R2_FAILED', 'FAILED'],
    'R2_VERIFIED': ['BUFFER_SUBMITTED', 'BUFFER_FAILED', 'FAILED'],
    'BUFFER_SUBMITTED': ['PUBLICATION_CONFIRMED', 'PUBLICATION_FAILED', 'FAILED'],
    'PUBLICATION_CONFIRMED': [],
    'QC_FAILED': [],
    'R2_FAILED': [],
    'BUFFER_FAILED': [],
    'PUBLICATION_FAILED': [],
    'FAILED': [],
}

class PipelineStateMachine:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_tables()

    def _init_tables(self):
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS orchestrator_runs (
                run_id TEXT PRIMARY KEY,
                slug TEXT,
                status TEXT DEFAULT 'DISCOVERED',
                step TEXT DEFAULT 'init',
                mp4_path TEXT,
                r2_key TEXT,
                r2_url TEXT,
                worker_url TEXT,
                buffer_post_id TEXT,
                buffer_status TEXT,
                error TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS run_transitions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT,
                from_status TEXT,
                to_status TEXT,
                step TEXT,
                error TEXT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

    def create_run(self, run_id: str, slug: str) -> bool:
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute('INSERT OR IGNORE INTO orchestrator_runs (run_id, slug, status, step) VALUES (?,?,?,?)',
                  (run_id, slug, 'DISCOVERED', 'discovered'))
        conn.commit()
        conn.close()
        return True

    def transition(self, run_id: str, to_status: str, step: str = '', error: str = '',
                    mp4_path: str = '', r2_key: str = '', r2_url: str = '',
                    worker_url: str = '', buffer_post_id: str = '', buffer_status: str = '') -> bool:
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute('SELECT status FROM orchestrator_runs WHERE run_id=?', (run_id,))
        row = c.fetchone()
        if not row:
            conn.close()
            return False
        from_status = row[0]
        if to_status not in VALID_TRANSITIONS.get(from_status, []):
            if to_status != from_status:
                conn.close()
                raise ValueError(f"Invalid transition: {from_status} -> {to_status}")
        completed_at = ''
        if to_status in ('PUBLICATION_CONFIRMED', 'QC_FAILED', 'R2_FAILED', 'BUFFER_FAILED', 'PUBLICATION_FAILED', 'FAILED'):
            completed_at = datetime.now().isoformat()
        fields = []
        values = []
        if mp4_path:
            fields.append('mp4_path=?')
            values.append(mp4_path)
        if r2_key:
            fields.append('r2_key=?')
            values.append(r2_key)
        if r2_url:
            fields.append('r2_url=?')
            values.append(r2_url)
        if worker_url:
            fields.append('worker_url=?')
            values.append(worker_url)
        if buffer_post_id:
            fields.append('buffer_post_id=?')
            values.append(buffer_post_id)
        if buffer_status:
            fields.append('buffer_status=?')
            values.append(buffer_status)
        if error:
            fields.append('error=?')
            values.append(error)
        if step:
            fields.append('step=?')
            values.append(step)
        fields.append('status=?')
        values.append(to_status)
        fields.append('updated_at=?')
        values.append(datetime.now().isoformat())
        if completed_at:
            fields.append('completed_at=?')
            values.append(completed_at)
        values.append(run_id)
        sql = f"UPDATE orchestrator_runs SET {', '.join(fields)} WHERE run_id=?"
        c.execute(sql, values)
        c.execute('INSERT INTO run_transitions (run_id, from_status, to_status, step, error) VALUES (?,?,?,?,?)',
                  (run_id, from_status, to_status, step, error))
        conn.commit()
        conn.close()
        return True

    def get_run(self, run_id: str) -> Optional[Dict]:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute('SELECT * FROM orchestrator_runs WHERE run_id=?', (run_id,))
        row = c.fetchone()
        conn.close()
        return dict(row) if row else None

    def list_runs(self, slug: str = '') -> List[Dict]:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        if slug:
            c.execute('SELECT * FROM orchestrator_runs WHERE slug=? ORDER BY updated_at DESC', (slug,))
        else:
            c.execute('SELECT * FROM orchestrator_runs ORDER BY updated_at DESC')
        rows = c.fetchall()
        conn.close()
        return [dict(r) for r in rows]