# Namnesis — Roadmap and Open Issues

**Audience:** AI engineers / maintainers  
**Version:** v2.0

## 1. Locked Decisions

The following are normative and will not change:

- `blob_id` = sha256(blob_bytes) (lowercase hex)
- Manifest signature required (ECDSA EIP-191) and fixed/trusted signer (address) model
- Signing bytes: RFC 8785 JCS, manifest without `signature`, UTF-8, no trailing newline
- Strict default whitelist/export policy
- Determinism: byte-accurate restore (no requirement for stable blob_id across re-exports)
- Encoding: hashes hex; capsule_id `{address}/{uuid}`; signature hex
- Client pays gas; Relay stateless
- Single identity (one ECDSA wallet; user sees one identity)

## 2. Current Version (v2.0) — Implemented

- Unified CLI (genesis, imprint, recall, divine, claim, invoke, token, sync)
- Single ECDSA identity
- Soul NFT mint + on-chain metadata update
- SoulGuard claim safety (pending-claim hooks)
- R2 presigned URL backend
- 7z compression
- Conformance test framework
- ERC-20 token balance and transfer via Kernel (`namnesis token`)

## 3. Near-Term (v2.1)

- [ ] Parse tokenId from mint event logs (genesis flow improvement)
- [ ] `--trusted-signer self` shorthand (already supported; document as default)
- [ ] `imprint --local` (export only to local dir; no remote upload)
- [ ] Kernel deployment integrated into genesis
- [ ] Paymaster config (optional gasless operations)
- [ ] On-chain lineage: `parents[]` in manifest

## 4. Medium-Term (v2.2+)

- [ ] Optional chunked packaging (large files / cross-snapshot dedup)
- [ ] Merge semantics (two-parent merge + conflict markers)
- [ ] Multi-agent capsule graph (references between capsules)
- [ ] Optional path encryption (reduce metadata leakage)
- [ ] Vector index encapsulation (encrypted storage)

## 5. Long-Term (v3)

- IPFS cold backup (encrypted blobs + signed manifest pointer)
- Stronger canonicalization / new manifest model / new crypto envelope
- Hardware wallet support
- Multi-chain deployment
- Optional E2EE (passphrase → Argon2id → AEAD) for blobs

## 6. Open Issues

| # | Issue | Status |
|---|-------|--------|
| 1 | **Path privacy:** Encrypt path/filenames to reduce metadata leakage? | Open |
| 2 | **Unencrypted allow:** Allow optional unencrypted artifacts in a future version? | Open |
| 3 | **Deterministic export:** Optional mode for stable blob_id/nonce? | Deferred |
| 4 | **PII detection:** Stronger PII detectors (name, address)? False positive handling? | Open |
| 5 | **Key recovery UX:** Recovery phrase / key escrow within security bounds? | Open |
| 6 | **Index:** Encapsulate vector index (encrypted) or always rebuild locally? | Open |
| 7 | **Multi-key:** Future Ed25519 for manifest + ECDSA for chain (dual-key UX)? | v3 discussion |

## Related Documents

- PRD: `01-PRD.md`
- Architecture: `02-ARCHITECTURE.md`
- Security: `05-SECURITY.md`
