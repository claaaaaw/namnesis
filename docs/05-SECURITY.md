# Namnesis — Security Model and Redaction Policy

**Audience:** AI engineers / security auditors  
**Version:** v2.0

## 1. Summary

Namnesis assumes **remote storage is not trusted** for access. Security is provided by:

- **Relay access control:** Only NFT holder (and authorized readers, if supported) obtain presigned URLs to read/write blobs.
- **Manifest signature** (ECDSA EIP-191, required) for provenance and tamper detection.
- **Blob integrity:** `blob_id = sha256(blob_bytes)`; restore verifies `plaintext_hash` per artifact.
- **Strict redaction policy** so secrets/PII are not included by default.
- **On-chain ownership:** NFT holder is the authority for write and for Relay auth.

**Current implementation:** No client-side encryption. Confidentiality is enforced by the Relay (NFT gate + presigned URLs). Blobs are stored as plaintext; only authorized parties can obtain URLs to read them.

## 2. Assets Protected

- Agent persistent state (memory, persona, runbooks).
- Secrets that may appear in files (API keys, tokens, cookies).
- User PII (e.g. in logs).
- Provenance: who produced the capsule and whether it was tampered with.
- On-chain: Soul NFT ownership, Kernel control.

## 3. Adversary Model

Assume attacker can:

- Read all objects in remote storage **if** they obtain valid presigned URLs (Relay restricts this to NFT holder / authorized readers).
- Modify/replace/replay blobs and manifest if they could write (again gated by Relay).
- Delete or withhold objects.

Assume attacker cannot:

- Break modern crypto (ECDSA, hash).
- Compromise the Relay’s verification of NFT ownership.
- Steal the client’s ECDSA key without compromising the machine.

Out of scope:

- Fully compromised client device.
- TEE / remote attestation.
- Preventing authorized users from copying data after restore.

## 4. Security Properties

### 4.1 Confidentiality

- **Current:** No client-side encryption; confidentiality by Relay (only NFT holder gets presigned URLs). Storage provider (R2) must not expose objects to unauthorized callers.
- **Future:** Optional E2EE (passphrase/Argon2id + AEAD) can be added; then blob_id may be derived from ciphertext.

### 4.2 Integrity

- Each blob verified by hash (`blob_id` / `plaintext_hash`).
- Manifest signature verified before restore.

### 4.3 Authenticity / Provenance

- Manifest MUST be signed (ECDSA).
- Verification uses RFC 8785 JCS bytes.
- Verifier MUST use a fixed set of trusted signer addresses.

### 4.4 Safe Defaults

- Strict policy; fail closed.
- Forbidden findings MUST block export unless explicitly overridden.

## 5. Key Management

### 5.1 Key Source

| Key | Source | Use |
|-----|--------|-----|
| ECDSA | Generated at genesis | Chain tx, Relay auth, manifest signing |

Single key: one ECDSA wallet for all operations.

### 5.2 Recovery

- Lost key → Cannot sign new capsules or perform chain/Relay operations.
- Recommend: backup `~/.namnesis/` (e.g. password manager, offline).

## 6. Common Attacks and Mitigations

| Attack | Mitigation |
|--------|-------------|
| Unauthorized read | Relay checks NFT ownership before issuing presigned URLs |
| Blob replacement/tampering | Hash verification on restore; signature on manifest |
| Rollback | manifest `created_at` + on-chain `samsaraCycles` |
| Secret leakage | Redaction report never contains raw secret substrings |
| NFT ownership abuse | SoulGuard claim flow + Kernel hook (pending-claim restrictions) |

---

## 7. Redaction Policy

### 7.1 Principles

- **Fail closed by default.**
- **Whitelist:** Only known-safe paths included.
- **No secrets in reports:** Findings only type/rule ID/location.
- **Deterministic:** Same input + same policy → same decisions.

### 7.2 Data Classes

| Class | Description | Default action |
|-------|--------------|----------------|
| Public | Rare; may be plaintext in future | include_plaintext |
| Private | Exportable with access control | include_encrypted / include_plaintext |
| Sensitive | Explicit opt-in | exclude |
| Forbidden | Never export | exclude + block export |

### 7.3 Default Whitelist

- `MEMORY.md`, `memory/**` (md/json)
- `SOUL.md`, `USER.md`, `IDENTITY.md`
- `AGENTS.md`, `TOOLS.md`, `HEARTBEAT.md`
- `projects/**/STATUS.md`

All else excluded by default.

### 7.4 Default Blacklist (Forbidden)

- `.env`
- `**/*.pem`, `**/*id_rsa*`, `**/*private_key*`
- `**/*token*`, `**/*secret*`
- `**/*cookies*.json`, `**/*_cookies.json`
- `memory/moltbook.json` (credentials)
- Browser/session storage, SQLite cookie jars
- Files over size limit

### 7.5 Detectors (Heuristic)

| Detector | Detects |
|----------|---------|
| API Key | Patterns like `sk-`, `ghp_` |
| JWT | JWT token pattern |
| Private key block | `-----BEGIN ... PRIVATE KEY-----` |
| Cookie/Session | `session`, `csrf`, `auth` fields |

Output: `rule_id`, `severity`, `locations`. **Never include matched strings.**

### 7.6 Decisions and Actions

Per artifact: `exclude` | `include_encrypted` | `include_redacted` | `include_plaintext`. Forbidden defaults to exclude and blocks export.

### 7.7 Redaction Report

Export MUST produce `redaction.report.json` with policy version, schema version, capsule_id, detectors, per-file decisions and reasons, and findings summary. `decisions` MUST cover all candidate files (including excluded).

### 7.8 Detector Config Hash

Each detector entry MUST include `config_hash`: e.g. `sha256(JCS(detector_config))` (lowercase hex). Use JCS of `{}` when no config.

### 7.9 CLI Safeguards

- `--dry-run`: Only produce redaction report.
- `--strict` (default): Forbidden blocks export.
- `--i-know-what-im-doing`: Include Forbidden class (with `--no-strict`).

## 8. Security Checklist

- [ ] Manifest signed and verified before restore.
- [ ] Default strict redaction applied.
- [ ] Redaction report free of secret substrings.
- [ ] Conformance tests cover tamper, wrong trusted signer, Forbidden.
- [ ] On-chain operations verify NFT ownership.
- [ ] Claim safety (pending-claim hooks) verified.

## Related Documents

- PRD: `01-PRD.md`
- Architecture: `02-ARCHITECTURE.md`
- Schema: `03-SCHEMAS.md`
- CLI spec: `04-CLI-SPEC.md`
- Conformance: `06-CONFORMANCE.md`
