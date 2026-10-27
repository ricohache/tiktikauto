#!/usr/bin/env python3
"""Orchestrateur central TikTokHistoryFactory.
Point d entree unique pour le pipeline complet.
"""
import argparse
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

PROJECT_ROOT = Path(r"C:\TikTokHistoryFactory")
sys.path.insert(0, str(PROJECT_ROOT / "src" / "v5_factory"))
sys.path.insert(0, str(PROJECT_ROOT / "TikTokHistoryFactory_finish_v5"))

from state_machine import PipelineStateMachine

TARGET_SECONDS = 90
FPS = 30


class PipelineOrchestrator:
    def __init__(self, project_root: Path = PROJECT_ROOT):
        self.project = project_root.resolve()
        self.db_path = self.project / "data" / "factory.db"
        self.state = PipelineStateMachine(self.db_path)
        self.approvals_path = self.project / "data" / "decisions" / "upload_approvals.json"
        self.log_file = self.project / "data" / "orchestrator.log"
        self.ffmpeg = self.project / "ffmpeg" / "bin" / "ffmpeg.exe"
        self.ffprobe = self.project / "ffmpeg" / "bin" / "ffprobe.exe"

    def log(self, level: str, message: str):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"{ts} [{level}] {message}"
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass
        print(line, flush=True)

    def _add_approval(self, slug: str):
        self.approvals_path.parent.mkdir(parents=True, exist_ok=True)
        data = {"approved_slugs": []}
        if self.approvals_path.exists():
            try:
                data = json.loads(self.approvals_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        slugs = data.get("approved_slugs", [])
        if slug not in slugs:
            slugs.append(slug)
        data["approved_slugs"] = slugs
        self.approvals_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def discover_next_subject(self, excluded=None) -> Optional[str]:
        from catalogue import SubjectCatalogue
        import random
        if excluded is None:
            excluded = {"angolan-civil-war-1975"}
        cat_path = self.project / "data" / "catalogue" / "subjects.json"
        cat = SubjectCatalogue(cat_path)
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute("SELECT slug, status FROM auto_productions")
        produced = {r[0]: r[1] for r in c.fetchall()}
        conn.close()
        candidates = []
        for s in cat.subjects:
            slug = s["slug"]
            if slug in excluded:
                continue
            if produced.get(slug) == "completed":
                continue
            out_dir = self.project / "output"
            existing = list(out_dir.rglob(f"*{slug}*.mp4"))
            if existing:
                continue
            candidates.append(slug)
        if candidates:
            return candidates[0]
        all_slugs = [s["slug"] for s in cat.subjects if s["slug"] not in excluded]
        if all_slugs:
            random.seed()
            return random.choice(all_slugs)
        return None

    def produce_video(self, slug: str, run_id: str) -> Dict:
        from auto_engine import AutoProductionEngine
        self.state.transition(run_id, "PRODUCING", step="production")
        self.log("INFO", f"Production demarree: {slug} | RUN_ID={run_id}")
        engine = AutoProductionEngine(self.project)
        try:
            result = engine.produce_subject(slug, run_id=run_id)
            mp4 = result.get("mp4")
            if not mp4 or not Path(mp4).exists():
                raise RuntimeError("Production terminee mais MP4 introuvable")
            self.state.transition(run_id, "PRODUCED", step="production", mp4_path=mp4)
            self.log("SUCCESS", f"Production terminee: {slug} | MP4={mp4}")
            return {"ok": True, "mp4": mp4, "slug": slug, "run_id": run_id}
        except Exception as e:
            self.state.transition(run_id, "FAILED", step="production", error=str(e))
            self.log("ERROR", f"Production echouee: {slug} | {e}")
            return {"ok": False, "error": str(e), "slug": slug, "run_id": run_id}

    def qc_video(self, slug: str, mp4_path: Path, run_id: str) -> Dict:
        self.state.transition(run_id, "PRODUCED", step="qc")
        self.log("INFO", f"QC demarre: {slug} | {mp4_path}")
        if not mp4_path.exists():
            self.state.transition(run_id, "QC_FAILED", step="qc", error="MP4_NOT_FOUND")
            return {"ok": False, "error": "MP4_NOT_FOUND"}
        meta = {}
        try:
            result = subprocess.run(
                [str(self.ffprobe), "-v", "quiet", "-print_format", "json",
                 "-show_format", "-show_streams", str(mp4_path)],
                capture_output=True, text=True, timeout=60
            )
            if result.returncode == 0:
                meta = json.loads(result.stdout)
        except Exception as e:
            self.log("WARN", f"ffprobe failed: {e}")
        streams = meta.get("streams", [])
        has_video = any(s.get("codec_type") == "video" for s in streams)
        has_audio = any(s.get("codec_type") == "audio" for s in streams)
        if not has_video:
            self.state.transition(run_id, "QC_FAILED", step="qc", error="NO_VIDEO_STREAM")
            return {"ok": False, "error": "NO_VIDEO_STREAM"}
        if not has_audio:
            self.state.transition(run_id, "QC_FAILED", step="qc", error="NO_AUDIO_STREAM")
            return {"ok": False, "error": "NO_AUDIO_STREAM"}
        duration = 0
        try:
            duration = float(meta.get("format", {}).get("duration", 0))
        except Exception:
            pass
        if duration < 30:
            self.state.transition(run_id, "QC_FAILED", step="qc", error=f"DURATION_TOO_SHORT:{duration}")
            return {"ok": False, "error": f"DURATION_TOO_SHORT:{duration}"}
        size = mp4_path.stat().st_size
        if size < 1_000_000:
            self.state.transition(run_id, "QC_FAILED", step="qc", error=f"FILE_TOO_SMALL:{size}")
            return {"ok": False, "error": f"FILE_TOO_SMALL:{size}"}
        self.state.transition(run_id, "QC_PASSED", step="qc")
        self.log("SUCCESS", f"QC PASS: {slug} | duration={duration:.1f}s | size={size/1024/1024:.1f}MB")
        return {"ok": True, "duration": duration, "size": size, "meta": meta}

    def upload_r2(self, slug: str, mp4_path: Path, run_id: str) -> Dict:
        from video_hosting import CloudflareR2Provider
        self.state.transition(run_id, "R2_UPLOADING", step="r2_upload")
        self.log("INFO", f"R2 upload demarre: {slug} | {mp4_path}")
        sha256 = hashlib.sha256(mp4_path.read_bytes()).hexdigest()
        local_size = mp4_path.stat().st_size
        try:
            provider = CloudflareR2Provider.from_dpapi()
            if not provider:
                raise RuntimeError("R2 credentials not available in DPAPI")
        except Exception as e:
            self.state.transition(run_id, "R2_FAILED", step="r2_upload", error=f"CREDENTIALS:{e}")
            return {"ok": False, "error": f"CREDENTIALS:{e}"}
        r2_slug = f"{slug}_{sha256[:16]}"
        key = f"thf/{r2_slug}.mp4"
        try:
            url = provider.upload(mp4_path, r2_slug)
            if not url:
                raise RuntimeError("Upload returned empty URL")
        except Exception as e:
            self.state.transition(run_id, "R2_FAILED", step="r2_upload", error=f"UPLOAD:{e}")
            return {"ok": False, "error": f"UPLOAD:{e}"}
        try:
            s3 = provider._get_s3_client()
            resp = s3.head_object(Bucket=provider.bucket_name, Key=key)
            remote_size = resp.get("ContentLength", 0)
        except Exception as e:
            self.state.transition(run_id, "R2_FAILED", step="r2_upload", error=f"VERIFY:{e}")
            return {"ok": False, "error": f"VERIFY:{e}"}
        if remote_size != local_size:
            self.state.transition(run_id, "R2_FAILED", step="r2_upload", error=f"SIZE_MISMATCH:local={local_size} remote={remote_size}")
            return {"ok": False, "error": f"SIZE_MISMATCH:local={local_size} remote={remote_size}"}
        worker_url = provider.get_worker_url(key)
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute("""
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
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                run_id TEXT
            )
        """)
        c.execute("""
            INSERT OR REPLACE INTO r2_uploads
            (slug, status, local_mp4_path, local_sha256, local_size_bytes, r2_key, r2_size_bytes, r2_url, worker_url, run_id, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)
        """, (slug, "VERIFIED", str(mp4_path), sha256, local_size, key, remote_size, url, worker_url, run_id))
        conn.commit()
        conn.close()
        self.state.transition(run_id, "R2_VERIFIED", step="r2_upload", r2_key=key, r2_url=url, worker_url=worker_url)
        self.log("SUCCESS", f"R2 VERIFIED: {slug} | key={key} | worker={worker_url}")
        return {"ok": True, "r2_key": key, "r2_url": url, "worker_url": worker_url, "remote_size": remote_size}

    def submit_buffer(self, slug: str, run_id: str, mode: str, due_at: str) -> Dict:
        from buffer_adapter import BufferAdapter
        from secure_credentials import CredentialStore
        self.state.transition(run_id, "BUFFER_SUBMITTED", step="buffer_submit")
        self.log("INFO", f"Buffer submission demarre: {slug} | mode={mode}")
        try:
            store = CredentialStore()
            token = store.get("buffer_access_token")
            if not token:
                raise RuntimeError("Token Buffer introuvable")
        except Exception as e:
            self.state.transition(run_id, "BUFFER_FAILED", step="buffer_submit", error=f"TOKEN:{e}")
            return {"ok": False, "error": f"TOKEN:{e}"}
        try:
            buf = BufferAdapter(token)
            ch = buf.get_tiktok_channel()
            if not ch or ch.get("_error"):
                raise RuntimeError("Canal TikTok non disponible")
            if ch.get("isDisconnected"):
                raise RuntimeError("Canal deconnecte")
            if ch.get("isLocked"):
                raise RuntimeError("Canal verrouille")
            ch_id = ch["id"]
        except Exception as e:
            self.state.transition(run_id, "BUFFER_FAILED", step="buffer_submit", error=f"CHANNEL:{e}")
            return {"ok": False, "error": f"CHANNEL:{e}"}
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("""
            SELECT q.slug, q.title_fr, q.description_fr, q.hashtags, q.mention_ia,
                   q.mp4_path, q.thumbnail_path, q.sources_json,
                   r.worker_url, r.r2_url
            FROM tiktok_queue q
            LEFT JOIN r2_uploads r ON q.slug = r.slug
            WHERE q.slug = ?
        """, (slug,))
        row = c.fetchone()
        conn.close()
        if not row:
            self.state.transition(run_id, "BUFFER_FAILED", step="buffer_submit", error="EPISODE_NOT_FOUND")
            return {"ok": False, "error": "EPISODE_NOT_FOUND"}
        ep = dict(row)
        video_url = ep.get("worker_url") or ep.get("r2_url")
        if not video_url:
            self.state.transition(run_id, "BUFFER_FAILED", step="buffer_submit", error="NO_VIDEO_URL")
            return {"ok": False, "error": "NO_VIDEO_URL"}
        desc = ep.get("description_fr") or ""
        sources = json.loads(ep["sources_json"]) if ep["sources_json"] else []
        source_lines = []
        for s in sources[:2]:
            if isinstance(s, dict):
                source_lines.append(f"{s.get('name', '')} ({s.get('url', '')})")
        parts = [desc]
        if source_lines:
            parts.extend(["", "Sources : " + " ; ".join(source_lines)])
        parts.extend(["", ep.get("mention_ia", "Reconstitution historique generee par IA.")])
        desc = "\n".join(parts)
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute("SELECT status FROM buffer_attempts WHERE slug=?", (slug,))
        dup_row = c.fetchone()
        conn.close()
        if dup_row:
            self.state.transition(run_id, "BUFFER_FAILED", step="buffer_submit", error=f"DUPLICATE_SQLITE:{dup_row[0]}")
            return {"ok": False, "error": f"DUPLICATE_SQLITE:{dup_row[0]}"}
        try:
            dup_check = buf.check_existing_posts(ch_id, slug)
            matches = dup_check.get("matches", [])
            if matches:
                self.state.transition(run_id, "BUFFER_FAILED", step="buffer_submit", error=f"DUPLICATE_BUFFER:{len(matches)}")
                return {"ok": False, "error": f"DUPLICATE_BUFFER:{len(matches)}"}
        except Exception as e:
            self.log("WARN", f"Buffer duplicate check failed: {e}")
        try:
            result = buf.create_post(
                channel_id=ch_id,
                text=desc,
                video_url=video_url,
                is_ai_generated=True,
                mode=mode,
                due_at=due_at
            )
        except Exception as e:
            self.state.transition(run_id, "BUFFER_FAILED", step="buffer_submit", error=f"API:{e}")
            return {"ok": False, "error": f"API:{e}"}
        if result.get("status") == "SUCCESS":
            post_id = result["post"]["id"]
            post_status = result["post"].get("status", "unknown")
            conn = sqlite3.connect(str(self.db_path))
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
            c.execute("INSERT OR REPLACE INTO buffer_attempts (slug,status,buffer_post_id,error,run_id) VALUES (?,?,?,?,?)",
                      (slug, "PUBLISHED", post_id, "", run_id))
            c.execute("UPDATE tiktok_queue SET status=?, scheduled_at=CURRENT_TIMESTAMP WHERE slug=?",
                      ("scheduled", slug))
            conn.commit()
            conn.close()
            self.state.transition(run_id, "PUBLICATION_CONFIRMED", step="buffer_submit", buffer_post_id=post_id, buffer_status=post_status)
            self.log("SUCCESS", f"Buffer PUBLISHED: {slug} | post_id={post_id}")
            return {"ok": True, "post_id": post_id, "status": post_status}
        elif result.get("status") == "BLOCKED":
            self.state.transition(run_id, "BUFFER_FAILED", step="buffer_submit", error=f"BLOCKED:{result.get('error')}")
            return {"ok": False, "error": f"BLOCKED:{result.get('error')}"}
        elif result.get("status") == "MUTATION_ERROR":
            self.state.transition(run_id, "BUFFER_FAILED", step="buffer_submit", error=f"MUTATION:{result.get('error')}")
            return {"ok": False, "error": f"MUTATION:{result.get('error')}"}
        else:
            self.state.transition(run_id, "BUFFER_FAILED", step="buffer_submit", error=f"UNKNOWN:{result.get('error')}")
            return {"ok": False, "error": f"UNKNOWN:{result.get('error')}"}

    def _reconstruct_state(self, slug: str, run_id: str) -> str:
        self.log("INFO", "Reconstruction etat legacy pour " + slug + " | run_id=" + run_id)
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute("SELECT status, mp4_path, qc_passed FROM auto_productions WHERE slug=?", (slug,))
        prod = c.fetchone()
        c.execute("SELECT status, r2_key, r2_url, worker_url FROM r2_uploads WHERE slug=?", (slug,))
        r2 = c.fetchone()
        c.execute("SELECT status, buffer_post_id FROM buffer_attempts WHERE slug=?", (slug,))
        buf = c.fetchone()
        conn.close()
        status = "DISCOVERED"
        mp4_path = ""
        r2_key = ""
        r2_url = ""
        worker_url = ""
        buffer_post_id = ""
        if prod and prod[0] == "completed" and prod[1] and Path(prod[1]).exists():
            status = "PRODUCED"
            mp4_path = prod[1]
            if prod[2]:
                status = "QC_PASSED"
        if r2 and r2[0] == "VERIFIED":
            status = "R2_VERIFIED"
            r2_key = r2[1]
            r2_url = r2[2]
            worker_url = r2[3]
        if buf:
            status = "PUBLICATION_CONFIRMED"
            buffer_post_id = buf[1]
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute("UPDATE orchestrator_runs SET status=?, step=?, mp4_path=?, r2_key=?, r2_url=?, worker_url=?, buffer_post_id=?, updated_at=CURRENT_TIMESTAMP WHERE run_id=?",
                  (status, "resume_reconstruct", mp4_path, r2_key, r2_url, worker_url, buffer_post_id, run_id))
        conn.commit()
        conn.close()
        self.log("INFO", "Etat reconstruit: " + status)
        return status

    def run_pipeline(self, slug: str = "", run_id: str = "", mode: str = "TestEndToEnd", resume: bool = False) -> Dict:
        import uuid
        if not run_id:
            run_id = uuid.uuid4().hex[:12]
        self.log("INFO", f"=== PIPELINE START | RUN_ID={run_id} | MODE={mode} | RESUME={resume} ===")
        if not slug:
            slug = self.discover_next_subject()
            if not slug:
                self.log("ERROR", "Aucun nouveau sujet disponible")
                return {"ok": False, "error": "NO_SUBJECT_AVAILABLE", "run_id": run_id}
        self.state.create_run(run_id, slug)
        run_state = self.state.get_run(run_id)
        current_status = run_state["status"]
        if resume:
            current_status = self._reconstruct_state(slug, run_id)
            run_state = self.state.get_run(run_id)
        if current_status in ("DISCOVERED", "FAILED"):
            result = self.produce_video(slug, run_id)
            if not result["ok"]:
                return {"ok": False, "error": result["error"], "run_id": run_id, "step": "production"}
            current_status = self.state.get_run(run_id)["status"]
        if current_status == "PRODUCED":
            mp4 = Path(run_state["mp4_path"])
            result = self.qc_video(slug, mp4, run_id)
            if not result["ok"]:
                return {"ok": False, "error": result["error"], "run_id": run_id, "step": "qc"}
            current_status = self.state.get_run(run_id)["status"]
        if current_status == "QC_PASSED":
            mp4 = Path(self.state.get_run(run_id)["mp4_path"])
            self._add_approval(slug)
            result = self.upload_r2(slug, mp4, run_id)
            if not result["ok"]:
                return {"ok": False, "error": result["error"], "run_id": run_id, "step": "r2"}
            current_status = self.state.get_run(run_id)["status"]
        if current_status == "R2_VERIFIED":
            if mode == "TestEndToEnd":
                self.log("INFO", "TestEndToEnd: publication skipped (use --publish to confirm)")
                return {
                    "ok": True,
                    "status": "READY_FOR_PUBLICATION",
                    "run_id": run_id,
                    "slug": slug,
                    "message": "Episode pret. Utiliser --publish pour confirmer la publication."
                }
            else:
                self.log("INFO", "Auto mode: publication skipped pending explicit confirmation")
                return {
                    "ok": True,
                    "status": "READY_FOR_PUBLICATION",
                    "run_id": run_id,
                    "slug": slug,
                    "message": "Episode pret. Publication en attente de confirmation."
                }
        if current_status == "BUFFER_SUBMITTED":
            return {"ok": True, "status": "PUBLICATION_PENDING", "run_id": run_id, "slug": slug}
        if current_status == "PUBLICATION_CONFIRMED":
            return {"ok": True, "status": "COMPLETE", "run_id": run_id, "slug": slug}
        return {"ok": False, "error": f"Unexpected state: {current_status}", "run_id": run_id}

    def publish(self, slug: str, run_id: str, mode: str, due_at: str) -> Dict:
        run_state = self.state.get_run(run_id)
        if not run_state:
            return {"ok": False, "error": "RUN_NOT_FOUND"}
        if run_state["status"] != "R2_VERIFIED":
            return {"ok": False, "error": f"Invalid state for publication: {run_state['status']}"}
        return self.submit_buffer(slug, run_id, mode, due_at)

    def status(self):
        import sqlite3
        conn = sqlite3.connect(str(self.db_path))
        c = conn.cursor()
        c.execute("SELECT slug, status, mp4_path, qc_passed FROM auto_productions ORDER BY started_at DESC")
        rows = c.fetchall()
        conn.close()
        print("=== ETAT DES PRODUCTIONS ===")
        for row in rows:
            print(f"{row[0]:30s} | {row[1]:15s} | QC={row[3]} | {row[2]}")
        print("\n=== ORCHESTRATOR RUNS ===")
        for run in self.state.list_runs():
            print(f"{run['run_id']:12s} | {run['slug']:30s} | {run['status']:20s} | {run['step']:20s} | {run.get('error','')}")


def main():
    parser = argparse.ArgumentParser(description="TikTokHistoryFactory - Orchestrateur Central")
    parser.add_argument("--mode", choices=["TestEndToEnd", "Auto10h", "Auto12h", "Auto14h", "Status", "Publish"],
                        default="TestEndToEnd")
    parser.add_argument("--subject", type=str, default="")
    parser.add_argument("--run-id", type=str, default="")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--publish", action="store_true", help="Confirmer publication explicite")
    parser.add_argument("--publish-mode", choices=["shareNow", "customScheduled", "addToQueue"],
                        default="customScheduled")
    parser.add_argument("--due-at", type=str, default="")
    args = parser.parse_args()
    orch = PipelineOrchestrator()
    if args.mode == "Status":
        orch.status()
        return
    if args.publish:
        if not args.run_id or not args.subject:
            print("ERREUR: --publish requiert --run-id et --subject")
            sys.exit(1)
        result = orch.publish(args.subject, args.run_id, args.publish_mode, args.due_at)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        sys.exit(0 if result["ok"] else 1)
    result = orch.run_pipeline(
        slug=args.subject,
        run_id=args.run_id,
        mode=args.mode,
        resume=args.resume
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()