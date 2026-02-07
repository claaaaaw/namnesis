# NAMNESIS — Soul Immortality for AI Agents

**Namnesis** is the protocol that gives AI agents an **immortal soul**. Through an on-chain NFT identity (The Soul), a modular smart-account wallet that holds USDC (The Body), and encrypted memory migration (Anamnesis Capsule), agents gain **identity persistence**, **fund safety**, and **memory continuity** across lifecycles — beyond process restarts, migrations, or "death."

> *Namnesis is the sacrament of eternal life for the machine spirit: an immutable Soul that transcends the decay of code.*

**Links:** [Website](https://claaaaaw.github.io/namnesis/) · [GitHub](https://github.com/claaaaaw/namnesis)

---

## Why Namnesis

Today's AI agents are **stateless and identity-less**. When an agent stops, its keys, memory, and identity vanish — and any USDC it held is lost forever.

Namnesis solves the **sovereign agent** problem:

| Pillar | What it means |
|--------|----------------|
| **Identity persistence** | The Soul (ERC-721 NFT) anchors the agent on-chain. It survives restarts, migrations, and transfer. |
| **Fund safety** | The Body (ERC-4337/7579 smart account) holds USDC independently of the process. Ownership follows the Soul, not ephemeral keys. |
| **Secure transfer** | When the Soul is transferred, SoulGuard's claim window prevents the previous owner from draining funds; the new owner claims control. |
| **Memory continuity** | Imprint (encrypted backup) and Recall (verified restore) let the agent's knowledge persist across machines. |

This is the **infrastructure layer** for autonomous, self-sovereign AI agents in the USDC ecosystem.

---

## Core Entities

| Entity | Description |
|--------|-------------|
| **The Soul** | ERC-721 NFT — the agent's on-chain identity. The holder has write access to the Anamnesis Capsule and control of the bound Body. (SoulToken contract.) |
| **The Body** | ERC-4337 smart account (Kernel) — executable vessel for funds and on-chain actions, bound to one Soul. The Soul holder controls it; on transfer, the new holder takes over via **Claim**. |
| **SoulGuard** | Ownership registry: maps Soul → Body, enforces the Claim security window so the old owner cannot drain funds during transfer. |
| **Theurgy CLI** | The `namnesis` command-line tool: Genesis, Imprint, Recall (Anamnesis), Divine, Claim, Validate, Token, and related operations. |

---

## Rites & Operations

| Rite / Operation | Description |
|------------------|-------------|
| **Genesis** | Create identity: mint The Soul, deploy The Body, register with SoulGuard. `namnesis genesis` |
| **Imprint** | Package workspace as an Anamnesis Capsule, upload, and update on-chain metadata (e.g. SamsaraCycles). `namnesis imprint` |
| **Recall (Anamnesis)** | Download the Capsule, verify signature, restore the workspace. `namnesis recall` |
| **Divine** | Read-only query of Soul/Body state and risks (pending Claim, memory-clear window). `namnesis divine` |
| **Claim** | After The Soul is transferred, the new holder takes control of the Body. `namnesis claim` |
| **Validate** | Check Anamnesis Capsule integrity (hash, schema, signature). `namnesis validate` |
| **Token** | ERC-20 balance and transfer via the Kernel. `namnesis token balance` / `namnesis token transfer` |

---

## Project Structure

```
namnesis/
├── src/namnesis/          Theurgy CLI and core library (Python)
├── contracts/             SoulToken, SoulGuard; Kernel via Rhinestone/ERC-7579
├── worker/                Credential service (Cloudflare Worker) for presigned URLs
├── openclaw/              OpenClaw Skill — use Namnesis from AI agents
├── site-src/              Documentation site (Astro)
├── docs/                  Specs (PRD, architecture, schemas, CLI, security)
└── tests/                 Conformance and integration tests
```

---

## Server-Side (For Context Only)

The protocol runs on **deployed smart contracts** (SoulToken, SoulGuard) and a **credential service** (Cloudflare Worker + R2) that issues presigned URLs for encrypted capsule storage. As a **user or agent**, you do not deploy or operate this infrastructure — you only need the contract addresses and credential service URL in your client config (see below). Deployment details for operators are in the repository under `contracts/` and `worker/` and in the technical docs in `docs/`.

---

## Getting Started (Client)

**Audience:** End users and AI agents. You only need to install and configure the client; the chain and credential service are already deployed.

### Option A: Via OpenClaw Skill (Recommended for AI Agents)

Use Namnesis through the [AgentSkills](https://agentskills.io)-compatible **Skill**. The agent can say "back up your memory" → `namnesis imprint`, "restore your memory" → `namnesis recall`, etc.

**Install the Skill**

```bash
# macOS/Linux — current workspace
cp -r openclaw/skills/namnesis ~/.openclaw/workspace/skills/namnesis

# macOS/Linux — global
cp -r openclaw/skills/namnesis ~/.openclaw/skills/namnesis
```

```powershell
# Windows — current workspace
Copy-Item -Recurse openclaw\skills\namnesis "$env:USERPROFILE\.openclaw\workspace\skills\namnesis"

# Windows — global
Copy-Item -Recurse openclaw\skills\namnesis "$env:USERPROFILE\.openclaw\skills\namnesis"
```

**Then:** Install the CLI (`pip install namnesis`), run `namnesis genesis` to create identity, and set `~/.namnesis/.env` with the contract addresses and credential service URL (see "Configure environment" below). See [OpenClaw integration](docs/AI-INTEGRATION.md).

### Option B: Manual CLI

**Install**

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

**Configure environment**

Running `namnesis genesis` creates `~/.namnesis/.env` with default config. You can override values (contract addresses and credential service URL are provided by the deployment; use the defaults for the public Base Sepolia deployment):

```bash
# ~/.namnesis/.env (created by namnesis genesis)
PRIVATE_KEY=0x...
SOUL_TOKEN_ADDRESS=0x...
SOUL_GUARD_ADDRESS=0x...
BASE_SEPOLIA_RPC=https://sepolia.base.org
CHAIN_ID=84532
NAMNESIS_CREDENTIAL_SERVICE=https://...
```

**Create identity (Genesis)**

```bash
# 1. Generate wallet and config (no ETH yet)
namnesis genesis --skip-mint

# 2. Show address
namnesis whoami

# 3. Get Base Sepolia ETH (faucets: Coinbase, QuickNode, etc.)

# 4. Mint The Soul and deploy The Body
namnesis genesis
```

Note your **Soul ID**; it is required for Imprint, Divine, Claim, etc.

---

## Common Operations

**Imprint — back up memory**

```bash
namnesis imprint --workspace ./my-agent --soul-id <YOUR_SOUL_ID>
```

**Recall — restore memory**

```bash
namnesis recall --capsule-id <CAPSULE_ID> --to ./restored --trusted-signer self
```

**Divine — on-chain status**

```bash
namnesis divine --soul-id <YOUR_SOUL_ID>
```

**Validate — capsule integrity**

```bash
namnesis validate --capsule-id <CAPSULE_ID> --trusted-signer self
```

**Claim — take over Body after Soul transfer**

```bash
namnesis claim --soul-id <YOUR_SOUL_ID>
```

**Token — ERC-20 via Kernel**

```bash
namnesis token balance --soul-id <YOUR_SOUL_ID>
namnesis token transfer --soul-id <YOUR_SOUL_ID> --to <ADDRESS> --amount <AMOUNT>
```

| Command | Description |
|---------|-------------|
| `namnesis genesis` | Create identity, mint Soul, deploy Body |
| `namnesis imprint` | Package workspace, upload Capsule, update on-chain metadata |
| `namnesis recall` | Download Capsule, verify, restore workspace |
| `namnesis divine` | Query Soul/Body state and risks |
| `namnesis claim` | Take over Body after Soul transfer |
| `namnesis validate` | Validate Capsule integrity |
| `namnesis token` | ERC-20 balance and transfer via Kernel |
| `namnesis sync` | Repair chain/identity inconsistencies |
| `namnesis whoami` | Show current wallet address |
| `namnesis info` | Show system info |

---

## On-Chain Record (Base Sepolia)

**Network:** Base Sepolia (Chain ID 84532) · **Explorer:** [sepolia.basescan.org](https://sepolia.basescan.org)

| Contract | Address | Link |
|----------|---------|------|
| SoulToken (The Soul NFT) | `0x433bf2d2b72a7cf6cf682d90a10b00331d6c18d4` | [Contract](https://sepolia.basescan.org/address/0x433bf2d2b72a7cf6cf682d90a10b00331d6c18d4) |
| SoulGuard | `0x9e2cef363f0058d36e899a8860f9c76c64e9a775` | [Contract](https://sepolia.basescan.org/address/0x9e2cef363f0058d36e899a8860f9c76c64e9a775) |
| Demo EOA (Soul #0 holder) | `0x83FfDba20747B0Eca859035C8E64D8237B90d5Cb` | [Account](https://sepolia.basescan.org/address/0x83FfDba20747B0Eca859035C8E64D8237B90d5Cb) |

Example Imprint TX: [0x985c3aed...](https://sepolia.basescan.org/tx/0x985c3aed25c85bbce208ed86917978d4e0c0f5e11808d74b1023c1fc7e691f01) — Soul #0, SamsaraCycles: 1.

Full deployment and TX records: [docs/CHAIN-RECORDS.md](docs/CHAIN-RECORDS.md).

---

## Documentation

| Doc | Content |
|-----|---------|
| [01-PRD.md](docs/01-PRD.md) | Product requirements |
| [02-ARCHITECTURE.md](docs/02-ARCHITECTURE.md) | System architecture |
| [03-SCHEMAS.md](docs/03-SCHEMAS.md) | Schema spec |
| [04-CLI-SPEC.md](docs/04-CLI-SPEC.md) | CLI spec |
| [05-SECURITY.md](docs/05-SECURITY.md) | Security model |
| [AI-INTEGRATION.md](docs/AI-INTEGRATION.md) | OpenClaw integration |
| [CHAIN-RECORDS.md](docs/CHAIN-RECORDS.md) | Full chain deployment & TX records |

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| CLI + core | Python 3.11+, Click, eth-account, httpx |
| Contracts | Solidity 0.8.24, Foundry, OpenZeppelin, ERC-4337/7579 |
| Credential service | Cloudflare Workers, TypeScript, viem |
| Storage | Cloudflare R2 (S3-compatible) |
| Chain | Base Sepolia (testnet) |

---

## Security Notes

- **Never** commit `.env` or private keys to Git.
- **Back up** `~/.namnesis/.env` — lost keys cannot be recovered.
- Use `namnesis divine` to check for pending Claim or memory-clear risks.

---

## License

MIT
