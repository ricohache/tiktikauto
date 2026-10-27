#!/usr/bin/env python3
"""Adaptateur Buffer en mode simulation pour TikTokHistoryFactory.

Ce module prépare une payload `createPost` complète pour Buffer/TikTok
sans jamais exécuter la mutation réelle. Il utilise le canal TikTok
réel déjà détecté et loggue chaque simulation dans SQLite pour
prévenir les doublons.
"""
import json
import os
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Any

from buffer_adapter import BufferAdapter

DB_PATH = Path(r"C:\TikTokHistoryFactory\data\factory.db")


class BufferSimulationAdapter:
    """Prépare une publication Buffer en mode simulation (aucun appel réel)."""

    def __init__(self, buffer_adapter: BufferAdapter, db_path: Optional[Path] = None):
        self.buffer = buffer_adapter
        self.db_path = db_path or DB_PATH
        self._channel_cache: Optional[Dict[str, Any]] = None

    # ------------------------------------------------------------------
    # Channel resolution (reuses real BufferAdapter read-only methods)
    # ------------------------------------------------------------------
    def _resolve_tiktok_channel(self) -> Optional[Dict[str, Any]]:
        """Retourne le canal TikTok connecté, avec cache."""
        if self._channel_cache is not None:
            return self._channel_cache
        ch = self.buffer.get_tiktok_channel()
        if ch and not ch.get("_error"):
            self._channel_cache = ch
        return self._channel_cache

    # ------------------------------------------------------------------
    # Duplicate prevention
    # ------------------------------------------------------------------
    def _check_duplicate(self, slug: str) -> bool:
        """Vérifie si le slug a déjà fait l\'objet d\'une simulation."""
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS buffer_simulations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT UNIQUE,
                status TEXT,
                channel_id TEXT,
                simulated_post_id TEXT,
                payload_json TEXT,
                simulated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        c.execute("SELECT status FROM buffer_simulations WHERE slug = ?", (slug,))
        row = c.fetchone()
        conn.close()
        return row is not None and row[0] == "SIMULATED"

    def _log_simulation(self, slug: str, status: str, channel_id: str,
                        simulated_post_id: str, payload: dict):
        """Enregistre la simulation dans SQLite."""
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS buffer_simulations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT UNIQUE,
                status TEXT,
                channel_id TEXT,
                simulated_post_id TEXT,
                payload_json TEXT,
                simulated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        c.execute('''
            INSERT OR REPLACE INTO buffer_simulations
            (slug, status, channel_id, simulated_post_id, payload_json)
            VALUES (?, ?, ?, ?, ?)
        ''', (slug, status, channel_id, simulated_post_id,
              json.dumps(payload, ensure_ascii=False)))
        conn.commit()
        conn.close()

    # ------------------------------------------------------------------
    # Simulation
    # ------------------------------------------------------------------
    def simulate_publish(self,
                         slug: str,
                         video_url: str,
                         description: str,
                         channel_id: Optional[str] = None,
                         thumbnail_url: Optional[str] = None,
                         mode: str = "addToQueue",
                         due_at: Optional[str] = None) -> Dict[str, Any]:
        """Simule la création d\'un post Buffer/TikTok.

        Args:
            slug: Identifiant de la vidéo (ex: angolan-civil-war-1975).
            video_url: URL HTTPS stable de la vidéo (Worker ou signed).
            description: Texte de la légende (sera complété par la mention IA).
            channel_id: Optionnel — forcera ce canal. Sinon, auto-détection TikTok.
            thumbnail_url: Optionnel — URL de la vignette.

        Returns:
            dict avec les champs : status, slug, channel_id, simulated_post_id, payload.
        """
        # --- 1. Duplicate guard ---
        if self._check_duplicate(slug):
            return {
                "status": "DUPLICATE",
                "slug": slug,
                "error": "Ce slug a déjà été simulé. Utilisez un nouveau slug ou supprimez l\'entrée SQLite.",
            }

        # --- 2. Channel resolution ---
        if not channel_id:
            tiktok = self._resolve_tiktok_channel()
            if not tiktok:
                return {
                    "status": "MISSING_CHANNEL",
                    "slug": slug,
                    "error": "Aucun canal TikTok connecté dans Buffer.",
                }
            if tiktok.get("isDisconnected"):
                return {
                    "status": "CHANNEL_DISCONNECTED",
                    "slug": slug,
                    "error": "Le canal TikTok est déconnecté dans Buffer.",
                }
            if tiktok.get("isLocked"):
                return {
                    "status": "CHANNEL_LOCKED",
                    "slug": slug,
                    "error": "Le canal TikTok est verrouillé dans Buffer.",
                }
            channel_id = tiktok["id"]
            channel_name = tiktok.get("name", "TikTok")
        else:
            channel_name = "Forced"

        # --- 3. Build payload (identique à la mutation réelle) ---
        ai_description = description
        assets: List[Dict[str, Any]] = [{
            "video": {
                "url": video_url
            }
        }]
        if thumbnail_url:
            assets[0]["video"]["thumbnailOffset"] = 0

        input_data = {
            "channelId": channel_id,
            "text": ai_description,
            "assets": assets,
            "aiAssisted": True,
            "mode": mode,
            "schedulingType": "automatic",
            "metadata": {
                "tiktok": {
                    "isAiGenerated": True
                }
            }
        }
        if mode == "customScheduled":
            if not due_at:
                return {
                    "status": "BLOCKED",
                    "slug": slug,
                    "error": "customScheduled mode requires due_at.",
                }
            input_data["mode"] = "customScheduled"
            input_data["schedulingType"] = "automatic"
            input_data["dueAt"] = due_at

        # --- 4. Simulate post ID ---
        simulated_post_id = f"SIM-{slug}-{os.urandom(4).hex()}"

        # --- 5. Persist in SQLite ---
        self._log_simulation(
            slug=slug,
            status="SIMULATED",
            channel_id=channel_id,
            simulated_post_id=simulated_post_id,
            payload=input_data
        )

        return {
            "status": "SIMULATED",
            "slug": slug,
            "channel_id": channel_id,
            "channel_name": channel_name,
            "simulated_post_id": simulated_post_id,
            "payload": input_data,
            "note": "Aucune requête createPost n\'a été envoyée. Cette entrée est prête pour activation.",
        }


# ------------------------------------------------------------------
# CLI helpers
# ------------------------------------------------------------------
def build_ai_description(base_text: str) -> str:
    """Ajoute la mention IA obligatoire à la description."""
    return f"{base_text}\\n\\n— Reconstitution historique générée par IA."


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from secure_credentials import CredentialStore

    store = CredentialStore()
    token = store.get("buffer_access_token")
    if not token:
        print("Usage: configurez d\'abord la clé via buffer_config_cli.py")
        sys.exit(1)

    buf = BufferAdapter(token)
    sim = BufferSimulationAdapter(buf)

    print("=== Buffer Simulation Adapter ===")
    print("Mode: SIMULATION (aucun appel réel à createPost)")

    # Example for the Angola video
    result = sim.simulate_publish(
        slug="angolan-civil-war-1975",
        video_url="https://thf-media-worker.example.workers.dev/thf/angolan-civil-war-1975_b54b077af9055e23.mp4",
        description="Angolan Civil War (1975) — a turning point in African history.",
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
