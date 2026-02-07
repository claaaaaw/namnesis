# Namnesis — Sovereign Agent Protocol

Namnesis: on-chain sovereign AI agent identity and memory protocol — sign, upload, restore, and transfer ownership.

## Overview

Namnesis is an **AI-first** on-chain sovereign agent protocol. It binds an agent’s identity and memory to an on-chain NFT (The Soul), with signed storage, integrity verification, and ownership transfer (Claim / Resurrection).

Core capabilities:

- **Identity creation** (`genesis`): Create identity and mint Soul NFT
- **Memory imprint** (`imprint`): Package workspace, upload to R2, update on-chain metadata
- **Memory recall** (`recall`): Download, verify signature, restore workspace
- **Ownership transfer** (`claim`): Take over Kernel after NFT transfer
- **On-chain query** (`divine`): Query chain state and risk (e.g. pending Claim)
- **State sync** (`sync`): Repair identity/chain inconsistencies
- **Token** (`token`): ERC-20 balance and transfer via Kernel

## Tech Stack

| Layer | Technology |
|-------|------------|
| CLI | Python 3.11+ / Click |
| Signing | ECDSA/secp256k1 (EIP-191) for manifest and Relay auth |
| On-chain | Base Sepolia / ERC-721 / ERC-4337 |
| Storage | Cloudflare R2 (presigned URLs) |
| Credential service | Cloudflare Workers (stateless) |
| Contracts | Foundry / Solidity 0.8.24 |

Data confidentiality is enforced by the Relay (NFT ownership gate + presigned URLs); the current implementation does not use client-side encryption.

## Document Order

| # | Document | Content |
|---|----------|---------|
| 1 | **01-PRD.md** | Product overview, requirements, user stories |
| 2 | **02-ARCHITECTURE.md** | System architecture, identity, storage, chain design |
| 3 | **03-SCHEMAS.md** | Machine-layer contract (JSON Schema) |
| 4 | **04-CLI-SPEC.md** | CLI commands, options, exit codes |
| 5 | **05-SECURITY.md** | Security model, threats, redaction policy |
| 6 | **06-CONFORMANCE.md** | Conformance test requirements |
| 7 | **07-ROADMAP.md** | Roadmap and open issues |
| — | **AI-INTEGRATION.md** | OpenClaw Skill integration |

## Spec Resources

- JSON Schemas: `docs/schemas/v1/`
- Example capsules: `docs/examples/`
- Conformance fixtures: `conformance/`

## Quick Start

```bash
# Install
pip install -e ".[all]"

# Create identity and mint Soul NFT
namnesis genesis

# Identity only (offline testing)
namnesis genesis --skip-mint

# Show identity
namnesis whoami

# Package and upload memory
namnesis imprint --workspace ./my-agent --soul-id 0

# Download and restore memory
namnesis recall --capsule-id <ID> --to ./restored --trusted-signer self

# Query on-chain status
namnesis divine --soul-id 0

# Repair inconsistent state
namnesis sync --soul-id 0
```

## Locked Design Decisions

1. **Blob addressing:** `blob_id = sha256(blob_bytes)` (current: plaintext blobs).
2. **Manifest signature required:** ECDSA (EIP-191) + RFC 8785 JCS canonicalization.
3. **Single identity:** One ECDSA/secp256k1 wallet; user sees one “identity”.
4. **Strict redaction:** Whitelist by default; forbidden paths block export unless overridden.
5. **Byte-accurate restore:** Import must restore file contents exactly.
6. **Client pays gas:** All on-chain transactions sent by the client.
7. **Capsule ID:** `{owner_ethereum_address}/{uuid}` (e.g. `0x.../01925b6a-7c8d-7def-9012-345678abcdef`).
