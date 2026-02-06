"""
Capsule — Package, sign, store, and retrieve AI agent memory.

No client-side encryption.  Files are stored as plaintext blobs.
Confidentiality is provided by Relay access control (NFT ownership
verification + presigned URLs with short TTL).

Integrity is guaranteed by ECDSA manifest signatures.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from ..sigil.crypto import (
    CryptoError,
    SignatureError,
    blob_id,
    sign_manifest,
    verify_manifest_signature,
)
from ..spec.models import CapsuleManifest, RedactionReport, RestoreReport
from ..spec.redaction import RedactionPolicy
from ..spec.schemas import SchemaValidationError
from .compression import (
    CompressionError,
    CompressionOptions,
    CompressionResult,
    compress_files,
    decompress_archive,
)
from .storage import LocalDirBackend, PresignedUrlBackend, S3Backend, StorageBackend
from ..utils import sha256_hex, utc_now_rfc3339, uuidv7


class CapsuleError(RuntimeError):
    exit_code: int = 1


class PolicyViolationError(CapsuleError):
    exit_code = 2


class SchemaInvalidError(CapsuleError):
    exit_code = 3


class SignatureInvalidError(CapsuleError):
    exit_code = 4


class BlobInvalidError(CapsuleError):
    exit_code = 5


class RestoreFailedError(CapsuleError):
    exit_code = 7


@dataclass(frozen=True)
class AccessControl:
    """
    Access control configuration for a capsule.

    Attributes:
        owner: Owner's Ethereum address (checksummed, 0x-prefixed)
        readers: List of authorized reader addresses
        public: Whether the capsule is publicly accessible
    """
    owner: str
    readers: list[str] = field(default_factory=list)
    public: bool = False

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"owner": self.owner}
        if self.readers:
            result["readers"] = list(self.readers)
        result["public"] = self.public
        return result


@dataclass(frozen=True)
class ExportOptions:
    workspace: Path
    backend: StorageBackend
    private_key_hex: str | None  # 0x-prefixed ECDSA private key for signing
    policy: RedactionPolicy
    strict: bool = True
    dry_run: bool = False
    compression: CompressionOptions = field(default_factory=lambda: CompressionOptions(enabled=False))
    access: Optional[AccessControl] = None


@dataclass(frozen=True)
class ImportOptions:
    capsule_id: str
    backend: StorageBackend
    target_workspace: Path
    trusted_fingerprints: set[str]  # actually trusted addresses
    overwrite: bool = False
    partial: bool = False
    restore_report_path: Path | None = None


@dataclass(frozen=True)
class ValidateOptions:
    capsule_id: str
    backend: StorageBackend
    trusted_fingerprints: set[str]  # actually trusted addresses


@dataclass(frozen=True)
class ChainMetadata:
    """On-chain metadata linking a capsule to its Soul NFT."""
    soul_id: int
    chain_id: int = 84532
    kernel_address: Optional[str] = None
    soul_token_address: Optional[str] = None
    soul_guard_address: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "soul_id": self.soul_id,
            "chain_id": self.chain_id,
        }
        if self.kernel_address:
            result["kernel_address"] = self.kernel_address
        if self.soul_token_address:
            result["soul_token_address"] = self.soul_token_address
        if self.soul_guard_address:
            result["soul_guard_address"] = self.soul_guard_address
        return result


# ============ Export ============


def export_capsule(options: ExportOptions) -> tuple[str, dict[str, Any]]:
    """Export a workspace to a signed capsule (plaintext blobs).

    Returns:
        Tuple of (capsule_id, manifest)
    """
    capsule_id = _generate_capsule_id(options.private_key_hex)

    report = options.policy.scan_workspace(options.workspace)
    report["capsule_id"] = capsule_id

    if options.strict and any(d["class"] == "forbidden" for d in report["decisions"]):
        _write_redaction_report(options.backend, capsule_id, report)
        raise PolicyViolationError("Forbidden findings detected in strict mode.")

    if options.dry_run:
        _write_redaction_report(options.backend, capsule_id, report)
        RedactionReport.from_dict(report)
        return capsule_id, report

    if not options.private_key_hex:
        raise CapsuleError("Private key is required for export.")

    included_files = [
        d["path"] for d in report["decisions"]
        if d["decision"] != "exclude"
    ]

    artifacts: list[dict[str, Any]] = []
    blobs: list[dict[str, Any]] = []
    compression_info: dict[str, Any] = {"enabled": False}

    if options.compression.enabled and included_files:
        # === Compressed mode: single 7z archive blob ===
        try:
            compress_result = compress_files(
                workspace=options.workspace,
                file_paths=included_files,
                options=options.compression,
            )
        except CompressionError as exc:
            raise CapsuleError(f"Compression failed: {exc}") from exc

        data = compress_result.archive_data
        bid = blob_id(data)
        ref = options.backend.put_blob(capsule_id, bid, data)

        blobs.append({
            "blob_id": bid,
            "hash": bid,
            "size_bytes": len(data),
            "storage": {"backend": _backend_name(options.backend), "ref": ref},
            "is_archive": True,
            "archive_format": "7z",
        })

        for decision in report["decisions"]:
            if decision["decision"] == "exclude":
                continue
            rel_path = decision["path"]
            full_path = options.workspace / rel_path
            payload = full_path.read_bytes()
            artifacts.append({
                "path": rel_path,
                "kind": artifact_kind(rel_path),
                "mode": decision["decision"],
                "plaintext_hash": sha256_hex(payload),
                "size_bytes": len(payload),
                "blob_id": bid,
            })

        compression_info = {
            "enabled": True,
            "algorithm": options.compression.algorithm,
            "level": options.compression.level,
            "original_size_bytes": compress_result.original_size,
            "compressed_size_bytes": compress_result.compressed_size,
            "compression_ratio": round(compress_result.compression_ratio, 4),
        }
    else:
        # === Default mode: one blob per file ===
        for decision in report["decisions"]:
            if decision["decision"] == "exclude":
                continue
            rel_path = decision["path"]
            full_path = options.workspace / rel_path
            payload = full_path.read_bytes()
            bid = blob_id(payload)
            ref = options.backend.put_blob(capsule_id, bid, payload)
            blobs.append({
                "blob_id": bid,
                "hash": bid,
                "size_bytes": len(payload),
                "storage": {"backend": _backend_name(options.backend), "ref": ref},
            })
            artifacts.append({
                "path": rel_path,
                "kind": artifact_kind(rel_path),
                "mode": decision["decision"],
                "plaintext_hash": sha256_hex(payload),
                "size_bytes": len(payload),
                "blob_id": bid,
            })

    manifest = build_manifest(
        capsule_id=capsule_id,
        artifacts=artifacts,
        blobs=blobs,
        policy_version=options.policy.policy_version,
        compression=compression_info,
        access=options.access,
    )
    manifest["signature"] = sign_manifest(manifest, options.private_key_hex)

    CapsuleManifest.from_dict(manifest)
    RedactionReport.from_dict(report)

    _write_redaction_report(options.backend, capsule_id, report)
    _write_manifest(options.backend, capsule_id, manifest)
    return capsule_id, manifest


# ============ Import ============


def import_capsule(options: ImportOptions) -> dict[str, Any]:
    """Import a workspace from a signed capsule (plaintext blobs).

    Returns:
        Restore report dict
    """
    manifest = _load_manifest(options.backend, options.capsule_id)
    _ensure_supported_spec_version(manifest)
    _ensure_signature_present(manifest)
    try:
        CapsuleManifest.from_dict(manifest)
    except SchemaValidationError as exc:
        raise SchemaInvalidError(str(exc)) from exc

    _verify_manifest_or_raise(manifest, options.trusted_fingerprints)

    results: dict[str, list] = {"created": [], "skipped": [], "overwritten": [], "failed": []}

    compression = manifest.get("compression", {})
    is_compressed = compression.get("enabled", False)

    if is_compressed:
        archive_blob = next((b for b in manifest["blobs"] if b.get("is_archive")), None)
        if not archive_blob:
            raise BlobInvalidError("Compressed capsule missing archive blob.")

        data = _get_and_verify_blob(options.backend, archive_blob)

        try:
            expected_files = [a["path"] for a in manifest["artifacts"]]
            decompress_archive(data, options.target_workspace, expected_files)
        except CompressionError as exc:
            raise RestoreFailedError(f"Failed to extract archive: {exc}") from exc

        for artifact in manifest["artifacts"]:
            path = artifact["path"]
            target = options.target_workspace / path
            if not target.exists():
                results["failed"].append({"path": path, "error": "File not extracted"})
                continue
            extracted = target.read_bytes()
            if sha256_hex(extracted) != artifact["plaintext_hash"]:
                results["failed"].append({"path": path, "error": "Plaintext hash mismatch"})
                continue
            results["created"].append({
                "path": path,
                "size_bytes": len(extracted),
                "plaintext_hash": artifact["plaintext_hash"],
            })
    else:
        for artifact in manifest["artifacts"]:
            path = artifact["path"]
            target = options.target_workspace / path
            existed = target.exists()
            if existed and not options.overwrite:
                results["skipped"].append({"path": path, "reason": "exists"})
                continue
            try:
                blob_entry = _lookup_blob(manifest, artifact["blob_id"])
                data = _get_and_verify_blob(options.backend, blob_entry)
                if sha256_hex(data) != artifact["plaintext_hash"]:
                    raise BlobInvalidError("Plaintext hash mismatch.")
                try:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(data)
                except OSError as exc:
                    raise RestoreFailedError("Failed to write restored file.") from exc
                entry = {"path": path, "size_bytes": len(data), "plaintext_hash": artifact["plaintext_hash"]}
                if existed and options.overwrite:
                    results["overwritten"].append({**entry, "reason": "overwrite"})
                else:
                    results["created"].append(entry)
            except CapsuleError as exc:
                if options.partial:
                    results["failed"].append({"path": path, "error": str(exc)})
                    continue
                raise

    report = build_restore_report(options.capsule_id, options.target_workspace, results)
    if options.restore_report_path:
        RestoreReport.from_dict(report)
        options.restore_report_path.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    return report


# ============ Validate ============


def validate_capsule(options: ValidateOptions) -> None:
    manifest = _load_manifest(options.backend, options.capsule_id)
    _ensure_supported_spec_version(manifest)
    _ensure_signature_present(manifest)
    try:
        CapsuleManifest.from_dict(manifest)
    except SchemaValidationError as exc:
        raise SchemaInvalidError(str(exc)) from exc

    _verify_manifest_or_raise(manifest, options.trusted_fingerprints)

    for b in manifest["blobs"]:
        _get_and_verify_blob(options.backend, b)


# ============ Manifest Builder ============


def build_manifest(
    capsule_id: str,
    artifacts: list[dict[str, Any]],
    blobs: list[dict[str, Any]],
    policy_version: str,
    compression: Optional[dict[str, Any]] = None,
    access: Optional[AccessControl] = None,
    chain_metadata: Optional[ChainMetadata] = None,
) -> dict[str, Any]:
    manifest: dict[str, Any] = {
        "spec_version": "v1",
        "schema_version": "2.0.0",
        "capsule_id": capsule_id,
        "created_at": utc_now_rfc3339(),
        "tool": _tool_info(),
        "artifacts": artifacts,
        "blobs": blobs,
        "redaction": {"report_path": "redaction.report.json", "policy_version": policy_version},
        "signature": {},
    }
    if compression:
        manifest["compression"] = compression
    if access:
        manifest["access"] = access.to_dict()
    if chain_metadata:
        manifest["chain_metadata"] = chain_metadata.to_dict()
    return manifest


def build_restore_report(capsule_id: str, target_workspace: Path, results: dict[str, Any]) -> dict[str, Any]:
    return {
        "spec_version": "v1",
        "schema_version": "1.0.0",
        "created_at": utc_now_rfc3339(),
        "capsule_id": capsule_id,
        "target_workspace": str(target_workspace),
        "results": results,
    }


def artifact_kind(rel_path: str) -> str:
    posix = Path(rel_path)
    if rel_path.startswith("memory/") or rel_path == "MEMORY.md":
        return "memory"
    if posix.name in {"SOUL.md", "USER.md", "IDENTITY.md"}:
        return "persona"
    if posix.name in {"AGENTS.md", "TOOLS.md", "HEARTBEAT.md"}:
        return "ops"
    if rel_path.endswith("STATUS.md") and rel_path.startswith("projects/"):
        return "project"
    return "other"


# ============ Internal Helpers ============


def _tool_info() -> dict[str, str]:
    return {"name": "namnesis", "version": "2.0.0"}


def _backend_name(backend: StorageBackend) -> str:
    if isinstance(backend, LocalDirBackend):
        return "local_dir"
    if isinstance(backend, S3Backend):
        return "s3"
    if isinstance(backend, PresignedUrlBackend):
        return "presigned_url"
    raise CapsuleError(f"Unknown backend type: {type(backend).__name__}")


def _generate_capsule_id(private_key_hex: str | None) -> str:
    uuid_part = str(uuidv7())
    if private_key_hex:
        try:
            from eth_account import Account
            account = Account.from_key(private_key_hex)
            return f"{account.address}/{uuid_part}"
        except Exception:  # noqa: BLE001
            pass
    return uuid_part


def _write_manifest(backend: StorageBackend, capsule_id: str, manifest: dict[str, Any]) -> None:
    backend.put_document(capsule_id, "capsule.manifest.json", _json_bytes(manifest))


def _write_redaction_report(backend: StorageBackend, capsule_id: str, report: dict[str, Any]) -> None:
    backend.put_document(capsule_id, "redaction.report.json", _json_bytes(report))


def _load_manifest(backend: StorageBackend, capsule_id: str) -> dict[str, Any]:
    payload = backend.get_document(capsule_id, "capsule.manifest.json")
    return json.loads(payload.decode("utf-8"))


def _lookup_blob(manifest: dict[str, Any], blob_id_val: str) -> dict[str, Any]:
    for b in manifest["blobs"]:
        if b["blob_id"] == blob_id_val:
            return b
    raise BlobInvalidError(f"Blob {blob_id_val} not found in manifest.")


def _get_and_verify_blob(backend: StorageBackend, blob_entry: dict[str, Any]) -> bytes:
    """Download a blob and verify its hash."""
    try:
        data = backend.get_blob(blob_entry["storage"]["ref"])
    except FileNotFoundError as exc:
        raise BlobInvalidError("Missing blob.") from exc
    if sha256_hex(data) != blob_entry["blob_id"]:
        raise BlobInvalidError("Blob hash mismatch.")
    return data


def _verify_manifest_or_raise(manifest: dict[str, Any], trusted_addresses: set[str]) -> None:
    try:
        verify_manifest_signature(manifest, trusted_addresses)
    except SignatureError as exc:
        raise SignatureInvalidError(str(exc)) from exc


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _ensure_supported_spec_version(manifest: dict[str, Any]) -> None:
    if manifest.get("spec_version") != "v1":
        raise SchemaInvalidError(f"Unsupported spec_version: {manifest.get('spec_version')}")


def _ensure_signature_present(manifest: dict[str, Any]) -> None:
    signature = manifest.get("signature")
    if not isinstance(signature, dict):
        raise SignatureInvalidError("Manifest missing signature object.")
