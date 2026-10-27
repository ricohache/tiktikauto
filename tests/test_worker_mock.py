#!/usr/bin/env python3
"""Tests locaux (mocks) du Cloudflare Worker logic.

Ce script simule le comportement du Worker TypeScript en Python afin de
valider la logique de sécurité, de streaming et de Range sans dépendre
du déploiement Cloudflare.
"""
import hashlib
import io
import os
import tempfile
import unittest
from pathlib import Path

# ------------------------------------------------------------------
# Mock R2 object
# ------------------------------------------------------------------
class MockR2ObjectBody:
    def __init__(self, data: bytes, content_type: str = "video/mp4"):
        self.body = io.BytesIO(data)
        self.size = len(data)
        self.httpMetadata = {"contentType": content_type}

class MockR2Bucket:
    def __init__(self, objects: dict):
        # objects: dict key -> bytes
        self._objects = objects

    def get(self, key: str, options: dict = None):
        data = self._objects.get(key)
        if data is None:
            return None
        if options and "range" in options:
            rng = options["range"]
            offset = rng.get("offset", 0)
            length = rng.get("length", len(data) - offset)
            sliced = data[offset:offset + length]
            obj = MockR2ObjectBody(sliced)
            obj._full_size = len(data)
            return obj
        return MockR2ObjectBody(data)

# ------------------------------------------------------------------
# Worker logic porté en Python
# ------------------------------------------------------------------
def parse_range(range_header: str, full_size: int):
    import re
    m = re.match(r"^bytes=(\d+)-(\d*)$", range_header)
    if not m:
        return None
    start = int(m.group(1))
    end = int(m.group(2)) if m.group(2) else full_size - 1
    if start >= full_size or (m.group(2) and (end < start or end >= full_size)):
        return None
    return {"offset": start, "length": end - start + 1}

def worker_fetch(request_method, request_url, request_headers, env):
    from urllib.parse import urlparse
    parsed = urlparse(request_url)
    key = parsed.path.lstrip("/")

    if request_method not in ("GET", "HEAD"):
        return {"status": 405, "body": "Method Not Allowed", "headers": {}}

    allowed = json.loads(env.get("ALLOWED_KEYS", "[]"))
    if key not in allowed:
        return {"status": 403, "body": "Forbidden", "headers": {}}

    obj = env["BUCKET"].get(key)
    if obj is None:
        return {"status": 404, "body": "Not Found", "headers": {}}

    full_size = obj.size if not hasattr(obj, "_full_size") else obj._full_size
    headers = {
        "Content-Type": obj.httpMetadata.get("contentType", "video/mp4"),
        "Accept-Ranges": "bytes",
        "Cache-Control": "public, max-age=31536000, immutable",
    }

    if request_method == "HEAD":
        headers["Content-Length"] = str(full_size)
        return {"status": 200, "body": None, "headers": headers}

    range_hdr = request_headers.get("Range")
    if range_hdr:
        rng = parse_range(range_hdr, full_size)
        if rng:
            ranged_obj = env["BUCKET"].get(key, {"range": rng})
            end = rng["offset"] + ranged_obj.size - 1
            headers["Content-Length"] = str(ranged_obj.size)
            headers["Content-Range"] = f"bytes {rng['offset']}-{end}/{full_size}"
            return {"status": 206, "body": ranged_obj.body.read(), "headers": headers}
        else:
            headers["Content-Range"] = f"bytes */{full_size}"
            return {"status": 416, "body": "Range Not Satisfiable", "headers": headers}

    headers["Content-Length"] = str(full_size)
    return {"status": 200, "body": obj.body.read(), "headers": headers}

# ------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------
import json

class TestWorkerMock(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mp4_data = b"\x00\x00\x00\x00" + b"fake mp4 data" * 200  # ~2.6 KB
        cls.allowed_key = "thf/angolan-civil-war-1975_b54b077af9055e23.mp4"
        cls.bucket = MockR2Bucket({cls.allowed_key: cls.mp4_data})
        cls.env = {
            "BUCKET": cls.bucket,
            "ALLOWED_KEYS": json.dumps([cls.allowed_key]),
        }

    def test_get_allowed(self):
        resp = worker_fetch("GET", f"https://worker.dev/{self.allowed_key}", {}, self.env)
        self.assertEqual(resp["status"], 200)
        self.assertEqual(resp["headers"]["Content-Type"], "video/mp4")
        self.assertEqual(resp["headers"]["Accept-Ranges"], "bytes")
        self.assertEqual(int(resp["headers"]["Content-Length"]), len(self.mp4_data))
        self.assertEqual(resp["body"], self.mp4_data)

    def test_head_allowed(self):
        resp = worker_fetch("HEAD", f"https://worker.dev/{self.allowed_key}", {}, self.env)
        self.assertEqual(resp["status"], 200)
        self.assertIsNone(resp["body"])
        self.assertEqual(int(resp["headers"]["Content-Length"]), len(self.mp4_data))

    def test_get_forbidden(self):
        resp = worker_fetch("GET", "https://worker.dev/thf/unknown.mp4", {}, self.env)
        self.assertEqual(resp["status"], 403)

    def test_put_not_allowed(self):
        resp = worker_fetch("PUT", f"https://worker.dev/{self.allowed_key}", {}, self.env)
        self.assertEqual(resp["status"], 405)

    def test_range_partial(self):
        headers = {"Range": "bytes=0-1023"}
        resp = worker_fetch("GET", f"https://worker.dev/{self.allowed_key}", headers, self.env)
        self.assertEqual(resp["status"], 206)
        self.assertEqual(len(resp["body"]), 1024)
        self.assertIn("Content-Range", resp["headers"])

    def test_range_invalid(self):
        headers = {"Range": "bytes=999999-1000000"}
        resp = worker_fetch("GET", f"https://worker.dev/{self.allowed_key}", headers, self.env)
        self.assertEqual(resp["status"], 416)

    def test_not_found(self):
        # Key is allowed but missing from bucket
        env = {
            "BUCKET": MockR2Bucket({}),
            "ALLOWED_KEYS": json.dumps([self.allowed_key]),
        }
        resp = worker_fetch("GET", f"https://worker.dev/{self.allowed_key}", {}, env)
        self.assertEqual(resp["status"], 404)

if __name__ == "__main__":
    unittest.main(verbosity=2)
