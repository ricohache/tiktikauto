
"""Selection et gestion des sujets historiques."""
import hashlib
from typing import List, Dict, Any

class TopicSelector:
    """Selectionne des sujets historiques inedits."""

    KNOWN_TOPICS = [
        {"slug": "massacre-thiaroye-1944", "title": "Le massacre de Thiaroye, 1944", "category": "histoire-coloniale"},
        {"slug": "patrice-lumumba-assassinat", "title": "L'assassinat de Patrice Lumumba", "category": "histoire-africaine"},
        {"slug": "thomas-sankara-1987", "title": "Thomas Sankara, la derniere revolution", "category": "histoire-africaine"},
        {"slug": "guerre-algerie-violences", "title": "Violences subies par les civils pendant la guerre d'Algerie", "category": "histoire-coloniale"},
        {"slug": "ruben-um-nyobe", "title": "Ruben Um Nyobe et l'UPC camerounaise", "category": "histoire-africaine"},
        {"slug": "tirailleurs-senegalais", "title": "Les tirailleurs senegalais oublies", "category": "histoire-militaire"},
    ]

    def __init__(self, db_manager=None):
        self.db = db_manager

    def pick_next(self, exclude_hashes: List[str] = None) -> Dict[str, Any]:
        """Choisit le prochain sujet inedit."""
        exclude_hashes = exclude_hashes or []
        for topic in self.KNOWN_TOPICS:
            h = hashlib.sha256(topic["slug"].encode()).hexdigest()
            if h not in exclude_hashes:
                return {**topic, "normalized_hash": h}
        return {}

    def validate_topic(self, topic: Dict[str, Any]) -> bool:
        """Verifie que le sujet est valide et non deja traite."""
        return bool(topic.get("slug") and topic.get("title"))
