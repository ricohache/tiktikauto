
"""Gestion des assets statiques (polices, musique, overlays)."""
from pathlib import Path
from typing import Dict, Any

class AssetManager:
    """Acces aux assets licences du projet."""

    def __init__(self, assets_dir: str = "assets"):
        self.assets_dir = Path(assets_dir)

    def get_font_path(self, font_name: str = "default") -> str:
        fonts = self.assets_dir / "fonts_licensed"
        candidates = list(fonts.glob("*.ttf")) + list(fonts.glob("*.otf"))
        return str(candidates[0]) if candidates else ""

    def get_music_path(self, mood: str = "somber") -> str:
        music = self.assets_dir / "music_licensed"
        candidates = list(music.glob("*.mp3")) + list(music.glob("*.wav"))
        return str(candidates[0]) if candidates else ""

    def get_style_guide(self, name: str = "manga_seinen") -> Dict[str, Any]:
        guide = self.assets_dir / "style_guides" / f"{name}.md"
        if guide.exists():
            return {"name": name, "content": guide.read_text(encoding="utf-8")}
        return {"name": name, "content": "", "error": "Style guide non trouve"}
