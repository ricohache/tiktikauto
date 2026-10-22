"""Interfaces pour la publication sur TikTok."""

from abc import ABC, abstractmethod
from typing import Dict, Any


class TikTokUploader(ABC):
    """Connecteur d'upload vidéo vers TikTok."""

    @abstractmethod
    async def upload_video(
        self,
        video_path: str,
        title: str,
        description: str,
        privacy_status: str = "public",
    ) -> Dict[str, Any]:
        """Upload une vidéo et retourne les métadonnées de publication."""
        ...

    @abstractmethod
    async def refresh_access_token(self) -> str:
        """Rafraîchit le token d'accès TikTok et retourne le nouveau token."""
        ...


class TikTokScheduler(ABC):
    """Planification de publications TikTok."""

    @abstractmethod
    async def schedule(
        self,
        video_path: str,
        publish_at: str,  # ISO 8601
    ) -> Dict[str, Any]:
        """Planifie une publication différée."""
        ...
