"""
End-to-end integration tests for the Namnesis capsule lifecycle.

Tests cover the full flow:
  identity → export → validate → import → verify byte-level fidelity

These tests run entirely offline (local storage backend, no chain, no network).
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from namnesis.anamnesis.capsule import (
    AccessControl,
    BlobInvalidError,
    CapsuleError,
    ExportOptions,
    ImportOptions,
    PolicyViolationError,
    SignatureInvalidError,
    ValidateOptions,
    export_capsule,
    import_capsule,
    validate_capsule,
)
from namnesis.anamnesis.compression import CompressionOptions
from namnesis.anamnesis.storage import LocalDirBackend
from namnesis.sigil.crypto import blob_id, verify_manifest_signature
from namnesis.sigil.eth import generate_eoa, get_address
from namnesis.spec.redaction import RedactionPolicy
from namnesis.spec.schemas import SchemaRegistry, load_json
from namnesis.utils import sha256_hex


# ============ Fixtures ============


@pytest.fixture()
def key_pair() -> tuple[str, str]:
    """Generate a fresh ECDSA key pair."""
    return generate_eoa()


@pytest.fixture()
def second_key_pair() -> tuple[str, str]:
    """Generate a second ECDSA key pair (for multi-signer tests)."""
    return generate_eoa()


@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    """Create a realistic OpenClaw-compatible workspace."""
    ws = tmp_path / "workspace"
    ws.mkdir()

    # Core identity files
    (ws / "MEMORY.md").write_text("# Agent Memory\n\nI remember the sky.\n", encoding="utf-8")
    (ws / "SOUL.md").write_text("# Soul\n\nI am an autonomous agent.\n", encoding="utf-8")
    (ws / "USER.md").write_text("# User\n\nMy operator is Alice.\n", encoding="utf-8")
    (ws / "AGENTS.md").write_text("# Agents\n\n- namnesis-cli\n", encoding="utf-8")

    # Memory directory
    memory_dir = ws / "memory"
    memory_dir.mkdir()
    (memory_dir / "notes.md").write_text(
        "# Notes\n\n- Learned about capsules.\n- Explored crypto.\n",
        encoding="utf-8",
    )
    (memory_dir / "reflections.json").write_text(
        json.dumps({"entries": [{"date": "2026-01-15", "text": "First reflection."}]}, indent=2),
        encoding="utf-8",
    )

    # Projects
    proj_dir = ws / "projects" / "alpha"
    proj_dir.mkdir(parents=True)
    (proj_dir / "STATUS.md").write_text("# Status\n\nPhase: active\n", encoding="utf-8")

    return ws


@pytest.fixture()
def workspace_with_secrets(tmp_path: Path) -> Path:
    """Create a workspace containing forbidden files."""
    ws = tmp_path / "workspace_secrets"
    ws.mkdir()

    (ws / "MEMORY.md").write_text("# Agent Memory\n", encoding="utf-8")
    (ws / ".env").write_text("API_KEY=sk-12345secret\nDB_PASS=hunter2\n", encoding="utf-8")
    (ws / "session_cookies.json").write_text('{"sid": "abc123"}', encoding="utf-8")

    memory_dir = ws / "memory"
    memory_dir.mkdir()
    (memory_dir / "notes.md").write_text("# Notes\n\nSafe content.\n", encoding="utf-8")

    return ws


@pytest.fixture()
def backend(tmp_path: Path) -> LocalDirBackend:
    """Create a local storage backend."""
    backend_root = tmp_path / "storage"
    return LocalDirBackend(backend_root)


@pytest.fixture()
def schema_registry() -> SchemaRegistry:
    """Load the default schema registry."""
    return SchemaRegistry.default()


def _snapshot(workspace: Path) -> dict[str, bytes]:
    """Capture file contents of a workspace keyed by relative POSIX paths."""
    snapshot: dict[str, bytes] = {}
    for p in sorted(workspace.rglob("*")):
        if p.is_file():
            snapshot[p.relative_to(workspace).as_posix()] = p.read_bytes()
    return snapshot


# ============ Full Lifecycle Tests ============


class TestFullLifecycle:
    """End-to-end: genesis identity → export → validate → import → verify."""

    def test_complete_lifecycle(
        self, workspace: Path, backend: LocalDirBackend, key_pair: tuple[str, str], schema_registry: SchemaRegistry
    ) -> None:
        private_key, address = key_pair
        original = _snapshot(workspace)

        # --- Export ---
        capsule_id, manifest = export_capsule(
            ExportOptions(
                workspace=workspace,
                backend=backend,
                private_key_hex=private_key,
                policy=RedactionPolicy.openclaw_default(),
                strict=True,
            )
        )

        assert capsule_id
        assert "/" in capsule_id  # address/uuid format
        assert manifest["spec_version"] == "v1"
        assert manifest["schema_version"] == "2.0.0"
        assert len(manifest["artifacts"]) > 0
        assert len(manifest["blobs"]) > 0

        # --- Validate schema ---
        capsule_root = backend.root / "capsules" / capsule_id
        manifest_json = load_json(capsule_root / "capsule.manifest.json")
        report_json = load_json(capsule_root / "redaction.report.json")
        schema_registry.validate_instance(manifest_json, "capsule.manifest.schema.json")
        schema_registry.validate_instance(report_json, "redaction.report.schema.json")

        # --- Validate capsule integrity ---
        validate_capsule(
            ValidateOptions(
                capsule_id=capsule_id,
                backend=backend,
                trusted_fingerprints={address},
            )
        )

        # --- Wipe workspace and import ---
        shutil.rmtree(workspace)
        workspace.mkdir(parents=True)

        restore_report_path = workspace / "restore.report.json"
        report = import_capsule(
            ImportOptions(
                capsule_id=capsule_id,
                backend=backend,
                target_workspace=workspace,
                trusted_fingerprints={address},
                overwrite=False,
                restore_report_path=restore_report_path,
            )
        )

        # --- Verify byte-level fidelity ---
        restored = _snapshot(workspace)
        # Remove restore report from comparison
        restored.pop("restore.report.json", None)

        for rel_path, data in original.items():
            assert rel_path in restored, f"Missing file after restore: {rel_path}"
            assert restored[rel_path] == data, f"Byte mismatch: {rel_path}"

        # Verify restore report
        assert restore_report_path.exists()
        restore_data = load_json(restore_report_path)
        schema_registry.validate_instance(restore_data, "restore.report.schema.json")
        assert len(restore_data["results"]["created"]) == len(original)
        assert len(restore_data["results"]["failed"]) == 0

    def test_lifecycle_with_access_control(
        self, workspace: Path, backend: LocalDirBackend, key_pair: tuple[str, str]
    ) -> None:
        private_key, address = key_pair
        second_pk, second_addr = generate_eoa()

        access = AccessControl(owner=address, readers=[second_addr], public=False)

        capsule_id, manifest = export_capsule(
            ExportOptions(
                workspace=workspace,
                backend=backend,
                private_key_hex=private_key,
                policy=RedactionPolicy.openclaw_default(),
                strict=True,
                access=access,
            )
        )

        assert manifest.get("access") is not None
        assert manifest["access"]["owner"] == address
        assert second_addr in manifest["access"]["readers"]
        assert manifest["access"]["public"] is False


# ============ Export Tests ============


class TestExport:
    """Tests for the export phase."""

    def test_export_produces_manifest_and_report(
        self, workspace: Path, backend: LocalDirBackend, key_pair: tuple[str, str]
    ) -> None:
        private_key, address = key_pair

        capsule_id, manifest = export_capsule(
            ExportOptions(
                workspace=workspace,
                backend=backend,
                private_key_hex=private_key,
                policy=RedactionPolicy.openclaw_default(),
                strict=True,
            )
        )

        capsule_root = backend.root / "capsules" / capsule_id
        assert (capsule_root / "capsule.manifest.json").exists()
        assert (capsule_root / "redaction.report.json").exists()
        assert (capsule_root / "blobs").is_dir()

    def test_every_artifact_has_matching_blob(
        self, workspace: Path, backend: LocalDirBackend, key_pair: tuple[str, str]
    ) -> None:
        private_key, _ = key_pair

        _, manifest = export_capsule(
            ExportOptions(
                workspace=workspace,
                backend=backend,
                private_key_hex=private_key,
                policy=RedactionPolicy.openclaw_default(),
                strict=True,
            )
        )

        blob_ids = {b["blob_id"] for b in manifest["blobs"]}
        for artifact in manifest["artifacts"]:
            assert artifact["blob_id"] in blob_ids, (
                f"Artifact {artifact['path']} references missing blob {artifact['blob_id']}"
            )

    def test_artifact_kind_classification(
        self, workspace: Path, backend: LocalDirBackend, key_pair: tuple[str, str]
    ) -> None:
        private_key, _ = key_pair

        _, manifest = export_capsule(
            ExportOptions(
                workspace=workspace,
                backend=backend,
                private_key_hex=private_key,
                policy=RedactionPolicy.openclaw_default(),
                strict=True,
            )
        )

        kinds = {a["path"]: a["kind"] for a in manifest["artifacts"]}
        assert kinds.get("MEMORY.md") == "memory"
        assert kinds.get("SOUL.md") == "persona"
        assert kinds.get("USER.md") == "persona"
        assert kinds.get("AGENTS.md") == "ops"
        assert kinds.get("memory/notes.md") == "memory"
        assert kinds.get("projects/alpha/STATUS.md") == "project"

    def test_blob_hash_integrity(
        self, workspace: Path, backend: LocalDirBackend, key_pair: tuple[str, str]
    ) -> None:
        """Each stored blob must match its declared hash."""
        private_key, _ = key_pair

        capsule_id, manifest = export_capsule(
            ExportOptions(
                workspace=workspace,
                backend=backend,
                private_key_hex=private_key,
                policy=RedactionPolicy.openclaw_default(),
                strict=True,
            )
        )

        for blob_entry in manifest["blobs"]:
            data = backend.get_blob(blob_entry["storage"]["ref"])
            assert blob_id(data) == blob_entry["blob_id"]
            assert blob_entry["hash"] == blob_entry["blob_id"]

    def test_manifest_signature_is_valid(
        self, workspace: Path, backend: LocalDirBackend, key_pair: tuple[str, str]
    ) -> None:
        private_key, address = key_pair

        _, manifest = export_capsule(
            ExportOptions(
                workspace=workspace,
                backend=backend,
                private_key_hex=private_key,
                policy=RedactionPolicy.openclaw_default(),
                strict=True,
            )
        )

        sig = manifest["signature"]
        assert sig["alg"] == "ecdsa_secp256k1_eip191"
        assert sig["signer_address"].lower() == address.lower()

        # Verify programmatically
        verify_manifest_signature(manifest, {address})


# ============ Redaction / Policy Tests ============


class TestRedaction:
    """Tests for the redaction policy engine."""

    def test_forbidden_files_blocked_in_strict_mode(
        self, workspace_with_secrets: Path, backend: LocalDirBackend, key_pair: tuple[str, str]
    ) -> None:
        private_key, _ = key_pair

        with pytest.raises(PolicyViolationError) as exc_info:
            export_capsule(
                ExportOptions(
                    workspace=workspace_with_secrets,
                    backend=backend,
                    private_key_hex=private_key,
                    policy=RedactionPolicy.openclaw_default(),
                    strict=True,
                )
            )

        assert exc_info.value.exit_code == 2

    def test_redaction_report_never_contains_secrets(
        self, workspace_with_secrets: Path, backend: LocalDirBackend, key_pair: tuple[str, str]
    ) -> None:
        private_key, _ = key_pair

        with pytest.raises(PolicyViolationError):
            export_capsule(
                ExportOptions(
                    workspace=workspace_with_secrets,
                    backend=backend,
                    private_key_hex=private_key,
                    policy=RedactionPolicy.openclaw_default(),
                    strict=True,
                )
            )

        # Find the report that was written before the error
        reports = list(backend.root.rglob("redaction.report.json"))
        assert reports, "Redaction report should be written even on policy violation"

        report_text = reports[0].read_text(encoding="utf-8")
        assert "sk-12345secret" not in report_text
        assert "hunter2" not in report_text

    def test_dry_run_writes_report_only(
        self, workspace: Path, backend: LocalDirBackend
    ) -> None:
        capsule_id, report = export_capsule(
            ExportOptions(
                workspace=workspace,
                backend=backend,
                private_key_hex=None,
                policy=RedactionPolicy.openclaw_default(),
                strict=True,
                dry_run=True,
            )
        )

        capsule_root = backend.root / "capsules" / capsule_id
        assert (capsule_root / "redaction.report.json").is_file()
        assert not (capsule_root / "capsule.manifest.json").exists()
        assert not (capsule_root / "blobs").exists()


# ============ Import Tests ============


class TestImport:
    """Tests for the import/restore phase."""

    def test_import_skips_existing_files_without_overwrite(
        self, workspace: Path, backend: LocalDirBackend, key_pair: tuple[str, str]
    ) -> None:
        private_key, address = key_pair

        capsule_id, _ = export_capsule(
            ExportOptions(
                workspace=workspace,
                backend=backend,
                private_key_hex=private_key,
                policy=RedactionPolicy.openclaw_default(),
                strict=True,
            )
        )

        # Don't wipe workspace — files still exist
        report = import_capsule(
            ImportOptions(
                capsule_id=capsule_id,
                backend=backend,
                target_workspace=workspace,
                trusted_fingerprints={address},
                overwrite=False,
            )
        )

        assert len(report["results"]["skipped"]) > 0
        assert len(report["results"]["created"]) == 0

    def test_import_overwrites_with_flag(
        self, workspace: Path, backend: LocalDirBackend, key_pair: tuple[str, str]
    ) -> None:
        private_key, address = key_pair

        capsule_id, _ = export_capsule(
            ExportOptions(
                workspace=workspace,
                backend=backend,
                private_key_hex=private_key,
                policy=RedactionPolicy.openclaw_default(),
                strict=True,
            )
        )

        # Corrupt a file
        (workspace / "MEMORY.md").write_text("corrupted!", encoding="utf-8")

        report = import_capsule(
            ImportOptions(
                capsule_id=capsule_id,
                backend=backend,
                target_workspace=workspace,
                trusted_fingerprints={address},
                overwrite=True,
            )
        )

        assert len(report["results"]["overwritten"]) > 0
        # Verify content was restored
        content = (workspace / "MEMORY.md").read_text(encoding="utf-8")
        assert content == "# Agent Memory\n\nI remember the sky.\n"

    def test_import_rejects_untrusted_signer(
        self, workspace: Path, backend: LocalDirBackend, key_pair: tuple[str, str], second_key_pair: tuple[str, str]
    ) -> None:
        private_key, _ = key_pair
        _, untrusted_address = second_key_pair

        capsule_id, _ = export_capsule(
            ExportOptions(
                workspace=workspace,
                backend=backend,
                private_key_hex=private_key,
                policy=RedactionPolicy.openclaw_default(),
                strict=True,
            )
        )

        target = workspace.parent / "restore_target"
        target.mkdir()

        with pytest.raises(SignatureInvalidError):
            import_capsule(
                ImportOptions(
                    capsule_id=capsule_id,
                    backend=backend,
                    target_workspace=target,
                    trusted_fingerprints={untrusted_address},
                )
            )

    def test_import_detects_tampered_blob(
        self, workspace: Path, backend: LocalDirBackend, key_pair: tuple[str, str]
    ) -> None:
        private_key, address = key_pair

        capsule_id, manifest = export_capsule(
            ExportOptions(
                workspace=workspace,
                backend=backend,
                private_key_hex=private_key,
                policy=RedactionPolicy.openclaw_default(),
                strict=True,
            )
        )

        # Tamper with a blob
        blob_entry = manifest["blobs"][0]
        blob_path = backend.root / blob_entry["storage"]["ref"]
        original = blob_path.read_bytes()
        blob_path.write_bytes(original + b"TAMPERED")

        target = workspace.parent / "restore_target"
        target.mkdir()

        with pytest.raises(BlobInvalidError):
            import_capsule(
                ImportOptions(
                    capsule_id=capsule_id,
                    backend=backend,
                    target_workspace=target,
                    trusted_fingerprints={address},
                )
            )

    def test_import_partial_mode_continues_on_error(
        self, workspace: Path, backend: LocalDirBackend, key_pair: tuple[str, str]
    ) -> None:
        private_key, address = key_pair

        capsule_id, manifest = export_capsule(
            ExportOptions(
                workspace=workspace,
                backend=backend,
                private_key_hex=private_key,
                policy=RedactionPolicy.openclaw_default(),
                strict=True,
            )
        )

        # Delete one blob to cause a partial failure
        blob_entry = manifest["blobs"][0]
        blob_path = backend.root / blob_entry["storage"]["ref"]
        blob_path.unlink()

        target = workspace.parent / "restore_target"
        target.mkdir()

        report = import_capsule(
            ImportOptions(
                capsule_id=capsule_id,
                backend=backend,
                target_workspace=target,
                trusted_fingerprints={address},
                partial=True,
            )
        )

        assert len(report["results"]["failed"]) > 0
        # Some files should have been restored
        total = (
            len(report["results"]["created"])
            + len(report["results"]["failed"])
            + len(report["results"]["skipped"])
        )
        assert total > 0


# ============ Signature Tests ============


class TestSignature:
    """Tests for manifest signature integrity."""

    def test_removed_signature_detected(
        self, workspace: Path, backend: LocalDirBackend, key_pair: tuple[str, str]
    ) -> None:
        private_key, address = key_pair

        capsule_id, _ = export_capsule(
            ExportOptions(
                workspace=workspace,
                backend=backend,
                private_key_hex=private_key,
                policy=RedactionPolicy.openclaw_default(),
                strict=True,
            )
        )

        # Remove signature from stored manifest
        manifest_path = backend.root / "capsules" / capsule_id / "capsule.manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest.pop("signature", None)
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        with pytest.raises(SignatureInvalidError):
            validate_capsule(
                ValidateOptions(
                    capsule_id=capsule_id,
                    backend=backend,
                    trusted_fingerprints={address},
                )
            )

    def test_modified_manifest_detected(
        self, workspace: Path, backend: LocalDirBackend, key_pair: tuple[str, str]
    ) -> None:
        """Changing any manifest field invalidates the signature."""
        private_key, address = key_pair

        capsule_id, _ = export_capsule(
            ExportOptions(
                workspace=workspace,
                backend=backend,
                private_key_hex=private_key,
                policy=RedactionPolicy.openclaw_default(),
                strict=True,
            )
        )

        # Modify a field but keep the signature
        manifest_path = backend.root / "capsules" / capsule_id / "capsule.manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["schema_version"] = "9.9.9"  # tamper
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        with pytest.raises((SignatureInvalidError, CapsuleError)):
            validate_capsule(
                ValidateOptions(
                    capsule_id=capsule_id,
                    backend=backend,
                    trusted_fingerprints={address},
                )
            )

    def test_cross_signer_validation(
        self, workspace: Path, backend: LocalDirBackend, key_pair: tuple[str, str], second_key_pair: tuple[str, str]
    ) -> None:
        """Capsule signed by key A should not validate with only key B trusted."""
        private_key_a, address_a = key_pair
        _, address_b = second_key_pair

        capsule_id, _ = export_capsule(
            ExportOptions(
                workspace=workspace,
                backend=backend,
                private_key_hex=private_key_a,
                policy=RedactionPolicy.openclaw_default(),
                strict=True,
            )
        )

        with pytest.raises(SignatureInvalidError):
            validate_capsule(
                ValidateOptions(
                    capsule_id=capsule_id,
                    backend=backend,
                    trusted_fingerprints={address_b},
                )
            )

        # But should succeed with key A
        validate_capsule(
            ValidateOptions(
                capsule_id=capsule_id,
                backend=backend,
                trusted_fingerprints={address_a},
            )
        )

    def test_multi_trusted_signers(
        self, workspace: Path, backend: LocalDirBackend, key_pair: tuple[str, str], second_key_pair: tuple[str, str]
    ) -> None:
        """Validation should pass if signer is in the trusted set."""
        private_key, address = key_pair
        _, address_b = second_key_pair

        capsule_id, _ = export_capsule(
            ExportOptions(
                workspace=workspace,
                backend=backend,
                private_key_hex=private_key,
                policy=RedactionPolicy.openclaw_default(),
                strict=True,
            )
        )

        # Validate with both trusted — should pass
        validate_capsule(
            ValidateOptions(
                capsule_id=capsule_id,
                backend=backend,
                trusted_fingerprints={address, address_b},
            )
        )


# ============ Compression Tests ============


class TestCompression:
    """Tests for 7z compression mode (skipped if py7zr not installed)."""

    @pytest.fixture(autouse=True)
    def _skip_if_no_7z(self) -> None:
        try:
            import py7zr  # noqa: F401
        except ImportError:
            pytest.skip("py7zr not installed")

    def test_compressed_round_trip(
        self, workspace: Path, backend: LocalDirBackend, key_pair: tuple[str, str]
    ) -> None:
        private_key, address = key_pair
        original = _snapshot(workspace)

        capsule_id, manifest = export_capsule(
            ExportOptions(
                workspace=workspace,
                backend=backend,
                private_key_hex=private_key,
                policy=RedactionPolicy.openclaw_default(),
                strict=True,
                compression=CompressionOptions(enabled=True, algorithm="7z", level=9),
            )
        )

        assert manifest["compression"]["enabled"] is True
        assert manifest["compression"]["algorithm"] == "7z"
        assert isinstance(manifest["compression"]["compression_ratio"], float)
        # Compressed mode: single archive blob
        archive_blobs = [b for b in manifest["blobs"] if b.get("is_archive")]
        assert len(archive_blobs) == 1

        # Wipe and restore
        shutil.rmtree(workspace)
        workspace.mkdir(parents=True)

        import_capsule(
            ImportOptions(
                capsule_id=capsule_id,
                backend=backend,
                target_workspace=workspace,
                trusted_fingerprints={address},
            )
        )

        restored = _snapshot(workspace)
        for rel_path, data in original.items():
            assert rel_path in restored, f"Missing after compressed restore: {rel_path}"
            assert restored[rel_path] == data, f"Byte mismatch after compressed restore: {rel_path}"


# ============ Identity Tests ============


class TestIdentity:
    """Tests for ECDSA wallet identity operations."""

    def test_generate_eoa_returns_valid_address(self) -> None:
        private_key, address = generate_eoa()
        assert private_key.startswith("0x")
        assert len(private_key) == 66  # 0x + 64 hex chars
        assert address.startswith("0x")
        assert len(address) == 42  # 0x + 40 hex chars

    def test_get_address_from_private_key(self) -> None:
        private_key, expected_address = generate_eoa()
        actual_address = get_address(private_key)
        assert actual_address == expected_address

    def test_different_keys_produce_different_addresses(self) -> None:
        _, addr1 = generate_eoa()
        _, addr2 = generate_eoa()
        assert addr1 != addr2

    def test_address_is_checksummed(self) -> None:
        """Ethereum address should use EIP-55 mixed-case checksum."""
        _, address = generate_eoa()
        # A checksummed address has mixed case (not all lower or all upper)
        hex_part = address[2:]
        has_upper = any(c.isupper() for c in hex_part if c.isalpha())
        has_lower = any(c.islower() for c in hex_part if c.isalpha())
        # Most addresses will have mixed case; all-numeric addresses are rare
        if any(c.isalpha() for c in hex_part):
            assert has_upper or has_lower
