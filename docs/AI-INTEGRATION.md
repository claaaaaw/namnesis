# Namnesis × OpenClaw 集成指南

**受众:** AI 工程师 / OpenClaw 用户  
**版本:** v1.0

## 概述

Namnesis 为 OpenClaw Agent 提供**主权记忆协议**：将 Agent 的工作区（记忆、人格、操作手册）加密签名后上传至云端，并锚定到链上 Soul NFT。任何时候都可以验证完整性、恢复到新环境、或通过 NFT 转让实现"夺舍"。

两个系统共享**完全相同的工作区文件结构**：

| 文件 | OpenClaw 用途 | Namnesis 处理 |
|------|--------------|---------------|
| `MEMORY.md` | 长期记忆 | 包含在 Capsule |
| `memory/*.md` | 每日记忆日志 | 包含在 Capsule |
| `SOUL.md` | 人格/语气/边界 | 包含在 Capsule |
| `USER.md` | 用户信息 | 包含在 Capsule |
| `IDENTITY.md` | Agent 名称/风格 | 包含在 Capsule |
| `AGENTS.md` | 操作指令 | 包含在 Capsule |
| `TOOLS.md` | 工具使用备注 | 包含在 Capsule |
| `HEARTBEAT.md` | 心跳检查清单 | 包含在 Capsule |

## 集成方式：OpenClaw Skill

Namnesis 以 **[AgentSkills](https://agentskills.io) 兼容的 Skill** 形式集成到 OpenClaw。Skill 是一个包含 `SKILL.md` 的目录，教 Agent 如何通过 `exec` 工具调用 `namnesis` CLI。

### 安装步骤

#### 1. 安装 Namnesis CLI

```bash
pip install namnesis
```

验证安装：

```bash
namnesis info
```

#### 2. 初始化身份

```bash
# 生成钱包（如果还没有 testnet ETH，先 --skip-mint）
namnesis genesis --skip-mint

# 获取 Base Sepolia testnet ETH 后铸造 Soul NFT
namnesis genesis
```

#### 3. 配置环境变量

在 `~/.namnesis/.env` 中添加合约地址：

```
SOUL_TOKEN_ADDRESS=0x...
SOUL_GUARD_ADDRESS=0x...
```

#### 4. 安装 Skill 到 OpenClaw

将 Skill 目录复制到 OpenClaw 的 skills 目录中：

```bash
# 方式 A：安装到当前 Agent 的 workspace（仅当前 Agent 可用）
cp -r openclaw/skills/namnesis ~/.openclaw/workspace/skills/namnesis

# 方式 B：安装到全局 skills（所有 Agent 共享）
cp -r openclaw/skills/namnesis ~/.openclaw/skills/namnesis
```

#### 5. 验证 Skill 已加载

重启 Gateway 后：

```bash
# Agent 应该能看到 namnesis skill
# 通过消息通道发送: "用 namnesis 备份我的记忆"
```

### 使用方式

安装完成后，OpenClaw Agent 会自动了解 Namnesis 的功能。你可以通过消息通道指示 Agent：

- **"备份你的记忆"** → Agent 执行 `namnesis imprint`
- **"恢复你的记忆"** → Agent 执行 `namnesis recall`
- **"检查你的链上状态"** → Agent 执行 `namnesis divine`
- **"验证这个备份"** → Agent 执行 `namnesis validate`

Agent 也会在适当时机主动备份（迁移前、定期、风险操作前）。

## 多 Agent 场景

在 OpenClaw 的多 Agent 配置中，每个 Agent 可以拥有独立的 Namnesis 身份：

```jsonc
// ~/.openclaw/openclaw.json
{
  agents: {
    list: [
      {
        id: "personal",
        workspace: "~/.openclaw/workspace-personal"
        // 使用自己的 ~/.namnesis 身份
      },
      {
        id: "work",
        workspace: "~/.openclaw/workspace-work"
        // 可以配置不同的 NAMNESIS_DIR
      }
    ]
  }
}
```

每个 Agent 的 `namnesis imprint` 指向各自的 workspace 路径。

## 目录结构

```
namnesis/
└── openclaw/
    └── skills/
        └── namnesis/
            └── SKILL.md          # OpenClaw Agent Skill 定义
```

## 进阶集成（未来）

| 方式 | 描述 | 状态 |
|------|------|------|
| **Skill** | Agent 通过 exec 调用 namnesis CLI | ✅ 已实现 |
| **Hook** | 会话重置时自动触发 imprint | 🔮 计划中 |
| **Cron** | Skill 中包含设置定期备份的指引 | ✅ 已包含在 Skill 中 |
| **Plugin** | 原生 TypeScript 工具注册 | 🔮 未来考虑 |

## 相关文档

- Namnesis PRD: `docs/01-PRD.md`
- Namnesis 架构: `docs/02-ARCHITECTURE.md`
- Namnesis CLI 规范: `docs/04-CLI-SPEC.md`
- OpenClaw Skills 文档: https://docs.openclaw.ai/tools/skills
- OpenClaw Agent Workspace: https://docs.openclaw.ai/concepts/agent-workspace
