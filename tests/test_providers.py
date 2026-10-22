
"""Tests des fournisseurs."""
import unittest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tiktok_history_factory.providers.tiktok_official import TikTokOfficialProvider
from tiktok_history_factory.providers.local_export import LocalExportProvider
from tiktok_history_factory.providers.ffmpeg import FFmpegProvider


class TestTikTokProvider(unittest.TestCase):
    def test_local_export_by_default(self):
        """Par defaut : LOCAL_EXPORT, aucun appel API."""
        provider = TikTokOfficialProvider("", "", "")
        result = provider.upload_video("/tmp/test.mp4", "Titre", "Desc")
        self.assertEqual(result["status"], "READY_FOR_EXPORT")
        self.assertEqual(result["mode"], "LOCAL_EXPORT")

    def test_blocked_without_credentials(self):
        """Bloque si credentials manquants."""
        provider = TikTokOfficialProvider("", "", "", mode="TIKTOK_DRAFT")
        result = provider.upload_video("/tmp/test.mp4", "Titre", "Desc")
        self.assertEqual(result["status"], "BLOCKED")


class TestLocalExport(unittest.TestCase):
    def test_export_creates_manifest(self):
        """L'export cree un manifeste."""
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / 'unit-fixture.mp4'
            source.write_bytes(b'explicit simulated media bytes for copy-contract unit test')
            provider = LocalExportProvider()
            result = provider.export(str(source), {"title": "Test"}, str(Path(td)/'export'))
            self.assertEqual(result["status"], "READY_FOR_EXPORT")
            self.assertTrue(Path(result["manifest"]).exists())
            self.assertEqual(Path(result['video_path']).read_bytes(), source.read_bytes())

    def test_export_blocks_missing_video(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(LocalExportProvider().export('missing.mp4', {}, td)['status'], 'BLOCKED')


class TestFFmpegProvider(unittest.TestCase):
    def test_probe_without_ffmpeg(self):
        """Graceful degradation si FFmpeg absent."""
        provider = FFmpegProvider(ffmpeg_path="nonexistent", ffprobe_path="nonexistent")
        result = provider.probe_file("/tmp/nonexistent.mp4")
        self.assertIn("error", result)


if __name__ == "__main__":
    unittest.main()
