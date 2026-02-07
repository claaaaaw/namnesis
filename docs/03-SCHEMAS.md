# Namnesis — Schemas v2.0 (Machine Layer)

**Audience:** AI engineers  
**Version:** v2.0 (normative)

## 0. Purpose

Define the **Machine Layer contract** for Namnesis. This document is normative; other docs must not contradict it.

## Related Documents

- Architecture: `02-ARCHITECTURE.md`
- CLI spec: `04-CLI-SPEC.md`
- Security: `05-SECURITY.md`
- Conformance: `06-CONFORMANCE.md`

## 1. Versioning and Extension

- Capsule format versions: `v1`, `v1.1`, … (non-breaking within v1.x).
- Each JSON document includes:
  - `spec_version`: e.g. `"v1"`
  - `schema_version`: semver for the schema (e.g. `"2.0.0"`)
- Implementations MUST ignore unknown fields **only if** they are prefixed with `x_`.
- Unknown non-`x_` fields MUST be rejected as invalid.
- Extension fields MUST use `x_` prefix and MUST NOT change v1 semantics.

## 2. Encodings and Normalization (v1.1, normative)

- **Hashes:** lowercase hex (e.g. sha256 = 64 hex chars).
- **capsule_id (v2):** `{owner_ethereum_address}/{uuid}`
  - `owner_ethereum_address`: 0x-prefixed 40 hex chars
  - `uuid`: UUIDv7 string
  - Example: `0x1234567890abcdef1234567890abcdef12345678/01925b6a-7c8d-7def-9012-345678abcdef`
- `created_at`: RFC3339.
- **Paths (artifacts):**
  - POSIX-style `/` only; relative; no leading `/`.
  - No `..` or drive letters.
  - Unicode normalized to NFC.

## 3. Required JSON Documents (v1)

1. `capsule.manifest.json`
2. `redaction.report.json`

Optional: `restore.report.json`

## 4. `capsule.manifest.json` (normative)

### 4.1 Purpose

Describes one capsule snapshot: which artifacts are included, how to fetch blobs, how to check integrity, and redaction/policy linkage.

### 4.2 Required Top-Level Fields (v1)

- `spec_version` (string) — MUST be `"v1"`
- `schema_version` (string) — semver (e.g. `"2.0.0"`)
- `capsule_id` (string) — `{owner_address}/{uuid}` format
- `created_at` (RFC3339)
- `tool` (object): `{ name, version }`
- `source` (object, optional): `{ workspace_fingerprint?, openclaw_version?, host_tz? }` (non-sensitive only)
- `artifacts` (array)
- `blobs` (array)
- `redaction` (object): `report_path` (MUST be `redaction.report.json`), `policy_version`
- `signature` (object) — **required**

### 4.2.1 Signature Object (v2, normative)

Current implementation uses ECDSA (no Ed25519).

- `alg` (string) — MUST be `ecdsa_secp256k1_eip191`
- `payload_alg` (string) — MUST be `rfc8785_jcs_without_signature_utf8`
- `signer_address` (string) — Ethereum address (0x-prefixed, 40 hex chars)
- `sig` (string) — hex-encoded signature (no 0x prefix in manifest)

**Bytes to sign:**

1. Remove top-level `signature` from manifest.
2. Canonicalize with **RFC 8785 (JCS)**.
3. UTF-8 encode; no trailing newline.
4. Sign those bytes with EIP-191 personal_sign.

Validator MUST recompute the same bytes and verify the signature; signer_address MUST be in the trusted set.

### 4.2.2 Access (optional)

- `access` (object):
  - `owner` (string): Ethereum address or legacy identifier
  - `readers` (array of strings, optional)
  - `public` (boolean, default false)

### 4.2.3 Compression (optional)

- `compression` (object): present only if compression was used
  - `enabled` (boolean)
  - `algorithm` (string), e.g. `"7z"`
  - `level` (int), `original_size_bytes`, `compressed_size_bytes`, `compression_ratio`

### 4.2.4 chain_metadata (optional)

- `chain_metadata` (object): `soul_id`, `chain_id`, `kernel` (address), etc.

### 4.3 Artifact Record (v1)

Each artifact is one file to restore.

- `path` (string) — relative, normalized
- `kind` (string) — `memory | persona | ops | project | other` (or `x_*`)
- `mode` (string) — `include_encrypted | include_redacted | include_plaintext`
- `plaintext_hash` (string) — lowercase hex sha256 of bytes to restore
- `size_bytes` (int)
- `blob_id` (string) — lowercase hex; references `blobs[]`

Only non-excluded artifacts appear. Exclusions are in `redaction.report.json`.

### 4.4 Blob Record (v1)

- `blob_id` (string) — lowercase hex sha256(blob_bytes)
- `hash` (string) — same as blob_id (for compatibility)
- `size_bytes` (int)
- `storage` (object): `backend` (`local_dir | s3 | presigned_url`), `ref` (backend-specific)
- `is_archive` (boolean, optional)
- `archive_format` (string, optional), e.g. `"7z"`

**Consistency:**

- `artifacts[].path` unique; `blobs[].blob_id` unique; every `artifacts[].blob_id` in `blobs[]`.

## 5. `redaction.report.json` (normative)

### 5.1 Required Fields (v1)

- `spec_version`, `schema_version`, `policy_version`, `created_at`, `capsule_id`
- `detectors` (array): `{ id, version?, config_hash }`
- `decisions` (array): `{ path, decision, class, reasons, detector_hits? }`
  - `decision`: `exclude | include_encrypted | include_redacted | include_plaintext`
  - `class`: `public | private | sensitive | forbidden`
- `findings` (array): `{ path, rule_id, severity, locations }`
- `findings_summary`: `total`, `by_class`, `by_decision`

### 5.2 Safety

Findings MUST NOT contain raw secret values or matching substrings; only types, rule IDs, and locations.

## 6. `restore.report.json` (optional)

- `spec_version`, `schema_version`, `created_at`, `capsule_id`, `target_workspace`
- `results`: `created`, `skipped`, `overwritten`, `failed` (each list of path + reason or error)

## 7. Schema Resources

- `schemas/v1/capsule.manifest.schema.json`
- `schemas/v1/redaction.report.schema.json`
- `schemas/v1/restore.report.schema.json`
- Examples: `examples/minimal/`, `examples/typical/`, `examples/redaction/`
