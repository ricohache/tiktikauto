"""Catalogue de sujets historiques avec anti-doublon SQLite."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from typing import Dict, List, Optional, Any

CATALOGUE_PATH = Path(__file__).resolve().parent.parent.parent / 'data' / 'catalogue' / 'subjects.json'


def _slug_hash(slug: str) -> str:
    return hashlib.sha256(slug.lower().strip().encode()).hexdigest()


class SubjectCatalogue:
    """Charge et filtre les sujets disponibles."""

    def __init__(self, path: Optional[Path] = None):
        self.path = path or CATALOGUE_PATH
        self.data = json.loads(self.path.read_text(encoding='utf-8'))
        self.subjects = self.data.get('subjects', [])

    def list_available(self, exclude_hashes: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Retourne les sujets non encore traités."""
        exclude = set(exclude_hashes or [])
        available = []
        for s in self.subjects:
            h = _slug_hash(s['slug'])
            if h not in exclude:
                s['normalized_hash'] = h
                available.append(s)
        return available

    def get_next(self, exclude_hashes: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """Choisit le prochain sujet disponible."""
        available = self.list_available(exclude_hashes)
        return available[0] if available else None

    def get_by_slug(self, slug: str) -> Optional[Dict[str, Any]]:
        """Récupère un sujet par son slug."""
        for s in self.subjects:
            if s['slug'].lower() == slug.lower().strip():
                s['normalized_hash'] = _slug_hash(slug)
                return s
        return None


def load_catalogue(path: Optional[Path] = None) -> SubjectCatalogue:
    return SubjectCatalogue(path)
