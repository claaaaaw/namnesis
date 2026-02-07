# Namnesis — Conformance Testing

**Audience:** AI engineers  
**Version:** v2.0 (normative)

## 0. Purpose

Define compatibility criteria so any implementation can be verified as: safe defaults, correct Machine Layer contract.

## 1. Test Fixture Convention

Fixtures under `conformance/fixtures/`:

- `workspace_minimal/` — Minimal workspace sample
- `workspace_with_secrets/` — Contains Forbidden files and secret strings
- `expected_capsule_minimal/` — Golden manifest/report reference

## 2. Required Tests

### 2.1 Round-Trip (Byte-Identical)

**Given** fixture workspace:

- Run `imprint` (or export) to produce a capsule.
- Remove workspace.
- Run `recall` (or import) into an empty directory.

**Assert:**

- Restored files match original bytes (for whitelisted artifacts).
- `capsule.manifest.json` is valid.
- `redaction.report.json` exists and is valid.
- Manifest has `schema_version`, `signature` (ECDSA), and artifact/blob consistency.

### 2.2 Strict Policy (Fail Closed)

Fixture includes:

- `.env`
- `memory/moltbook.json`
- `*_cookies.json`

**Assert:**

- Export in strict mode exits with code `2`.
- Redaction report marks Forbidden items as `exclude`.
- Report findings contain only type/rule ID (no secret substrings).

### 2.3 Dry Run

**Assert:**

- `--dry-run` produces only `redaction.report.json`.
- No blobs or manifest written.
- Report includes `capsule_id`.

### 2.4 Tamper Detection

After export, modify one blob.

**Assert:**

- `validate` exits with code `5`.

### 2.5 Signature and Canonicalization

After export, remove `signature` or change any signature field.

**Assert:**

- `validate` exits with code `4`.

Additional: Verifier must recompute bytes with **RFC 8785 JCS** (no `signature` field) + UTF-8, no trailing newline, and verify ECDSA only over those bytes.

### 2.6 Trusted Signer

Run validate/recall with an untrusted signer (address not matching manifest `signer_address`).

**Assert:**

- `validate` exits with code `4`.
- `recall` fails before writing files (verification before restore).

### 2.7 Manifest Consistency

**Assert:**

- `artifacts[].path` unique.
- `blobs[].blob_id` unique.
- Every `artifacts[].blob_id` present in `blobs[]`.
- `signature.signer_address` is a valid Ethereum address; signature verifies for that address.

### 2.8 Redaction Report Coverage and Summary

**Assert:**

- `decisions` cover all candidate files (including excluded).
- `findings_summary` totals match actual findings and decisions.

## 3. Compatibility Definition

An implementation is compatible if it:

- Can export/import workspace files without changing their content.
- Treats `memory/` as an extensible namespace (no hardcoded filenames).
- Applies strict redaction by default and never exports secrets in plaintext in reports.

## 4. Test Resources

- Golden examples: `docs/examples/` (minimal, typical, redaction)
- JSON Schema: `docs/schemas/v1/`
- Run schema validation and all above tests in CI.

## Related Documents

- PRD: `01-PRD.md`
- Schema: `03-SCHEMAS.md`
- CLI spec: `04-CLI-SPEC.md`
- Security: `05-SECURITY.md`
