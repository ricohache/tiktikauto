
"""Metadonnees et manifestes des productions."""
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, List

@dataclass
class ProductionManifest:
    manifest_version: str = "1.0"
    created_at: str = ""
    title: str = ""
    description: str = ""
    duration_seconds: int = 0
    sources: List[Dict[str, Any]] = None
    aigc_disclaimer: str = "Reconstitution historique generee par IA"
    characters: List[Dict[str, Any]] = None

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if self.sources is None:
            self.sources = []
        if self.characters is None:
            self.characters = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "manifest_version": self.manifest_version,
            "created_at": self.created_at,
            "title": self.title,
            "description": self.description,
            "duration_seconds": self.duration_seconds,
            "sources": self.sources,
            "aigc_disclaimer": self.aigc_disclaimer,
            "characters": self.characters,
        }

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
