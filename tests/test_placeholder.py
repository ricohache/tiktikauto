"""Tests unitaires — placeholder pour l'étape 1."""


def test_imports():
    """Vérifie que tous les packages principaux sont importables."""
    from tiktok_history_factory import __version__
    from tiktok_history_factory.config import Settings
    from tiktok_history_factory.database import TaskStatus, VideoTask, init_database
    from tiktok_history_factory.pipeline import PipelineOrchestrator
    from tiktok_history_factory.agents import ResearchAgent
    from tiktok_history_factory.providers import HistoryProvider
    from tiktok_history_factory.media import TTSProvider
    from tiktok_history_factory.publishing import TikTokUploader
    assert __version__ == "0.1.0"


def test_settings_no_secrets():
    """Vérifie qu'aucun secret n'est codé en dur dans les settings."""
    from tiktok_history_factory.config import Settings
    s = Settings()
    assert s.TIKTOK_ACCESS_TOKEN == ""
    assert s.TIKTOK_PUBLISH_ENABLED is False
