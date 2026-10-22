
"""Gestion des brouillons de publication."""
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, List

@dataclass
class PublicationDraft:
    id: str
    created_at: str
    video_path: str
    title: str
    description: str
    hashtags: List[str]
    mode: str  # LOCAL_EXPORT, TIKTOK_DRAFT, etc.
    status: str  # PENDING, SUBMITTED, CONFIRMED

class DraftManager:
    """Stocke et gere les brouillons avant publication."""

    def __init__(self, db_manager=None):
        self.db = db_manager
        self.drafts: Dict[str, PublicationDraft] = {}

    def create_draft(self, video_path: str, title: str, description: str,
                     hashtags: List[str] = None, mode: str = "LOCAL_EXPORT") -> str:
        draft_id = f"draft_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.drafts[draft_id] = PublicationDraft(
            id=draft_id,
            created_at=datetime.now().isoformat(),
            video_path=video_path,
            title=title,
            description=description,
            hashtags=hashtags or [],
            mode=mode,
            status="PENDING",
        )
        return draft_id

    def get_draft(self, draft_id: str) -> PublicationDraft:
        return self.drafts.get(draft_id)
