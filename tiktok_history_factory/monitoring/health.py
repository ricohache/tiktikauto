
"""Verifications de sante du systeme."""
import subprocess
from typing import Dict, Any

class HealthChecker:
    """Verifie que tous les composants requis sont disponibles."""

    def __init__(self, settings):
        self.settings = settings

    def check_all(self) -> Dict[str, Any]:
        results = {}
        results["python"] = self._check_command(["python", "--version"])
        results["ffmpeg"] = self._check_command([self.settings.FFMPEG_PATH, "-version"])
        results["sqlite"] = self._check_sqlite()
        results["disk_space"] = self._check_disk()
        results['comfyui'] = self._check_comfy()
        results['piper_en'] = self._check_piper()
        results['ollama_model'] = self._check_ollama()
        return {
            "overall": all(r.get("ok", False) for r in results.values()),
            "checks": results,
        }

    def _check_command(self, cmd: list) -> Dict[str, Any]:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            return {"ok": result.returncode == 0, "output": result.stdout[:200]}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _check_sqlite(self) -> Dict[str, Any]:
        try:
            import sqlite3
            conn = sqlite3.connect(":memory:")
            conn.execute("SELECT 1")
            conn.close()
            return {"ok": True, "version": sqlite3.sqlite_version}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _check_disk(self) -> Dict[str, Any]:
        try:
            import shutil
            total, used, free = shutil.disk_usage("C:\\")
            free_gb = free // (2**30)
            return {"ok": free_gb > 10, "free_gb": free_gb}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _check_comfy(self):
        from tiktok_history_factory.providers.comfyui_images import ComfyUIImageProvider
        try:
            provider = ComfyUIImageProvider(self.settings.COMFYUI_BASE_URL)
            models = provider.list_checkpoints()
            ready = self.settings.COMFYUI_CHECKPOINT in models
            return {'ok': ready, 'models': models, 'error': '' if ready else 'Configured checkpoint missing'}
        except Exception as exc:
            return {'ok': False, 'error': str(exc)}

    def _check_piper(self):
        from tiktok_history_factory.providers.piper_tts import PiperTTSProvider
        try:
            provider = PiperTTSProvider(self.settings.PIPER_MODEL_PATH, expected_language=self.settings.SPOKEN_LANGUAGE)
            return {'ok': provider.available, 'error': '' if provider.available else 'English Piper voice missing or incompatible'}
        except Exception as exc:
            return {'ok': False, 'error': str(exc)}

    def _check_ollama(self):
        import json
        import urllib.request
        try:
            with urllib.request.urlopen(self.settings.OLLAMA_LOCAL_URL.rstrip('/') + '/api/tags', timeout=5) as response:
                models = [m['name'] for m in json.load(response)['models']]
            ready = self.settings.OLLAMA_MODEL in models
            return {'ok': ready, 'error': '' if ready else 'Configured model not listed; inference is not checked by doctor'}
        except Exception as exc:
            return {'ok': False, 'error': str(exc)}
