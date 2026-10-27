#!/usr/bin/env python3
import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(r"C:\TikTokHistoryFactory")
ENV_FILE = PROJECT_ROOT / ".env"
DB_PATH = PROJECT_ROOT / "data" / "factory.db"
VIDEO_URL = "https://thf-media-worker.rico-hache.workers.dev/thf/angolan-civil-war-1975_b54b077af9055e23.mp4"

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

def check_duplicate_sqlite():
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("SELECT status FROM buffer_attempts WHERE slug=?", ("angolan-civil-war-1975",))
    row = c.fetchone()
    conn.close()
    if row:
        print(f"BLOCKED: Doublon detecte dans SQLite ({row[0]}).")
        sys.exit(1)
    print("Aucun doublon SQLite. PASS")

def check_duplicate_buffer(token, ch_id):
    from buffer_adapter import BufferAdapter
    buf = BufferAdapter(token)
    result = buf.check_existing_posts(ch_id, "angolan-civil-war-1975")
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

def build_desc():
    return "\n".join([
        "En 1975, l'Angola accede a l'independance mais plonge dans la guerre civile. Un conflit qui opposa le MPLA, le FNLA et l'UNITA, avec l'intervention des puissances de la Guerre froide.",
        "",
        "Sources : Office of the Historian, U.S. Department of State (history.state.gov) ; Uppsala Conflict Data Program (ucdp.uu.se).",
        "",
        "Reconstitution historique generee par IA."
    ])

def confirm(ch_name, ch_id, desc, mode):
    print("\nPayload:")
    print(f"  Channel: {ch_name} ({ch_id})")
    print(f"  Video:   {VIDEO_URL}")
    print(f"  Mode:    {mode}")
    print("  IA:      isAiGenerated=true | aiAssisted=true")
    print(f"  Text:    {desc[:80]}...")
    confirm = input("\nConfirmez l'envoi reel (oui/NON): ")
    if confirm.strip().lower() != "oui":
        print("Annule.")
        sys.exit(0)

def send_post(token, ch_id, desc, mode, due_at=None):
    from buffer_adapter import BufferAdapter
    buf = BufferAdapter(token)
    result = buf.create_post(
        channel_id=ch_id,
        text=desc,
        video_url=VIDEO_URL,
        is_ai_generated=True,
        mode=mode,
        due_at=due_at
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return result

def log_result(post_id, status, error=None):
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS buffer_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug TEXT UNIQUE,
            status TEXT,
            error TEXT,
            buffer_post_id TEXT,
            attempted_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("INSERT OR REPLACE INTO buffer_attempts (slug,status,buffer_post_id,error) VALUES (?,?,?,?)",
              ("angolan-civil-war-1975", status, post_id, error))
    conn.commit()
    conn.close()
    print("SQLite log OK")

def run_simulation(token, ch_id, ch_name, desc, mode, due_at=None):
    import sys
    sys.path.insert(0, str(PROJECT_ROOT / "src" / "v5_factory"))
    from buffer_simulation_adapter import BufferSimulationAdapter
    from buffer_adapter import BufferAdapter
    if token:
        buf = BufferAdapter(token)
    else:
        # Mock adapter for simulation when token is not available
        class _MockBuf:
            pass
        buf = _MockBuf()
    sim = BufferSimulationAdapter(buf)
    result = sim.simulate_publish(
        slug="angolan-civil-war-1975",
        video_url=VIDEO_URL,
        description=desc,
        channel_id=ch_id,
        mode=mode,
        due_at=due_at
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if result["status"] == "SIMULATED":
        print("\n=== SIMULATION OK ===")
        print(f"Payload prete pour mode '{mode}'. Aucun appel createPost effectue.")
    else:
        print(f"\n=== SIMULATION FAILED: {result['status']} ===")
    return result

def run_live(token, ch_id, ch_name, desc, mode, due_at=None):
    if mode == "shareNow":
        print("\n[ATTENTION] Mode shareNow demande. Verifiez THF_BUFFER_SHARE_NOW_ALLOWED=1.")
    confirm(ch_name, ch_id, desc, mode)
    print("\nEnvoi createPost...")
    result = send_post(token, ch_id, desc, mode, due_at=due_at)

    if result.get("status") == "SUCCESS":
        post_id = result["post"]["id"]
        print(f"\nBuffer post ID: {post_id}")
        log_result(post_id, "PUBLISHED")
        print("\n=== Termine ===")
        print("Buffer: REAL PASS | TikTok: PLANIFIEE | Usine: NON activee")
    elif result.get("status") == "BLOCKED":
        print("PUBLICATION BLOQUEE.")
        log_result(None, "BLOCKED", result.get("error"))
        sys.exit(1)
    elif result.get("status") == "MUTATION_ERROR":
        print(f"MUTATION ERROR: {result.get('error')}")
        log_result(None, "MUTATION_ERROR", result.get("error"))
        sys.exit(1)
    else:
        print(f"ERREUR: {result.get('error', 'inconnue')}")
        log_result(None, result.get("status", "FAILED"), result.get("error"))
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Publication test TikTok -- Angola 1975")
    parser.add_argument("--mode", choices=["addToQueue", "shareNow", "customScheduled"], default="addToQueue",
                        help="Mode de publication Buffer (defaut: addToQueue)")
    parser.add_argument("--due-at", default=None,
                        help="Date/heure ISO 8601 pour customScheduled (ex: 2026-10-27T09:00:00Z)")
    parser.add_argument("--simulate", action="store_true", help="Simule sans envoyer createPost")
    parser.add_argument("--live", action="store_true", help="Execute la publication reelle")
    parser.add_argument("--sim-channel-id", default=None, help="Canal factice pour la simulation (optionnel)")
    args = parser.parse_args()

    if not args.simulate and not args.live:
        parser.print_help()
        sys.exit(0)

    # Time guard: refuse if 10:00 local time (system configured for Europe/Paris) already passed on 2026-10-27
    import datetime, time
    now_local = datetime.datetime.now()
    if now_local.date() >= datetime.date(2026, 10, 27) and now_local.time() >= datetime.time(10, 0):
        print(f"BLOCKED: Il est deja {now_local.strftime('%H:%M')} (10 h Paris depassee). Programmation refusee.")
        sys.exit(1)

    print("=== Publication test TikTok — Angola 1975 ===")
    if args.live:
        check_env_guard()
    token = load_token() if args.live else None
    desc = build_desc()

    # Default dueAt for Angola customScheduled
    if args.mode == "customScheduled" and not args.due_at:
        args.due_at = "2026-10-27T09:00:00Z"

    if args.simulate:
        # En simulation, on force un canal factice ; aucun appel API reel n'est fait.
        ch_id = args.sim_channel_id or "sim-channel-id"
        ch_name = "SimulationTikTok"
        check_duplicate_sqlite()
        run_simulation(token, ch_id, ch_name, desc, args.mode, due_at=args.due_at)
    elif args.live:
        ch_id, ch_name = check_channel(token)
        check_duplicate_sqlite()
        check_duplicate_buffer(token, ch_id)
        run_live(token, ch_id, ch_name, desc, args.mode, due_at=args.due_at)

if __name__ == "__main__":
    main()
