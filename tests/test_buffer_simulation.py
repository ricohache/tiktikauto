#!/usr/bin/env python3
"""Tests locaux (mocks) du Buffer Simulation Adapter.

Valide la logique de simulation sans appeler l'API Buffer réelle.
"""
import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

# Ensure imports resolve
os.sys.path.insert(0, r"C:\TikTokHistoryFactory\src\v5_factory")

from buffer_simulation_adapter import BufferSimulationAdapter, build_ai_description


class MockBufferAdapter:
    """Mock minimal de BufferAdapter pour les tests."""
    def __init__(self, has_tiktok=True, disconnected=False, locked=False):
        self._has_tiktok = has_tiktok
        self._disconnected = disconnected
        self._locked = locked

    def get_tiktok_channel(self, org_id=None):
        if not self._has_tiktok:
            return None
        return {
            "id": "tiktok-123",
            "name": "Test TikTok",
            "service": "TIKTOK",
            "isDisconnected": self._disconnected,
            "isLocked": self._locked,
        }


class TestBufferSimulationAdapter(unittest.TestCase):
    def setUp(self):
        self.tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp_db.close()
        self.db_path = Path(self.tmp_db.name)

    def tearDown(self):
        if self.db_path.exists():
            self.db_path.unlink()

    def test_simulate_publish_success(self):
        mock_buf = MockBufferAdapter()
        sim = BufferSimulationAdapter(mock_buf, db_path=self.db_path)
        result = sim.simulate_publish(
            slug="angolan-civil-war-1975",
            video_url="https://worker.dev/thf/angolan-civil-war-1975_b54b077af9055e23.mp4",
            description="Angolan Civil War (1975)",
        )
        self.assertEqual(result["status"], "SIMULATED")
        self.assertEqual(result["channel_id"], "tiktok-123")
        self.assertEqual(result["channel_name"], "Test TikTok")
        self.assertTrue(result["simulated_post_id"].startswith("SIM-"))
        self.assertEqual(result["payload"]["schedulingType"], "automatic")
        self.assertTrue(result["payload"]["aiAssisted"])
        self.assertTrue(result["payload"]["metadata"]["tiktok"]["isAiGenerated"])
        self.assertIn("Reconstitution historique générée par IA", result["payload"]["text"])

    def test_duplicate_prevention(self):
        mock_buf = MockBufferAdapter()
        sim = BufferSimulationAdapter(mock_buf, db_path=self.db_path)
        sim.simulate_publish(
            slug="angolan-civil-war-1975",
            video_url="https://worker.dev/thf/angolan-civil-war-1975_b54b077af9055e23.mp4",
            description="Angolan Civil War (1975)",
        )
        result = sim.simulate_publish(
            slug="angolan-civil-war-1975",
            video_url="https://worker.dev/thf/angolan-civil-war-1975_b54b077af9055e23.mp4",
            description="Angolan Civil War (1975)",
        )
        self.assertEqual(result["status"], "DUPLICATE")

    def test_missing_channel(self):
        mock_buf = MockBufferAdapter(has_tiktok=False)
        sim = BufferSimulationAdapter(mock_buf, db_path=self.db_path)
        result = sim.simulate_publish(
            slug="angolan-civil-war-1975",
            video_url="https://worker.dev/thf/angolan-civil-war-1975_b54b077af9055e23.mp4",
            description="Angolan Civil War (1975)",
        )
        self.assertEqual(result["status"], "MISSING_CHANNEL")

    def test_disconnected_channel(self):
        mock_buf = MockBufferAdapter(disconnected=True)
        sim = BufferSimulationAdapter(mock_buf, db_path=self.db_path)
        result = sim.simulate_publish(
            slug="angolan-civil-war-1975",
            video_url="https://worker.dev/thf/angolan-civil-war-1975_b54b077af9055e23.mp4",
            description="Angolan Civil War (1975)",
        )
        self.assertEqual(result["status"], "CHANNEL_DISCONNECTED")

    def test_locked_channel(self):
        mock_buf = MockBufferAdapter(locked=True)
        sim = BufferSimulationAdapter(mock_buf, db_path=self.db_path)
        result = sim.simulate_publish(
            slug="angolan-civil-war-1975",
            video_url="https://worker.dev/thf/angolan-civil-war-1975_b54b077af9055e23.mp4",
            description="Angolan Civil War (1975)",
        )
        self.assertEqual(result["status"], "CHANNEL_LOCKED")

    def test_sqlite_log(self):
        mock_buf = MockBufferAdapter()
        sim = BufferSimulationAdapter(mock_buf, db_path=self.db_path)
        sim.simulate_publish(
            slug="angolan-civil-war-1975",
            video_url="https://worker.dev/thf/angolan-civil-war-1975_b54b077af9055e23.mp4",
            description="Angolan Civil War (1975)",
        )
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute("SELECT slug, status, channel_id, simulated_post_id FROM buffer_simulations WHERE slug = ?",
                  ("angolan-civil-war-1975",))
        row = c.fetchone()
        conn.close()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], "angolan-civil-war-1975")
        self.assertEqual(row[1], "SIMULATED")
        self.assertEqual(row[2], "tiktok-123")
        self.assertTrue(row[3].startswith("SIM-"))

    def test_build_ai_description(self):
        desc = build_ai_description("Test description.")
        self.assertIn("Test description.", desc)
        self.assertIn("Reconstitution historique générée par IA", desc)

if __name__ == "__main__":
    unittest.main(verbosity=2)
