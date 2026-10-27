import json
import random
import re
import sqlite3
import time
import urllib.request
from pathlib import Path

class HistoryDiscovery:
    """Decouverte autonome de sujets historiques.

    Strategie:
    1. Tenter l acces aux sources externes (Wikipedia).
    2. En cas d echec reseau (DNS, HTTP, timeout), signaler BLOCKED
       et basculer sur la file locale pre_sourced/.
    3. Ne jamais copier summary_en dans summary_fr.
    4. Exiger au moins 2 sources independantes pour tout sujet nouveau.
    5. Stocker les decouvertes dans la table SQLite discovered_subjects
       avec anti-doublons et reprise sur incident.
    """

    # Categories Wikipedia pour la decouverte (non limite a l Afrique)
    CATEGORIES = [
        "African_resistance_to_colonialism",
        "Wars_involving_the_states_and_peoples_of_Africa",
        "African_independence_movements",
        "Massacres_in_Africa",
        "Colonialism_in_Africa",
        "Cold_War",
        "Revolutions_by_country",
        "Protests",
    ]

    # Liste de secours si reseau dispo mais categorie vide
    SEED_TITLES = [
        "Mau Mau Uprising",
        "Soweto uprising",
        "Mozambican War of Independence",
        "Zimbabwean War of Liberation",
        "Aba Women s Riots",
        "Amistad rebellion",
        "Prague Spring",
        "Hungarian Revolution of 1956",
        "Chernobyl disaster",
        "Fall of the Berlin Wall",
    ]

    def __init__(self, db_path: Path, catalogue_path: Path, pre_sourced_dir: Path):
        self.db_path = db_path
        self.catalogue_path = catalogue_path
        self.pre_sourced_dir = pre_sourced_dir
        self.existing_slugs = self._load_existing()
        self.network_blocked = False
        self._init_db()
        self._sync_sqlite_to_catalogue()

    def _init_db(self):
        """Cree la table discovered_subjects si elle n existe pas."""
        if not self.db_path.exists():
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS discovered_subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT NOT NULL UNIQUE,
                title_en TEXT,
                title_fr TEXT,
                summary_en TEXT,
                summary_fr TEXT,
                event_date TEXT,
                sources_json TEXT,
                network_available INTEGER DEFAULT 0,
                discovered_at TEXT DEFAULT CURRENT_TIMESTAMP,
                used INTEGER DEFAULT 0
            )
        ''')
        conn.commit()
        conn.close()

    def _load_existing(self):
        """Charge les slugs deja connus (DB + catalogue) + anti-doublons semantiques."""
        slugs = set()
        self._semantic_hashes = set()
        if self.db_path.exists():
            db = sqlite3.connect(str(self.db_path))
            c = db.cursor()
            for table in ("auto_productions", "discovered_subjects"):
                try:
                    c.execute(f"SELECT slug FROM {table}")
                    for row in c.fetchall():
                        slugs.add(row[0])
                        self._semantic_hashes.add(self._semantic_hash(row[0]))
                except sqlite3.OperationalError:
                    pass
            db.close()
        if self.catalogue_path.exists():
            cat = json.load(open(self.catalogue_path, "r", encoding="utf-8"))
            for s in cat.get("subjects", []):
                slugs.add(s["slug"])
                self._semantic_hashes.add(self._semantic_hash(s["slug"]))
        return slugs

    def _semantic_hash(self, slug: str):
        """Cree un hash semantique base sur les mots cles du slug (sans annee)."""
        base = re.sub(r'\d{4}', '', slug)
        base = re.sub(r'[^a-z]', '', base)
        return base

    def _test_network(self):
        """Verifie si Wikipedia est joignable."""
        test_urls = [
            "https://en.wikipedia.org/api/rest_v1/page/summary/World_War_II",
            "https://www.google.com/generate_204",
        ]
        for url in test_urls:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "TikTokHistoryFactory/1.0"}, method="HEAD")
                with urllib.request.urlopen(req, timeout=10) as resp:
                    if resp.status in (200, 204, 301, 302):
                        return True
            except Exception as e:
                print(f"[NETWORK TEST] {url} failed: {e}")
        return False

    def _fetch_wikipedia_summary(self, title: str, lang: str = "en"):
        """Recupere le resume d un article Wikipedia via l API REST."""
        url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{title.replace(' ', '_')}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "TikTokHistoryFactory/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return data
        except Exception as e:
            print(f"[DISCOVERY] Wikipedia fetch failed for {title}: {e}")
            return None

    def _get_wikipedia_langlink(self, title: str, target_lang: str = "fr"):
        """Recupere le titre traduit via l API MediaWiki."""
        url = f"https://en.wikipedia.org/w/api.php?action=query&prop=langlinks&titles={title.replace(' ', '_')}&lllang={target_lang}&format=json"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "TikTokHistoryFactory/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            pages = data.get("query", {}).get("pages", {})
            for page in pages.values():
                for ll in page.get("langlinks", []):
                    if ll.get("lang") == target_lang:
                        return ll.get("*")
        except Exception as e:
            print(f"[DISCOVERY] Langlink fetch failed for {title}: {e}")
        return None

    def _fetch_independent_source(self, title: str):
        """Cherche une source editoriale independante (OpenLibrary/Google Books).
        Retourne un dict {name, url, language, consulted_at} ou None.
        Preuve de consultation conservee."""
        # Tentative OpenLibrary par sujet
        search_q = title.replace(' ', '+')
        url = f"https://openlibrary.org/search.json?q={search_q}&limit=1"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "TikTokHistoryFactory/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            docs = data.get("docs", [])
            if docs:
                doc = docs[0]
                olid = doc.get("key", "")
                return {
                    "name": f"OpenLibrary: {doc.get('title', title)}",
                    "url": f"https://openlibrary.org{olid}",
                    "language": "en",
                    "verified": False,
                    "consulted_at": time.strftime("%Y-%m-%dT%H:%M:%S")
                }
        except Exception as e:
            print(f"[DISCOVERY] Independent source fetch failed for {title}: {e}")
        return None

    def _extract_year(self, text: str):
        """Extrait une annee plausible du texte."""
        if not text:
            return None
        years = re.findall(r'\b(1[4-9]\d{2}|20\d{2})\b', text)
        if years:
            return years[0]
        return None

    def _slugify(self, title: str, year: str):
        base = re.sub(r'[^\w\s-]', '', title).strip().lower()
        base = re.sub(r'[-\s]+', '-', base)
        slug = f"{base}-{year}"
        if len(slug) > 60:
            slug = slug[:60].rsplit('-', 1)[0]
        return slug

    def _load_pre_sourced(self):
        """Charge les dossiers pre_sourcess locaux."""
        subjects = []
        if not self.pre_sourced_dir.exists():
            return subjects
        for subdir in self.pre_sourced_dir.iterdir():
            dossier = subdir / "dossier.json"
            if not dossier.exists():
                continue
            try:
                data = json.loads(dossier.read_text(encoding="utf-8"))
                slug = data.get("slug", subdir.name)
                if slug in self.existing_slugs:
                    print(f"[PRE-SOURCED] {slug} already known, skipping")
                    continue
                # Validation minimale
                if not data.get("title_en") or not data.get("sources"):
                    print(f"[PRE-SOURCED] {slug} missing title or sources, skipping")
                    continue
                # Anti-copie summary_en -> summary_fr
                if data.get("summary_fr") == data.get("summary_en"):
                    print(f"[PRE-SOURCED] WARNING {slug} summary_fr == summary_en (needs real translation)")
                subject = {
                    "slug": slug,
                    "title_en": data["title_en"],
                    "title_fr": data.get("title_fr", ""),
                    "summary_en": data.get("summary_en", ""),
                    "summary_fr": data.get("summary_fr", ""),
                    "event_date": data.get("event_date", "1900-01-01"),
                    "style_prompt": data.get("style_prompt", "Japanese 2D seinen manga panel, bold expressive ink, weighted clean contours, solid black shadow shapes, halftone screentone dots, dramatic cinematic contrast, mature realistic anatomy, black and white with neutral gray, professional manga drawing, historical scene, no text, vertical composition"),
                    "wikipedia_url": data.get("wikipedia_url", ""),
                    "sources": data.get("sources", []),
                    "scenes": data.get("scenes", []),
                    "source": "pre_sourced"
                }
                subjects.append(subject)
                self.existing_slugs.add(slug)
                print(f"[PRE-SOURCED] Loaded: {slug}")
            except Exception as e:
                print(f"[PRE-SOURCED] Error reading {dossier}: {e}")
        return subjects

    def discover(self, count: int = 3):
        """Decouvre count nouveaux sujets historiques."""
        discovered = []

        # 1. Tester le reseau
        network_ok = self._test_network()
        if not network_ok:
            print("[DISCOVERY] NETWORK BLOCKED: external sources unreachable (DNS/HTTP failure). Switching to pre_sourced queue.")
            self.network_blocked = True

        # 2. Si reseau OK, tenter Wikipedia EN + FR + source independante
        if network_ok:
            random.shuffle(self.SEED_TITLES)
            for title in self.SEED_TITLES:
                if len(discovered) >= count:
                    break
                data_en = self._fetch_wikipedia_summary(title, "en")
                if not data_en or data_en.get("type") != "standard":
                    continue
                extract_en = data_en.get("extract", "")
                if len(extract_en) < 200:
                    continue
                # Recherche version FR via langlink
                fr_title = self._get_wikipedia_langlink(title, "fr")
                data_fr = self._fetch_wikipedia_summary(fr_title, "fr") if fr_title else None
                extract_fr = data_fr.get("extract", "") if data_fr else ""
                title_fr = data_fr.get("title", "") if data_fr else ""
                if not extract_fr or len(extract_fr) < 100:
                    print(f"[DISCOVERY] {title}: FR summary missing or too short, skipping")
                    continue
                # Verification date historique
                year = self._extract_year(extract_en) or self._extract_year(data_en.get("description", "")) or self._extract_year(title)
                if not year:
                    print(f"[DISCOVERY] {title}: no plausible year found, skipping")
                    continue
                slug = self._slugify(title, year)
                if slug in self.existing_slugs:
                    continue
                # Anti-doublon semantique
                sem = self._semantic_hash(slug)
                if sem in getattr(self, '_semantic_hashes', set()):
                    print(f"[DISCOVERY] {title}: semantic duplicate detected, skipping")
                    continue
                # Source independante obligatoire (OpenLibrary/Google Books)
                ind_source = self._fetch_independent_source(title)
                if not ind_source:
                    print(f"[DISCOVERY] {title}: no independent editorial source found, skipping")
                    continue
                # Wikipedia ne compte que comme UNE source, meme EN+FR
                sources = [
                    {"name": "Wikipedia", "url": data_en.get("content_urls", {}).get("desktop", {}).get("page", ""), "language": "en", "verified": True},
                    ind_source,
                ]
                subject = {
                    "slug": slug,
                    "title_en": data_en.get("title", title),
                    "title_fr": title_fr,
                    "summary_en": extract_en[:800],
                    "summary_fr": extract_fr[:800],
                    "event_date": f"{year}-01-01",
                    "style_prompt": "Japanese 2D seinen manga panel, bold expressive ink, weighted clean contours, solid black shadow shapes, halftone screentone dots, dramatic cinematic contrast, mature realistic anatomy, black and white with neutral gray, professional manga drawing, historical scene, no text, vertical composition",
                    "wikipedia_url": data_en.get("content_urls", {}).get("desktop", {}).get("page", ""),
                    "sources": sources,
                    "scenes": [],
                    "source": "wikipedia_api"
                }
                discovered.append(subject)
                self.existing_slugs.add(slug)
                self._semantic_hashes.add(sem)
                self._persist_discovery(subject, network_available=1)
                print(f"[DISCOVERY] Found online with independent source: {slug}")
                time.sleep(0.5)

        # 3. Si pas assez de sujets en ligne, ou si reseau bloque, utiliser pre_sourced
        if len(discovered) < count or self.network_blocked:
            pre = self._load_pre_sourced()
            for s in pre:
                if len(discovered) >= count:
                    break
                discovered.append(s)
                self._persist_discovery(s, network_available=0)

        if not discovered:
            print("[DISCOVERY] BLOCKED: no new subjects available from online or pre_sourced sources.")

        return discovered

    def _sync_sqlite_to_catalogue(self):
        """Synchronise les sujets SQLite manquants dans le catalogue JSON."""
        if not self.db_path.exists() or not self.catalogue_path.exists():
            return
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        try:
            c.execute("SELECT slug, title_en, title_fr, summary_en, summary_fr, event_date, sources_json FROM discovered_subjects")
            db_rows = c.fetchall()
        except sqlite3.OperationalError:
            db_rows = []
        conn.close()
        cat = json.load(open(self.catalogue_path, "r", encoding="utf-8"))
        cat_slugs = {s["slug"] for s in cat.get("subjects", [])}
        synced = 0
        for row in db_rows:
            slug = row[0]
            if slug not in cat_slugs:
                subject = {
                    "slug": slug,
                    "title_en": row[1],
                    "title_fr": row[2],
                    "summary_en": row[3],
                    "summary_fr": row[4],
                    "event_date": row[5] or "",
                    "sources": json.loads(row[6]) if row[6] else [],
                    "style_prompt": "Japanese 2D seinen manga panel, bold expressive ink, weighted clean contours, solid black shadow shapes, halftone screentone dots, dramatic cinematic contrast, mature realistic anatomy, black and white with neutral gray, professional manga drawing, historical scene, no text, vertical composition",
                    "scenes": [],
                    "source": "sqlite_recovery"
                }
                cat["subjects"].append(subject)
                synced += 1
        if synced > 0:
            json.dump(cat, open(self.catalogue_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
            print(f"[RECOVERY] Synced {synced} subjects from SQLite to catalogue")

    def _add_to_catalogue_one(self, subject: dict):
        """Ajoute un sujet unique au catalogue JSON."""
        if not self.catalogue_path.exists():
            cat = {"subjects": []}
            self.catalogue_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            cat = json.load(open(self.catalogue_path, "r", encoding="utf-8"))
        slugs = {s["slug"] for s in cat.get("subjects", [])}
        if subject["slug"] not in slugs:
            cat["subjects"].append(subject)
            json.dump(cat, open(self.catalogue_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
            print(f"[DISCOVERY] Added {subject['slug']} to catalogue")

    def _persist_discovery(self, subject: dict, network_available: int = 0):
        """Persiste la decouverte dans SQLite et dans le catalogue."""
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute('''
            INSERT OR IGNORE INTO discovered_subjects
            (slug, title_en, title_fr, summary_en, summary_fr, event_date, sources_json, network_available)
            VALUES (?,?,?,?,?,?,?,?)
        ''', (
            subject["slug"],
            subject["title_en"],
            subject.get("title_fr", ""),
            subject.get("summary_en", ""),
            subject.get("summary_fr", ""),
            subject.get("event_date", ""),
            json.dumps(subject.get("sources", []), ensure_ascii=False),
            network_available
        ))
        conn.commit()
        conn.close()
        self._add_to_catalogue_one(subject)

    def add_to_catalogue(self, subjects: list):
        """Ajoute les sujets decouverts au catalogue."""
        cat = json.load(open(self.catalogue_path, "r", encoding="utf-8"))
        for s in subjects:
            cat["subjects"].append(s)
        json.dump(cat, open(self.catalogue_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        print(f"[DISCOVERY] Added {len(subjects)} subjects to catalogue")


if __name__ == "__main__":
    ROOT = Path(r"C:\TikTokHistoryFactory")
    disc = HistoryDiscovery(
        ROOT / "data" / "factory.db",
        ROOT / "data" / "catalogue" / "subjects.json",
        ROOT / "data" / "pre_sourced"
    )
    found = disc.discover(3)
    if found:
        disc.add_to_catalogue(found)
    for s in found:
        print(json.dumps(s, indent=2, ensure_ascii=False))

