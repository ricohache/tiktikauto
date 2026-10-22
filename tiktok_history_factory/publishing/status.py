
"""Suivi des statuts de publication."""
from enum import Enum
from typing import Dict, Any

class PublishStatus(Enum):
    NOT_STARTED = "not_started"
    READY = "ready"
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PUBLISHED = "published"
    FAILED = "failed"
    REJECTED = "rejected"

class PublishStatusTracker:
    """Suit le statut d'une publication TikTok."""

    def __init__(self):
        self.statuses: Dict[str, Dict[str, Any]] = {}

    def set_status(self, publish_id: str, status: PublishStatus, details: Dict[str, Any] = None):
        self.statuses[publish_id] = {
            "status": status.value,
            "details": details or {},
        }

    def get_status(self, publish_id: str) -> Dict[str, Any]:
        return self.statuses.get(publish_id, {"status": "unknown"})
