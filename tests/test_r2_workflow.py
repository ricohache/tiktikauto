#!/usr/bin/env python3
"""Tests unitaires du workflow R2 upload.
Aucun acces reseau ni DPAPI reel."""
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'src' / 'v5_factory'))

from r2_upload_workflow import (
    _ensure_r2_table, _update_status, select_video, qc_video,
    upload_to_r2, verify_remote_object, load_approved_slugs
)


def test_load_approved_slugs():
    print("=== TEST: load_approved_slugs ===")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({"approved_slugs": ["test-a", "test-b"]}, f)
        approvals_path = Path(f.name)
    
    with patch("r2_upload_workflow.APPROVALS_PATH", approvals_path):
        slugs = load_approved_slugs()
        assert slugs == ["test-a", "test-b"]
        print("[PASS] load_approved_slugs reads JSON")
    
    approvals_path.unlink(missing_ok=True)


def test_ensure_r2_table():
    print("\n=== TEST: _ensure_r2_table ===")
    import sqlite3
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    conn = sqlite3.connect(str(db_path))
    _ensure_r2_table(conn)
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='r2_uploads'")
    assert c.fetchone() is not None
    conn.close()
    db_path.unlink(missing_ok=True)
    print("[PASS] r2_uploads table created")


def test_update_status_idempotent():
    print("\n=== TEST: _update_status idempotent ===")
    import sqlite3
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    conn = sqlite3.connect(str(db_path))
    _ensure_r2_table(conn)
    
    _update_status(conn, "test-slug", "UPLOAD_PENDING")
    c = conn.cursor()
    c.execute("SELECT status FROM r2_uploads WHERE slug = 'test-slug'")
    assert c.fetchone()[0] == "UPLOAD_PENDING"
    
    _update_status(conn, "test-slug", "UPLOADED", r2_key="thf/test.mp4")
    c.execute("SELECT status, r2_key FROM r2_uploads WHERE slug = 'test-slug'")
    row = c.fetchone()
    assert row[0] == "UPLOADED"
    assert row[1] == "thf/test.mp4"
    
    conn.close()
    db_path.unlink(missing_ok=True)
    print("[PASS] _update_status idempotent")


def test_select_video_approved():
    print("\n=== TEST: select_video (approved list) ===")
    import sqlite3
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    conn = sqlite3.connect(str(db_path))
    _ensure_r2_table(conn)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE tiktok_queue (
            slug TEXT PRIMARY KEY,
            status TEXT,
            mp4_path TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    temp_files = []
    for slug in ["test-approved", "test-missing", "test-uploaded"]:
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tf:
            tf.write(b"fake")
            temp_files.append(Path(tf.name))
        c.execute("INSERT INTO tiktok_queue (slug, status, mp4_path) VALUES (?, 'pending', ?)",
                  (slug, str(temp_files[-1])))
    # Mark test-uploaded as already uploaded
    c.execute("INSERT INTO r2_uploads (slug, status) VALUES (?, 'VERIFIED')", ("test-uploaded",))
    conn.commit()
    
    with patch("r2_upload_workflow.DB_PATH", db_path):
        slug, path = select_video(conn, ["test-approved", "test-missing", "test-uploaded"])
        assert slug == "test-approved"
        assert path.exists()
    
    for tf in temp_files:
        tf.unlink(missing_ok=True)
    conn.close()
    db_path.unlink(missing_ok=True)
    print("[PASS] select_video picks first approved with existing MP4")


def test_select_video_dry_run():
    print("\n=== TEST: select_video dry_run ===")
    import sqlite3
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    conn = sqlite3.connect(str(db_path))
    _ensure_r2_table(conn)
    c = conn.cursor()
    c.execute('''CREATE TABLE tiktok_queue (slug TEXT PRIMARY KEY, status TEXT, mp4_path TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tf:
        tf.write(b"fake")
        mp4 = tf.name
    c.execute("INSERT INTO tiktok_queue (slug, status, mp4_path) VALUES (?, 'pending', ?)", ("dry-slug", mp4))
    conn.commit()
    
    with patch("r2_upload_workflow.DB_PATH", db_path):
        result = select_video(conn, ["dry-slug"], dry_run=True)
        assert result is None  # dry_run returns None
    
    Path(mp4).unlink(missing_ok=True)
    conn.close()
    db_path.unlink(missing_ok=True)
    print("[PASS] select_video dry_run returns None")


def test_qc_video():
    print("\n=== TEST: qc_video ===")
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
        f.write(b"fake mp4 content")
        f.flush()
        mp4_path = Path(f.name)
    
    # Patch ffprobe path to non-existent to force fallback
    with patch("r2_upload_workflow.Path") as mock_path_cls:
        mock_path_cls.return_value.exists.return_value = False
        ok, meta, sha = qc_video(mp4_path)
    
    assert ok is True
    assert len(sha) == 64
    assert mp4_path.stat().st_size > 0
    
    mp4_path.unlink(missing_ok=True)
    print("[PASS] qc_video computes SHA256")


def test_upload_to_r2_mock():
    print("\n=== TEST: upload_to_r2 (mocked) ===")
    provider = MagicMock()
    provider.upload = MagicMock(return_value="https://signed.url/thf/test_episode.mp4")
    
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
        f.write(b"fake")
        f.flush()
        mp4_path = Path(f.name)
    
    url, key = upload_to_r2(provider, "test", mp4_path, "abc123def456")
    assert "abc123def456" in key
    assert key == "thf/test_abc123def456.mp4"
    provider.upload.assert_called_once()
    
    mp4_path.unlink(missing_ok=True)
    print("[PASS] upload_to_r2 uses SHA256 in key")


def test_verify_remote_object_mock():
    print("\n=== TEST: verify_remote_object (mocked) ===")
    provider = MagicMock()
    mock_s3 = MagicMock()
    mock_s3.head_object = MagicMock(return_value={"ContentLength": 12345})
    provider._get_s3_client = MagicMock(return_value=mock_s3)
    
    ok, size = verify_remote_object(provider, "thf/test.mp4")
    assert ok is True
    assert size == 12345
    mock_s3.head_object.assert_called_once_with(Bucket=provider.bucket_name, Key="thf/test.mp4")
    
    print("[PASS] verify_remote_object checks head_object")


if __name__ == '__main__':
    test_load_approved_slugs()
    test_ensure_r2_table()
    test_update_status_idempotent()
    test_select_video_approved()
    test_select_video_dry_run()
    test_qc_video()
    test_upload_to_r2_mock()
    test_verify_remote_object_mock()
    print("\n=== ALL R2 WORKFLOW TESTS PASSED ===")
