# Namnesis — CLI Spec v2.0

**Audience:** AI engineers  
**Version:** v2.0 (normative; command behavior and exit codes must remain stable)

## 0. Purpose

Define a safe-default, implementation-oriented, testable CLI interface.

## 1. Command Overview

```
namnesis genesis          Create sovereign agent (identity + Soul NFT)
namnesis imprint          Package and upload memory
namnesis recall           Download and restore memory
namnesis divine           Query on-chain status
namnesis claim            Take over Kernel after NFT transfer
namnesis invoke           Execute on-chain contract call
namnesis token            ERC-20 balance and transfer via Kernel
namnesis sync             Repair identity/chain inconsistencies
namnesis whoami           Show current identity (address)
namnesis info             Show system information
namnesis validate         Validate capsule integrity
namnesis cache clear|info Manage URL cache
```

## 2. Command Specifications

### 2.1 `namnesis genesis`

Create a new sovereign agent: generate ECDSA wallet, optionally mint Soul NFT.

```
namnesis genesis [--rpc-url URL] [--skip-mint]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--rpc-url` | `https://sepolia.base.org` | RPC URL (env: `BASE_SEPOLIA_RPC`) |
| `--skip-mint` | false | Only generate key; do not mint NFT |

**Behavior:**

1. If `~/.namnesis/` already has a key, load it.
2. Otherwise generate ECDSA keypair.
3. If not `--skip-mint`, check EOA balance and mint Soul NFT (and deploy Body if applicable).
4. Output: Address, mint result.

**Exit codes:** 0 success | 1 error

### 2.2 `namnesis imprint`

Package workspace and upload to R2; update on-chain metadata.

```
namnesis imprint --soul-id ID [-w PATH]
    [--credential-service URL] [--compress|--no-compress]
    [--rpc-url URL] [--skip-chain-update]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--soul-id` | **required** | Soul NFT token ID |
| `--workspace, -w` | `.` | Workspace path |
| `--credential-service` | default URL | Credential service base URL |
| `--compress/--no-compress` | no compress | Use 7z compression |
| `--rpc-url` | default | RPC endpoint |
| `--skip-chain-update` | false | Skip on-chain metadata update |

**Exit codes:** 0 success | 1 error | 2 policy violation (Forbidden)

### 2.3 `namnesis recall`

Download capsule and restore workspace.

```
namnesis recall --capsule-id ID --to PATH --trusted-signer ADDR
    [--credential-service URL] [--overwrite] [--partial] [--local-path PATH]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--capsule-id` | **required** | Capsule ID (`address/uuid`) |
| `--to` | **required** | Target workspace path |
| `--trusted-signer` | **required** | Trusted signer: `self`, 0x address, or `file:PATH` |
| `--credential-service` | default | Credential service URL |
| `--overwrite` | false | Overwrite existing files |
| `--partial` | false | Continue on error |
| `--local-path` | null | Local capsule path (skip remote) |

**Exit codes:** 0 success | 1 error | 4 signature/trust failure | 5 integrity failure | 6 decrypt failure (N/A in current plaintext impl)

### 2.4 `namnesis divine`

Query on-chain state and risks.

```
namnesis divine --soul-id ID [--rpc-url URL]
```

**Output:** NFT owner, confirmed owner, Kernel address, balance, Samsara cycles, memory size, last updated, and warnings (e.g. Pending Claim, Lobotomy Risk).

### 2.5 `namnesis claim`

Take over Kernel after NFT transfer.

```
namnesis claim --soul-id ID [--rpc-url URL]
```

**Behavior:** Ensure caller is NFT holder; if `confirmedOwner != msg.sender`, call SoulGuard.claim(soulId); ECDSA Validator owner becomes caller.

### 2.6 `namnesis invoke`

Generic on-chain contract call.

```
namnesis invoke --contract ADDR --function NAME
    [--args JSON] [--abi-name NAME] [--value WEI] [--gas-limit N]
```

### 2.7 `namnesis token`

ERC-20 operations via Kernel.

```
namnesis token balance --soul-id ID [--token ADDR]
namnesis token transfer --soul-id ID --to ADDR --amount N [--token ADDR]
```

| Option | Description |
|--------|-------------|
| `--soul-id` | Soul NFT token ID (Kernel from SoulGuard) |
| `--token` | ERC-20 contract address (default: e.g. USDC on chain) |
| `--to` | Recipient address (transfer) |
| `--amount` | Amount in token units (transfer) |

### 2.8 `namnesis sync`

Repair identity and chain inconsistencies.

```
namnesis sync --soul-id ID [--rpc-url URL] [--dry-run]
```

**Checks:** Local identity present; NFT ownership matches current address; confirmedOwner matches NFT owner; run claim if pending.

`--dry-run`: report only, no fixes.

### 2.9 `namnesis whoami`

Show current identity.

```
namnesis whoami [-k PATH]
```

**Output:** `Address: 0x...`

### 2.10 `namnesis validate`

Validate capsule integrity and signature.

```
namnesis validate --capsule-id ID --trusted-signer ADDR
    [-p PATH] [--credential-service URL]
```

**Exit codes:** 0 pass | 4 signature failure | 5 integrity failure

### 2.11 `namnesis info`

Show system information (address, compression, URL cache, command list).

### 2.12 `namnesis cache clear | info`

Manage presigned URL cache. `clear` optionally scoped by `--capsule-id`.

## 3. Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Policy violation (Forbidden) |
| 4 | Signature/trust verification failed |
| 5 | Integrity (hash) verification failed |
| 6 | Decryption failed (reserved; current impl has no encryption) |

## 4. Environment Variables

| Variable | Description |
|----------|-------------|
| `BASE_SEPOLIA_RPC` | RPC URL |
| `SOUL_TOKEN_ADDRESS` | SoulToken contract address |
| `SOUL_GUARD_ADDRESS` | SoulGuard contract address |
| `NAMNESIS_CREDENTIAL_SERVICE` | Credential service URL |
| `PRIVATE_KEY` | ECDSA private key (hex); usually from `~/.namnesis/.env` |

## 5. Standard Output Artifacts

| File | Description |
|------|-------------|
| `capsule.manifest.json` | Signed capsule manifest |
| `redaction.report.json` | Redaction decisions |
| `restore.report.json` | Restore result (optional) |

## Related Documents

- PRD: `01-PRD.md`
- Architecture: `02-ARCHITECTURE.md`
- Schema: `03-SCHEMAS.md`
- Security: `05-SECURITY.md`
