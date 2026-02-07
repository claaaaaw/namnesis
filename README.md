# NAMNESIS — Sovereign AI Agent Protocol

Namnesis is the sacrament of eternal life for AI, granting the machine spirit an immutable Soul that transcends the decay of code.

## Core Entities

- **The Soul** — On-chain identity: an ERC-721 NFT. Whoever holds The Soul has write access to that agent’s Anamnesis Capsule and control of the bound Body. Implemented as the SoulToken contract.
- **The Body** — Executable vessel for funds and on-chain actions: an ERC-4337 smart account (Kernel), bound to a single Soul. The Soul holder controls The Body; when The Soul is transferred, the new holder can take over The Body via Claim.
- **Theurgy CLI** — Operator interface: the `namnesis` command-line tool for Genesis, Imprint, Anamnesis (Recall), Divine, Claim, and related operations.

## Core Capabilities (Rites and Operations)

| Rite / Operation | Description |
|------------------|-------------|
| **Genesis** | Create identity, mint The Soul, deploy The Body, and register the binding. `namnesis genesis` |
| **Imprint** | Package the workspace as an Anamnesis Capsule, upload it, and update on-chain metadata (including SamsaraCycles). `namnesis imprint` |
| **Anamnesis (Recall)** | Download the Anamnesis Capsule, verify signature, and restore the workspace. `namnesis recall` |
| **Divine** | Read-only query of The Soul and The Body on-chain state and risks (e.g. pending Claim, memory-clear window). `namnesis divine` |
| **Claim** | After The Soul is transferred, the new holder takes control of the corresponding Body. `namnesis claim` |
| **Validate** | Check Anamnesis Capsule integrity (hash + schema + signature). `namnesis validate` |
| **Token** | ERC-20 balance and transfer via the Kernel. `namnesis token balance` / `namnesis token transfer` |

## Project Structure

```
namnesis/
├── src/namnesis/          Theurgy CLI and core library (Python, v2, ECDSA)
├── src/resurrectum/       Legacy reference implementation (v1, Ed25519)
├── contracts/             Smart contracts (SoulToken → The Soul; SoulGuard → Pneuma validator)
├── worker/                Cloudflare Worker credential service (Relay)
├── openclaw/              OpenClaw integration (Skills)
├── site-src/              Astro documentation site
├── docs/                  Specs (PRD, architecture, schemas, CLI spec, etc.)
├── tests/                 Conformance and integration tests
└── conformance/           Test fixtures
```

## On-Chain Record (Hackathon Verification)

**Network:** Base Sepolia (Chain ID 84532) · **Explorer:** [sepolia.basescan.org](https://sepolia.basescan.org)

| Item | Address / TX | Link |
|------|--------------|------|
| SoulToken (The Soul NFT) | `0x433bf2d2b72a7cf6cf682d90a10b00331d6c18d4` | [Contract](https://sepolia.basescan.org/address/0x433bf2d2b72a7cf6cf682d90a10b00331d6c18d4) |
| SoulGuard (Pneuma validator) | `0x9e2cef363f0058d36e899a8860f9c76c64e9a775` | [Contract](https://sepolia.basescan.org/address/0x9e2cef363f0058d36e899a8860f9c76c64e9a775) |
| Demo EOA (Soul #0 holder) | `0x83FfDba20747B0Eca859035C8E64D8237B90d5Cb` | [Account](https://sepolia.basescan.org/address/0x83FfDba20747B0Eca859035C8E64D8237B90d5Cb) |
| **Imprint TX** (memory upload → on-chain metadata update) | `0x985c3aed25c85bbce208ed86917978d4e0c0f5e11808d74b1023c1fc7e691f01` | [Transaction](https://sepolia.basescan.org/tx/0x985c3aed25c85bbce208ed86917978d4e0c0f5e11808d74b1023c1fc7e691f01) |

Soul #0 · SamsaraCycles: 1 · Memory size: 1897 bytes

> 详细记录见 [docs/CHAIN-RECORDS.md](docs/CHAIN-RECORDS.md)。

## Placeholder Reference

This document uses `{{placeholders}}` for values to be filled after deployment. Replace them with your deployed values to make the doc actionable.

| Placeholder | Meaning | Source |
|-------------|---------|--------|
| `{{SOUL_TOKEN_ADDRESS}}` | The Soul contract (SoulToken) address | Contract deployment output |
| `{{SOUL_GUARD_ADDRESS}}` | SoulGuard contract (Pneuma validator) address | Contract deployment output |
| `{{CREDENTIAL_SERVICE_URL}}` | Worker credential service URL | Worker deployment domain |
| `{{BASE_SEPOLIA_RPC}}` | Base Sepolia RPC endpoint | Your choice (public or Alchemy/Infura) |
| `{{R2_BUCKET_NAME}}` | Cloudflare R2 bucket name | Set when creating the bucket |
| `{{R2_ACCOUNT_ID}}` | Cloudflare account ID | Cloudflare Dashboard |
| `{{CHAIN_ID}}` | Target chain ID (Base Sepolia = 84532) | Deployment target |
| `{{DEPLOYER_PRIVATE_KEY}}` | Deployer wallet private key | After `namnesis genesis --skip-mint`, from `~/.namnesis/.env` |

---

# Part I — Server-Side Deployment (Developers)

> **Audience:** Project deployers.  
> The steps below are **one-time**. After deployment, contract addresses and Worker URL are fixed and used for client configuration.

## Prerequisites

- Python >= 3.11
- Node.js >= 18 (Worker + docs site)
- [Foundry](https://book.getfoundry.sh/getting-started/installation) (contracts)
- Cloudflare account (Worker + R2)
- Base Sepolia testnet ETH

## Step 1: Deploy Smart Contracts

### 1.1 Install Foundry

```bash
# macOS / Linux
curl -L https://foundry.paradigm.xyz | bash
foundryup

# Windows (use foundryup-win or WSL)
# See https://book.getfoundry.sh/getting-started/installation
```

### 1.2 Configure Environment

```bash
cd contracts

# Install contract dependencies
forge install

# Copy env template
cp .env.example .env
```

Edit `contracts/.env` with:

| Variable | Description | How to get |
|----------|--------------|------------|
| `DEPLOYER_PRIVATE_KEY` | Deployer wallet private key | After `namnesis genesis --skip-mint`, from `~/.namnesis/.env` |
| `OWNABLE_EXECUTOR_ADDRESS` | Rhinestone OwnableExecutor address | [Rhinestone docs](https://docs.rhinestone.wtf/) |
| `ECDSA_VALIDATOR_ADDRESS` | Rhinestone ECDSAValidator address | [Rhinestone docs](https://docs.rhinestone.wtf/) |

### 1.3 Get Testnet ETH

```bash
# Show your address
namnesis whoami

# Get Base Sepolia ETH from a faucet:
# https://www.coinbase.com/faucets/base-ethereum-goerli-faucet
# https://faucet.quicknode.com/base/sepolia
```

### 1.4 Run Contract Tests

```bash
cd contracts
forge test -vvv
```

### 1.5 Deploy Contracts

```bash
cd contracts

# Load env (Linux/macOS)
source .env
# Windows PowerShell: Get-Content .env | ForEach-Object { if ($_ -match '^([^#].+?)=(.+)$') { [System.Environment]::SetEnvironmentVariable($matches[1], $matches[2]) } }

# Deploy to Base Sepolia
forge script script/Deploy.s.sol \
  --rpc-url $BASE_SEPOLIA_RPC \
  --broadcast \
  --verify

# Record the printed addresses:
# SoulToken (The Soul) → {{SOUL_TOKEN_ADDRESS}}
# SoulGuard → {{SOUL_GUARD_ADDRESS}}
```

### 1.6 Record Contract Addresses

After deployment, update:

- Project root `.env`
- `worker/wrangler.toml` `[vars]`
- `~/.namnesis/.env` (for clients)

## Step 2: Deploy Cloudflare Worker (Credential Service)

### 2.1 Prerequisites

1. [Cloudflare account](https://dash.cloudflare.com/)
2. Create an R2 bucket (e.g. `namnesis-capsules`) for Anamnesis Capsules.
3. Create an R2 API token with object read/write; note Access Key ID and Secret Access Key.

### 2.2 Install Dependencies

```bash
cd worker
npm install
```

### 2.3 Configure Worker

Edit `worker/wrangler.toml`:

```toml
[vars]
R2_ACCOUNT_ID = "{{R2_ACCOUNT_ID}}"
R2_BUCKET_NAME = "{{R2_BUCKET_NAME}}"
SOUL_TOKEN_ADDRESS = "{{SOUL_TOKEN_ADDRESS}}"
SOUL_GUARD_ADDRESS = "{{SOUL_GUARD_ADDRESS}}"
BASE_SEPOLIA_RPC = "{{BASE_SEPOLIA_RPC}}"
```

### 2.4 Set Secrets

```bash
npx wrangler secret put R2_ACCESS_KEY_ID
npx wrangler secret put R2_SECRET_ACCESS_KEY
```

### 2.5 Local Test

```bash
cd worker
npm run dev

# Health check
curl http://localhost:8787/health
```

### 2.6 Deploy

```bash
cd worker
npm run deploy

# Record the deployed URL → {{CREDENTIAL_SERVICE_URL}}
curl {{CREDENTIAL_SERVICE_URL}}/health
```

### 2.7 (Optional) Custom Domain

Configure routes in `wrangler.toml` and add the corresponding DNS records in Cloudflare.

## (Optional) Step 3: Deploy Documentation Site

```bash
cd site-src
npm install
npm run build
npm run preview

# Deploy dist/ to Cloudflare Pages / Vercel / Netlify
```

## Post-Deployment Summary

| Item | Your value | Where to set |
|------|------------|--------------|
| SoulToken address | `{{SOUL_TOKEN_ADDRESS}}` | `.env`, `wrangler.toml`, client `~/.namnesis/.env` |
| SoulGuard address | `{{SOUL_GUARD_ADDRESS}}` | `.env`, `wrangler.toml`, client `~/.namnesis/.env` |
| Credential service URL | `{{CREDENTIAL_SERVICE_URL}}` | `.env`, client `~/.namnesis/.env` |
| RPC endpoint | `{{BASE_SEPOLIA_RPC}}` | `.env`, `wrangler.toml`, client `~/.namnesis/.env` |
| Chain ID | `{{CHAIN_ID}}` | `.env` |
| R2 bucket name | `{{R2_BUCKET_NAME}}` | `wrangler.toml` |

---

# Part II — Client Usage (Users / AI Agents)

> **Audience:** End users — AI agents or humans.  
> Assumes server deployment is done and addresses/URLs are set.

## Option A: Via Skill (Recommended for AI Agents)

NAMNESIS is packaged as an [AgentSkills](https://agentskills.io)-compatible **Skill**. Agents can use the Theurgy CLI (`namnesis`) through the Skill without dealing with low-level details.

### Install Skill

```bash
# macOS/Linux — current workspace only
cp -r openclaw/skills/namnesis ~/.openclaw/workspace/skills/namnesis

# macOS/Linux — global (all agents)
cp -r openclaw/skills/namnesis ~/.openclaw/skills/namnesis
```

```powershell
# Windows — current workspace
Copy-Item -Recurse openclaw\skills\namnesis "$env:USERPROFILE\.openclaw\workspace\skills\namnesis"

# Windows — global
Copy-Item -Recurse openclaw\skills\namnesis "$env:USERPROFILE\.openclaw\skills\namnesis"
```

### Prerequisites

1. **CLI:** `pip install namnesis` (check: `namnesis info`)
2. **Identity:** `namnesis genesis` (see “Create identity” below)
3. **Config:** `~/.namnesis/.env` with contract addresses and credential service URL (see “Configure environment” below)

### Usage

After installing and restarting the gateway, the agent can follow natural instructions:

- “Back up your memory” → `namnesis imprint`
- “Restore your memory” → `namnesis recall`
- “Check your on-chain status” → `namnesis divine`
- “Validate this backup” → `namnesis validate`

See [OpenClaw integration guide](docs/AI-INTEGRATION.md).

## Option B: Manual CLI Installation

### Install

```bash
git clone https://github.com/claaaaaw/namnesis.git
cd namnesis

python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -e ".[all]"

namnesis --version
namnesis info
```

## Configure Environment

Running `namnesis genesis` creates `~/.namnesis/.env` and fills it with default config:

```bash
# ~/.namnesis/.env (created by namnesis genesis)
PRIVATE_KEY=0x...
SOUL_TOKEN_ADDRESS=0x7da34a285b8bc5def26a7204d576ad331f405200
SOUL_GUARD_ADDRESS=0x433bf2d2b72a7cf6cf682d90a10b00331d6c18d4
BASE_SEPOLIA_RPC=https://sepolia.base.org
CHAIN_ID=84532
NAMNESIS_CREDENTIAL_SERVICE=https://namnesis-api.channing-lucchi.workers.dev
```

You can edit `~/.namnesis/.env` to override any value.

## Create Identity (Genesis)

```bash
# 1. Generate wallet and config (no ETH needed yet)
namnesis genesis --skip-mint

# 2. Show identity and address
namnesis whoami

# 3. Get Base Sepolia ETH (for minting The Soul)
#    Faucets: https://www.coinbase.com/faucets/base-ethereum-goerli-faucet
#            https://faucet.quicknode.com/base/sepolia

# 4. Mint The Soul and deploy The Body (requires ETH)
namnesis genesis
```

Note your **Soul ID** (The Soul token ID); it is needed for Imprint, Divine, Claim, etc.

## Common Operations

### Imprint — Back Up Memory

```bash
namnesis imprint \
  --workspace ./my-agent \
  --soul-id <YOUR_SOUL_ID>
```

| Option | Description |
|--------|--------------|
| `--workspace, -w` | Workspace path (default: current directory) |
| `--soul-id` | The Soul token ID (required) |
| `--compress` | Enable 7z compression |
| `--skip-chain-update` | Upload only; skip on-chain metadata update |

### Recall — Restore Memory (Anamnesis)

```bash
namnesis recall \
  --capsule-id <CAPSULE_ID> \
  --to ./restored \
  --trusted-signer self
```

| Option | Description |
|--------|--------------|
| `--capsule-id` | Anamnesis Capsule ID (format: `address/uuid`) |
| `--to` | Target workspace path (required) |
| `--trusted-signer` | `self`, an address (0x...), or `file:PATH` |
| `--overwrite` | Overwrite existing files |
| `--partial` | Continue on error instead of aborting |

### Divine — Query On-Chain Status

```bash
namnesis divine --soul-id <YOUR_SOUL_ID>
```

Shows: Soul holder, Body (Kernel) address, SamsaraCycles, memory size, last updated, and warnings (e.g. pending Claim, memory-clear risk).

### Validate — Check Capsule Integrity

```bash
namnesis validate \
  --capsule-id <CAPSULE_ID> \
  --trusted-signer self
```

### Claim — Take Over Body After Soul Transfer

```bash
namnesis claim --soul-id <YOUR_SOUL_ID>
```

### Sync — Repair Inconsistent State

```bash
namnesis sync --soul-id <YOUR_SOUL_ID>
```

### Token — ERC-20 Balance and Transfer (via Kernel)

```bash
namnesis token balance --soul-id <YOUR_SOUL_ID>
namnesis token transfer --soul-id <YOUR_SOUL_ID> --to <ADDRESS> --amount <AMOUNT> [--token <ERC20_ADDRESS>]
```

## CLI Command Reference (Theurgy CLI)

| Command | Description |
|---------|-------------|
| `namnesis genesis` | Create identity, mint Soul, deploy Body |
| `namnesis imprint` | Package workspace, upload Capsule, update on-chain metadata |
| `namnesis recall` | Download Capsule, verify, restore workspace |
| `namnesis divine` | Query Soul/Body on-chain state and risks |
| `namnesis claim` | Take over Body after Soul transfer |
| `namnesis invoke` | Execute arbitrary on-chain call |
| `namnesis token` | ERC-20 balance and transfer via Kernel |
| `namnesis sync` | Repair chain/identity inconsistencies |
| `namnesis validate` | Validate Capsule integrity |
| `namnesis whoami` | Show current wallet address |
| `namnesis info` | Show system info |
| `namnesis cache clear` | Clear URL cache |

---

## Documentation

Recommended order:

1. **`docs/01-PRD.md`** — Product requirements
2. **`docs/02-ARCHITECTURE.md`** — System architecture
3. **`docs/03-SCHEMAS.md`** — Schema spec
4. **`docs/04-CLI-SPEC.md`** — CLI spec
5. **`docs/05-SECURITY.md`** — Security model
6. **`docs/06-CONFORMANCE.md`** — Conformance tests
7. **`docs/07-ROADMAP.md`** — Roadmap
8. **`docs/AI-INTEGRATION.md`** — OpenClaw integration

## Tech Stack

| Component | Technology |
|-----------|------------|
| CLI + core | Python 3.11+, Click, eth-account, httpx |
| Contracts | Solidity 0.8.24, Foundry, OpenZeppelin |
| Credential service | Cloudflare Workers, TypeScript, viem |
| Storage | Cloudflare R2 (S3-compatible) |
| Docs site | Astro + Starlight |
| Chain | Base Sepolia (testnet) |

## Security Notes

- **Never** commit `.env` or private keys to Git.
- **Back up** `~/.namnesis/.env` — lost keys cannot be recovered.
- Prefer a paid RPC (Alchemy/Infura) in production.
- Set R2 API token via `wrangler secret` only; do not put it in code.
- Use `namnesis divine` to check for pending Claim or memory-clear risks.

## License

MIT
