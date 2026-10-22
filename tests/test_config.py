
"""Tests de configuration."""
import os
import tempfile
import unittest
from pathlib import Path

# Ajouter le projet au path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tiktok_history_factory.config.settings import Settings
from tiktok_history_factory.config.validation import ConfigValidator


class TestSettings(unittest.TestCase):
    def test_default_values(self):
        """Les valeurs par defaut sont securisees."""
        s = Settings()
        self.assertEqual(s.TIKTOK_PUBLISH_MODE, "LOCAL_EXPORT")
        self.assertFalse(s.TIKTOK_PUBLISH_ENABLED)
        self.assertEqual(s.LOG_LEVEL, "INFO")
        self.assertEqual(s.MAX_DAILY_VIDEOS, 3)
        self.assertEqual(s.MAX_RETRY_ATTEMPTS, 3)
        self.assertEqual(s.KWH_PRICE_EUR, 0.20)

    def test_no_secrets_in_code(self):
        """Aucun secret n'est code en dur."""
        s = Settings()
        self.assertEqual(s.TIKTOK_ACCESS_TOKEN, "")
        self.assertEqual(s.TIKTOK_CLIENT_SECRET, "")
        self.assertEqual(s.OLLAMA_API_KEY, "")

    def test_paths_are_absolute(self):
        """Les chemins sont absolus depuis la racine projet."""
        s = Settings()
        self.assertTrue(s.DB_PATH.is_absolute())
        self.assertTrue(s.LOG_DIR.is_absolute())

    def test_ensure_directories(self):
        """Creation des repertoires fonctionne."""
        with tempfile.TemporaryDirectory() as td:
            os.environ["DB_PATH"] = str(Path(td) / "data" / "test.db")
            os.environ["LOG_DIR"] = str(Path(td) / "logs")
            s = Settings()
            s.ensure_directories()
            self.assertTrue(s.DB_PATH.parent.exists())
            self.assertTrue(s.LOG_DIR.exists())


class TestConfigValidator(unittest.TestCase):
    def test_default_config_is_valid(self):
        """La configuration par defaut est valide."""
        s = Settings()
        validator = ConfigValidator(s)
        result = validator.validate()
        self.assertTrue(result["valid"], f"Erreurs : {result['errors']}")


if __name__ == "__main__":
    unittest.main()
