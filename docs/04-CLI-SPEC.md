# Namnesis — CLI 规范 v2.0

**受众:** AI 工程师  
**版本:** v2.0（规范性文档，命令行为和退出码必须保持稳定）

## 0. 目标

定义安全默认、面向实现、可测试的 CLI 接口。

## 1. 命令概览

```
namnesis genesis          创建主权智能体（身份 + Soul NFT）
namnesis imprint          加密并上传记忆
namnesis recall           下载并解密记忆
namnesis divine           查询链上状态
namnesis claim            NFT 转让后接管 Kernel
namnesis invoke           执行链上合约调用
namnesis sync             修复身份/链上不一致状态
namnesis whoami           查看当前身份
namnesis info             查看系统信息
namnesis validate         验证 Capsule 完整性
namnesis cache clear|info 管理 URL 缓存
```

## 2. 命令详细规范

### 2.1 `namnesis genesis`

创建新的主权智能体。生成统一身份（Ed25519 + ECDSA），可选铸造 Soul NFT。

```
namnesis genesis [--rpc-url URL] [--skip-mint]
```

| 选项 | 默认值 | 说明 |
|------|--------|------|
| `--rpc-url` | `https://sepolia.base.org` | RPC 端点（envvar: `BASE_SEPOLIA_RPC`） |
| `--skip-mint` | false | 仅生成密钥，跳过 NFT 铸造 |

**行为:**
1. 检查 `~/.namnesis/` 中是否已有密钥，已存在则加载
2. 不存在则自动生成双密钥对
3. 若未 `--skip-mint`，检查 EOA 余额并铸造 Soul NFT
4. 输出: Identity (fingerprint)、Address、铸造结果

**退出码:** 0 成功 | 1 通用错误

### 2.2 `namnesis imprint`

加密工作区文件并上传到 R2，更新链上元数据。

```
namnesis imprint --soul-id ID [-w PATH] [--passphrase SRC]
    [--credential-service URL] [--compress|--no-compress]
    [--rpc-url URL] [--skip-chain-update]
```

| 选项 | 默认值 | 说明 |
|------|--------|------|
| `--soul-id` | **必需** | Soul NFT token ID |
| `--workspace, -w` | `.` | 工作区路径 |
| `--passphrase` | `prompt` | 口令来源: `prompt` / `env:VAR` / `file:PATH` / 字面值 |
| `--credential-service` | `https://namnesis-api.channing-lucchi.workers.dev` | 凭证服务 URL |
| `--compress/--no-compress` | 不压缩 | 启用 7z 压缩 |
| `--rpc-url` | `https://sepolia.base.org` | RPC 端点 |
| `--skip-chain-update` | false | 跳过链上元数据更新 |

**行为:**
1. 加载身份密钥（Ed25519 + ECDSA）
2. 按脱敏策略过滤文件
3. 加密并上传 Capsule 到 R2
4. 调用 `SoulToken.updateMetadata()` 更新链上元数据
5. 链上更新失败时记忆仍然已上传，提示使用 `namnesis sync`

**退出码:** 0 成功 | 1 通用错误 | 2 策略违规（Forbidden 发现）

### 2.3 `namnesis recall`

从远程或本地下载 Capsule 并解密恢复。

```
namnesis recall --capsule-id ID --to PATH --trusted-signer FP
    [--passphrase SRC] [--credential-service URL]
    [--overwrite] [--partial] [--local-path PATH]
```

| 选项 | 默认值 | 说明 |
|------|--------|------|
| `--capsule-id` | **必需** | Capsule ID (`owner_fp/uuid`) |
| `--to` | **必需** | 目标工作区路径 |
| `--trusted-signer` | **必需** | 受信签名者指纹或 `file:PATH` |
| `--passphrase` | `prompt` | 口令来源 |
| `--credential-service` | `https://namnesis-api.channing-lucchi.workers.dev` | 凭证服务 URL |
| `--overwrite` | false | 覆盖现有文件 |
| `--partial` | false | 错误时继续 |
| `--local-path` | null | 本地 Capsule 路径（跳过远程） |

**退出码:** 0 成功 | 1 通用错误 | 4 签名/信任失败 | 5 完整性失败 | 6 解密失败

### 2.4 `namnesis divine`

查询链上状态并检测风险。

```
namnesis divine --soul-id ID [--rpc-url URL]
```

**输出:**
- NFT Owner / Confirmed Owner
- Kernel 地址 + 余额
- Samsara Cycles / Memory Size / Last Updated
- 安全警告: Pending Claim、Lobotomy Risk

### 2.5 `namnesis claim`

NFT 转让后接管 Kernel 控制权。

```
namnesis claim --soul-id ID [--rpc-url URL]
```

**行为:**
1. 验证调用者是 NFT 持有者
2. 检查是否需要 claim（`confirmedOwner != msg.sender`）
3. 调用 `SoulGuard.claim(soulId)`
4. ECDSA Validator owner 变更为调用者

### 2.6 `namnesis invoke`

执行通用链上合约调用。

```
namnesis invoke --contract ADDR --function NAME
    [--args JSON] [--abi-name NAME] [--value WEI] [--gas-limit N]
```

### 2.7 `namnesis sync`

修复身份和链上不一致状态。

```
namnesis sync --soul-id ID [--rpc-url URL] [--dry-run]
```

**检查项:**
1. 本地身份完整性（Ed25519 + ECDSA 均存在）
2. NFT 所有权是否匹配当前地址
3. `confirmedOwner` 是否与 NFT owner 一致
4. 自动修复: 执行 `claim()` 解决 pending claim

`--dry-run` 仅显示问题但不执行修复。

### 2.8 `namnesis whoami`

显示当前身份。

```
namnesis whoami [-k PATH]
```

**输出:**
```
Identity: <fingerprint>
Address:  <ethereum_address>
```

### 2.9 `namnesis validate`

验证 Capsule 完整性和签名。

```
namnesis validate --capsule-id ID --trusted-signer FP
    [-p PATH] [--passphrase SRC]
```

**退出码:** 0 通过 | 4 签名失败 | 5 完整性失败

### 2.10 `namnesis info`

显示系统信息。

### 2.11 `namnesis cache clear|info`

管理 presigned URL 缓存。

## 3. 退出码

| 代码 | 含义 |
|------|------|
| 0 | 成功 |
| 1 | 通用错误 |
| 2 | 策略违规（Forbidden 发现） |
| 4 | 签名/信任验证失败 |
| 5 | 完整性（哈希）验证失败 |
| 6 | 解密失败（错误口令） |

## 4. 口令来源

所有需要口令的命令统一支持 `--passphrase` 选项：

| 来源 | 格式 | 示例 |
|------|------|------|
| 交互式提示 | `prompt` | `--passphrase prompt`（默认） |
| 环境变量 | `env:VAR` | `--passphrase env:MY_PASS` |
| 文件 | `file:PATH` | `--passphrase file:~/.secret` |
| 字面值 | 任意字符串 | `--passphrase "my-secret"` |

## 5. 环境变量

| 变量 | 说明 |
|------|------|
| `BASE_SEPOLIA_RPC` | RPC 端点 URL |
| `SOUL_TOKEN_ADDRESS` | SoulToken 合约地址 |
| `SOUL_GUARD_ADDRESS` | SoulGuard 合约地址 |
| `NAMNESIS_CREDENTIAL_SERVICE` | 凭证服务 URL |
| `PRIVATE_KEY` | ECDSA 私钥 (hex)，通常从 `~/.namnesis/.env` 加载 |

## 6. 标准输出工件

| 文件 | 说明 |
|------|------|
| `capsule.manifest.json` | 签名的 capsule 清单 |
| `redaction.report.json` | 脱敏决策报告 |
| `restore.report.json` | 恢复结果报告（可选） |

## 关联文档

- 需求: `01-PRD.md`
- 架构: `02-ARCHITECTURE.md`
- Schema 规范: `03-SCHEMAS.md`
- 安全模型: `05-SECURITY.md`
