#!/usr/bin/env python3
"""Cloudflare Worker URL adapter for stable video distribution.

Provides a stable HTTPS URL for each uploaded R2 object via the
Cloudflare Worker (thf-media-worker). The Worker acts as a secure
read-only proxy to the private R2 bucket.
"""
import json
import os
from pathlib import Path
from typing import Optional


def get_worker_url(r2_key: str) -> Optional[str]:
    """Return the stable Worker URL for a given R2 object key.
    
    Expects the environment variable THF_WORKER_URL to be set to the
    deployed Worker origin (e.g. https://thf-media-worker.<account>.workers.dev).
    
    If THF_WORKER_ENABLED is not "true", returns None so the caller
    can fall back to the signed R2 URL.
    """
    enabled = os.environ.get("THF_WORKER_ENABLED", "false").lower()
    if enabled != "true":
        return None
    base = os.environ.get("THF_WORKER_URL", "").rstrip("/")
    if not base:
        return None
    # Ensure key does not start with a slash
    key = r2_key.lstrip("/")
    return f"{base}/{key}"


def is_worker_configured() -> bool:
    """Return True if the Worker distribution is enabled."""
    return os.environ.get("THF_WORKER_ENABLED", "false").lower() == "true"


def get_worker_info() -> dict:
    """Return diagnostic info about the Worker configuration."""
    return {
        "enabled": is_worker_configured(),
        "base_url": os.environ.get("THF_WORKER_URL", ""),
        "note": "Set THF_WORKER_ENABLED=true and THF_WORKER_URL in .env after deployment",
    }


if __name__ == "__main__":
    import sys
    print("=== Cloudflare Worker Adapter ===")
    print(json.dumps(get_worker_info(), indent=2, ensure_ascii=False))
    test_key = "thf/angolan-civil-war-1975_b54b077af9055e23.mp4"
    url = get_worker_url(test_key)
    if url:
        print(f"\nExample URL: {url}")
    else:
        print(f"\nWorker not enabled — would serve key: {test_key}")
