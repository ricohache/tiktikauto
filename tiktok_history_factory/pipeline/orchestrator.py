
"""Orchestrateur principal du pipeline de production video."""
import asyncio
import hashlib
import logging
from pathlib import Path
from typing import Optional

from tiktok_history_factory.config.settings import Settings
from tiktok_history_factory.database.models import DatabaseManager, TaskStatus, VideoTask

logger = logging.getLogger(__name__)

def _compute_topic_hash(topic_slug: str) -> str:
    normalized = topic_slug.lower().strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

class PipelineOrchestrator:
    """Gere le cycle de vie des taches de production video."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or Settings()
        self.db = DatabaseManager(str(self.settings.DB_PATH))

    def enqueue(self, topic_slug: str, topic_title: str, topic_description: str = "") -> int:
        topic_hash = _compute_topic_hash(topic_slug)
        existing = self.db.get_task_by_hash(topic_hash)
        if existing:
            logger.info('Sujet deja en file : %s (id=%d)', topic_slug, existing['id'])
            return existing['id']
        task = VideoTask(
            topic_slug=topic_slug,
            topic_title=topic_title,
            topic_description=topic_description,
            topic_hash=topic_hash,
            status=TaskStatus.CREATED,
            max_attempts=self.settings.MAX_RETRY_ATTEMPTS,
        )
        task_id = self.db.insert_video_task(task)
        logger.info("Tache cree : id=%d, sujet=%s", task_id, topic_slug)
        return task_id

    def get_next_pending(self) -> Optional[VideoTask]:
        return self.db.get_next_pending_task()

    def update_status(self, task_id: int, status: TaskStatus, error: Optional[str] = None) -> None:
        self.db.update_task_status(task_id, status, error)
        logger.info("Statut mis a jour : id=%d -> %s", task_id, status.value)

    def list_tasks(self, status: Optional[TaskStatus] = None, limit: int = 50):
        return self.db.list_tasks(status=status, limit=limit)

    async def run_cycle(self) -> None:
        task = self.get_next_pending()
        if not task:
            logger.info("Aucune tache en attente.")
            return
        logger.info("Cycle pour tache id=%d | sujet=%s", task.id, task.topic_slug)
        import json
        from tiktok_history_factory.pipeline.pilot import PilotRunner
        dossier_path = Path(self.settings.PILOT_DOSSIER)
        dossier = json.loads(dossier_path.read_text(encoding='utf-8'))
        if task.topic_slug != dossier['slug']:
            self.update_status(task.id, TaskStatus.BLOCKED, 'No reviewed dossier for this task; use pilot --dossier')
            raise RuntimeError('A reviewed dossier matching this task is required')
        await asyncio.to_thread(PilotRunner(self.settings, self.db, task.id, dossier_path).run)

    async def run(self) -> None:
        logger.info("Orchestrateur demarre. Max quotidien=%d", self.settings.MAX_DAILY_VIDEOS)
        await self.run_cycle()

def main() -> None:
    settings = Settings()
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    log_dir = Path(settings.LOG_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_dir / "orchestrator.log"),
        ],
    )
    Settings.ensure_directories()
    orchestrator = PipelineOrchestrator()
    asyncio.run(orchestrator.run())

if __name__ == "__main__":
    main()
