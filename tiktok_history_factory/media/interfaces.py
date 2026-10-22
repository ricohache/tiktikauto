"""Interfaces pour la création et le montage média en CPU."""

from abc import ABC, abstractmethod
from typing import Dict, Any, List



class TTSProvider(ABC):
    """Fournisseur de synthèse vocale (CPU, sans GPU)."""

    @abstractmethod
    async def synthesize(self, text: str, output_path: str, voice: str = "default") -> str:
        """Génère un fichier audio WAV/MP3 à partir du texte fourni."""
        ...


class ImageProvider(ABC):
    """Fournisseur d'images / illustrations (CPU via Ollama ou stock)."""

    @abstractmethod
    async def generate(self, prompt: str, output_path: str, width: int = 1080, height: int = 1920) -> str:
        """Génère une image au format vertical (9:16 par défaut)."""
        ...


class SubtitleRenderer(ABC):
    """Rendu des sous-titres synchronisés avec l'audio."""

    @abstractmethod
    async def render(
        self,
        video_path: str,
        subtitles: list[Dict[str, Any]],
        output_path: str,
    ) -> str:
        """Superpose les sous-titres sur la vidéo et retourne le chemin du fichier final."""
        ...


class FFmpegEditor(ABC):
    """Abstraction du montage FFmpeg en CPU."""

    @abstractmethod
    async def assemble(
        self,
        video_segments: list[str],
        audio_path: str,
        output_path: str,
        duration: int = 60,
    ) -> str:
        """Assemble les segments vidéo et l'audio en un fichier MP4 final."""
        ...

