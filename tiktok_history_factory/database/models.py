
"""Modeles de donnees SQLite natif pour le pipeline de production."""
import enum
import sqlite3
from dataclasses import dataclass
from typing import Optional, List, Dict, Any


class TaskStatus(str, enum.Enum):
    CREATED = "created"
    QUEUED = "queued"
    RESEARCHING = "researching"
    FACT_CHECKING = "fact_checking"
    WAITING_FOR_SOURCES = "waiting_for_sources"
    SCRIPTING = "scripting"
    STORYBOARDING = "storyboarding"
    GENERATING_IMAGES = "generating_images"
    GENERATING_VIDEO = "generating_video"
    GENERATING_AUDIO = "generating_audio"
    RENDERING = "rendering"
    TECH_QC = "tech_qc"
    EDITORIAL_QC = "editorial_qc"
    AWAITING_REVIEW = "awaiting_review"
    APPROVED = "approved"
    READY_FOR_EXPORT = "ready_for_export"
    READY_FOR_UPLOAD = "ready_for_upload"
    UPLOADING = "uploading"
    SUBMITTED = "submitted"
    PUBLISHED_CONFIRMED = "published_confirmed"
    BLOCKED = "blocked"
    RETRY_WAIT = "retry_wait"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Topic:
    id: Optional[int] = None
    created_at: Optional[str] = None
    slug: str = ""
    title: str = ""
    description: str = ""
    language: str = "fr"
    category: str = ""
    event_date: str = ""
    normalized_hash: str = ""


@dataclass
class SourceDocument:
    id: Optional[int] = None
    topic_id: int = 0
    url: str = ""
    title: str = ""
    content_snippet: str = ""
    retrieved_at: Optional[str] = None
    trust_score: float = 0.0
    source_type: str = ""


@dataclass
class Claim:
    id: Optional[int] = None
    topic_id: int = 0
    statement: str = ""
    certainty: str = "UNVERIFIED"
    sources: str = ""
    verifier_notes: str = ""


@dataclass
class CharacterSheet:
    id: Optional[int] = None
    topic_id: int = 0
    name: str = ""
    description: str = ""
    visual_prompt: str = ""
    consistency_hash: str = ""


@dataclass
class VideoTask:
    id: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    topic_slug: str = ""
    topic_title: str = ""
    topic_description: str = ""
    status: TaskStatus = TaskStatus.CREATED
    attempt_count: int = 0
    max_attempts: int = 3
    topic_hash: str = ""
    research_data: str = ""
    script_text: str = ""
    media_paths: str = ""
    tiktok_video_id: str = ""
    published_at: Optional[str] = None
    last_error: str = ""


class DatabaseManager:
    """Gestionnaire SQLite natif avec schema versionne."""

    SCHEMA_VERSION = 1

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._connect() as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS schema_versions (version INTEGER PRIMARY KEY, applied_at TEXT DEFAULT CURRENT_TIMESTAMP)")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS topics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    slug TEXT NOT NULL UNIQUE,
                    title TEXT NOT NULL,
                    description TEXT,
                    language TEXT DEFAULT 'fr',
                    category TEXT,
                    event_date TEXT,
                    normalized_hash TEXT NOT NULL UNIQUE
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS source_documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic_id INTEGER NOT NULL,
                    url TEXT NOT NULL,
                    title TEXT,
                    content_snippet TEXT,
                    retrieved_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    trust_score REAL DEFAULT 0.0,
                    source_type TEXT,
                    FOREIGN KEY (topic_id) REFERENCES topics(id)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS claims (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic_id INTEGER NOT NULL,
                    statement TEXT NOT NULL,
                    certainty TEXT DEFAULT 'UNVERIFIED',
                    sources TEXT,
                    verifier_notes TEXT,
                    FOREIGN KEY (topic_id) REFERENCES topics(id)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS character_sheets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    visual_prompt TEXT,
                    consistency_hash TEXT,
                    FOREIGN KEY (topic_id) REFERENCES topics(id)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS video_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    topic_slug TEXT NOT NULL,
                    topic_title TEXT NOT NULL,
                    topic_description TEXT,
                    status TEXT DEFAULT 'created',
                    attempt_count INTEGER DEFAULT 0,
                    max_attempts INTEGER DEFAULT 3,
                    topic_hash TEXT NOT NULL UNIQUE,
                    research_data TEXT,
                    script_text TEXT,
                    media_paths TEXT,
                    tiktok_video_id TEXT,
                    published_at TEXT,
                    last_error TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS run_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    task_id INTEGER,
                    phase TEXT,
                    duration_ms INTEGER,
                    success INTEGER,
                    error TEXT,
                    vram_peak_mb REAL,
                    ram_peak_mb REAL
                )
            """)
            conn.commit()

    def insert_topic(self, topic: Topic) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO topics (slug, title, description, language, category, event_date, normalized_hash) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (topic.slug, topic.title, topic.description, topic.language, topic.category, topic.event_date, topic.normalized_hash)
            )
            conn.commit()
            return cur.lastrowid

    def insert_video_task(self, task: VideoTask) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO video_tasks (topic_slug, topic_title, topic_description, status, max_attempts, topic_hash) VALUES (?, ?, ?, ?, ?, ?)",
                (task.topic_slug, task.topic_title, task.topic_description, task.status.value, task.max_attempts, task.topic_hash)
            )
            conn.commit()
            return cur.lastrowid

    def get_next_pending_task(self) -> Optional[VideoTask]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM video_tasks WHERE status = 'created' ORDER BY created_at ASC LIMIT 1").fetchone()
            if row:
                return VideoTask(**{k: row[k] for k in row.keys()})
            return None

    def get_task_by_hash(self, topic_hash):
        with self._connect() as conn:
            row = conn.execute('SELECT * FROM video_tasks WHERE topic_hash=?', (topic_hash,)).fetchone()
            return dict(row) if row else None

    def update_task_status(self, task_id: int, status: TaskStatus, error: Optional[str] = None):
        with self._connect() as conn:
            if error:
                conn.execute(
                    "UPDATE video_tasks SET status = ?, last_error = ?, attempt_count = attempt_count + 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (status.value, error, task_id)
                )
            else:
                conn.execute(
                    "UPDATE video_tasks SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (status.value, task_id)
                )
            conn.commit()

    def list_tasks(self, status: Optional[TaskStatus] = None, limit: int = 50) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            if status:
                rows = conn.execute("SELECT * FROM video_tasks WHERE status = ? ORDER BY created_at DESC LIMIT ?", (status.value, limit)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM video_tasks ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
            return [dict(r) for r in rows]

    def record_phase(self, task_id, phase, duration_ms, success, error=''):
        with self._connect() as conn:
            conn.execute('INSERT INTO run_history (task_id,phase,duration_ms,success,error) VALUES (?,?,?,?,?)',
                         (task_id, phase, duration_ms, int(success), error))

    def save_production(self, task_id, research, script, media):
        import json
        with self._connect() as conn:
            conn.execute('UPDATE video_tasks SET research_data=?,script_text=?,media_paths=?,updated_at=CURRENT_TIMESTAMP WHERE id=?',
                         (json.dumps(research, ensure_ascii=False), script, json.dumps(media, ensure_ascii=False), task_id))


def init_database(db_path: str) -> DatabaseManager:
    return DatabaseManager(db_path)
