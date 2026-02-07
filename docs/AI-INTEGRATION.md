# Namnesis × OpenClaw Integration Guide

**Audience:** AI engineers / OpenClaw users  
**Version:** v1.0

## Overview

Namnesis provides OpenClaw agents with a **sovereign memory protocol**: package the agent workspace (memory, persona, runbooks), sign it, upload to cloud storage, and anchor it to an on-chain Soul NFT. You can verify integrity, restore in a new environment, or transfer ownership via NFT (“Claim”).

The two systems share the **same workspace file layout**:

| File | OpenClaw use | Namnesis handling |
|------|--------------|-------------------|
| `MEMORY.md` | Long-term memory | Included in capsule |
| `memory/*.md` | Daily memory logs | Included in capsule |
| `SOUL.md` | Persona / tone / boundaries | Included in capsule |
| `USER.md` | User info | Included in capsule |
| `IDENTITY.md` | Agent name / style | Included in capsule |
| `AGENTS.md` | Operations instructions | Included in capsule |
| `TOOLS.md` | Tool usage notes | Included in capsule |
| `HEARTBEAT.md` | Heartbeat checklist | Included in capsule |

## Integration: OpenClaw Skill

Namnesis is integrated as an **[AgentSkills](https://agentskills.io)-compatible Skill**. The Skill is a directory containing `SKILL.md` that teaches the agent how to call the `namnesis` CLI via the `exec` tool.

### Installation

#### 1. Install Namnesis CLI

```bash
pip install namnesis
```

Verify:

```bash
namnesis info
```

#### 2. Create Identity

```bash
# Generate wallet (use --skip-mint if you don’t have testnet ETH yet)
namnesis genesis --skip-mint

# After getting Base Sepolia ETH, mint Soul NFT
namnesis genesis
```

#### 3. Configure Environment

Ensure `~/.namnesis/.env` contains contract addresses and credential service URL (usually created by `namnesis genesis`):

```
SOUL_TOKEN_ADDRESS=0x...
SOUL_GUARD_ADDRESS=0x...
NAMNESIS_CREDENTIAL_SERVICE=https://...
```

#### 4. Install Skill into OpenClaw

Copy the Skill directory into OpenClaw’s skills directory:

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

#### 5. Confirm Skill Is Loaded

After restarting the gateway, the agent should recognize Namnesis. You can ask via the message channel: “Back up my memory with namnesis.”

### Usage

Once installed, the agent can follow natural-language instructions:

- **“Back up your memory”** → runs `namnesis imprint`
- **“Restore your memory”** → runs `namnesis recall`
- **“Check your on-chain status”** → runs `namnesis divine`
- **“Validate this backup”** → runs `namnesis validate`

The agent can also trigger backups at appropriate times (before migration, periodically, or before risky operations).

## Multi-Agent Setup

Each OpenClaw agent can have its own Namnesis identity by using different workspaces (and optionally different `~/.namnesis` or env):

```jsonc
// ~/.openclaw/openclaw.json
{
  "agents": {
    "list": [
      {
        "id": "personal",
        "workspace": "~/.openclaw/workspace-personal"
      },
      {
        "id": "work",
        "workspace": "~/.openclaw/workspace-work"
      }
    ]
  }
}
```

Each agent’s `namnesis imprint` uses its workspace path.

## Directory Layout

```
namnesis/
└── openclaw/
    └── skills/
        └── namnesis/
            └── SKILL.md    # OpenClaw Agent Skill definition
```

## Advanced Integration (Future)

| Method | Description | Status |
|--------|--------------|--------|
| **Skill** | Agent calls namnesis via exec | ✅ Implemented |
| **Hook** | Auto trigger imprint on session reset | 🔮 Planned |
| **Cron** | Skill includes guidance for scheduled backup | ✅ In Skill |
| **Plugin** | Native TypeScript tool registration | 🔮 Future |

## Related Documentation

- Namnesis PRD: `docs/01-PRD.md`
- Namnesis architecture: `docs/02-ARCHITECTURE.md`
- Namnesis CLI spec: `docs/04-CLI-SPEC.md`
- AgentSkills: https://agentskills.io
- Repository: https://github.com/claaaaaw/namnesis
