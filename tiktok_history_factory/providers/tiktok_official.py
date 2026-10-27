
"""Connecteur API officielle TikTok — MODE EXPORT PAR DEFAUT."""
import json
from typing import Dict, Any

class TikTokOfficialProvider:
    """
    Connecteur API TikTok.
    PAR DEFAUT : mode LOCAL_EXPORT (aucun appel API).
    Les modes TIKTOK_DRAFT/PRIVATE necessitent :
      - Compte Developpeur TikTok approuve
      - Scopes video.upload et/ou video.publish
      - OAuth token valide et consentement utilisateur
    """

    VALID_MODES = ["LOCAL_EXPORT", "TIKTOK_DRAFT", "TIKTOK_PRIVATE", "TIKTOK_PUBLIC"]

    def __init__(self, client_key: str, client_secret: str, access_token: str = "", mode: str = "LOCAL_EXPORT"):
        self.client_key = client_key
        self.client_secret = client_secret
        self.access_token = access_token
        self.mode = mode if mode in self.VALID_MODES else "LOCAL_EXPORT"
        self.enabled = (mode != "LOCAL_EXPORT") and bool(access_token and client_key and client_secret)

    def upload_video(self, video_path: str, title: str, description: str, privacy: str = "SELF_ONLY") -> Dict[str, Any]:
        """Upload une video selon le mode configure."""
        if self.mode == "LOCAL_EXPORT":
            return {
                "status": "READY_FOR_EXPORT",
                "mode": "LOCAL_EXPORT",
                "video_path": video_path,
                "title": title,
                "description": description,
                "note": "Aucun appel API TikTok effectue. Importer manuellement ou activer TIKTOK_DRAFT.",
            }
        if not self.enabled:
            return {"status": "BLOCKED", "error": "Credentials TikTok manquants ou mode non autorise"}
        return {"status": "NOT_IMPLEMENTED", "mode": self.mode}
