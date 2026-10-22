
"""Validation de la configuration et des contraintes."""
from pathlib import Path
from typing import Dict, Any, List

class ConfigValidator:
    """Valide que la configuration est coherente et securisee."""

    def __init__(self, settings):
        self.settings = settings

    def validate(self) -> Dict[str, Any]:
        errors = []
        warnings = []

        # Verification chemins critiques
        if not Path(self.settings.DB_PATH).parent.exists():
            errors.append(f"Repertoire DB inexistant : {Path(self.settings.DB_PATH).parent}")

        # Verification securite
        if self.settings.TIKTOK_PUBLISH_ENABLED and self.settings.TIKTOK_PUBLISH_MODE == "TIKTOK_PUBLIC":
            errors.append("TIKTOK_PUBLIC active sans verification explicite de consentement")

        if not self.settings.TIKTOK_ACCESS_TOKEN and self.settings.TIKTOK_PUBLISH_MODE != "LOCAL_EXPORT":
            warnings.append("Mode non-LOCAL_EXPORT mais TIKTOK_ACCESS_TOKEN vide")

        # Verification modeles
        if not self.settings.OLLAMA_MODEL:
            errors.append("OLLAMA_MODEL non configure")
        if self.settings.SPOKEN_LANGUAGE not in ('en-US', 'en-GB') or self.settings.SUBTITLE_LANGUAGE != 'fr-FR':
            errors.append('V2 requires English speech and French subtitles')
        if self.settings.TTS_LENGTH_SCALE < 1:
            errors.append('Narration acceleration prohibited')

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }
