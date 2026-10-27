#!/usr/bin/env python3
"""Publication Buffer generique pour le prochain episode de la file TikTok.
Sans argument --slug, publie le premier episode pending avec URL Worker valide.
"""
import argparse
import datetime
import json
import os
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(r"C:\TikTokHistoryFactory")
ENV_FILE = PROJECT_ROOT / ".env"
DB_PATH = PROJECT_ROOT / "data" / "factory.db"

def check_env_guard():
    content = ENV_FILE.read_text(encoding="utf-8")
    if "THF_BUFFER_PUBLISH_ALLOWED=1" not in content:
        print("BLOCKED: THF_BUFFER_PUBLISH_ALLOWED != 1")
        sys.exit(1)

def load_token():
    sys.path.insert(0, str(PROJECT_ROOT / "src" / "v5_factory"))
    from secure_credentials import CredentialStore
    store = CredentialStore()
    token = store.get("buffer_access_token")
    if not token:
        print("BLOCKED: Token Buffer introuvable.")
        sys.exit(1)
    print(f"Token: {len(token)} chars")
    return token

def check_channel(token):
    from buffer_adapter import BufferAdapter
    buf = BufferAdapter(token)
    ch = buf.get_tiktok_channel()
    if not ch or ch.get("_error"):
        print("BLOCKED: Canal TikTok non disponible.")
        sys.exit(1)
    if ch.get("isDisconnected"):
        print("BLOCKED: Canal deconnecte.")
        sys.exit(1)
    if ch.get("isLocked"):
        print("BLOCKED: Canal verrouille.")
        sys.exit(1)
    print(f"Canal OK: {ch.get('name')} (id={ch['id']})")
    return ch["id"], ch.get("name", "TikTok")

def get_next_pending_episode():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    # Join tiktok_queue with r2_uploads to find episodes with worker_url
    c.execute("""
        SELECT q.slug, q.title_fr, q.description_fr, q.hashtags, q.mention_ia,
               q.mp4_path, q.thumbnail_path, q.sources_json,
               r.worker_url, r.r2_url, r.local_sha256
        FROM tiktok_queue q
        LEFT JOIN r2_uploads r ON q.slug = r.slug
        WHERE q.status = 'pending'
        ORDER BY q.created_at
        LIMIT 1
    """)
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    return dict(row)

def check_duplicate_sqlite(slug):
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("SELECT status FROM buffer_attempts WHERE slug=?", (slug,))
    row = c.fetchone()
    conn.close()
    if row:
        print(f"BLOCKED: Doublon detecte dans SQLite ({row[0]}).")
        sys.exit(1)
    print("Aucun doublon SQLite. PASS")

def check_duplicate_buffer(token, ch_id, slug):
    from buffer_adapter import BufferAdapter
    buf = BufferAdapter(token)
    result = buf.check_existing_posts(ch_id, slug)
    if result.get("status") == "ERROR":
        print(f"BLOCKED: Verification Buffer API impossible: {result.get('error')}")
        sys.exit(1)
    matches = result.get("matches", [])
    if matches:
        print(f"BLOCKED: Doublon detecte dans Buffer ({len(matches)} post(s)).")
        for m in matches:
            print(f"  - {m.get('id')} | {m.get('status')}")
        sys.exit(1)
    print("Aucun doublon Buffer API. PASS")

def build_desc(ep):
    desc = ep["description_fr"] or ""
    sources = json.loads(ep["sources_json"]) if ep["sources_json"] else []
    source_lines = []
    for s in sources[:2]:
        if isinstance(s, dict):
            source_lines.append(f"{s.get('name', '')} ({s.get('url', '')})")
    parts = [desc]
    if source_lines:
        parts.extend(["", "Sources : " + " ; ".join(source_lines)])
    parts.extend(["", ep.get("mention_ia", "Reconstitution historique generee par IA.")])
    return "\n".join(parts)

def confirm(ch_name, ch_id, ep, mode, due_at, run_id=None, skip=False):
    if skip:
        print("[SKIP] Confirmation bypassed by --yes")
        return
    print("\n" + "="*50)
    print("RESUME AVANT PUBLICATION")
    print("="*50)
    print(f"  VIDEO         = {ep['title_fr']} ({ep['slug']})")
    print(f"  CHANNEL       = {ch_id}")
    due_dt = None
    if due_at:
        try:
            due_dt = datetime.datetime.fromisoformat(due_at.replace("Z", "+00:00"))
        except Exception:
            pass
    if due_dt:
        paris_offset = datetime.timedelta(hours=2)  # Approx Europe/Paris (sufficient for display)
        paris_dt = due_dt.astimezone(datetime.timezone(paris_offset))
        date_paris = paris_dt.strftime("%d/%m/%Y %H:%M")
    else:
        date_paris = "IMMEDIATE"
    print(f"  DATE_PARIS    = {date_paris}")
    print(f"  DUE_AT_UTC    = {due_at or 'N/A'}")
    print(f"  MODE          = {mode}")
    print(f"  DOUBLON_SQLITE= NO")
    print(f"  DOUBLON_BUFFER= NO")
    print("="*50)
    confirm = input("\nConfirmez l'envoi reel (oui/NON): ")
    if confirm.strip().lower() != "oui":
        print("Annule.")
        sys.exit(0)

def send_post(token, ch_id, desc, video_url, mode, due_at=None):
    from buffer_adapter import BufferAdapter
    buf = BufferAdapter(token)
    result = buf.create_post(
        channel_id=ch_id,
        text=desc,
        video_url=video_url,
        is_ai_generated=True,
        mode=mode,
        due_at=due_at
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return result

def log_result(slug, post_id, status, error=None, run_id=None):
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS buffer_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug TEXT UNIQUE,
            status TEXT,
            error TEXT,
            buffer_post_id TEXT,
            run_id TEXT,
            attempted_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Add run_id column if missing
    c.execute("PRAGMA table_info(buffer_attempts)")
    cols = [r[1] for r in c.fetchall()]
    if 'run_id' not in cols:
        c.execute("ALTER TABLE buffer_attempts ADD COLUMN run_id TEXT")
    c.execute("INSERT OR REPLACE INTO buffer_attempts (slug,status,buffer_post_id,error,run_id) VALUES (?,?,?,?,?)",
              (slug, status, post_id, error, run_id))
    conn.commit()
    conn.close()
    print("SQLite log OK")

def update_queue_status(slug, status, tiktok_id=None, error=None):
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    now = datetime.datetime.now().isoformat()
    if status == "published":
        c.execute("UPDATE tiktok_queue SET status=?, published_at=?, tiktok_video_id=? WHERE slug=?",
                  (status, now, tiktok_id or "", slug))
    elif status == "scheduled":
        c.execute("UPDATE tiktok_queue SET status=?, scheduled_at=? WHERE slug=?",
                  (status, now, slug))
    else:
        c.execute("UPDATE tiktok_queue SET status=?, error=? WHERE slug=?",
                  (status, error or "", slug))
    conn.commit()
    conn.close()

def run_live(token, ch_id, ch_name, ep, mode, due_at):
    slug = ep["slug"]
    video_url = ep.get("worker_url") or ep.get("r2_url")
    if not video_url:
        print("BLOCKED: Aucune URL publique (Worker ou R2) pour cette video.")
        sys.exit(1)
    desc = build_desc(ep)
    if mode == "shareNow":
        print("\n[ATTENTION] Mode shareNow demande. Verifiez THF_BUFFER_SHARE_NOW_ALLOWED=1.")
    confirm(ch_name, ch_id, ep, mode, due_at, run_id=args.run_id, skip=args.yes)
    print("\nEnvoi createPost...")
    result = send_post(token, ch_id, desc, video_url, mode, due_at)

    if result.get("status") == "SUCCESS":
        post_id = result["post"]["id"]
        post_status = result["post"].get("status", "unknown")
        post_due = result["post"].get("dueAt", "N/A")
        print(f"\nBuffer post ID: {post_id}")
        print(f"Buffer status : {post_status}")
        print(f"Buffer dueAt  : {post_due}")
        log_result(slug, post_id, "PUBLISHED", run_id=args.run_id)
        update_queue_status(slug, "scheduled", tiktok_id=post_id)
        print("\n=== Termine ===")
        print("Buffer: REAL PASS | TikTok: PLANIFIEE | Usine: NON activee")
    elif result.get("status") == "BLOCKED":
        print("PUBLICATION BLOQUEE.")
        log_result(slug, None, "BLOCKED", result.get("error"), run_id=args.run_id)
        sys.exit(1)
    elif result.get("status") == "MUTATION_ERROR":
        print(f"MUTATION ERROR: {result.get('error')}")
        log_result(slug, None, "MUTATION_ERROR", result.get("error"), run_id=args.run_id)
        sys.exit(1)
    else:
        print(f"ERREUR: {result.get('error', 'inconnue')}")
        log_result(slug, None, result.get("status", "FAILED"), result.get("error"), run_id=args.run_id)
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Publication Buffer generique - prochain episode")
    parser.add_argument("--mode", choices=["addToQueue", "shareNow", "customScheduled"], default="addToQueue")
    parser.add_argument("--due-at", default=None)
    parser.add_argument("--live", action="store_true", help="Execute la publication reelle")
    parser.add_argument("--slug", default=None, help="Forcer un slug specifique")
    parser.add_argument("--run-id", default="", help="Identifiant de run pour tracabilite")
    parser.add_argument("--yes", action="store_true", help="Skip confirmation prompt")
    args = parser.parse_args()

    if not args.live:
        print("Usage: ajoutez --live pour publier reellement.")
        sys.exit(0)

    # No hardcoded time guard — scheduling is handled by orchestrator

    print("=== Publication Buffer - Episode suivant ===")
    check_env_guard()
    token = load_token()
    ch_id, ch_name = check_channel(token)

    if args.slug:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT q.*, r.worker_url, r.r2_url FROM tiktok_queue q LEFT JOIN r2_uploads r ON q.slug=r.slug WHERE q.slug=?", (args.slug,))
        row = c.fetchone()
        conn.close()
        if not row:
            print(f"ERREUR: {args.slug} non trouve.")
            sys.exit(1)
        ep = dict(row)
    else:
        ep = get_next_pending_episode()
        if not ep:
            print("BLOCKED: Aucun episode pending avec URL Worker.")
            sys.exit(1)

    slug = ep["slug"]
    print(f"Episode selectionne: {slug}")
    check_duplicate_sqlite(slug)
    check_duplicate_buffer(token, ch_id, slug)

    if args.mode == "customScheduled" and not args.due_at:
        print("BLOCKED: customScheduled requiert --due-at.")
        sys.exit(1)

    run_live(token, ch_id, ch_name, ep, args.mode, args.due_at)

if __name__ == "__main__":
    main()
