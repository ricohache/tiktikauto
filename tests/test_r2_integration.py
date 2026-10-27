#!/usr/bin/env python3
"""Tests unitaires de l'integration Cloudflare R2.
Aucun appel reseau reel. Aucun acces au coffre DPAPI reel.
Tous les credentials sont fictifs et manifestement invalides."""
import sys
import tempfile
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'src' / 'v5_factory'))

from r2_config_cli import parse_r2_token_file
from video_hosting import CloudflareR2Provider, create_r2_provider

# Fictitious values — never real credentials
FAKE_ACCESS_KEY = "FAKE_R2_ACCESS_KEY_12345_INVALID"
FAKE_SECRET_KEY = "FAKE_R2_SECRET_KEY_67890_THIS_IS_NOT_REAL"
FAKE_ENDPOINT = "https://fake-account.r2.cloudflarestorage.com"
FAKE_BUCKET = "tiktokhistoryfactory-fake-test"


class FakeCredentialStore:
    """Stockage en memoire totalement isole pour les tests.
    Ne touche jamais au coffre DPAPI reel.
    """
    def __init__(self):
        self._data = {}

    def set(self, key: str, value: str):
        self._data[key] = value

    def get(self, key: str) -> str:
        return self._data.get(key, "")

    def has(self, key: str) -> bool:
        return key in self._data

    def delete(self, key: str):
        self._data.pop(key, None)


def test_parse_r2_token_file():
    print("=== TEST: parse_r2_token_file ===")
    mock_content = f"""
TikTokHistoryFactory-R2 was successfully created
Summary:
Permissions:
Buckets:
{FAKE_BUCKET}
Use the following credentials for S3 clients:
Access Key ID

{FAKE_ACCESS_KEY}

Secret Access Key

{FAKE_SECRET_KEY}

Default
{FAKE_ENDPOINT}
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".tkn", delete=False) as f:
        f.write(mock_content)
        token_path = Path(f.name)
    
    try:
        creds = parse_r2_token_file(token_path)
        assert creds["bucket_name"] == FAKE_BUCKET
        assert creds["access_key_id"] == FAKE_ACCESS_KEY
        assert creds["secret_access_key"] == FAKE_SECRET_KEY
        assert "r2.cloudflarestorage" in creds["endpoint_url"]
        print("[PASS] parse_r2_token_file (all fields extracted)")
    finally:
        token_path.unlink(missing_ok=True)


def test_fake_dpapi_r2_storage():
    print("\n=== TEST: FakeCredentialStore (isolated) ===")
    store = FakeCredentialStore()
    store.set("r2_access_key_id", "test_ak_123")
    store.set("r2_secret_access_key", "test_sk_456")
    store.set("r2_endpoint_url", "https://test.r2.cloudflarestorage.com")
    store.set("r2_bucket_name", "test-bucket")
    
    assert store.get("r2_access_key_id") == "test_ak_123"
    assert store.get("r2_secret_access_key") == "test_sk_456"
    assert store.get("r2_endpoint_url") == "https://test.r2.cloudflarestorage.com"
    assert store.get("r2_bucket_name") == "test-bucket"
    
    store.delete("r2_access_key_id")
    store.delete("r2_secret_access_key")
    store.delete("r2_endpoint_url")
    store.delete("r2_bucket_name")
    
    print("[PASS] FakeCredentialStore roundtrip (isolated from real DPAPI)")


def test_r2_provider_from_dpapi_mocked():
    print("\n=== TEST: CloudflareR2Provider.from_dpapi (mocked) ===")
    
    fake_store = FakeCredentialStore()
    fake_store.set("r2_access_key_id", "dpapi_ak_123")
    fake_store.set("r2_secret_access_key", "dpapi_sk_456")
    fake_store.set("r2_endpoint_url", "https://dpapi.r2.cloudflarestorage.com")
    fake_store.set("r2_bucket_name", "dpapi-bucket")
    
    # Patch _get_r2_credentials_from_dpapi to use fake store
    with patch("video_hosting._get_r2_credentials_from_dpapi") as mock_get_creds:
        mock_get_creds.return_value = {
            "access_key_id": fake_store.get("r2_access_key_id"),
            "secret_access_key": fake_store.get("r2_secret_access_key"),
            "endpoint_url": fake_store.get("r2_endpoint_url"),
            "bucket_name": fake_store.get("r2_bucket_name"),
        }
        provider = CloudflareR2Provider.from_dpapi()
        assert provider is not None
        assert provider.access_key_id == "dpapi_ak_123"
        assert provider.secret_access_key == "dpapi_sk_456"
        assert provider.endpoint == "https://dpapi.r2.cloudflarestorage.com"
        assert provider.bucket_name == "dpapi-bucket"
        print("[PASS] from_dpapi creates provider correctly (mocked)")


def test_r2_provider_is_configured_mocked():
    print("\n=== TEST: CloudflareR2Provider.is_configured (mocked) ===")
    
    # Not configured
    with patch("video_hosting._get_r2_credentials_from_dpapi") as mock_get_creds:
        mock_get_creds.return_value = None
        assert CloudflareR2Provider.is_configured() == False
        print("[PASS] is_configured False when no credentials")
    
    # Configured
    with patch("video_hosting._get_r2_credentials_from_dpapi") as mock_get_creds:
        mock_get_creds.return_value = {
            "access_key_id": "cfg_ak",
            "secret_access_key": "cfg_sk",
            "endpoint_url": "https://cfg.r2.cloudflarestorage.com",
            "bucket_name": "cfg-bucket",
        }
        assert CloudflareR2Provider.is_configured() == True
        print("[PASS] is_configured True when credentials present")


def test_r2_provider_upload_mock():
    print("\n=== TEST: CloudflareR2Provider.upload (mock boto3) ===")
    provider = CloudflareR2Provider(
        access_key_id="mock_ak",
        secret_access_key="mock_sk",
        endpoint="https://mock.r2.cloudflarestorage.com",
        bucket_name="mock-bucket",
        public_domain=""
    )
    
    mock_s3 = MagicMock()
    mock_s3.upload_file = MagicMock(return_value=None)
    mock_s3.generate_presigned_url = MagicMock(return_value="https://presigned.url/thf/test_episode.mp4")
    
    provider._s3_client = mock_s3
    
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
        mp4_path = Path(f.name)
        f.write(b"fake mp4 data")
    
    try:
        url = provider.upload(mp4_path, "test_episode")
        assert url == "https://presigned.url/thf/test_episode.mp4"
        mock_s3.upload_file.assert_called_once()
        print("[PASS] upload generates presigned URL")
    finally:
        mp4_path.unlink(missing_ok=True)


def test_r2_provider_upload_with_public_domain():
    print("\n=== TEST: CloudflareR2Provider.upload (public domain) ===")
    provider = CloudflareR2Provider(
        access_key_id="mock_ak",
        secret_access_key="mock_sk",
        endpoint="https://mock.r2.cloudflarestorage.com",
        bucket_name="mock-bucket",
        public_domain="https://cdn.example.com"
    )
    
    mock_s3 = MagicMock()
    mock_s3.upload_file = MagicMock(return_value=None)
    provider._s3_client = mock_s3
    
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
        mp4_path = Path(f.name)
        f.write(b"fake mp4 data")
    
    try:
        url = provider.upload(mp4_path, "test_episode")
        assert url == "https://cdn.example.com/thf/test_episode.mp4"
        print("[PASS] upload returns public domain URL")
    finally:
        mp4_path.unlink(missing_ok=True)


def test_r2_provider_delete():
    print("\n=== TEST: CloudflareR2Provider.delete ===")
    provider = CloudflareR2Provider(
        access_key_id="mock_ak",
        secret_access_key="mock_sk",
        endpoint="https://mock.r2.cloudflarestorage.com",
        bucket_name="mock-bucket",
    )
    
    mock_s3 = MagicMock()
    mock_s3.delete_object = MagicMock(return_value=None)
    provider._s3_client = mock_s3
    
    result = provider.delete("https://cdn.example.com/thf/test.mp4")
    assert result == True
    mock_s3.delete_object.assert_called_once_with(Bucket="mock-bucket", Key="thf/test.mp4")
    print("[PASS] delete extracts key from URL")


def test_no_buffer_conflict_mocked():
    print("\n=== TEST: No Buffer credential conflict (mocked) ===")
    fake_store = FakeCredentialStore()
    
    fake_store.set("buffer_access_token", "buffer_token_123")
    fake_store.set("r2_access_key_id", "r2_ak")
    fake_store.set("r2_secret_access_key", "r2_sk")
    
    assert fake_store.get("buffer_access_token") == "buffer_token_123"
    assert fake_store.get("r2_access_key_id") == "r2_ak"
    assert fake_store.get("r2_secret_access_key") == "r2_sk"
    
    # Verify deletion of R2 does not affect Buffer
    fake_store.delete("r2_access_key_id")
    fake_store.delete("r2_secret_access_key")
    assert fake_store.get("buffer_access_token") == "buffer_token_123"
    
    print("[PASS] Buffer and R2 credentials coexist (isolated store)")


if __name__ == '__main__':
    test_parse_r2_token_file()
    test_fake_dpapi_r2_storage()
    test_r2_provider_from_dpapi_mocked()
    test_r2_provider_is_configured_mocked()
    test_r2_provider_upload_mock()
    test_r2_provider_upload_with_public_domain()
    test_r2_provider_delete()
    test_no_buffer_conflict_mocked()
    print("\n=== ALL R2 INTEGRATION TESTS PASSED ===")
