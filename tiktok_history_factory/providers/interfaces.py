"""Interfaces pour les fournisseurs de données historiques manga."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any


class HistoryProvider(ABC):
    """Contrat pour tout fournisseur de données historiques."""

    @abstractmethod
    async def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Recherche d'informations historiques à partir d'une requête textuelle."""
        ...

    @abstractmethod
    async def fetch_article(self, identifier: str) -> Dict[str, Any]:
        """Récupère l'article complet correspondant à l'identifiant fourni."""
        ...

    @abstractmethod
    async def verify_fact(self, claim: str) -> Dict[str, Any]:
        """Vérifie une affirmation historique et retourne sources + score de confiance."""
        ...
