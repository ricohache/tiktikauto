"""Configuration centralisee via variables d'environnement (modules standards)."""

import os
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Charger .env manuellement si python-dotenv n'est pas disponible
_env_path = _PROJECT_ROOT / ".env"
if _env_path.exists():
    with open(_env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key not in os.environ:
                os.environ[key] = value


class Settings:
    """Configuration de l'usine — relecture des variables a chaque instanciation."""

    PROJECT_ROOT: Path = _PROJECT_ROOT

    def __init__(self):
        self.DB_PATH: Path = _PROJECT_ROOT / os.getenv("DB_PATH", "data/factory.db")
        self.LOG_DIR: Path = _PROJECT_ROOT / os.getenv("LOG_DIR", "logs")

        self.FFMPEG_PATH: str = os.getenv("FFMPEG_PATH", r"C:\TikTokHistoryFactory\ffmpeg\bin\ffmpeg.exe")
        self.FFPROBE_PATH: str = os.getenv("FFPROBE_PATH", r"C:\TikTokHistoryFactory\ffmpeg\bin\ffprobe.exe")
        self.COMFYUI_BASE_URL: str = os.getenv("COMFYUI_BASE_URL", "http://127.0.0.1:8188")
        self.COMFYUI_ROOT: str = os.getenv("COMFYUI_ROOT", r"C:\TikTokHistoryFactory\ComfyUI\ComfyUI")
        self.PIPER_MODEL_PATH: str = os.getenv("PIPER_MODEL_PATH", "") or str(_PROJECT_ROOT / 'tools/piper/voices/en_US-john-medium.onnx')
        self.SPOKEN_LANGUAGE = os.getenv('SPOKEN_LANGUAGE', 'en-US')
        self.SUBTITLE_LANGUAGE = os.getenv('SUBTITLE_LANGUAGE', 'fr-FR')
        self.TRANSLATION_LOCALE = os.getenv('TRANSLATION_LOCALE', 'fr-FR')
        self.TTS_LENGTH_SCALE = float(os.getenv('TTS_LENGTH_SCALE', '1.0'))
        self.COMFYUI_LORA = os.getenv('COMFYUI_LORA', 'LineAniRedmondV2-Lineart-LineAniAF.safetensors')
        self.COMFYUI_LORA_STRENGTH = float(os.getenv('COMFYUI_LORA_STRENGTH', '1.0'))
        self.COMFYUI_CHECKPOINT: str = os.getenv('COMFYUI_CHECKPOINT', 'sd_xl_base_1.0.safetensors')
        self.PILOT_DOSSIER: str = os.getenv('PILOT_DOSSIER', str(_PROJECT_ROOT / 'data/subjects/thiaroye-1944-v2.json'))
        self.PILOT_TRY_WAN: bool = os.getenv('PILOT_TRY_WAN', 'false').lower() == 'true'

        self.TIKTOK_PUBLISH_MODE: str = os.getenv("TIKTOK_PUBLISH_MODE", "LOCAL_EXPORT")
        self.TIKTOK_ACCESS_TOKEN: str = os.getenv("TIKTOK_ACCESS_TOKEN", "")
        self.TIKTOK_REFRESH_TOKEN: str = os.getenv("TIKTOK_REFRESH_TOKEN", "")
        self.TIKTOK_CLIENT_KEY: str = os.getenv("TIKTOK_CLIENT_KEY", "")
        self.TIKTOK_CLIENT_SECRET: str = os.getenv("TIKTOK_CLIENT_SECRET", "")
        self.TIKTOK_PUBLISH_ENABLED: bool = os.getenv("TIKTOK_PUBLISH_ENABLED", "false").lower() == "true"

        self.WIKIPEDIA_USER_AGENT: str = os.getenv(
            "WIKIPEDIA_USER_AGENT",
            "TikTokHistoryFactory/0.2 (local historical research)",
        )
        self.GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")

        self.MAX_DAILY_VIDEOS: int = int(os.getenv("MAX_DAILY_VIDEOS", "3"))
        self.MAX_RETRY_ATTEMPTS: int = int(os.getenv("MAX_RETRY_ATTEMPTS", "3"))
        self.TASK_TIMEOUT_SECONDS: int = int(os.getenv("TASK_TIMEOUT_SECONDS", "1800"))

        self.OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434/api")
        self.OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "kimi-k3:cloud")
        self.OLLAMA_API_KEY: str = os.getenv("OLLAMA_API_KEY", "")
        self.OLLAMA_LOCAL_URL: str = os.getenv("OLLAMA_LOCAL_URL", "http://localhost:11434")
        self.OLLAMA_LOCAL_MODEL: str = os.getenv("OLLAMA_LOCAL_MODEL", "gemma3:4b")

        self.LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
        self.KWH_PRICE_EUR: float = float(os.getenv("KWH_PRICE_EUR", "0.20"))

    @classmethod
    def ensure_directories(cls) -> None:
        """Cree les repertoires necessaires s'ils n'existent pas."""
        s = cls()
        s.LOG_DIR.mkdir(parents=True, exist_ok=True)
        s.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
