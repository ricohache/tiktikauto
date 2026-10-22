
"""Fournisseurs de donnees historiques sourcees."""
import urllib.request
import urllib.parse
import json
from typing import Dict, Any, Optional

class WikipediaProvider:
    """Acces aux articles Wikipedia en francais."""

    def __init__(self, user_agent: str = "TikTokHistoryFactory/0.1"):
        self.user_agent = user_agent

    def search(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """Recherche via l'API Wikipedia."""
        url = f"https://fr.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(query)}&srlimit={limit}&format=json"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            return {"error": str(e), "results": []}

    def fetch_article(self, page_id: int) -> Dict[str, Any]:
        """Recupere le contenu d'un article par son ID."""
        url = f"https://fr.wikipedia.org/w/api.php?action=query&pageids={page_id}&prop=extracts&explaintext&format=json"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            return {"error": str(e)}


class HistoricalSourceProvider:
    """Fetch only explicitly approved HTTPS source hosts; cache bounded documents."""

    def __init__(self, user_agent='TikTokHistoryFactory/0.2 (local historical research)'):
        self.user_agent = user_agent

    def fetch(self, url, output_path, allowed_hosts):
        from pathlib import Path
        from datetime import datetime, timezone
        import hashlib
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme != 'https' or parsed.hostname not in allowed_hosts or parsed.username or parsed.port not in (None, 443):
            raise ValueError('Source must use an approved public HTTPS host')

        class Redirects(urllib.request.HTTPRedirectHandler):
            count = 0

            def redirect_request(self, req, fp, code, msg, headers, newurl):
                self.count += 1
                target = urllib.parse.urlsplit(newurl)
                if self.count > 3 or target.scheme != 'https' or target.hostname not in allowed_hosts or target.username or target.port not in (None, 443):
                    raise ValueError('Unapproved source redirect')
                return super().redirect_request(req, fp, code, msg, headers, newurl)

        request = urllib.request.Request(url, headers={'User-Agent': self.user_agent, 'Accept': 'text/html,application/pdf,text/plain'})
        with urllib.request.build_opener(Redirects()).open(request, timeout=30) as response:
            content_type = response.headers.get_content_type()
            if content_type not in ('text/html', 'text/plain', 'application/pdf', 'application/json'):
                raise ValueError('Unsupported source MIME type')
            body = response.read(8 * 1024**2 + 1)
            if len(body) > 8 * 1024**2:
                raise ValueError('Historical source exceeds size limit')
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_bytes(body)
            return {'url': url, 'http_code': response.status, 'mime': content_type,
                    'retrieved_at': datetime.now(timezone.utc).isoformat(),
                    'sha256': hashlib.sha256(body).hexdigest(), 'bytes': len(body),
                    'path': str(output_path)}
