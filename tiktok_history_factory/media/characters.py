
"""Gestion des fiches personnages pour la coherence visuelle."""
from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class Character:
    name: str
    description: str
    visual_prompt: str
    consistency_tags: List[str]

class CharacterManager:
    """Maintient la coherence des personnages entre les plans."""

    def __init__(self):
        self.characters: Dict[str, Character] = {}

    def add_character(self, character: Character) -> None:
        self.characters[character.name] = character

    def get_prompt_for_character(self, name: str, scene_description: str) -> str:
        char = self.characters.get(name)
        if not char:
            return scene_description
        tags = ", ".join(char.consistency_tags)
        return f"{char.visual_prompt}, {tags}, {scene_description}"

    def export_character_sheet(self, output_path: str) -> Dict[str, Any]:
        return {
            "characters": [
                {"name": c.name, "description": c.description, "visual_prompt": c.visual_prompt}
                for c in self.characters.values()
            ]
        }
