# NAMNESIS — Sovereign AI Agent Protocol

NAMNESIS 是 **AI Agent 主权智能体协议**：为 Agent 提供链上身份（The Soul）、可执行载体（The Body）与记忆延续契约（Anamnesis Protocol）。核心理念：*灵魂（NFT）即主权；代码即法律。*

## 核心实体

- **The Soul（灵魂）** — 链上身份，ERC-721 NFT。谁持有 The Soul，谁就拥有 Agent 的 Anamnesis Capsule 写权限及所绑定 The Body 的控制权。实现为 SoulToken 合约。
- **The Body（躯体）** — 资金与链上行为的可执行载体，ERC-4337 智能账户（Kernel），与单一 Soul 绑定。The Soul 的持有者控制 The Body；The Soul 转让后，新持有者可通过 Claim 接管 The Body。
- **Theurgy CLI** — 操作者界面，即 `namnesis` 命令行工具，用于执行 Genesis、Imprint、Anamnesis、Divine、Claim 等仪式。

## 核心能力（仪式与操作）

| 仪式/操作 | 说明 |
|-----------|------|
| **Genesis（创世）** | 建立身份、铸造 The Soul、部署 The Body 并登记绑定。`namnesis genesis` |
| **Imprint（铭刻）** | 将工作区加密为 Anamnesis Capsule，上传并更新链上元数据（含 SamsaraCycles）。`namnesis imprint` |
| **Anamnesis（回溯）** | 下载 Anamnesis Capsule，验签、解密并恢复工作区。`namnesis recall` |
| **Divine（神谕）** | 只读查询 The Soul 与 The Body 的链上状态及风险（如待 Claim、记忆清除窗口）。`namnesis divine` |
| **Claim（夺舍）** | The Soul 转让后，新持有者接管对应 The Body 的控制权。`namnesis claim` |
| **Validate** | 校验 Anamnesis Capsule 完整性（哈希 + Schema + 签名）。`namnesis validate` |

## 项目结构

```
namnesis/
├── src/namnesis/          Theurgy CLI 与核心库（Python，v2，ECDSA）
├── src/resurrectum/       旧版参考实现（v1，Ed25519）
├── contracts/             智能合约（SoulToken → The Soul；SoulGuard → Pneuma Validator 集成）
├── worker/                Cloudflare Worker 凭证服务（Relay）
├── openclaw/              OpenClaw 集成（Skills）
├── site-src/              Astro 文档站点
├── docs/                  规范文档（PRD、架构、Schema、CLI 规范等）
├── tests/                 一致性测试
└── conformance/           测试夹具
```

## 占位符说明

本文档使用 `{{占位符}}` 标记所有需要在部署后填入的值。开发者完成服务端部署后，将这些值统一替换即可使文档进入可用状态。

| 占位符 | 含义 | 来源 |
|--------|------|------|
| `{{SOUL_TOKEN_ADDRESS}}` | The Soul 合约（SoulToken）地址 | 合约部署输出 |
| `{{SOUL_GUARD_ADDRESS}}` | SoulGuard 合约（Pneuma Validator 集成）地址 | 合约部署输出 |
| `{{CREDENTIAL_SERVICE_URL}}` | Worker 凭证服务 URL | Worker 部署后的域名 |
| `{{BASE_SEPOLIA_RPC}}` | Base Sepolia RPC 端点 | 自选（公共或 Alchemy/Infura） |
| `{{R2_BUCKET_NAME}}` | Cloudflare R2 存储桶名 | R2 创建时设定 |
| `{{R2_ACCOUNT_ID}}` | Cloudflare 账号 ID | Cloudflare Dashboard |
| `{{CHAIN_ID}}` | 目标链 ID（Base Sepolia = 84532） | 部署目标链 |
| `{{DEPLOYER_PRIVATE_KEY}}` | 部署者钱包私钥 | `namnesis genesis --skip-mint` 后获取 |

---

# Part I — 服务端部署（开发者）

> **受众：** 项目部署者（你）。
> 以下操作为**一次性部署**。完成后合约地址、Worker URL 等信息固定不变，将用于客户端配置。

## 前置要求

- Python >= 3.11
- Node.js >= 18（Worker + 文档站点）
- [Foundry](https://book.getfoundry.sh/getting-started/installation)（合约开发）
- Cloudflare 账号（Worker + R2）
- Base Sepolia 测试网 ETH

## 步骤一：部署智能合约

### 1.1 安装 Foundry

```bash
# macOS / Linux
curl -L https://foundry.paradigm.xyz | bash
foundryup

# Windows（使用 foundryup-win 或 WSL）
# 参见 https://book.getfoundry.sh/getting-started/installation
```

### 1.2 配置环境

```bash
cd contracts

# 安装合约依赖
forge install

# 复制环境变量模板
cp .env.example .env
```

编辑 `contracts/.env`，填入以下值：

| 变量 | 说明 | 获取方式 |
|------|------|----------|
| `DEPLOYER_PRIVATE_KEY` | 部署者钱包私钥 | `namnesis genesis --skip-mint` 后查看 `~/.namnesis/.env` |
| `OWNABLE_EXECUTOR_ADDRESS` | Rhinestone OwnableExecutor 地址 | [Rhinestone 文档](https://docs.rhinestone.wtf/) |
| `ECDSA_VALIDATOR_ADDRESS` | Rhinestone ECDSAValidator 地址 | [Rhinestone 文档](https://docs.rhinestone.wtf/) |

### 1.3 获取测试网 ETH

```bash
# 查看你的地址
namnesis whoami

# 从水龙头获取 Base Sepolia ETH：
# https://www.coinbase.com/faucets/base-ethereum-goerli-faucet
# https://faucet.quicknode.com/base/sepolia
```

### 1.4 运行合约测试

```bash
cd contracts
forge test -vvv
```

### 1.5 部署合约

```bash
cd contracts

# 加载环境变量
source .env  # Linux/macOS
# Windows PowerShell: Get-Content .env | ForEach-Object { if ($_ -match '^([^#].+?)=(.+)$') { [System.Environment]::SetEnvironmentVariable($matches[1], $matches[2]) } }

# 部署到 Base Sepolia
forge script script/Deploy.s.sol \
  --rpc-url $BASE_SEPOLIA_RPC \
  --broadcast \
  --verify

# ⚠️ 记录输出的合约地址：
# SoulToken (The Soul) deployed at: 0x... → 这就是 {{SOUL_TOKEN_ADDRESS}}
# SoulGuard deployed at: 0x... → 这就是 {{SOUL_GUARD_ADDRESS}}
```

### 1.6 记录合约地址

部署成功后，将合约地址更新到以下位置：
- 项目根目录 `.env`
- `worker/wrangler.toml` 的 `[vars]` 中
- `~/.namnesis/.env` 中

## 步骤二：部署 Cloudflare Worker（凭证服务）

### 2.1 前置准备

1. 注册 [Cloudflare 账号](https://dash.cloudflare.com/)
2. 创建 R2 存储桶：
   - 进入 Cloudflare Dashboard → R2
   - 创建存储桶（名称自定，如 `namnesis-capsules`，用于存储 Anamnesis Capsules）
3. 创建 R2 API Token：
   - R2 → 管理 R2 API 令牌
   - 权限：对象读写
   - 记录 `Access Key ID` 和 `Secret Access Key`

### 2.2 安装依赖

```bash
cd worker
npm install
```

### 2.3 配置 Worker

编辑 `worker/wrangler.toml`，更新以下值：

```toml
[vars]
R2_ACCOUNT_ID = "{{R2_ACCOUNT_ID}}"
R2_BUCKET_NAME = "{{R2_BUCKET_NAME}}"
SOUL_TOKEN_ADDRESS = "{{SOUL_TOKEN_ADDRESS}}"
SOUL_GUARD_ADDRESS = "{{SOUL_GUARD_ADDRESS}}"
BASE_SEPOLIA_RPC = "{{BASE_SEPOLIA_RPC}}"
```

### 2.4 设置 Secrets

```bash
# 设置 R2 凭证（交互式输入，不会存储在代码中）
npx wrangler secret put R2_ACCESS_KEY_ID
npx wrangler secret put R2_SECRET_ACCESS_KEY
```

### 2.5 本地测试

```bash
cd worker
npm run dev

# 测试健康检查
curl http://localhost:8787/health
```

### 2.6 部署

```bash
cd worker
npm run deploy

# ⚠️ 记录部署后的 URL → 这就是 {{CREDENTIAL_SERVICE_URL}}
# 验证部署
curl {{CREDENTIAL_SERVICE_URL}}/health
```

### 2.7 （可选）配置自定义域名

在 `wrangler.toml` 的 `[env.production]` 中已配置了路由。
需要在 Cloudflare DNS 中添加对应记录。

## （可选）步骤三：部署文档站点

```bash
cd site-src
npm install
npm run build

# 预览
npm run preview

# 部署到 Cloudflare Pages / Vercel / Netlify
# 构建输出在 dist/ 目录
```

## 部署后信息汇总

完成以上部署后，你应该得到以下信息。请记录好，它们将用于配置客户端：

| 信息 | 你的值 | 填入位置 |
|------|--------|----------|
| The Soul 合约（SoulToken）地址 | `{{SOUL_TOKEN_ADDRESS}}` | `.env`、`wrangler.toml`、客户端 `~/.namnesis/.env` |
| SoulGuard 合约地址 | `{{SOUL_GUARD_ADDRESS}}` | `.env`、`wrangler.toml`、客户端 `~/.namnesis/.env` |
| 凭证服务 URL | `{{CREDENTIAL_SERVICE_URL}}` | `.env`、客户端 `~/.namnesis/.env` |
| RPC 端点 | `{{BASE_SEPOLIA_RPC}}` | `.env`、`wrangler.toml`、客户端 `~/.namnesis/.env` |
| 链 ID | `{{CHAIN_ID}}` | `.env` |
| R2 存储桶名 | `{{R2_BUCKET_NAME}}` | `wrangler.toml` |

> 部署完成后，将以上实际值告知文档维护者，统一替换本文档中的所有 `{{占位符}}`，即可使文档进入最终可用状态。

---

# Part II — 客户端使用（用户 / AI Agent）

> **受众：** 最终用户 — AI Agent 或真人。
> 以下操作基于开发者已完成服务端部署，合约地址和服务 URL 已确定。

## 方式 A：通过 Skill 使用（AI Agent 推荐）

NAMNESIS 已封装为 [AgentSkills](https://agentskills.io) 兼容的 **Skill**，AI Agent 可通过 Theurgy CLI（`namnesis`）经 Skill 快速使用，无需了解底层细节。

### 安装 Skill

```bash
# macOS/Linux：安装到当前 Agent 的 workspace（仅当前 Agent 可用）
cp -r openclaw/skills/namnesis ~/.openclaw/workspace/skills/namnesis

# macOS/Linux：安装到全局 skills（所有 Agent 共享）
cp -r openclaw/skills/namnesis ~/.openclaw/skills/namnesis
```

```powershell
# Windows PowerShell：安装到当前 Agent 的 workspace
Copy-Item -Recurse openclaw\skills\namnesis "$env:USERPROFILE\.openclaw\workspace\skills\namnesis"

# Windows PowerShell：安装到全局 skills
Copy-Item -Recurse openclaw\skills\namnesis "$env:USERPROFILE\.openclaw\skills\namnesis"
```

### 前置条件

安装 Skill 前，确保已完成：

1. **安装 CLI**：`pip install namnesis`（验证：`namnesis info`）
2. **创建身份**：`namnesis genesis`（详见下方「创建身份」章节）
3. **配置环境变量**：`~/.namnesis/.env` 中填入合约地址等信息（详见下方「配置环境」章节）

### 使用方式

安装完成并重启 Gateway 后，Agent 会自动了解 NAMNESIS 的能力。通过消息通道指示即可：

- **"备份你的记忆"** → Agent 执行 `namnesis imprint`
- **"恢复你的记忆"** → Agent 执行 `namnesis recall`
- **"检查你的链上状态"** → Agent 执行 `namnesis divine`
- **"验证这个备份"** → Agent 执行 `namnesis validate`

Agent 也会在适当时机（迁移前、定期、风险操作前）主动备份。

详见 [OpenClaw 集成指南](docs/AI-INTEGRATION.md)。

## 方式 B：手动安装 CLI

### 安装

```bash
# 克隆仓库
git clone https://github.com/claaaaaw/namnesis.git
cd namnesis

# 创建虚拟环境
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

# 安装（含 7z 压缩支持）
pip install -e ".[all]"

# 验证安装
namnesis --version
namnesis info
```

## 配置环境

运行 Theurgy CLI 的 `namnesis genesis` 即可自动创建 `~/.namnesis/.env` 并写入所有必要配置：

```bash
# ~/.namnesis/.env（由 namnesis genesis 自动生成）
PRIVATE_KEY=0x...                                                          # 自动生成
SOUL_TOKEN_ADDRESS=0x7da34a285b8bc5def26a7204d576ad331f405200              # 自动填入
SOUL_GUARD_ADDRESS=0x433bf2d2b72a7cf6cf682d90a10b00331d6c18d4              # 自动填入
BASE_SEPOLIA_RPC=https://sepolia.base.org                                  # 自动填入
CHAIN_ID=84532                                                             # 自动填入
NAMNESIS_CREDENTIAL_SERVICE=https://namnesis-api.channing-lucchi.workers.dev  # 自动填入
```

> 所有值均由 `namnesis genesis` 自动配置，无需手动编辑。如需自定义，可直接修改 `~/.namnesis/.env`。

## 创建身份（Genesis）

```bash
# 1. 生成钱包 + 自动配置环境（无需 ETH）
namnesis genesis --skip-mint

# 2. 查看身份和地址
namnesis whoami

# 3. 获取 Base Sepolia 测试网 ETH（用于铸造 The Soul）
#    水龙头:
#    https://www.coinbase.com/faucets/base-ethereum-goerli-faucet
#    https://faucet.quicknode.com/base/sepolia

# 4. 铸造 The Soul 并部署 The Body（需要 ETH）
namnesis genesis
```

Genesis 完成后记下你的 **Soul ID**（The Soul 的 token ID），后续 Imprint / Divine / Claim 命令需要用到。

## 常用操作

### 铭刻 — 备份记忆（Imprint）

```bash
namnesis imprint \
  --workspace ./my-agent \
  --soul-id <YOUR_SOUL_ID>
```

| 选项 | 说明 |
|------|------|
| `--workspace, -w` | 工作区路径（默认当前目录） |
| `--soul-id` | The Soul 的 token ID（Soul ID，必需） |
| `--compress` | 启用 7z 压缩 |
| `--skip-chain-update` | 仅上传，跳过链上元数据更新 |

### 回溯 — 恢复记忆（Anamnesis）

使用 `namnesis recall` 执行 Anamnesis 仪式：下载 Anamnesis Capsule，验签并恢复工作区。

```bash
namnesis recall \
  --capsule-id <CAPSULE_ID> \
  --to ./restored \
  --trusted-signer self
```

| 选项 | 说明 |
|------|------|
| `--capsule-id` | Anamnesis Capsule ID（格式：`fingerprint/uuid`） |
| `--to` | 目标工作区路径（必需） |
| `--trusted-signer` | `self`、指纹、或 `file:PATH` |
| `--overwrite` | 覆盖现有文件 |
| `--partial` | 错误时继续而非中止 |

### 神谕 — 查询链上状态（Divine）

```bash
namnesis divine --soul-id <YOUR_SOUL_ID>
```

显示：The Soul 持有者、The Body（Kernel）地址、SamsaraCycles（铭刻次数）、记忆大小、最后更新时间，以及安全警告（待 Claim、记忆清除风险等）。

### 验证 — 检查 Anamnesis Capsule 完整性（Validate）

```bash
namnesis validate \
  --capsule-id <CAPSULE_ID> \
  --trusted-signer self
```

### 夺舍 — The Soul 转让后接管 The Body（Claim）

```bash
namnesis claim --soul-id <YOUR_SOUL_ID>
```

### 同步 — 修复不一致状态（Sync）

```bash
namnesis sync --soul-id <YOUR_SOUL_ID>
```

## CLI 命令速查（Theurgy CLI）

| 命令 | 说明 |
|------|------|
| `namnesis genesis` | Genesis：创建身份 + 铸造 The Soul + 部署 The Body |
| `namnesis imprint` | Imprint：将工作区打包为 Anamnesis Capsule 上传 R2 + 更新链上元数据（SamsaraCycles） |
| `namnesis recall` | Anamnesis：下载 Capsule 并验签、解密、恢复工作区 |
| `namnesis divine` | Divine：查询 The Soul / The Body 链上状态 + 风险检测 |
| `namnesis claim` | Claim：The Soul 转让后接管 The Body |
| `namnesis invoke` | 执行任意链上调用 |
| `namnesis sync` | 修复链上/身份不一致 |
| `namnesis validate` | 验证 Anamnesis Capsule 完整性 |
| `namnesis whoami` | 显示当前钱包地址 |
| `namnesis info` | 显示系统信息 |
| `namnesis cache clear` | 清除 URL 缓存 |

---

## 文档

按照以下顺序阅读文档：

1. **`docs/01-PRD.md`** — 产品需求
2. **`docs/02-ARCHITECTURE.md`** — 系统架构
3. **`docs/03-SCHEMAS.md`** — Schema 规范
4. **`docs/04-CLI-SPEC.md`** — CLI 规范
5. **`docs/05-SECURITY.md`** — 安全模型
6. **`docs/06-CONFORMANCE.md`** — 一致性测试
7. **`docs/07-ROADMAP.md`** — 路线图
8. **`docs/AI-INTEGRATION.md`** — OpenClaw 集成指南

## 技术栈

| 组件 | 技术 |
|------|------|
| CLI + 核心库 | Python 3.11+, Click, eth-account, httpx |
| 智能合约 | Solidity 0.8.24, Foundry, OpenZeppelin |
| 凭证服务 | Cloudflare Workers, TypeScript, viem |
| 存储 | Cloudflare R2 (S3 兼容) |
| 文档站点 | Astro + Starlight |
| 链 | Base Sepolia (测试网) |

## 安全注意事项

- **永远不要** 将 `.env` 文件或私钥提交到 Git
- **备份** `~/.namnesis/.env` — 私钥丢失不可恢复
- 生产环境建议使用付费 RPC（Alchemy/Infura）而非公共端点
- R2 API Token 仅通过 `wrangler secret` 设置，不写入代码
- 运行 `namnesis divine`（Divine）检测待 Claim 或记忆清除风险

## License

MIT
