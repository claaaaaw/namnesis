# [SUPERSEDED] Temporary AI Integration Draft

> **⚠️ This file has been superseded.**
>
> The content originally in this file was a draft from the Resurrectum v1 era.
> It included old CLI commands (`summon export/import/validate`), Ed25519 signing,
> and an early MCP server prototype.
>
> All of this has been replaced by the Namnesis v2 implementation:
>
> - **AI Integration Guide:** `docs/AI-INTEGRATION.md`
> - **CLI Specification:** `docs/04-CLI-SPEC.md`
> - **CLI Implementation:** `src/namnesis/cli.py`
> - **OpenClaw Skill:** `openclaw/skills/namnesis/SKILL.md`
>
> This file is kept only as a historical marker. It can be safely deleted.

---

## Key Changes from v1 (Resurrectum) → v2 (Namnesis)

| Aspect | v1 (Resurrectum) | v2 (Namnesis) |
|--------|-------------------|---------------|
| CLI | `summon export/import/validate` | `namnesis genesis/imprint/recall/divine/claim/validate` |
| Signing | Ed25519 | ECDSA (secp256k1) |
| Identity | Local key pair | Soul NFT on Base Sepolia |
| Storage | Local / S3 | Cloudflare R2 via Credential Service |
| Ownership | None | NFT-based (SoulToken + SoulGuard) |
| Encryption | XChaCha20-Poly1305 | XChaCha20-Poly1305 (unchanged) |
| MCP Server | Draft prototype | Not implemented (uses Skill instead) |
