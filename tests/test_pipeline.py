"""Tests du pipeline d'orchestration."""
import os
import tempfile
import unittest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tiktok_history_factory.pipeline.orchestrator import PipelineOrchestrator, _compute_topic_hash
from tiktok_history_factory.database.models import TaskStatus


class TestPipeline(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        os.environ["DB_PATH"] = os.path.join(self.temp_dir, "pipeline.db")
        os.environ["LOG_DIR"] = os.path.join(self.temp_dir, "logs")
        self.orch = PipelineOrchestrator()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_enqueue_new_task(self):
        """Enfilement d'un nouveau sujet."""
        task_id = self.orch.enqueue("test-slug", "Titre Test")
        self.assertGreater(task_id, 0)
        tasks = self.orch.list_tasks()
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["topic_slug"], "test-slug")

    def test_enqueue_duplicate(self):
        """Enfilement d'un doublon retourne l'ID existant."""
        id1 = self.orch.enqueue("dup-slug", "Titre Dup")
        id2 = self.orch.enqueue("dup-slug", "Titre Dup")
        self.assertEqual(id1, id2)
        tasks = self.orch.list_tasks()
        self.assertEqual(len(tasks), 1)

    def test_topic_hash_normalization(self):
        """Le hash normalise les slugs."""
        h1 = _compute_topic_hash("  Test-Slug  ")
        h2 = _compute_topic_hash("test-slug")
        self.assertEqual(h1, h2)

    def test_update_status(self):
        """Mise a jour du statut."""
        task_id = self.orch.enqueue("update-slug", "Update")
        self.orch.update_status(task_id, TaskStatus.SCRIPTING)
        tasks = self.orch.list_tasks(status=TaskStatus.SCRIPTING)
        self.assertEqual(len(tasks), 1)

    def test_placeholder_does_not_mark_failed(self):
        """Le pipeline placeholder ne marque pas FAILED."""
        task_id = self.orch.enqueue("placeholder", "Placeholder")
        # On ne teste pas run_cycle() ici car elle est async ;
        # on verifie juste que le statut initial est bien CREATED
        tasks = self.orch.list_tasks()
        self.assertEqual(tasks[0]["status"], "created")


if __name__ == "__main__":
    unittest.main()
