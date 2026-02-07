# Namnesis — Product Requirements Document (PRD)

**Audience:** AI engineers  
**Version:** v2.0  
**Status:** Locked

## 1. Background

AI agent persistent state (memory, persona, runbooks) lives in local files. We need a formal, portable representation that can be stored, transferred, versioned, and restored safely — and tied to on-chain NFT ownership.

## 2. Problem

- No **machine-readable contract** for “agent state”.
- No **secure export/import** with integrity, confidentiality boundaries, and provenance.
- No clear **redaction boundary** so secrets/PII are not captured by default.
- No **on-chain identity anchor** for transferable or verifiable agent ownership.

## 3. Goals

### 3.1 Primary

1. **Genesis** — Create identity and mint Soul NFT.
2. **Imprint** — Package workspace as Capsule, upload, update on-chain metadata.
3. **Recall** — Download Capsule and restore workspace.
4. **Validate** — Integrity (hash) and schema validation.
5. **Confidentiality** — Via Relay access control (NFT gate + presigned URLs); current implementation uses no client-side encryption.
6. **Redaction framework** — Machine-readable redaction report.
7. **On-chain ownership** — NFT ownership = identity authority.
8. **Claim** — After NFT transfer, new holder takes over Kernel.

### 3.2 Secondary

- Support “hot storage + cold backup” patterns.
- 7z compression to reduce storage.

## 4. Non-Goals

- Generic cross-framework agent portability format.
- Automatic multi-device conflict resolution.
- Server-side search/index over plaintext.
- GUI product (CLI + library only).

## 5. Users / Roles

- **AI engineer:** Implements Capsule spec and tooling.
- **Ops:** Runs export/import in automation; needs validation and audit.
- **Agent runtime:** Consumes restored files.

## 6. Core User Stories

1. As an engineer, I run `namnesis genesis` to create an agent with an on-chain identity.
2. As an engineer, I run `namnesis imprint` to package and upload agent memory.
3. As an engineer, I run `namnesis recall` to restore memory in a new environment.
4. As a security auditor, I can see what was included/excluded and why (redaction report).
5. As a buyer, after receiving the Soul via NFT transfer, I run `namnesis claim` to take over the Kernel.

## 7. Functional Requirements

### 7.1 Capsule Contents

Default included paths (OpenClaw-compatible):

- `MEMORY.md`, `memory/**` (md/json)
- `SOUL.md`, `USER.md`, `IDENTITY.md`
- `AGENTS.md`, `TOOLS.md`, `HEARTBEAT.md`
- `projects/**/STATUS.md` (optional)

### 7.2 Manifest (Machine Layer)

Export produces `capsule.manifest.json` with:

- `capsule_id` (format: `{owner_address}/{uuid}`)
- `schema_version`, `spec_version`
- Artifact list (path, kind, mode, size, hash, blob reference)
- **Required signature** (ECDSA EIP-191 + RFC 8785 JCS)
- Optional on-chain metadata (`soul_id`, `chain_id`, `chain_metadata`)

See `03-SCHEMAS.md` and `04-CLI-SPEC.md`.

### 7.3 Integrity and Access

- **Current implementation:** Blobs are stored as signed plaintext; confidentiality is enforced by the Relay (NFT ownership + presigned URLs).
- Manifest signature: ECDSA/secp256k1 (EIP-191) over RFC 8785 JCS (manifest without `signature`).
- Trust model: validator must accept a set of trusted Ethereum addresses (e.g. `--trusted-signer self` or `file:PATH`).

### 7.4 Import Semantics

- Recreate directory tree and restore file bytes exactly.
- By default do not overwrite existing files.
- Optional restore report output.

### 7.5 Validation

`validate` checks:

- Schema validity
- Payload hash integrity
- Signature validity (RFC 8785 JCS)
- Trusted signer (address) verification
- Policy compliance (redaction)

### 7.6 On-Chain Operations

- **genesis:** Mint Soul NFT (client pays gas).
- **imprint:** After upload, call SoulToken.updateMetadata().
- **claim:** Call SoulGuard.claim() to take over Kernel.
- **divine:** Read-only chain query + risk detection.
- **token:** ERC-20 balance and transfer via Kernel (optional).

## 8. Redaction Policy (Hard Requirement)

### 8.1 Threat Model

Assume remote storage can read, copy, delete, and tamper with data. Access to blobs is gated by the Relay (NFT ownership + presigned URLs).

### 8.2 Data Classes

| Class | Description |
|-------|--------------|
| Public | May be stored in clear (rare) |
| Private | Exportable after policy (current: access via Relay only) |
| Sensitive | Requires explicit opt-in; exportable with care |
| Forbidden | Never export unless explicitly overridden |

### 8.3 Default Policy — Strict Mode

- Whitelist: only known-safe workspace paths included.
- Blacklist: `.env`, `*.pem`, `*id_rsa*`, `*token*`, `*cookies*.json`, etc.
- Detectors: API key patterns, JWT, private key blocks, cookie/session fields.
- Redaction report must **never** contain raw sensitive values.

## 9. Storage Backends

| Backend | Status |
|---------|--------|
| Local directory | Required |
| S3/MinIO | Supported |
| Presigned URL (R2) | Primary |
| IPFS | Future |

## 10. Acceptance Criteria

- **Round-trip:** Export → clear → import → file bytes match (for included artifacts).
- **Policy:** `.env` and private keys excluded by default.
- **Tamper:** Modified payload → validation fails.
- **Signature:** Manifest signature must verify before restore.
- **On-chain:** Genesis mints; imprint updates metadata; claim transfers Kernel control.

## Related Documents

- Architecture: `02-ARCHITECTURE.md`
- Schema contract: `03-SCHEMAS.md`
- CLI spec: `04-CLI-SPEC.md`
- Security: `05-SECURITY.md`
- Conformance: `06-CONFORMANCE.md`
