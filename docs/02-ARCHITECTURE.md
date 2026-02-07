# Namnesis — System Architecture

**Audience:** AI engineers  
**Version:** v2.0

## 0. Design Constraints

| Principle | Description |
|-----------|-------------|
| **Client-first** | All business logic (signing, verification, chain tx) runs on the client |
| **Server stateless** | Credential service has no DB, no KV, no persistent state |
| **Storage access gated** | Relay enforces NFT ownership; presigned URLs limit who can read/write |
| **Client pays gas** | All chain tx (genesis, claim, updateMetadata) sent by client EOA |
| **Single identity** | User sees one identity; one ECDSA wallet for chain + Relay + manifest signing |
| **Decentralization-ready** | Design allows future migration to IPFS / decentralized storage |

## 1. System Overview

### 1.1 Architecture Diagram

```
                          User / AI Agent
                                │
                  ┌─────────────┼─────────────┐
                  │             │             │
                  ▼             ▼             ▼
          ┌─────────────┐ ┌─────────┐ ┌──────────┐
          │  Namnesis   │ │  Base   │ │  Relay    │
          │  CLI        │ │ Sepolia │ │ (stateless)│
          │             │ │  chain  │ │          │
          │ • Sign/verify│ │         │ │ • Verify │
          │ • Chain tx  │ │ Soul NFT │ │ • Auth   │
          │ • Package   │ │ SoulGuard│ │ • Issue  │
          └──────┬──────┘ └────┬────┘ │  URLs    │
                 │             │      └────┬─────┘
                 │             │           │
                 │             │           ▼
                 │             │    ┌──────────────┐
                 └─────────────┴───>│ R2 Storage   │
                                    │ (signed blobs)│
                                    └──────────────┘
```

### 1.2 High-Level Pipeline

1. **Discover:** Enumerate candidate workspace files per policy.
2. **Classify & redact:** Run detectors; decide action per artifact.
3. **Package:** Split into artifacts (files), compute hashes.
4. **Upload:** Write to backend (local or R2); blob_id = sha256(contents).
5. **Manifest:** Write `capsule.manifest.json` and **sign (required)**.
6. **On-chain:** Update SoulToken metadata (cycles, size).
7. **Restore:** Fetch objects, verify hash/signature, write files.

## 2. Identity Model

### 2.1 Single Identity

User creates identity with `namnesis genesis`. One ECDSA/secp256k1 wallet is used for:

| Use | Storage | Identifier |
|-----|---------|-------------|
| Manifest signing | Same key as chain | Ethereum address |
| Chain transactions | `~/.namnesis/.env` (hex) | Ethereum address |
| Relay authentication | EIP-191 sign over request | Ethereum address |

CLI shows:

- **Address:** Ethereum address (from `namnesis whoami`).

### 2.2 Capsule ID

```
capsule_id = {owner_address}/{uuid}

Example: 0x1234...abcd/01925b6a-7c8d-7def-9012-345678abcdef
         ├── owner_address: 40-char hex (0x-prefixed)
         └── uuid: UUIDv7
```

### 2.3 Access Control

Access to Capsule blobs is enforced by the Relay:

- **Write:** Request signed by key that owns the Soul NFT for the given capsule context (soul_id).
- **Read:** Same ownership or explicit sharing (implementation-defined).

Manifest may include optional `access` for future use:

```json
{
  "access": {
    "owner": "0x...",
    "readers": ["0x..."],
    "public": false
  }
}
```

## 3. Signing Design

### 3.1 Manifest Signature (Locked)

- ECDSA/secp256k1 (EIP-191 personal_sign) over the manifest.
- Bytes to sign: RFC 8785 JCS (manifest with `signature` removed) → UTF-8, no trailing newline.
- Trust: Verifier must have a set of trusted Ethereum addresses; signer’s `signer_address` must be in that set.

### 3.2 Signature Object in Manifest

- `alg`: `ecdsa_secp256k1_eip191`
- `payload_alg`: `rfc8785_jcs_without_signature_utf8`
- `signer_address`: Ethereum address (0x-prefixed)
- `sig`: Hex-encoded signature

## 4. Packaging

### 4.1 File Granularity

One artifact per file; no chunking.

### 4.2 Compression (Optional)

With 7z enabled, all files are packed into one 7z archive, then stored as one blob.

```
Scan workspace → filter exclusions → 7z pack → sign → upload single blob
```

Manifest `compression`:

```json
{
  "compression": {
    "enabled": true,
    "algorithm": "7z",
    "level": 9,
    "original_size_bytes": 1234567,
    "compressed_size_bytes": 345678,
    "compression_ratio": 0.28
  }
}
```

## 5. Storage Backends

### 5.1 Backend Interface

```python
put_blob(capsule_id, blob_id, bytes) -> ref
get_blob(capsule_id, blob_id) -> bytes
has_blob(capsule_id, blob_id) -> bool
put_document(capsule_id, path, bytes)
get_document(capsule_id, path) -> bytes
```

All backends must provide **read-after-write consistency**.

### 5.2 Local Directory

```
<out>/capsules/{capsule_id}/
  ├── capsule.manifest.json
  ├── redaction.report.json
  └── blobs/
      ├── <blob_id>
      └── ...
```

Write order: blobs → redaction report → manifest last.

### 5.3 S3/MinIO

- Prefix: `capsules/<capsule_id>/`
- Bucket versioning recommended.

### 5.4 Presigned URL (Primary)

Used for Cloudflare R2 (no STS).

**Flow:**

1. Client signs request (ECDSA, EIP-191).
2. Relay verifies signature and NFT ownership (read-only chain call).
3. Relay returns presigned URLs (e.g. 1 hour).
4. Client talks to R2 directly with those URLs.

**Relay API:**

| Endpoint | Purpose |
|----------|---------|
| `POST /presign` | Verify ECDSA, return R2 presigned URLs |
| `GET /api/metadata/:id` | Read SoulToken metadata |
| `GET /health` | Health check |

**URL cache:**

- Location: `~/.namnesis/cache/`
- Refresh before expiry (e.g. 5 minutes early).
- `namnesis cache clear` to clear.

### 5.5 Delete Semantics

- Local: best-effort delete.
- S3/R2: best-effort; provider-dependent.
- No global delete guarantee.

## 6. On-Chain Architecture

### 6.1 Contracts

| Contract | Role |
|----------|------|
| **SoulToken** (ERC-721) | Soul NFT + memory metadata (cycles, size, lastUpdated) |
| **SoulGuard** | Soul→Kernel mapping, Claim, safety (pending-claim hooks) |

### 6.2 SoulToken

- `mint(to)`: Anyone can mint.
- `updateMetadata(tokenId, cycles, size)`: **Only NFT holder** (client sends tx).
- Stores: `samsaraCycles`, `memorySize`, `lastUpdated`.

### 6.3 SoulGuard

- `register(soulId, kernel)`: Register Soul→Kernel at genesis.
- `claim(soulId)`: New NFT holder takes Kernel control:
  1. Caller must be NFT holder.
  2. Require `confirmedOwner != msg.sender`.
  3. Via Ownable Executor, set ECDSA Validator owner.
  4. Update `confirmedOwner` and `lastClaimTime`.
- `isPendingClaim(soulId)`: True when NFT changed hands but claim not yet run.
- `isInClaimWindow(soulId)`: Safety window (e.g. 1 hour after claim).

### 6.4 Claim Flow

```
Alice (seller)                    Bob (buyer)
    │                                  │
    ├── [Genesis] mint Soul            │
    ├── [Genesis] deploy Kernel        │
    ├── [Genesis] register(soulId)     │
    │                                  │
    ├── Transfer Soul to Bob ──────────┤
    │   (isPendingClaim = true)        │
    │   (Kernel hook restricts ops)    │
    │                                  │
    │                                  ├── claim(soulId)
    │                                  ├── Kernel owner → Bob
    │                                  ├── (isPendingClaim = false)
```

### 6.5 Imprint Full Flow

```
CLI ──1. Package + sign manifest (ECDSA) ──→
CLI ──2. POST /presign (ECDSA) ──→ Relay
Relay ──3. ownerOf(soulId) ──→ Chain (read-only)
Relay ──4. Presigned URLs ──→ CLI
CLI ──5. Upload blobs ──→ R2
CLI ──6. updateMetadata() ──→ Chain (client pays gas)
```

## 7. Determinism and Reproducibility

**Locked:**

- Import **must** restore artifact bytes exactly.
- `plaintext_hash` must verify.
- Re-export need not produce same blob_id or same byte layout.
- `created_at` may differ.

## 8. Failure Modes

- Missing blob → import fails with actionable report.
- Wrong trusted signer → validation fails before restore.
- Policy violation → export fails by default.
- Chain update failure → memory may already be uploaded; `namnesis sync` to repair.

## Related Documents

- Requirements: `01-PRD.md`
- Schema contract: `03-SCHEMAS.md`
- CLI spec: `04-CLI-SPEC.md`
- Security: `05-SECURITY.md`
