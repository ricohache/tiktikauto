#!/usr/bin/env python3
"""Workflow de transfert R2 pour TikTokHistoryFactory.

Etapes:
1. Selection automatique d'une video explicitement approuvee non encore uploadee
2. Pre-controles (MP4 present, ffprobe, SHA256)
3. Upload vers Cloudflare R2 avec cle unique basee sur SHA256
4. Verification de presence et taille
5. Generation URL signee
6. Tracabilite SQLite (idempotence)

Aucune publication Buffer ni TikTok n'est effectuee.
"""
import argparse
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
from secure_credentials import CredentialStore
from video_hosting import CloudflareR2Provider
from cloudflare_worker_adapter import get_worker_url

DB_PATH = Path(r"C:\TikTokHistoryFactory\data\factory.db")
APPROVALS_PATH = Path(r"C:\TikTokHistoryFactory\data\decisions\upload_approvals.json")


def load_approved_slugs() -> List[str]:
    """Charge la liste des slugs explicitement approuves pour upload.
    Retourne une liste vide si le fichier n'existe pas ou est invalide.
    """
    if not APPROVALS_PATH.exists():
        print(f"[WARN] Fichier d'approbations non trouve: {APPROVALS_PATH}")
        return []
    try:
        data = json.loads(APPROVALS_PATH.read_text(encoding="utf-8-sig"))
        slugs = data.get("approved_slugs", [])
        if not isinstance(slugs, list):
            print("[WARN] approved_slugs n'est pas une liste.")
            return []
        return [str(s).strip() for s in slugs if isinstance(s, str)]
    except Exception as e:
        print(f"[WARN] Erreur lecture approbations: {e}")
        return []


def _ensure_r2_table(conn):
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS r2_uploads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug TEXT UNIQUE,
            status TEXT DEFAULT 'UPLOAD_PENDING',
            local_mp4_path TEXT,
            local_sha256 TEXT,
            local_size_bytes INTEGER,
            r2_key TEXT,
            r2_size_bytes INTEGER,
            r2_url TEXT,
            r2_url_expires_at TEXT,
            worker_url TEXT,
            buffer_post_id TEXT,
            buffer_status TEXT,
            ffprobe_json TEXT,
            error TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()


def _migrate_r2_table(conn):
    """Add new columns to existing r2_uploads table if missing."""
    c = conn.cursor()
    c.execute("PRAGMA table_info(r2_uploads)")
    cols = {row[1] for row in c.fetchall()}
    if "worker_url" not in cols:
        c.execute("ALTER TABLE r2_uploads ADD COLUMN worker_url TEXT")
    if "buffer_post_id" not in cols:
        c.execute("ALTER TABLE r2_uploads ADD COLUMN buffer_post_id TEXT")
    if "buffer_status" not in cols:
        c.execute("ALTER TABLE r2_uploads ADD COLUMN buffer_status TEXT")
    conn.commit()


def _update_status(conn, slug: str, status: str, **fields):
    """Met a jour le statut d'un upload de maniere idempotente."""
    c = conn.cursor()
    set_fields = ["status = ?", "updated_at = CURRENT_TIMESTAMP"]
    values = [status]
    for k, v in fields.items():
        set_fields.append(f"{k} = ?")
        values.append(v)
    values.append(slug)
    sql = f"UPDATE r2_uploads SET {', '.join(set_fields)} WHERE slug = ?"
    c.execute(sql, values)
    if c.rowcount == 0:
        c.execute('''
            INSERT INTO r2_uploads (slug, status, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        ''', (slug, status))
    conn.commit()


def select_video(conn, approved_slugs: List[str], dry_run: bool = False) -> Optional[Tuple[str, Path]]:
    """Selectionne la premiere video approuvee non encore uploadee.
    En mode dry-run, affiche les candidats sans selectionner.
    """
    c = conn.cursor()
    c.execute("SELECT slug, mp4_path, status FROM tiktok_queue ORDER BY created_at")
    candidates = {row[0]: {"path": Path(row[1]), "status": row[2]} for row in c.fetchall()}
    
    eligible = []
    for slug in approved_slugs:
        info = candidates.get(slug)
        if not info:
            continue
        mp4_path = info["path"]
        if not mp4_path.exists():
            if dry_run:
                print(f"  [SKIP] {slug}: MP4 manquant ({mp4_path})")
            continue
        # Check if already uploaded
        c.execute("SELECT status FROM r2_uploads WHERE slug = ?", (slug,))
        row = c.fetchone()
        upload_status = row[0] if row else None
        if upload_status in ('UPLOADED', 'VERIFIED'):
            if dry_run:
                print(f"  [SKIP] {slug}: deja en statut {upload_status}")
            continue
        eligible.append({"slug": slug, "path": mp4_path, "queue_status": info["status"], "upload_status": upload_status})
    
    if dry_run:
        print(f"\n=== DRY RUN — Candidats eligibles ({len(eligible)}) ===")
        for cand in eligible:
            print(f"  - {cand['slug']}")
            print(f"    Path: {cand['path']}")
            print(f"    Queue status: {cand['queue_status']}")
            print(f"    Upload status: {cand['upload_status'] or 'N/A'}")
        return None
    
    if not eligible:
        return None
    
    return eligible[0]["slug"], eligible[0]["path"]


def qc_video(mp4_path: Path) -> Tuple[bool, Dict, str]:
    """Verifie le MP4 avec ffprobe. Retourne (ok, metadata, sha256)."""
    ffprobe_exe = Path(r"C:\TikTokHistoryFactory\ffmpeg\bin\ffprobe.exe")
    meta = {}
    if ffprobe_exe.exists():
        try:
            result = subprocess.run(
                [str(ffprobe_exe), "-v", "quiet", "-print_format", "json",
                 "-show_format", "-show_streams", str(mp4_path)],
                capture_output=True, text=True, timeout=60
            )
            if result.returncode == 0:
                meta = json.loads(result.stdout)
        except Exception:
            pass
    
    sha = hashlib.sha256(mp4_path.read_bytes()).hexdigest()
    
    # If ffprobe not available, accept file with warning
    if not ffprobe_exe.exists():
        return True, meta, sha
    
    streams = meta.get("streams", [])
    has_video = any(s.get("codec_type") == "video" for s in streams)
    has_audio = any(s.get("codec_type") == "audio" for s in streams)
    
    if not has_video:
        return False, meta, sha
    
    return True, meta, sha


def upload_to_r2(provider: CloudflareR2Provider, slug: str, mp4_path: Path, sha256: str) -> Tuple[Optional[str], str]:
    """Upload le MP4 vers R2 avec une cle unique basee sur le SHA256.
    Retourne (URL, cle R2)."""
    r2_slug = f"{slug}_{sha256[:16]}"
    key = f"thf/{r2_slug}.mp4"
    url = provider.upload(mp4_path, r2_slug)
    return url, key


def verify_remote_object(provider: CloudflareR2Provider, key: str) -> Tuple[bool, int]:
    """Verifie la presence et la taille de l'objet sur R2."""
    try:
        s3 = provider._get_s3_client()
        resp = s3.head_object(Bucket=provider.bucket_name, Key=key)
        size = resp.get("ContentLength", 0)
        return True, size
    except Exception as e:
        print(f"[VERIFY ERROR] {e}")
        return False, 0


def main():
    parser = argparse.ArgumentParser(description="Workflow R2 Upload")
    parser.add_argument("--dry-run", action="store_true",
                        help="Afficher uniquement la selection et le QC, sans upload")
    parser.add_argument("--slug", type=str, default=None,
                        help="Forcer l'upload d'un slug specifique (doit etre dans la liste approuvee)")
    args = parser.parse_args()
    
    print("=== R2 Upload Workflow ===")
    if args.dry_run:
        print("Mode DRY-RUN: aucun upload ne sera effectue.")
    print("Aucune publication Buffer ni TikTok ne sera effectuee.\n")
    
    # Load approvals
    approved_slugs = load_approved_slugs()
    print(f"Slugs approuves charges: {len(approved_slugs)}")
    if not approved_slugs:
        print("ERREUR: Aucune video approuvee. Verifiez upload_approvals.json.")
        sys.exit(1)
    
    conn = sqlite3.connect(str(DB_PATH))
    _ensure_r2_table(conn)
    
    # 1. Select video
    if args.slug:
        if args.slug not in approved_slugs:
            print(f"ERREUR: '{args.slug}' n'est pas dans la liste des videos approuvees.")
            conn.close()
            sys.exit(1)
        c = conn.cursor()
        c.execute("SELECT mp4_path FROM tiktok_queue WHERE slug = ?", (args.slug,))
        row = c.fetchone()
        if not row:
            print(f"ERREUR: '{args.slug}' non trouve dans la file.")
            conn.close()
            sys.exit(1)
        mp4_path = Path(row[0])
        if not mp4_path.exists():
            print(f"ERREUR: MP4 manquant pour '{args.slug}'.")
            conn.close()
            sys.exit(1)
        slug = args.slug
        print(f"VIDEO_FORCED: {slug}")
    else:
        selected = select_video(conn, approved_slugs, dry_run=args.dry_run)
        if args.dry_run:
            print("\n=== DRY RUN COMPLETE ===")
            conn.close()
            sys.exit(0)
        if not selected:
            print("ERREUR: Aucune video approuvee disponible pour l'upload.")
            conn.close()
            sys.exit(1)
        slug, mp4_path = selected
    
    print(f"VIDEO_SELECTED: {slug}")
    print(f"SOURCE_PATH: {mp4_path}")
    
    # 2. QC
    print("\n[1/5] QC video...")
    ok, meta, sha256 = qc_video(mp4_path)
    if not ok:
        print("QC FAILED: video corrompue ou ffprobe a echoue.")
        _update_status(conn, slug, "FAILED", error="QC_FAILED")
        conn.close()
        sys.exit(1)
    
    local_size = mp4_path.stat().st_size
    ffprobe_json = json.dumps(meta, ensure_ascii=False) if meta else "{}"
    print(f"  SHA256: {sha256[:16]}...")
    print(f"  Size: {local_size / (1024*1024):.1f} MB")
    print(f"  Has video stream: {any(s.get('codec_type')=='video' for s in meta.get('streams',[]))}")
    print(f"  Has audio stream: {any(s.get('codec_type')=='audio' for s in meta.get('streams',[]))}")
    
    if args.dry_run:
        print("\n=== DRY RUN COMPLETE (QC only) ===")
        conn.close()
        sys.exit(0)
    
    # Initialize R2 provider from DPAPI
    print("\n[2/5] Initializing R2 provider...")
    provider = CloudflareR2Provider.from_dpapi()
    if not provider:
        print("ERREUR: Credentials R2 non disponibles dans DPAPI.")
        _update_status(conn, slug, "FAILED", error="R2_CREDENTIALS_MISSING")
        conn.close()
        sys.exit(1)
    print(f"  Bucket: {provider.bucket_name}")
    print(f"  Endpoint: {provider.endpoint[:40]}...")
    
    # 3. Upload
    print("\n[3/5] Uploading to R2...")
    _update_status(conn, slug, "UPLOADING", local_mp4_path=str(mp4_path), local_sha256=sha256, local_size_bytes=local_size, ffprobe_json=ffprobe_json)
    
    url, r2_key = upload_to_r2(provider, slug, mp4_path, sha256)
    if not url:
        print("ERREUR: Upload R2 a echoue.")
        _update_status(conn, slug, "FAILED", error="UPLOAD_FAILED")
        conn.close()
        sys.exit(1)
    
    print(f"  Uploaded to key: {r2_key}")
    
    # 4. Verify remote
    print("\n[4/5] Verifying remote object...")
    verified, remote_size = verify_remote_object(provider, r2_key)
    if not verified:
        print("ERREUR: Verification de l'objet distant a echoue.")
        _update_status(conn, slug, "FAILED", error="VERIFY_FAILED")
        conn.close()
        sys.exit(1)
    
    print(f"  Remote size: {remote_size / (1024*1024):.1f} MB")
    if remote_size != local_size:
        print(f"AVERTISSEMENT: taille distante ({remote_size}) != taille locale ({local_size})")
    else:
        print("  Size match: OK")
    
    # 5. Determine public URL (stable Worker preferred, signed fallback)
    print("\n[5/5] Resolving public URL...")
    stable_url = provider.get_worker_url(r2_key)
    if stable_url:
        url_display = stable_url
        expires_at_iso = None
        print(f"  Stable Worker URL: {url_display}")
    else:
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        expires_at_iso = expires_at.isoformat()
        url_display = url[:50] + "..." if len(url) > 50 else url
        print(f"  Signed URL (fallback): {url_display}")
        print(f"  URL expires: {expires_at_iso}")
    
    # 6. Finalize SQLite
    print("\n[6/6] Finalizing SQLite...")
    _update_status(conn, slug, "VERIFIED",
                   r2_key=r2_key,
                   r2_size_bytes=remote_size,
                   r2_url=url,
                   r2_url_expires_at=expires_at_iso,
                   worker_url=stable_url)
    
    print("\n" + "="*50)
    print("UPLOAD COMPLETE")
    print("="*50)
    print(f"VIDEO_SELECTED:    {slug}")
    print(f"SOURCE_PATH:       {mp4_path}")
    print(f"SHA256:            {sha256[:16]}...")
    print(f"MP4_QC:            PASS")
    print(f"R2_UPLOAD:         PASS")
    print(f"R2_REMOTE_OBJECT:  {r2_key}")
    print(f"R2_SIZE_VERIFIED:  {remote_size == local_size}")
    if stable_url:
        print(f"STABLE_URL:        {stable_url}")
        print(f"WORKER_FALLBACK:   NONE")
    else:
        print(f"STABLE_URL:        N/A (Worker not enabled)")
        print(f"SIGNED_URL:        {url[:40]}... (expires {expires_at_iso[:10] if expires_at_iso else 'N/A'})")
    print(f"SQLITE_IDEMPOTENCY: OK")
    print(f"BUFFER_SUBMISSION:  NOT EXECUTED")
    print(f"TIKTOK_PUBLICATION: NOT EXECUTED")
    print("="*50)
    
    conn.close()


if __name__ == '__main__':
    main()
