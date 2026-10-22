
"""Prompts specialises pour le style manga historique."""

MANGA_STYLE_PREFIX = (
    "LineAniAF, Japanese 2D seinen manga panel, bold expressive ink, weighted clean contours, "
    "solid black shadow shapes, halftone screentone dots, dramatic cinematic contrast, "
    "mature realistic anatomy, black and white with neutral gray, professional manga drawing"
)

CHARACTER_CONSISTENCY_TAGS = [
    "meme visage entre les plans",
    "coherence vestimentaire",
    "style graphique identique",
]

def build_image_prompt(scene_description: str, character_refs: str = "") -> str:
    """Construit un prompt complet pour une illustration manga."""
    parts = [MANGA_STYLE_PREFIX, scene_description]
    if character_refs:
        parts.append(character_refs)
    parts.append("vertical composition, historical reconstruction, no text")
    return ", ".join(parts)

def build_negative_prompt() -> str:
    """Prompt negatif pour eviter les artefacts indesirables."""
    return (
        "etching, engraving, crosshatching, sepia, pencil sketch, charcoal, photograph, photorealistic, 3D render, chibi, cute, neon colors, "
        "low quality, blurry, deformed hands, extra fingers, modern clothing, modern weapons, "
        "watermark, text, letters, nudity, nsfw, gore, blood, graphic violence, "
        "Asian architecture, pagoda, kimono, robe, straw hat, conical hat, samurai, katana, bamboo village"
        ", tactical vest, astronaut, spacesuit, face mask, modern helmet, nazi, swastika, medals, epaulettes, officer uniform"
    )
