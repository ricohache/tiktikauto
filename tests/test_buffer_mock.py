#!/usr/bin/env python3
"""Tests unitaires MOCK de l'adaptateur Buffer.
Aucun appel reseau reel. Tous les appels sont interceptes."""
import json
import sqlite3
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'src' / 'v5_factory'))

from buffer_adapter import BufferAdapter


def test_buffer_adapter_mock():
    print("=== TESTS MOCK ADAPTATEUR BUFFER ===\n")
    
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    
    try:
        buf = BufferAdapter("fake_test_token_12345", db_path=db_path)
        original_graphql = buf._graphql
        
        def mock_graphql(query, variables=None):
            if "GetAccount" in query and "organizations" in query:
                return {
                    "data": {
                        "account": {
                            "id": "user_123",
                            "email": "test@example.com",
                            "name": "Test User",
                            "organizations": [
                                {"id": "org_456", "name": "Test Org", "channelCount": 2}
                            ]
                        }
                    }
                }
            elif "GetChannels" in query and variables:
                org_id = variables.get("input", {}).get("organizationId")
                assert org_id == "org_456", f"Expected org_456, got {org_id}"
                return {
                    "data": {
                        "channels": [
                            {
                                "id": "chan_tiktok_789",
                                "name": "Test TikTok",
                                "service": "TIKTOK",
                                "isDisconnected": False,
                                "isLocked": False
                            },
                            {
                                "id": "chan_twitter_abc",
                                "name": "Test Twitter",
                                "service": "TWITTER",
                                "isDisconnected": False,
                                "isLocked": False
                            }
                        ]
                    }
                }
            return original_graphql(query, variables)
        
        buf._graphql = mock_graphql
        
        # Test verify_auth
        auth = buf.verify_auth()
        assert "data" in auth
        assert auth["data"]["account"]["email"] == "test@example.com"
        assert auth["data"]["account"]["organizations"][0]["channelCount"] == 2
        print("[PASS] verify_auth (with channelCount)")
        
        # Test _get_first_organization_id
        org_id = buf._get_first_organization_id()
        assert org_id == "org_456"
        print("[PASS] _get_first_organization_id: org_456")
        
        # Test list_channels (auto-resolved org)
        channels = buf.list_channels()
        assert len(channels) == 2
        assert "isDisconnected" in channels[0]
        assert "isLocked" in channels[0]
        assert "username" not in channels[0]
        print(f"[PASS] list_channels ({len(channels)} channels, valid schema)")
        
        # Test get_tiktok_channel (enum comparison)
        tiktok = buf.get_tiktok_channel()
        assert tiktok is not None
        assert tiktok["service"] == "TIKTOK"
        assert tiktok["id"] == "chan_tiktok_789"
        print(f"[PASS] get_tiktok_channel: {tiktok['id']}")
        
        # Test list_channels with explicit organization_id
        channels2 = buf.list_channels("org_456")
        assert len(channels2) == 2
        print("[PASS] list_channels (explicit org_id)")
        
        # Test error propagation (GraphQL errors should not be silently swallowed)
        def mock_graphql_error(query, variables=None):
            if "GetChannels" in query:
                return {"errors": [{"message": "Unauthorized"}]}
            return mock_graphql(query, variables)
        
        buf._channel_cache = None
        buf._graphql = mock_graphql_error
        err_channels = buf.list_channels("org_456")
        assert len(err_channels) == 1
        assert "_error" in err_channels[0]
        print("[PASS] list_channels propagates GraphQL errors")
        
        # Test error propagation for get_tiktok_channel
        buf._channel_cache = None
        err_tiktok = buf.get_tiktok_channel("org_456")
        assert err_tiktok is not None
        assert "_error" in err_tiktok
        print("[PASS] get_tiktok_channel propagates GraphQL errors")
        
        # Restore mock for create_post tests
        buf._graphql = mock_graphql
        buf._channel_cache = None
        
        # Test create_post BLOCKED by default
        result = buf.create_post("chan_tiktok_789", "Test post", "https://example.com/video.mp4")
        assert result["status"] == "BLOCKED"
        print("[PASS] create_post blocked by default")
        
        # Test create_post with env flag
        import os
        os.environ["THF_BUFFER_PUBLISH_ALLOWED"] = "1"
        
        def mock_create_post(query, variables=None):
            if "createPost" in query:
                assert "channelId" in variables["input"]
                assert "assets" in variables["input"]
                assert variables["input"]["assets"][0]["type"] == "video"
                assert variables["input"].get("aiAssisted") == True
                assert variables["input"].get("schedulingType") == "automatic"
                assert variables["input"].get("mode") == "addToQueue"
                assert variables["input"].get("metadata", {}).get("tiktok", {}).get("isAiGenerated") == True
                return {
                    "data": {
                        "createPost": {
                            "id": "post_123",
                            "status": "pending",
                            "text": "Test post",
                            "dueAt": None,
                            "channel": {
                                "id": "chan_tiktok_789",
                                "name": "Test TikTok",
                                "service": "TIKTOK"
                            }
                        }
                    }
                }
            return mock_graphql(query, variables)
        
        buf._graphql = mock_create_post
        result2 = buf.create_post(
            "chan_tiktok_789",
            "Test post",
            "https://example.com/video.mp4",
            is_ai_generated=True
        )
        assert result2["data"]["createPost"]["id"] == "post_123"
        print("[PASS] create_post with THF_BUFFER_PUBLISH_ALLOWED=1 (schema validation)")
        
        # Test create_post scheduled
        def mock_create_scheduled(query, variables=None):
            if "createPost" in query:
                assert variables["input"].get("schedulingType") == "customScheduled"
                assert "dueAt" in variables["input"]
                return {
                    "data": {
                        "createPost": {
                            "id": "post_456",
                            "status": "scheduled",
                            "text": "Scheduled post",
                            "dueAt": "2026-10-27T10:00:00Z",
                            "channel": {
                                "id": "chan_tiktok_789",
                                "name": "Test TikTok",
                                "service": "TIKTOK"
                            }
                        }
                    }
                }
            return mock_graphql(query, variables)
        
        buf._graphql = mock_create_scheduled
        result3 = buf.create_post(
            "chan_tiktok_789",
            "Scheduled post",
            "https://example.com/video.mp4",
            due_at="2026-10-27T10:00:00Z",
            mode="customScheduled"
        )
        assert result3["data"]["createPost"]["id"] == "post_456"
        print("[PASS] create_post scheduled with dueAt")
        
        del os.environ["THF_BUFFER_PUBLISH_ALLOWED"]
        
        # Test SQLite logging
        buf.log_buffer_check("test-slug", "chan_tiktok_789", {"test": "ok"})
        conn = sqlite3.connect(str(db_path))
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM buffer_checks")
        assert c.fetchone()[0] == 1
        conn.close()
        print("[PASS] log_buffer_check SQLite")
        
        buf.log_buffer_attempt("test-slug", "blocked", "Test error")
        conn = sqlite3.connect(str(db_path))
        c = conn.cursor()
        c.execute("SELECT status FROM buffer_attempts WHERE slug='test-slug'")
        assert c.fetchone()[0] == "blocked"
        conn.close()
        print("[PASS] log_buffer_attempt SQLite")
        
        print("\n=== ALL BUFFER MOCK TESTS PASSED ===")
        
    finally:
        db_path.unlink(missing_ok=True)


if __name__ == '__main__':
    test_buffer_adapter_mock()
