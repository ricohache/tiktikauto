
"""Gestion audio : voix, musique, mixage."""
from pathlib import Path
from typing import Dict, Any

class AudioManager:
    """Coordonne la synthese vocale et le mixage audio."""

    def __init__(self, tts_provider=None):
        self.tts = tts_provider

    def synthesize_narration(self, script_text: str, output_path: str) -> Dict[str, Any]:
        """Synthetise la narration complete."""
        if self.tts is None:
            return {
                "status": "BLOCKED",
                "error": "Aucun fournisseur TTS configure",
                "note": "Installer Piper et configurer PIPER_MODEL_PATH dans .env",
            }
        return self.tts.synthesize(script_text, output_path)

    def estimate_duration(self, text: str, wpm: int = 130) -> float:
        """Estime la duree de la narration en secondes."""
        words = len(text.split())
        return (words / wpm) * 60
