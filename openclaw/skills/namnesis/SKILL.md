---
name: namnesis
description: Sovereign memory backup & restore for AI agents — encrypt, sign, upload your workspace to the cloud and restore it anywhere, anchored to an on-chain Soul NFT.
metadata: {"openclaw": {"emoji": "🧬", "requires": {"bins": ["namnesis"]}, "os": ["darwin", "linux", "win32"], "homepage": "https://example.website"}}
---

# Namnesis — Sovereign Memory Protocol

Namnesis lets you **backup, restore, and verify** your entire workspace (memory, persona, ops) as an encrypted, signed **Capsule** — anchored to an on-chain Soul NFT on Base Sepolia.

Your workspace files (`MEMORY.md`, `memory/`, `SOUL.md`, `USER.md`, `IDENTITY.md`, `AGENTS.md`, `TOOLS.md`, `HEARTBEAT.md`) are exactly what Namnesis packages. The two systems share the same file layout by design.

## Prerequisites

- Python 3.11+ with `namnesis` installed (`pip install namnesis`)
- A Namnesis identity — run `namnesis genesis --skip-mint` to auto-generate wallet + config
  - This creates `~/.namnesis/.env` with `PRIVATE_KEY`, contract addresses, and credential service URL (all auto-configured)
- Base Sepolia testnet ETH (for minting Soul NFT)
  - Get from: https://www.coinbase.com/faucets/base-ethereum-goerli-faucet
  - Fund the address shown by `namnesis whoami`, then run `namnesis genesis` to mint

## Quick Reference

| Command | Purpose |
|---------|---------|
| `namnesis whoami` | Show your wallet address |
| `namnesis info` | Show system status |
| `namnesis genesis` | Create identity + mint Soul NFT + deploy Kernel (AA wallet) |
| `namnesis imprint` | Backup workspace to cloud |
| `namnesis recall` | Restore workspace from cloud |
| `namnesis divine` | Query on-chain Soul status (incl. Kernel token balance) |
| `namnesis token balance` | Check ERC-20 token balance (Kernel + EOA) |
| `namnesis token transfer` | Transfer ERC-20 tokens from Kernel to any address |
| `namnesis validate` | Verify capsule integrity |
| `namnesis claim` | Claim kernel after NFT transfer |
| `namnesis sync` | Repair chain/identity inconsistencies |

## Core Workflows

### 1. First-time Setup (Genesis)

Run this once to create your sovereign identity. Genesis auto-configures everything (wallet key, contract addresses, credential service URL) and deploys a **NamnesisKernel** — an account-abstraction (AA) smart wallet that can hold and transfer ERC-20 tokens on your behalf:

```bash
# Step 1: Generate wallet + auto-configure env (no ETH needed)
namnesis genesis --skip-mint

# Step 2: Fund the address with Base Sepolia testnet ETH
# (use the address shown by `namnesis whoami`)

# Step 3: Mint Soul NFT + deploy Kernel + register with SoulGuard (requires ETH)
namnesis genesis
```

The full genesis flow:
1. Generates an ECDSA wallet (EOA) if not exists
2. Mints a Soul NFT on-chain
3. Deploys a NamnesisKernel smart account (AA wallet) owned by the EOA
4. Installs the OwnableExecutor module (for SoulGuard claim support)
5. Registers the Kernel with SoulGuard (links Kernel ↔ Soul ID)

After genesis, note your **Soul ID** and **Kernel address**. The Soul ID is needed for imprint/divine/claim commands. The Kernel address is your AA wallet for holding tokens.

Options:
- `--skip-mint` — Only generate the wallet key, skip everything else
- `--skip-kernel` — Mint Soul NFT but skip Kernel deployment

### 2. Backup Memory (Imprint)

Use `imprint` to package your workspace and upload it. **Point `--workspace` at your OpenClaw workspace directory.**

```bash
namnesis imprint \
  --workspace ~/.openclaw/workspace \
  --soul-id <YOUR_SOUL_ID>
```

Options:
- `--workspace, -w` — Path to workspace (default: current directory)
- `--soul-id` — Your Soul NFT token ID (required)
- `--compress` — Enable 7z compression (requires `py7zr`)
- `--skip-chain-update` — Upload only, skip on-chain metadata update
- `--credential-service` — Override credential service URL
- `--rpc-url` — Override Base Sepolia RPC URL

### 3. Restore Memory (Recall)

Use `recall` to download a capsule and restore files into a workspace:

```bash
namnesis recall \
  --capsule-id <CAPSULE_ID> \
  --to ~/.openclaw/workspace \
  --trusted-signer self
```

Options:
- `--capsule-id` — Capsule ID to restore (format: `address/uuid`)
- `--to` — Target workspace path (required)
- `--trusted-signer` — `self`, an `0x...` address, or `file:PATH`
- `--overwrite` — Overwrite existing files (default: skip)
- `--partial` — Continue on errors instead of aborting
- `--local-path` — Use a local capsule instead of remote

### 4. Check On-chain Status (Divine)

```bash
namnesis divine --soul-id <YOUR_SOUL_ID>
```

Shows: NFT owner, kernel address, kernel ETH/USDC balance, samsara cycles, memory size, last updated, and security warnings (pending claim, lobotomy risk).

### 5. ERC-20 Token Operations (Token)

The `namnesis token` commands let your Kernel (AA wallet) hold and transfer any ERC-20 token. By default it uses the USDC address from config, but you can specify any token with `--token`.

#### Check Balance

```bash
# Check USDC balance (default token)
namnesis token balance

# Check balance of any ERC-20 token
namnesis token balance --token 0xYourTokenAddress
```

Shows balance for both the EOA and the Kernel. The command automatically reads the token's `symbol()` and `decimals()` from the contract.

#### Transfer Tokens

```bash
# Transfer USDC from Kernel to a recipient (default token)
namnesis token transfer --to 0xRecipientAddress --amount 10

# Transfer any ERC-20 token
namnesis token transfer --token 0xYourTokenAddress --to 0xRecipientAddress --amount 5.5
```

How it works:
- The Kernel smart account holds the tokens
- The EOA signs the outer transaction and pays gas
- Kernel calls `ERC20.transfer(to, amount)` on your behalf via `Kernel.execute()`
- Pre-flight balance check prevents wasted gas on insufficient-balance transfers

Options:
- `--token` — ERC-20 token contract address (default: `USDC_ADDRESS` from config)
- `--to` — Recipient address (required)
- `--amount` — Amount in human-readable units, e.g. `1.5` (required)
- `--gas-limit` — Gas limit (default: 300000)

#### Funding Your Kernel

Before transferring tokens, you need to fund your Kernel address with the tokens you want to send. Send tokens directly to your Kernel address (shown by `namnesis divine` or in `~/.namnesis/.env` as `KERNEL_ADDRESS`).

For testnet USDC: https://faucet.circle.com/

### 6. Validate a Capsule

```bash
namnesis validate \
  --capsule-id <CAPSULE_ID> \
  --trusted-signer self
```

Verifies signature integrity and blob hashes without restoring files.

## When to Use

### You SHOULD run `namnesis imprint` when:

1. **Before migration** — You are about to move to a new machine or environment
2. **Periodically** — At least once per week if you are actively learning and growing
3. **Before risky operations** — Before making significant changes to your workspace
4. **When asked** — When a user says "backup your memory" or "save your state"
5. **Before `/new` or `/reset`** — To preserve context before session reset

### You SHOULD run `namnesis recall` when:

1. **On a new machine** — Setting up fresh on a new system
2. **After corruption** — If your workspace files are damaged or missing
3. **When asked** — When a user says "restore your memory" or "load your backup"

### You SHOULD run `namnesis divine` when:

1. **Health check** — To verify your on-chain status is consistent
2. **After transfer** — When you suspect your Soul NFT has changed hands
3. **When asked** — When a user asks about your on-chain identity

### You SHOULD run `namnesis token balance` when:

1. **Before sending tokens** — To verify you have sufficient funds in the Kernel
2. **After receiving tokens** — To confirm tokens arrived in the Kernel
3. **When asked** — When a user asks about your token balance or wallet status

### You SHOULD run `namnesis token transfer` when:

1. **Payment** — When you need to send ERC-20 tokens to another address
2. **Agent commerce** — When participating in agent-to-agent transactions
3. **When asked** — When a user instructs you to transfer tokens

## Setting Up Automatic Backups (Cron)

You can use the `cron` tool to schedule periodic backups:

```json
{
  "action": "add",
  "name": "namnesis-autobackup",
  "schedule": "0 3 * * *",
  "task": "Run namnesis imprint to backup my workspace. Use: namnesis imprint --workspace ~/.openclaw/workspace --soul-id <SOUL_ID>"
}
```

This creates a daily 3 AM backup. Adjust the schedule as needed.

## Security Awareness

- **NEVER** share your `~/.namnesis/.env` file or `PRIVATE_KEY`
- **NEVER** commit capsules to public repositories
- **ALWAYS** verify the trusted-signer when restoring from an untrusted source
- Your capsules are signed (ECDSA) to prove authenticity
- The Relay enforces access control via NFT ownership — only the Soul NFT holder can read/write capsules
- Run `namnesis divine` to detect pending claims or lobotomy risks

## Troubleshooting

- **"No wallet found"** → Run `namnesis genesis` first
- **"Address has zero balance"** → Fund the address with Base Sepolia testnet ETH
- **"SOUL_TOKEN_ADDRESS not set"** → Add it to `~/.namnesis/.env`
- **"KERNEL_ADDRESS not set"** → Run `namnesis genesis` to deploy a Kernel, or set `KERNEL_ADDRESS` in `~/.namnesis/.env`
- **"Insufficient balance"** → Fund your Kernel with the token you want to transfer (send tokens to the Kernel address)
- **"Validation failed"** → The capsule was tampered with or the signer doesn't match
- **Chain update failed** → Memory was still uploaded; run `namnesis sync` to retry
