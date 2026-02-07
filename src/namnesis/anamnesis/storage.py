from __future__ import annotations

import json
import os
import time
from base64 import urlsafe_b64encode
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Protocol

import httpx


class StorageBackend(Protocol):
    def put_blob(self, capsule_id: str, blob_id: str, data: bytes) -> str:
        ...

    def get_blob(self, ref: str) -> bytes:
        ...

    def has_blob(self, ref: str) -> bool:
        ...

    def put_document(self, capsule_id: str, path: str, data: bytes) -> None:
        ...

    def get_document(self, capsule_id: str, path: str) -> bytes:
        ...

    def list(self, capsule_id: str, prefix: str) -> list[str]:
        ...


@dataclass(frozen=True)
class LocalDirBackend:
    root: Path

    def capsule_root(self, capsule_id: str) -> Path:
        return self.root / "capsules" / capsule_id

    def put_blob(self, capsule_id: str, blob_id: str, data: bytes) -> str:
        blobs_dir = self.capsule_root(capsule_id) / "blobs"
        blobs_dir.mkdir(parents=True, exist_ok=True)
        target = blobs_dir / blob_id
        self._atomic_write(target, data)
        rel = Path("capsules") / capsule_id / "blobs" / blob_id
        return rel.as_posix()

    def get_blob(self, ref: str) -> bytes:
        path = (self.root / ref).resolve()
        if not path.is_relative_to(self.root.resolve()):
            raise ValueError(f"Path traversal detected: {ref}")
        return path.read_bytes()

    def has_blob(self, ref: str) -> bool:
        path = (self.root / ref).resolve()
        if not path.is_relative_to(self.root.resolve()):
            return False
        return path.is_file()

    def put_document(self, capsule_id: str, path: str, data: bytes) -> None:
        target = self.capsule_root(capsule_id) / path
        target.parent.mkdir(parents=True, exist_ok=True)
        self._atomic_write(target, data)

    def get_document(self, capsule_id: str, path: str) -> bytes:
        target = (self.capsule_root(capsule_id) / path).resolve()
        if not target.is_relative_to(self.root.resolve()):
            raise ValueError(f"Path traversal detected: {path}")
        return target.read_bytes()

    def list(self, capsule_id: str, prefix: str) -> list[str]:
        base = self.capsule_root(capsule_id)
        root = base / prefix
        if not root.exists():
            return []
        paths = []
        for item in root.rglob("*"):
            if item.is_file():
                paths.append(item.relative_to(base).as_posix())
        return sorted(paths)

    def _atomic_write(self, path: Path, data: bytes) -> None:
        tmp = path.with_suffix(path.suffix + ".tmp")
        try:
            with tmp.open("wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            tmp.replace(path)
        except Exception:
            tmp.unlink(missing_ok=True)
            raise


@dataclass(frozen=True)
class S3Backend:
    bucket: str
    prefix: str = ""
    region: str | None = None
    endpoint_url: str | None = None
    access_key_id: str | None = None
    secret_access_key: str | None = None
    session_token: str | None = None
    read_after_write_retries: int = 3
    read_after_write_delay: float = 0.5

    def _client(self):
        try:
            import boto3
        except ImportError as exc:
            raise RuntimeError("boto3 is required for S3Backend.") from exc

        return boto3.client(
            "s3",
            region_name=self.region,
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
            aws_session_token=self.session_token,
        )

    def _key(self, capsule_id: str, path: str) -> str:
        prefix = self.prefix.strip("/")
        base = f"capsules/{capsule_id}/{path.lstrip('/')}"
        if not prefix:
            return base
        return f"{prefix}/{base}"

    def put_blob(self, capsule_id: str, blob_id: str, data: bytes) -> str:
        key = self._key(capsule_id, f"blobs/{blob_id}")
        client = self._client()
        client.put_object(Bucket=self.bucket, Key=key, Body=data)
        self._ensure_read_after_write(client, key)
        return key

    def get_blob(self, ref: str) -> bytes:
        client = self._client()
        response = client.get_object(Bucket=self.bucket, Key=ref)
        with response["Body"] as body:
            return body.read()

    def has_blob(self, ref: str) -> bool:
        try:
            from botocore.exceptions import ClientError
        except ImportError:
            ClientError = Exception  # type: ignore[misc]
        client = self._client()
        try:
            client.head_object(Bucket=self.bucket, Key=ref)
            return True
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "") if hasattr(e, "response") else ""
            if error_code in ("404", "NoSuchKey"):
                return False
            raise
        except Exception:  # noqa: BLE001
            return False

    def put_document(self, capsule_id: str, path: str, data: bytes) -> None:
        key = self._key(capsule_id, path)
        client = self._client()
        client.put_object(Bucket=self.bucket, Key=key, Body=data)
        self._ensure_read_after_write(client, key)

    def get_document(self, capsule_id: str, path: str) -> bytes:
        key = self._key(capsule_id, path)
        client = self._client()
        response = client.get_object(Bucket=self.bucket, Key=key)
        with response["Body"] as body:
            return body.read()

    def list(self, capsule_id: str, prefix: str) -> list[str]:
        client = self._client()
        key_prefix = self._key(capsule_id, prefix).rstrip("/") + "/"
        paginator = client.get_paginator("list_objects_v2")
        results: list[str] = []
        for page in paginator.paginate(Bucket=self.bucket, Prefix=key_prefix):
            for entry in page.get("Contents", []):
                results.append(entry["Key"])
        return sorted(results)

    def _ensure_read_after_write(self, client, key: str) -> None:
        for _ in range(self.read_after_write_retries):
            try:
                client.head_object(Bucket=self.bucket, Key=key)
                return
            except Exception:  # noqa: BLE001
                time.sleep(self.read_after_write_delay)
        raise RuntimeError(f"Read-after-write check failed for key: {key}")


# ============ Helper Functions ============


def _base64url_encode(data: bytes) -> str:
    """Base64url encode (no padding)."""
    return urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


# ============ Presigned URL Backend ============


@dataclass
class PresignedUrlBackend:
    """
    Remote storage backend using Presigned URLs via credential service.

    Uses ECDSA/secp256k1 (EIP-191 personal_sign) for Relay authentication.

    Workflow:
    1. Client signs request with ECDSA wallet key
    2. Credential service recovers signer, verifies NFT ownership on-chain
    3. Credential service returns Presigned URLs
    4. Client uses URLs to directly access R2/S3

    Attributes:
        credential_service_url: URL of the credential service
        private_key_hex: 0x-prefixed ECDSA private key for signing requests
    """

    credential_service_url: str
    private_key_hex: str
    
    # Internal URL cache (in-memory)
    _url_cache: dict[str, tuple[dict, float]] = field(
        default_factory=dict, repr=False, compare=False
    )
    _cache_buffer_seconds: float = 300  # Refresh 5 minutes before expiration
    
    def _get_presigned_urls(
        self,
        capsule_id: str,
        action: str,
        blobs: Optional[list[str]] = None,
    ) -> dict:
        """
        Get presigned URLs with caching.
        
        Note: Write requests typically aren't cached since blob lists may change.
        """
        # For read, try cache first
        if action == "read":
            cache_key = f"{capsule_id}:read"
            if cache_key in self._url_cache:
                urls, expires_at = self._url_cache[cache_key]
                if time.time() < expires_at - self._cache_buffer_seconds:
                    return urls
        
        # Request new presigned URLs
        result = self._request_presigned_urls(capsule_id, action, blobs)
        
        # Cache read URLs
        if action == "read":
            cache_key = f"{capsule_id}:read"
            self._url_cache[cache_key] = (result["urls"], result["expires_at"])
        
        return result["urls"]
    
    def _request_presigned_urls(
        self,
        capsule_id: str,
        action: str,
        blobs: Optional[list[str]] = None,
    ) -> dict:
        """Request presigned URLs from credential service using ECDSA."""
        from ..sigil.eth import sign_message, get_address

        timestamp = int(time.time())
        message = f"{capsule_id}:{action}:{timestamp}"

        raw_sig = sign_message(message, self.private_key_hex)
        # Ensure 0x prefix for viem compatibility on the Worker side
        signature = raw_sig if raw_sig.startswith("0x") else f"0x{raw_sig}"
        address = get_address(self.private_key_hex)

        payload = {
            "capsule_id": capsule_id,
            "action": action,
            "timestamp": timestamp,
            "signature": signature,
            "address": address,
        }
        if blobs:
            payload["blobs"] = blobs
        
        with httpx.Client(timeout=30) as client:
            resp = client.post(
                f"{self.credential_service_url}/presign",
                json=payload,
            )
        
        if resp.status_code != 200:
            raise RuntimeError(
                f"Credential service error: {resp.status_code} - {resp.text}"
            )
        return resp.json()
    
    # ============ StorageBackend Protocol Implementation ============
    
    def put_blob(self, capsule_id: str, blob_id: str, data: bytes) -> str:
        """Upload blob to R2 using presigned URL."""
        urls = self._get_presigned_urls(capsule_id, "write", blobs=[blob_id])
        url = urls.get("blobs", {}).get(blob_id)
        if not url:
            raise RuntimeError(f"No presigned URL for blob: {blob_id}")
        
        with httpx.Client(timeout=60) as client:
            resp = client.put(url, content=data, headers={"Content-Type": "application/octet-stream"})
        if resp.status_code not in (200, 201):
            raise RuntimeError(f"Upload failed: {resp.status_code}")
        
        return f"capsules/{capsule_id}/blobs/{blob_id}"
    
    def get_blob(self, ref: str) -> bytes:
        """Download blob from R2 using presigned URL."""
        # ref format: capsules/{owner_fp}/{uuid}/blobs/{blob_id}
        parts = ref.split("/")
        if len(parts) < 5:
            raise ValueError(f"Invalid blob reference: {ref}")
        # capsule_id = owner_fp/uuid
        capsule_id = f"{parts[1]}/{parts[2]}"
        blob_id = parts[-1]
        
        urls = self._get_presigned_urls(capsule_id, "read")
        url = urls.get("blobs", {}).get(blob_id)
        if not url:
            raise RuntimeError(f"No presigned URL for blob: {blob_id}")
        
        with httpx.Client(timeout=60) as client:
            resp = client.get(url)
        resp.raise_for_status()
        return resp.content
    
    def has_blob(self, ref: str) -> bool:
        """Check if blob exists."""
        try:
            # Try to get presigned URL - if it exists, blob should exist
            parts = ref.split("/")
            if len(parts) < 5:
                return False
            capsule_id = f"{parts[1]}/{parts[2]}"
            blob_id = parts[-1]
            urls = self._get_presigned_urls(capsule_id, "read")
            return blob_id in urls.get("blobs", {})
        except Exception:  # noqa: BLE001
            return False
    
    def put_document(self, capsule_id: str, path: str, data: bytes) -> None:
        """Upload document (manifest/report) using presigned URL."""
        urls = self._get_presigned_urls(capsule_id, "write", blobs=[])
        
        # Map path to URL key
        if path in ("manifest.json", "capsule.manifest.json"):
            url = urls.get("manifest")
        elif path == "redaction.report.json":
            url = urls.get("redaction_report")
        else:
            raise RuntimeError(f"Unknown document path: {path}")
        
        if not url:
            raise RuntimeError(f"No presigned URL for document: {path}")
        
        with httpx.Client(timeout=60) as client:
            resp = client.put(url, content=data, headers={"Content-Type": "application/json"})
        if resp.status_code not in (200, 201):
            raise RuntimeError(f"Upload failed: {resp.status_code}")
    
    def get_document(self, capsule_id: str, path: str) -> bytes:
        """Download document using presigned URL."""
        urls = self._get_presigned_urls(capsule_id, "read")
        
        if path in ("manifest.json", "capsule.manifest.json"):
            url = urls.get("manifest")
        elif path == "redaction.report.json":
            url = urls.get("redaction_report")
        else:
            raise RuntimeError(f"Unknown document path: {path}")
        
        if not url:
            raise RuntimeError(f"No presigned URL for document: {path}")
        
        with httpx.Client(timeout=60) as client:
            resp = client.get(url)
        resp.raise_for_status()
        return resp.content
    
    def list(self, capsule_id: str, prefix: str) -> list[str]:
        """List objects under prefix."""
        urls = self._get_presigned_urls(capsule_id, "read")
        
        if prefix.startswith("blobs"):
            # Return all blob keys
            return [
                f"capsules/{capsule_id}/blobs/{blob_id}"
                for blob_id in urls.get("blobs", {}).keys()
            ]
        
        return []


# ============ ECDSA Presigned URL Backend (New) ============


@dataclass
class EcdsaPresignedUrlBackend:
    """
    Remote storage backend using ECDSA-signed Presigned URLs.
    
    New Namnesis authentication: uses ECDSA/secp256k1 signing and
    on-chain NFT ownership verification.
    
    Workflow:
    1. Client ECDSA-signs request with soul_id
    2. Relay verifies signature + checks on-chain ownerOf(soulId)
    3. Relay returns presigned R2 URLs
    4. Client uploads/downloads directly via presigned URLs
    
    Attributes:
        credential_service_url: URL of the credential service
        soul_id: On-chain Soul NFT token ID
        private_key: ECDSA private key (hex). If None, loads from env.
    """
    
    credential_service_url: str
    soul_id: int
    private_key: Optional[str] = None
    
    # Internal URL cache (in-memory)
    _url_cache: dict[str, tuple[dict, float]] = field(
        default_factory=dict, repr=False, compare=False
    )
    _cache_buffer_seconds: float = 300
    
    def _get_presigned_urls(
        self,
        capsule_id: str,
        action: str,
        blobs: Optional[list[str]] = None,
    ) -> dict:
        """Get presigned URLs with caching."""
        if action == "read":
            cache_key = f"{capsule_id}:read"
            if cache_key in self._url_cache:
                urls, expires_at = self._url_cache[cache_key]
                if time.time() < expires_at - self._cache_buffer_seconds:
                    return urls
        
        result = self._request_presigned_urls(capsule_id, action, blobs)
        
        if action == "read":
            cache_key = f"{capsule_id}:read"
            self._url_cache[cache_key] = (result["urls"], result["expires_at"])
        
        return result["urls"]
    
    def _request_presigned_urls(
        self,
        capsule_id: str,
        action: str,
        blobs: Optional[list[str]] = None,
    ) -> dict:
        """Request presigned URLs using ECDSA authentication."""
        from ..sigil.eth import sign_message
        
        timestamp = int(time.time())
        message = f"{capsule_id}:{action}:{self.soul_id}:{timestamp}"
        raw_sig = sign_message(message, self.private_key)
        # Ensure 0x prefix for viem compatibility on the Worker side
        signature = raw_sig if raw_sig.startswith("0x") else f"0x{raw_sig}"
        
        payload = {
            "capsule_id": capsule_id,
            "soul_id": self.soul_id,
            "action": action,
            "timestamp": timestamp,
            "signature": signature,
        }
        if blobs:
            payload["blobs"] = blobs
        
        with httpx.Client(timeout=30) as client:
            resp = client.post(
                f"{self.credential_service_url}/presign",
                json=payload,
            )
        
        if resp.status_code != 200:
            raise RuntimeError(
                f"Credential service error: {resp.status_code} - {resp.text}"
            )
        return resp.json()
    
    # StorageBackend Protocol - delegates to same URL-based logic
    
    def put_blob(self, capsule_id: str, blob_id: str, data: bytes) -> str:
        """Upload blob to R2 using presigned URL."""
        urls = self._get_presigned_urls(capsule_id, "write", blobs=[blob_id])
        url = urls.get("blobs", {}).get(blob_id)
        if not url:
            raise RuntimeError(f"No presigned URL for blob: {blob_id}")
        
        with httpx.Client(timeout=60) as client:
            resp = client.put(url, content=data, headers={"Content-Type": "application/octet-stream"})
        if resp.status_code not in (200, 201):
            raise RuntimeError(f"Upload failed: {resp.status_code}")
        
        return f"capsules/{capsule_id}/blobs/{blob_id}"
    
    def get_blob(self, ref: str) -> bytes:
        """Download blob from R2."""
        parts = ref.split("/")
        if len(parts) < 5:
            raise ValueError(f"Invalid blob reference: {ref}")
        capsule_id = f"{parts[1]}/{parts[2]}"
        blob_id = parts[-1]
        
        urls = self._get_presigned_urls(capsule_id, "read")
        url = urls.get("blobs", {}).get(blob_id)
        if not url:
            raise RuntimeError(f"No presigned URL for blob: {blob_id}")
        
        with httpx.Client(timeout=60) as client:
            resp = client.get(url)
        resp.raise_for_status()
        return resp.content
    
    def has_blob(self, ref: str) -> bool:
        """Check if blob exists."""
        try:
            parts = ref.split("/")
            if len(parts) < 5:
                return False
            capsule_id = f"{parts[1]}/{parts[2]}"
            blob_id = parts[-1]
            urls = self._get_presigned_urls(capsule_id, "read")
            return blob_id in urls.get("blobs", {})
        except Exception:
            return False
    
    def put_document(self, capsule_id: str, path: str, data: bytes) -> None:
        """Upload document using presigned URL."""
        urls = self._get_presigned_urls(capsule_id, "write", blobs=[])
        
        if path in ("manifest.json", "capsule.manifest.json"):
            url = urls.get("manifest")
        elif path == "redaction.report.json":
            url = urls.get("redaction_report")
        else:
            raise RuntimeError(f"Unknown document path: {path}")
        
        if not url:
            raise RuntimeError(f"No presigned URL for document: {path}")
        
        with httpx.Client(timeout=60) as client:
            resp = client.put(url, content=data, headers={"Content-Type": "application/json"})
        if resp.status_code not in (200, 201):
            raise RuntimeError(f"Upload failed: {resp.status_code}")
    
    def get_document(self, capsule_id: str, path: str) -> bytes:
        """Download document using presigned URL."""
        urls = self._get_presigned_urls(capsule_id, "read")
        
        if path in ("manifest.json", "capsule.manifest.json"):
            url = urls.get("manifest")
        elif path == "redaction.report.json":
            url = urls.get("redaction_report")
        else:
            raise RuntimeError(f"Unknown document path: {path}")
        
        if not url:
            raise RuntimeError(f"No presigned URL for document: {path}")
        
        with httpx.Client(timeout=60) as client:
            resp = client.get(url)
        resp.raise_for_status()
        return resp.content
    
    def list(self, capsule_id: str, prefix: str) -> list[str]:
        """List objects under prefix."""
        urls = self._get_presigned_urls(capsule_id, "read")
        
        if prefix.startswith("blobs"):
            return [
                f"capsules/{capsule_id}/blobs/{blob_id}"
                for blob_id in urls.get("blobs", {}).keys()
            ]
        
        return []
