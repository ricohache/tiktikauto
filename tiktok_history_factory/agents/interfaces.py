
"""Interfaces pour les agents intelligents du pipeline."""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class ResearchAgent(ABC):
    """Agent de recherche historique sourcee."""
    @abstractmethod
    async def research(self, topic: str) -> Dict[str, Any]:
        """Retourne les donnees historiquees sourcees sur un sujet."""
        pass

class VerificationAgent(ABC):
    """Agent de verification des faits et sources."""
    @abstractmethod
    async def verify(self, research_data: Dict[str, Any]) -> Dict[str, Any]:
        """Verifie la coherence et authenticite des donnees."""
        pass

class WritingAgent(ABC):
    """Agent de redaction du script narratif TikTok."""
    @abstractmethod
    async def write_script(self, verified_data: Dict[str, Any], max_duration: int = 60) -> str:
        """Genere un script narratif adapte a la duree cible (en secondes)."""
        pass

class StoryboardAgent(ABC):
    """Agent de storyboard visuel."""
    @abstractmethod
    async def create_storyboard(self, script_text: str) -> Dict[str, Any]:
        """Produit un storyboard plan par plan."""
        pass

class MediaAgent(ABC):
    """Agent de creation media (voix, images, sous-titres)."""
    @abstractmethod
    async def generate_media(self, script_text: str, work_dir: str) -> Dict[str, str]:
        """Produit les ressources media et retourne les chemins des fichiers."""
        pass

class EditingAgent(ABC):
    """Agent de montage video (FFmpeg)."""
    @abstractmethod
    async def render_video(self, media_paths: Dict[str, str], output_path: str) -> str:
        """Assemble les ressources media en une video TikTok finalisee."""
        pass

class QualityControlAgent(ABC):
    """Agent de controle qualite avant publication."""
    @abstractmethod
    async def review(self, video_path: str, script_text: str) -> Dict[str, Any]:
        """Evalue la qualite technique et editoriale de la video produite."""
        pass

class ApprovalAgent(ABC):
    """Agent d'approbation (humain ou automatique selon configuration)."""
    @abstractmethod
    async def request_approval(self, task_id: int, video_path: str, script_text: str) -> bool:
        """Demande l'approbation pour publication. Retourne True si approuve."""
        pass

class PublishingAgent(ABC):
    """Agent de publication sur TikTok."""
    @abstractmethod
    async def publish(self, video_path: str, title: str, description: str) -> Dict[str, Any]:
        """Publie la video sur TikTok et retourne les metadonnees."""
        pass
