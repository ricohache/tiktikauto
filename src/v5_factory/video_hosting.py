#!/usr/bin/env python3
"""Module d'hebergement video pour Buffer API.

Buffer necessite une URL publique HTTPS pour chaque video.
Ce module supporte Cloudflare R2 (recommande), Cloudinary,
Transfer.sh et tunnel local.

Pre-requis R2:
    pip install boto3
"""
import json
import os
import urllib.request
from pathlib import Path

from cloudflare_worker_adapter import get_worker_url
from typing import Dict, List, Optional


def _get_r2_credentials_from_dpapi() -> Optional[Dict]:
    """Charge les credentials R2 depuis le coffre DPAPI Windows."""
    try:
        from secure_credentials import CredentialStore
        store = CredentialStore()
        ak = store.get("r2_access_key_id")
        sk = store.get("r2_secret_access_key")
        ep = store.get("r2_endpoint_url")
        bn = store.get("r2_bucket_name")
        if ak and sk and ep and bn:
            return {
                "access_key_id": ak,
                "secret_access_key": sk,
                "endpoint_url": ep,
                "bucket_name": bn,
            }
    except Exception:
        pass
    return None


class VideoHostingProvider:
    """Interface commune pour les fournisseurs d'hebergement video."""

    def upload(self, mp4_path: Path, slug: str) -> Optional[str]:
        """Upload un MP4 et retourne l'URL publique HTTPS."""
        raise NotImplementedError

    def delete(self, url: str) -> bool:
        """Supprime le fichier heberge."""
        raise NotImplementedError

    def get_info(self) -> Dict:
        """Retourne les infos du fournisseur."""
        raise NotImplementedError


class CloudflareR2Provider(VideoHostingProvider):
    """Provider Cloudflare R2 (stockage compatible S3, 10 Go gratuits/mois).
    
    Pre-requis:
    - pip install boto3
    - Credentials stockes dans DPAPI via r2_config_cli.py
    """

    def __init__(self, access_key_id: str, secret_access_key: str, endpoint: str, bucket_name: str, public_domain: str = ""):
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.endpoint = endpoint.rstrip("/")
        self.bucket_name = bucket_name
        self.public_domain = public_domain.rstrip("/") if public_domain else ""
        self._s3_client = None

    def _get_s3_client(self):
        """Initialise et met en cache le client S3."""
        if self._s3_client is not None:
            return self._s3_client
        try:
            import boto3
            from botocore.config import Config
        except ImportError:
            raise RuntimeError("boto3 requis: pip install boto3")
        
        self._s3_client = boto3.client(
            "s3",
            endpoint_url=self.endpoint,
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
            config=Config(signature_version="s3v4")
        )
        return self._s3_client

    def get_info(self) -> Dict:
        return {
            "provider": "Cloudflare R2",
            "free_tier": "10 Go/mois",
            "duration": "Illimitee (compte actif)",
            "public_url": True,
            "https": True,
            "requires_account": True,
            "signup_url": "https://dash.cloudflare.com/sign-up",
            "cost_after_free": "0.015$/Go/mois (stockage), 0$ egress",
            "recommended": True,
            "notes": "Quota gratuit genereux. 8 videos de ~50MB = ~400MB/mois. Compatible S3.",
        }

    def upload(self, mp4_path: Path, slug: str) -> Optional[str]:
        """Upload via l'API S3-compatible de Cloudflare R2."""
        s3 = self._get_s3_client()
        key = f"thf/{slug}.mp4"
        try:
            s3.upload_file(
                str(mp4_path), self.bucket_name, key,
                ExtraArgs={"ContentType": "video/mp4"}
            )
            if self.public_domain:
                return f"{self.public_domain}/{key}"
            # Generate presigned URL (7 days) if no public domain
            url = s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": key},
                ExpiresIn=7*24*3600
            )
            return url
        except Exception as e:
            print(f"[R2] Upload failed: {e}")
            return None

    def delete(self, url: str) -> bool:
        """Supprime un objet R2."""
        s3 = self._get_s3_client()
        # Extract key from URL (handles both public domain and presigned URLs)
        from urllib.parse import urlparse, unquote
        parsed = urlparse(url)
        path = unquote(parsed.path)
        # Remove leading slash and bucket prefix if present
        key = path.lstrip("/")
        if key.startswith(self.bucket_name + "/"):
            key = key[len(self.bucket_name) + 1:]
        try:
            s3.delete_object(Bucket=self.bucket_name, Key=key)
            return True
        except Exception:
            return False

    def get_worker_url(self, r2_key: str) -> Optional[str]:
        """Return a stable HTTPS URL via the Cloudflare Worker proxy.
        
        Falls back to the signed R2 URL if the Worker is not configured.
        """
        worker_url = get_worker_url(r2_key)
        if worker_url:
            return worker_url
        # Fallback: generate a presigned URL if no worker
        s3 = self._get_s3_client()
        try:
            return s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": r2_key},
                ExpiresIn=7*24*3600
            )
        except Exception as e:
            print(f"[R2] Failed to generate presigned URL: {e}")
            return None

    @classmethod
    def from_dpapi(cls, public_domain: str = "") -> Optional["CloudflareR2Provider"]:
        """Cree un provider R2 a partir des credentials DPAPI."""
        creds = _get_r2_credentials_from_dpapi()
        if not creds:
            return None
        return cls(
            access_key_id=creds["access_key_id"],
            secret_access_key=creds["secret_access_key"],
            endpoint=creds["endpoint_url"],
            bucket_name=creds["bucket_name"],
            public_domain=public_domain,
        )

    @classmethod
    def is_configured(cls) -> bool:
        """Verifie si les credentials R2 sont presents dans DPAPI."""
        creds = _get_r2_credentials_from_dpapi()
        return creds is not None


class CloudinaryProvider(VideoHostingProvider):
    """Provider Cloudinary (compte gratuit disponible)."""

    def __init__(self, cloud_name: str, api_key: str, api_secret: str):
        self.cloud_name = cloud_name
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = f"https://api.cloudinary.com/v1_1/{cloud_name}"

    def get_info(self) -> Dict:
        return {
            "provider": "Cloudinary",
            "free_tier": "25 credits/mois",
            "duration": "Illimitee (compte actif)",
            "public_url": True,
            "https": True,
            "requires_account": True,
            "signup_url": "https://cloudinary.com/users/register/free",
            "cost_after_free": "Payant par credit au-dela de 25",
            "recommended": False,
            "notes": "Credits limites pour un compte gratuit.",
        }

    def upload(self, mp4_path: Path, slug: str) -> Optional[str]:
        import hashlib
        import time
        timestamp = str(int(time.time()))
        signature_str = f"timestamp={timestamp}{self.api_secret}"
        signature = hashlib.sha1(signature_str.encode()).hexdigest()
        boundary = "----CloudinaryBoundary"
        data = []
        fields = {
            "api_key": self.api_key,
            "timestamp": timestamp,
            "signature": signature,
            "public_id": f"thf_{slug}",
            "resource_type": "video",
        }
        for key, value in fields.items():
            data.append(f"--{boundary}".encode())
            data.append(f'Content-Disposition: form-data; name="{key}"'.encode())
            data.append(b"")
            data.append(value.encode())
        data.append(f"--{boundary}".encode())
        data.append(f'Content-Disposition: form-data; name="file"; filename="{mp4_path.name}"'.encode())
        data.append(b"Content-Type: video/mp4")
        data.append(b"")
        data.append(mp4_path.read_bytes())
        data.append(f"--{boundary}--".encode())
        body = b"\r\n".join(data)
        req = urllib.request.Request(
            f"{self.base_url}/video/upload",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode("utf-8"))
            return result.get("secure_url")
        except Exception as e:
            print(f"[CLOUDINARY] Upload failed: {e}")
            return None

    def delete(self, url: str) -> bool:
        import re
        import hashlib
        import time
        match = re.search(r"/([^/]+)\.mp4$", url)
        if not match:
            return False
        public_id = match.group(1)
        timestamp = str(int(time.time()))
        signature_str = f"public_id={public_id}&timestamp={timestamp}{self.api_secret}"
        signature = hashlib.sha1(signature_str.encode()).hexdigest()
        payload = json.dumps({
            "public_id": public_id,
            "api_key": self.api_key,
            "timestamp": timestamp,
            "signature": signature,
            "resource_type": "video"
        }).encode()
        req = urllib.request.Request(
            f"{self.base_url}/video/destroy",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode()).get("result") == "ok"
        except Exception:
            return False


class TransferShProvider(VideoHostingProvider):
    """Provider Transfer.sh (service ephemere)."""

    def get_info(self) -> Dict:
        return {
            "provider": "Transfer.sh",
            "free_tier": "Gratuit (sans compte)",
            "duration": "~14 jours (variable)",
            "public_url": True,
            "https": True,
            "requires_account": False,
            "warning": "Service ephemere, non garanti pour production",
            "recommended": False,
        }

    def upload(self, mp4_path: Path, slug: str) -> Optional[str]:
        url = f"https://transfer.sh/{slug}.mp4"
        req = urllib.request.Request(
            url,
            data=mp4_path.read_bytes(),
            headers={"Content-Type": "video/mp4"},
            method="PUT"
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                return resp.read().decode("utf-8").strip()
        except Exception as e:
            print(f"[TRANSFER.SH] Upload failed: {e}")
            return None

    def delete(self, url: str) -> bool:
        return False


class LocalTunnelProvider(VideoHostingProvider):
    """Provider via tunnel local (ngrok/cloudflared)."""

    def get_info(self) -> Dict:
        return {
            "provider": "LocalTunnel (ngrok/cloudflared)",
            "free_tier": "Gratuit (ngrok free: URLs temporaires)",
            "duration": "Session",
            "public_url": True,
            "https": True,
            "requires_account": True,
            "requires_binary": True,
            "warning": "Necessite un tunnel en parallele",
            "recommended": False,
        }

    def upload(self, mp4_path: Path, slug: str) -> Optional[str]:
        raise NotImplementedError("LocalTunnel requires manual tunnel setup")

    def delete(self, url: str) -> bool:
        return True


def get_provider_choice() -> Dict:
    """Retourne un tableau comparatif des fournisseurs disponibles."""
    providers = {
        "cloudflare_r2": CloudflareR2Provider("", "", "", "").get_info(),
        "cloudinary": CloudinaryProvider("", "", "").get_info(),
        "transfer_sh": TransferShProvider().get_info(),
        "localtunnel": LocalTunnelProvider().get_info(),
    }
    return providers


def get_recommended_provider() -> str:
    """Retourne le nom du fournisseur recommande."""
    return "cloudflare_r2"


def create_r2_provider(public_domain: str = "") -> Optional[CloudflareR2Provider]:
    """Factory: cree un provider R2 depuis DPAPI."""
    return CloudflareR2Provider.from_dpapi(public_domain)


if __name__ == '__main__':
    print("=== OPTIONS D'HEBERGEMENT VIDEO ===")
    for name, info in get_provider_choice().items():
        print(f"\n{name.upper()}:")
        for key, value in info.items():
            print(f"  {key}: {value}")
    print(f"\n=== RECOMMANDATION ===")
    print(f"Fournisseur recommande: {get_recommended_provider()}")
    print("Raison: quota gratuit genereux (10 Go/mois), pas de frais de sortie, compatible S3.")
    
    # Show R2 DPAPI status
    if CloudflareR2Provider.is_configured():
        print("\n=== R2 STATUS ===")
        print("Credentials R2 trouves dans DPAPI.")
        provider = create_r2_provider()
        if provider:
            print(f"Bucket: {provider.bucket_name}")
            print(f"Endpoint: {provider.endpoint}")
    else:
        print("\n=== R2 STATUS ===")
        print("Credentials R2 NON configures.")
        print("Executez: r2_config_cli.py --import-file \"...\\TiktokcloudR2.tkn\"")
