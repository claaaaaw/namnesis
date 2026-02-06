from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from namnesis.anamnesis.capsule import (
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
from namnesis.sigil.crypto import blob_id
from namnesis.sigil.eth import generate_eoa
from namnesis.spec.redaction import RedactionPolicy
from namnesis.spec.schemas import SchemaRegistry, load_json
from namnesis.anamnesis.storage import LocalDirBackend
from namnesis.utils import sha256_hex

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_ROOT = REPO_ROOT / "conformance" / "fixtures"


def _copy_fixture(name: str, tmp_path: Path) -> Path:
    source = FIXTURES_ROOT / name
    target = tmp_path / name
    shutil.copytree(source, target)
    return target


def _generate_key() -> tuple[str, str]:
    """Generate an ECDSA key pair.  Returns (private_key_hex, address)."""
    return generate_eoa()


def _export_capsule(tmp_path: Path, workspace: Path) -> tuple[str, dict[str, object], LocalDirBackend, str]:
    backend_root = tmp_path / "backend"
    backend = LocalDirBackend(backend_root)
    private_key_hex, address = _generate_key()
    options = ExportOptions(
        workspace=workspace,
        backend=backend,
        private_key_hex=private_key_hex,
        policy=RedactionPolicy.openclaw_default(),
        strict=True,
        dry_run=False,
    )
    capsule_id, manifest = export_capsule(options)
    return capsule_id, manifest, backend, address


def _snapshot_workspace(workspace: Path) -> dict[str, bytes]:
    snapshot: dict[str, bytes] = {}
    for path in sorted(workspace.rglob("*")):
        if path.is_file():
            snapshot[path.relative_to(workspace).as_posix()] = path.read_bytes()
    return snapshot


def test_round_trip_minimal_workspace(tmp_path: Path) -> None:
    workspace = _copy_fixture("workspace_minimal", tmp_path)
    original = _snapshot_workspace(workspace)

    capsule_id, manifest, backend, address = _export_capsule(tmp_path, workspace)

    backend_root = backend.root
    manifest_path = backend_root / "capsules" / capsule_id / "capsule.manifest.json"
    report_path = backend_root / "capsules" / capsule_id / "redaction.report.json"

    registry = SchemaRegistry.default()
    registry.validate_instance(load_json(manifest_path), "capsule.manifest.schema.json")
    registry.validate_instance(load_json(report_path), "redaction.report.schema.json")

    assert "schema_version" in manifest

    shutil.rmtree(workspace)
    workspace.mkdir(parents=True, exist_ok=True)

    restore_report_path = workspace / "restore.report.json"
    import_capsule(
        ImportOptions(
            capsule_id=capsule_id,
            backend=backend,
            target_workspace=workspace,
            trusted_fingerprints={address},
            overwrite=False,
            partial=False,
            restore_report_path=restore_report_path,
        )
    )

    restored = _snapshot_workspace(workspace)
    for rel_path, data in original.items():
        assert rel_path in restored
        assert restored[rel_path] == data

    registry.validate_instance(load_json(restore_report_path), "restore.report.schema.json")


def test_policy_strict_blocks_forbidden_files(tmp_path: Path) -> None:
    workspace = _copy_fixture("workspace_with_secrets", tmp_path)
    backend_root = tmp_path / "backend"
    backend = LocalDirBackend(backend_root)
    private_key_hex, _ = _generate_key()

    with pytest.raises(PolicyViolationError) as exc:
        export_capsule(
            ExportOptions(
                workspace=workspace,
                backend=backend,
                private_key_hex=private_key_hex,
                policy=RedactionPolicy.openclaw_default(),
                strict=True,
                dry_run=False,
            )
        )

    assert exc.value.exit_code == 2

    reports = list((backend_root / "capsules").rglob("redaction.report.json"))
    assert reports, "Redaction report not written to backend"
    report = load_json(reports[0])

    forbidden = [d for d in report["decisions"] if d["class"] == "forbidden"]
    assert forbidden
    assert all(d["decision"] == "exclude" for d in forbidden)

    report_text = json.dumps(report)
    assert "sk-" not in report_text


def test_dry_run_writes_report_only(tmp_path: Path) -> None:
    workspace = _copy_fixture("workspace_minimal", tmp_path)
    backend = LocalDirBackend(tmp_path / "backend")

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
    assert report["capsule_id"] == capsule_id


def test_tamper_detection_fails_validation(tmp_path: Path) -> None:
    workspace = _copy_fixture("workspace_minimal", tmp_path)
    capsule_id, manifest, backend, address = _export_capsule(tmp_path, workspace)

    blob_entry = manifest["blobs"][0]
    blob_path = backend.root / blob_entry["storage"]["ref"]
    original = blob_path.read_bytes()
    blob_path.write_bytes(original + b"tamper")

    with pytest.raises(BlobInvalidError) as exc:
        validate_capsule(
            ValidateOptions(
                capsule_id=capsule_id,
                backend=backend,
                trusted_fingerprints={address},
            )
        )

    assert exc.value.exit_code == 5


def test_signature_required(tmp_path: Path) -> None:
    workspace = _copy_fixture("workspace_minimal", tmp_path)
    capsule_id, manifest, backend, address = _export_capsule(tmp_path, workspace)

    manifest_path = backend.root / "capsules" / capsule_id / "capsule.manifest.json"
    manifest.pop("signature", None)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(SignatureInvalidError) as exc:
        validate_capsule(
            ValidateOptions(
                capsule_id=capsule_id,
                backend=backend,
                trusted_fingerprints={address},
            )
        )

    assert exc.value.exit_code == 4


def test_trusted_signer_pinning(tmp_path: Path) -> None:
    workspace = _copy_fixture("workspace_minimal", tmp_path)
    capsule_id, _, backend, _ = _export_capsule(tmp_path, workspace)

    with pytest.raises(SignatureInvalidError) as exc:
        validate_capsule(
            ValidateOptions(
                capsule_id=capsule_id,
                backend=backend,
                trusted_fingerprints={"0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef"},
            )
        )

    assert exc.value.exit_code == 4


def test_manifest_consistency(tmp_path: Path) -> None:
    workspace = _copy_fixture("workspace_minimal", tmp_path)
    capsule_id, manifest, backend, address = _export_capsule(tmp_path, workspace)

    artifact_paths = [a["path"] for a in manifest["artifacts"]]
    blob_ids = [b["blob_id"] for b in manifest["blobs"]]

    assert len(artifact_paths) == len(set(artifact_paths))
    assert len(blob_ids) == len(set(blob_ids))
    assert {a["blob_id"] for a in manifest["artifacts"]} <= set(blob_ids)

    manifest_path = backend.root / "capsules" / capsule_id / "capsule.manifest.json"
    stored = load_json(manifest_path)
    stored_signature = stored["signature"]

    assert stored_signature["alg"] == "ecdsa_secp256k1_eip191"
    assert stored_signature["signer_address"].lower() == address.lower()

    blob_entry = manifest["blobs"][0]
    blob_path = backend.root / blob_entry["storage"]["ref"]
    assert blob_id(blob_path.read_bytes()) == blob_entry["blob_id"]


def test_redaction_report_coverage_and_summary(tmp_path: Path) -> None:
    workspace = _copy_fixture("workspace_minimal", tmp_path)
    backend_root = tmp_path / "backend"
    backend = LocalDirBackend(backend_root)
    private_key_hex, _ = _generate_key()

    capsule_id, _ = export_capsule(
        ExportOptions(
            workspace=workspace,
            backend=backend,
            private_key_hex=private_key_hex,
            policy=RedactionPolicy.openclaw_default(),
            strict=True,
            dry_run=False,
        )
    )

    report = load_json(backend_root / "capsules" / capsule_id / "redaction.report.json")

    decision_paths = {d["path"] for d in report["decisions"]}
    workspace_paths = {p.relative_to(workspace).as_posix() for p in workspace.rglob("*") if p.is_file()}
    assert decision_paths == workspace_paths

    findings = report["findings"]
    summary = report["findings_summary"]
    assert summary["total"] == len(findings)

    by_class = {"public": 0, "private": 0, "sensitive": 0, "forbidden": 0}
    by_decision = {
        "exclude": 0,
        "include_encrypted": 0,
        "include_redacted": 0,
        "include_plaintext": 0,
    }
    for decision in report["decisions"]:
        by_class[decision["class"]] = by_class.get(decision["class"], 0) + 1
        by_decision[decision["decision"]] = by_decision.get(decision["decision"], 0) + 1

    assert summary["by_class"] == by_class
    assert summary["by_decision"] == by_decision
