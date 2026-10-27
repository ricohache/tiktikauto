#!/usr/bin/env python3
"""Adaptateur API Buffer pour TikTokHistoryFactory V5.

Buffer supporte la publication automatique sur TikTok via l'API GraphQL.
Documentation: https://developers.buffer.com
API GraphQL: https://api.buffer.com/graphql
"""
import json
import os
import sqlite3
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Any

BUFFER_API_BASE = "https://api.buffer.com"
GRAPHQL_ENDPOINT = f"{BUFFER_API_BASE}/graphql"


class BufferAdapter:
    """Client Buffer API minimal. Mode READ-ONLY par defaut."""

    def __init__(self, access_token: str, db_path: Optional[Path] = None):
        self.access_token = access_token
        self.db_path = db_path or Path(r"C:\TikTokHistoryFactory\data\factory.db")
        self._channel_cache: Optional[List[Dict]] = None
        self._account_cache: Optional[Dict] = None
        self._org_id_cache: Optional[str] = None

    # --- Organization resolution ---

    def _get_first_organization_id(self) -> Optional[str]:
        """Recupere dynamiquement le premier organizationId depuis account."""
        if self._org_id_cache is not None:
            return self._org_id_cache
        auth = self.verify_auth()
        if "errors" in auth or auth.get("status") in ("HTTP_ERROR", "NETWORK_ERROR", "API_ERROR"):
            return None
        orgs = auth.get("data", {}).get("account", {}).get("organizations", [])
        if orgs:
            self._org_id_cache = orgs[0].get("id")
            return self._org_id_cache
        return None

    # --- Read-only verification methods ---

    def verify_auth(self) -> Dict[str, Any]:
        """Verifie que le token est valide via l'utilisateur courant.
        Retourne la reponse JSON brute de l'API, y compris les erreurs.
        """
        if self._account_cache is not None:
            return self._account_cache
        query = """
        query GetAccount {
            account {
                id
                email
                name
                organizations {
                    id
                    name
                    channelCount
                }
            }
        }
        """
        data = self._graphql(query)
        if "data" in data:
            self._account_cache = data
        return data

    def list_channels(self, organization_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Liste les canaux sociaux connectes a Buffer.
        Utilise UNIQUEMENT les champs valides du schema Buffer.
        """
        if self._channel_cache is not None:
            return self._channel_cache

        org_id = organization_id or self._get_first_organization_id()
        if not org_id:
            return [{"_error": "No organizationId available."}]

        query = """
        query GetChannels($input: ChannelsInput!) {
            channels(input: $input) {
                id
                name
                service
                isDisconnected
                isLocked
            }
        }
        """
        variables = {"input": {"organizationId": org_id}}
        data = self._graphql(query, variables)

        if "errors" in data:
            return [{"_error": f"GraphQL errors: {data['errors']}"}]
        if data.get("status") in ("HTTP_ERROR", "NETWORK_ERROR", "API_ERROR"):
            return [{"_error": f"API error: {data.get('status')} — {data.get('error', data.get('body', 'unknown'))}"}]

        channels = data.get("data", {}).get("channels")
        if channels is None:
            return [{"_error": "Response missing channels field."}]

        self._channel_cache = channels
        return channels

    def get_tiktok_channel(self, organization_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Retourne le canal TikTok connecte, s'il existe.
        Le champ service est un enum Buffer (ex: TIKTOK, INSTAGRAM, etc.).
        """
        channels = self.list_channels(organization_id)
        if channels and channels[0].get("_error"):
            return {"_error": channels[0]["_error"]}
        for ch in channels:
            svc = ch.get("service", "")
            if svc and svc.upper() == "TIKTOK":
                return ch
        return None

    def get_account_capabilities(self) -> Dict[str, Any]:
        """Retourne les capacites du compte.
        Requete minimisee pour eviter les erreurs GraphQL sur les champs inexistants.
        """
        query = """
        query GetAccount {
            account {
                id
                email
                organizations {
                    id
                    name
                    billing {
                        plan
                    }
                }
            }
        }
        """
        return self._graphql(query)


    # --- Duplicate check via Buffer API ---

    def _redact_errors(self, errors):
        try:
            return json.dumps(errors, ensure_ascii=False)
        except Exception:
            return str(errors)

    def check_existing_posts(self, channel_id: str, text_substring: str,
                             organization_id: Optional[str] = None) -> Dict[str, Any]:
        """Verifie si un post avec un texte similaire existe deja sur le canal.
        Interroge les posts scheduled et sent de Buffer avec pagination.
        Retourne un dict {status: OK|ERROR, matches: [...], error: str|None}.
        """
        org_id = organization_id or self._get_first_organization_id()
        if not org_id:
            return {"status": "ERROR", "matches": [], "error": "No organizationId available."}

        all_matches = []
        has_next = True
        cursor = None
        page_count = 0
        max_pages = 5  # Safety limit

        while has_next and page_count < max_pages:
            query = """
            query GetPosts($first: Int, $input: PostsInput!, $after: String) {
                posts(first: $first, input: $input, after: $after) {
                    edges {
                        node {
                            id
                            text
                            channelId
                            status
                            dueAt
                        }
                    }
                    pageInfo {
                        hasNextPage
                        endCursor
                    }
                }
            }
            """
            variables = {
                "first": 50,
                "input": {
                    "organizationId": org_id,
                    "filter": {
                        "channelIds": [channel_id],
                        "status": ["scheduled", "sent"]
                    }
                }
            }
            if cursor:
                variables["after"] = cursor

            data = self._graphql(query, variables)

            if data.get("status") in ("HTTP_ERROR", "NETWORK_ERROR", "API_ERROR"):
                return {
                    "status": "ERROR",
                    "matches": [],
                    "error": f"Buffer API network error: {data.get('status')}"
                }
            if "errors" in data:
                return {
                    "status": "ERROR",
                    "matches": [],
                    "error": f"Buffer API GraphQL error: {self._redact_errors(data['errors'])}"
                }

            posts_data = data.get("data", {}).get("posts", {})
            edges = posts_data.get("edges", [])
            for edge in edges:
                node = edge.get("node", {})
                if text_substring.lower() in (node.get("text") or "").lower():
                    all_matches.append(node)

            page_info = posts_data.get("pageInfo", {})
            has_next = page_info.get("hasNextPage", False)
            cursor = page_info.get("endCursor")
            page_count += 1

        return {"status": "OK", "matches": all_matches, "error": None}

    # --- Publication methods (write-guarded) ---

    def create_post(self, channel_id: str, text: str, video_url: str,
                    due_at: Optional[str] = None,
                    thumbnail_url: Optional[str] = None,
                    is_ai_generated: bool = True,
                    mode: str = "addToQueue") -> Dict[str, Any]:
        """Cree un post Buffer avec video pour TikTok.

        Args:
            mode: 'addToQueue' (prochain creneau) ou 'shareNow' (immediat).
                  shareNow exige une autorisation explicite (voir env THF_BUFFER_SHARE_NOW_ALLOWED).
        """
        env_flag = os.environ.get("THF_BUFFER_PUBLISH_ALLOWED", "0")
        if env_flag != "1":
            return {
                "status": "BLOCKED",
                "error": "Buffer publication blocked. Set THF_BUFFER_PUBLISH_ALLOWED=1 to enable.",
                "channel_id": channel_id,
                "text_preview": text[:100] if text else ""
            }

        if mode == "shareNow":
            share_now_flag = os.environ.get("THF_BUFFER_SHARE_NOW_ALLOWED", "0")
            if share_now_flag != "1":
                return {
                    "status": "BLOCKED",
                    "error": "shareNow blocked. Set THF_BUFFER_SHARE_NOW_ALLOWED=1 explicitly to enable immediate sharing.",
                    "channel_id": channel_id,
                    "mode": mode
                }
        
        mutation = """
        mutation CreatePost($input: CreatePostInput!) {
            createPost(input: $input) {
                ... on PostActionSuccess {
                    post {
                        id
                        status
                        text
                        dueAt
                        channel {
                            id
                            name
                            service
                        }
                    }
                }
                ... on MutationError {
                    message
                }
            }
        }
        """
        
        # Correct Buffer GraphQL video asset format per official docs:
        # assets: [{ video: { url: WORKER_URL } }]
        assets = [{
            "video": {
                "url": video_url
            }
        }]
        if thumbnail_url:
            assets[0]["video"]["thumbnailOffset"] = 0
        
        input_data = {
            "channelId": channel_id,
            "text": text,
            "assets": assets,
            "aiAssisted": is_ai_generated,
            "mode": mode,
        }
        
        if mode == "customScheduled":
            if not due_at:
                return {
                    "status": "BLOCKED",
                    "error": "customScheduled mode requires due_at.",
                    "channel_id": channel_id
                }
            input_data["mode"] = "customScheduled"
            input_data["schedulingType"] = "automatic"
            input_data["dueAt"] = due_at
        elif due_at:
            input_data["schedulingType"] = "customScheduled"
            input_data["dueAt"] = due_at
        else:
            input_data["schedulingType"] = "automatic"
        
        if is_ai_generated:
            input_data["metadata"] = {
                "tiktok": {
                    "isAiGenerated": True
                }
            }
        
        variables = {"input": input_data}
        result = self._graphql(mutation, variables)

        # Robust response handling: HTTP 200 alone does not prove creation.
        if result.get("status") in ("HTTP_ERROR", "NETWORK_ERROR", "API_ERROR"):
            return {
                "status": "FAILED",
                "error": result.get("body", result.get("error", "Unknown network/API error")),
                "raw": result
            }

        create_post_data = result.get("data", {}).get("createPost", {})
        if create_post_data.get("message"):
            return {
                "status": "MUTATION_ERROR",
                "error": create_post_data["message"],
                "raw": result
            }

        post = create_post_data.get("post")
        if post and post.get("id"):
            return {
                "status": "SUCCESS",
                "post": post,
                "raw": result
            }

        return {
            "status": "UNEXPECTED_RESPONSE",
            "error": "createPost succeeded but returned no identifiable post.",
            "raw": result
        }

    # --- Internal HTTP ---

    def _graphql(self, query: str, variables: Optional[Dict] = None) -> Dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "User-Agent": "TikTokHistoryFactory/1.0"
        }
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        req = urllib.request.Request(
            GRAPHQL_ENDPOINT,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if "errors" in data:
                return {"status": "API_ERROR", "errors": data["errors"]}
            return data
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            return {"status": "HTTP_ERROR", "code": e.code, "body": body}
        except Exception as e:
            return {"status": "NETWORK_ERROR", "error": str(e)}

    # --- SQLite tracking ---

    def log_buffer_check(self, slug: str, channel_id: str, result: Dict):
        """Trace une verification Buffer en lecture seule dans SQLite."""
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS buffer_checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT,
                channel_id TEXT,
                result_json TEXT,
                checked_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        c.execute('''INSERT INTO buffer_checks (slug, channel_id, result_json)
                       VALUES (?, ?, ?)''',
                  (slug, channel_id, json.dumps(result, ensure_ascii=False)))
        conn.commit()
        conn.close()

    def log_buffer_attempt(self, slug: str, status: str, error: str = None, buffer_post_id: str = None):
        """Trace une tentative de publication (ou blocage) Buffer."""
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS buffer_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT UNIQUE,
                status TEXT,
                error TEXT,
                buffer_post_id TEXT,
                attempted_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        c.execute('''INSERT OR REPLACE INTO buffer_attempts (slug, status, error, buffer_post_id)
                       VALUES (?, ?, ?, ?)''',
                  (slug, status, error, buffer_post_id))
        conn.commit()
        conn.close()


if __name__ == '__main__':
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from secure_credentials import CredentialStore
    
    store = CredentialStore()
    token = store.get("buffer_access_token")
    if not token:
        print("Usage: configurez d'abord la cle via buffer_config_cli.py")
        sys.exit(1)
    
    buf = BufferAdapter(token)
    print("=== Buffer Adapter (Read-Only Mode) ===")
    
    print("\n[AUTH]")
    auth = buf.verify_auth()
    print(json.dumps(auth, indent=2, ensure_ascii=False))
    
    org_id = buf._get_first_organization_id()
    print(f"\n[ORGANIZATION ID]")
    if org_id:
        print(f"Resolved: {org_id}")
    else:
        print("No organization found.")
    
    print("\n[CHANNELS]")
    channels = buf.list_channels(org_id)
    if channels and channels[0].get("_error"):
        print(f"ERROR: {channels[0]['_error']}")
    else:
        print(f"Count: {len(channels)}")
        for ch in channels:
            print(f"  - {ch.get('service', '?')}: {ch.get('name', '?')} (id={ch.get('id', '?')}, disconnected={ch.get('isDisconnected')}, locked={ch.get('isLocked')})")
    
    print("\n[TIKTOK CHANNEL]")
    tiktok = buf.get_tiktok_channel(org_id)
    if tiktok and tiktok.get("_error"):
        print(f"ERROR: {tiktok['_error']}")
    elif tiktok:
        print(f"Found: {tiktok.get('name', '?')} (id={tiktok.get('id', '?')})")
        print(f"  Disconnected: {tiktok.get('isDisconnected')}")
        print(f"  Locked: {tiktok.get('isLocked')}")
    else:
        print("NOT FOUND")
    
    print("\n[CAPABILITIES]")
    print(json.dumps(buf.get_account_capabilities(), indent=2, ensure_ascii=False))
