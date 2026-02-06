# Namnesis — 系统架构

**受众:** AI 工程师  
**版本:** v2.0

## 0. 设计约束

| 原则 | 说明 |
|------|------|
| **客户端优先** | 所有业务逻辑（加密/签名/验证/链上交易）在客户端执行 |
| **服务端无状态** | 凭证服务无数据库、无 KV、无持久状态 |
| **存储不可信** | E2EE 加密，远程存储可完全不可信 |
| **客户端付 Gas** | 所有链上交易（genesis/claim/updateMetadata）由客户端 EOA 直接发送 |
| **统一身份** | 用户感知一个身份，底层自动管理 Ed25519 + ECDSA 双密钥 |
| **去中心化就绪** | 架构设计便于未来迁移到 IPFS/去中心化存储 |

## 1. 系统概述

### 1.1 架构总图

```
                            用户 / AI Agent
                                  │
                    ┌─────────────┼─────────────┐
                    │             │             │
                    ▼             ▼             ▼
            ┌─────────────┐ ┌─────────┐ ┌──────────┐
            │  Namnesis   │ │  Base   │ │  Relay   │
            │  CLI        │ │ Sepolia │ │ (无状态)  │
            │             │ │  链上    │ │          │
            │ • 加密/解密  │ │         │ │ • 验签   │
            │ • 签名/验证  │ │ Soul NFT│ │ • 权限   │
            │ • 链上交易   │ │ SoulGuard│ │ • 发凭证 │
            └──────┬──────┘ └────┬────┘ └────┬─────┘
                   │             │           │
                   │             │           ▼
                   │             │    ┌──────────────┐
                   └─────────────┴───>│ R2 Storage   │
                                      │ (加密 blobs)  │
                                      └──────────────┘
```

### 1.2 高层流水线

1. **发现**: 按策略枚举候选工作区文件
2. **分类 & 脱敏**: 运行探测器，决定每个工件的操作
3. **打包**: 拆分为工件（文件），计算哈希
4. **加密**: 加密载荷，记录加密元数据
5. **上传**: 写入后端（本地目录或 R2），以密文哈希寻址
6. **Manifest**: 写入 `capsule.manifest.json`，**签名（必需）**
7. **链上**: 更新 SoulToken 元数据（cycles, size）
8. **恢复**: 获取对象，验证哈希/签名，解密，写入文件

## 2. 身份模型

### 2.1 统一身份

用户通过 `namnesis genesis` 创建身份。底层包含两套密钥，但用户只感知为"一个身份"：

| 密钥 | 用途 | 存储 | 标识 |
|------|------|------|------|
| Ed25519 | Capsule manifest 签名 + 完整性验证 | `~/.namnesis/identity.key` (PEM) | fingerprint = `sha256(public_key_bytes)` |
| ECDSA/secp256k1 | 链上交易 + Relay 认证 | `~/.namnesis/.env` (hex) | Ethereum address |

CLI 中对用户展示：
- **Identity**: Ed25519 fingerprint（64 字符 hex）
- **Address**: Ethereum 地址

### 2.2 Capsule ID

```
capsule_id = {owner_fingerprint}/{uuid}

示例: a1b2c3d4.../01925b6a-7c8d-7def-9012-345678abcdef
      ├── owner_fingerprint: 64 字符 hex (sha256 of Ed25519 public key)
      └── uuid: UUIDv7
```

### 2.3 访问控制

```json
{
  "access": {
    "owner": "ed25519:a1b2c3d4...",
    "readers": ["ed25519:e5f6g7h8..."],
    "public": false
  }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `owner` | string | 所有者指纹，唯一写权限 |
| `readers` | string[] | 授权读取者（可选） |
| `public` | boolean | 是否公开（默认 false） |

## 3. 加密设计

### 3.1 密钥层次

```
passphrase → Argon2id → Master Key (MK)
                              │
                    HKDF-SHA256 (per blob)
                              │
                    ┌─────────┴─────────┐
                    │                   │
                Data Key 1        Data Key 2  ...
```

- **MK**: 口令通过 Argon2id 派生
- **DK**: `HKDF-SHA256(MK, salt=blob.nonce, info='capsule:blob', length=32)`
- **AEAD**: XChaCha20-Poly1305（首选）或 AES-256-GCM
- Manifest 记录: 算法标识、Argon2id 参数 + salt、per-blob nonce
- **不记录任何密钥**

### 3.2 签名（已锁定）

- Ed25519 签名 manifest
- 签名字节: RFC 8785 JCS（移除 `signature` 字段后的 manifest）→ UTF-8 → 无尾换行
- 信任模型: 验证者必须固定/信任预期签名者（指纹或密钥文件）

### 3.3 推荐 Argon2id 参数

| 参数 | 默认值 |
|------|--------|
| `mem_kib` | 65536 (64 MiB) |
| `iterations` | 3 |
| `parallelism` | 1 |
| `hash_len` | 32 |

## 4. 打包策略

### 4.1 文件粒度

工件按文件粒度打包，不做分块。

### 4.2 压缩（可选）

启用 7z 压缩时，所有文件打包为单个 7z 归档后再加密。

```
扫描工作区 → 过滤排除项 → 7z 打包 → 加密签名 → 上传单 blob
```

Manifest compression 字段:
```json
{
  "compression": {
    "enabled": true,
    "algorithm": "7z",
    "level": 9,
    "original_size_bytes": 1234567,
    "compressed_size_bytes": 345678,
    "compression_ratio": 0.28
  }
}
```

## 5. 存储后端

### 5.1 后端接口

```python
put_blob(blob_id, bytes) -> ref
get_blob(blob_id) -> bytes
has_blob(blob_id) -> bool
put_document(path, bytes)      # manifest / report
get_document(path) -> bytes
```

所有后端必须提供 **写后即读一致性**。

### 5.2 本地目录后端

```
<out>/capsules/{owner_fingerprint}/{uuid}/
  ├── capsule.manifest.json
  ├── redaction.report.json
  └── blobs/
      ├── abc123def...
      └── 789xyz123...
```

写入顺序：blob → redaction report → manifest（最后写入）。

### 5.3 S3/MinIO 后端

- 前缀: `capsules/<capsule_id>/`
- 推荐开启 bucket 版本控制
- SSE 可选（已有 E2EE）

### 5.4 Presigned URL 后端（主要方式）

适用于 Cloudflare R2 等不支持 STS 的存储。

**工作流:**
```
1. 客户端签名请求 (ECDSA)
2. 凭证服务验签 + 检查 NFT 所有权 (链上只读查询)
3. 凭证服务返回 presigned URLs (1 小时有效)
4. 客户端直接使用 URL 与 R2 交互
```

**凭证服务 API:**

| 端点 | 功能 |
|------|------|
| `POST /presign` | ECDSA 验签 + 生成 R2 presigned URL |
| `GET /api/metadata/:id` | 读取链上 SoulToken 元数据 |
| `GET /health` | 健康检查 |

**访问控制:**
- Write: `owner_fp` 匹配请求者
- Read: `public=true` 或 `owner` 匹配 或 `readers[]` 包含请求者

**URL 缓存:**
- 缓存位置: `~/.namnesis/cache/`
- 提前 5 分钟刷新
- `namnesis cache clear` 清除

### 5.5 删除语义

- 本地: 尽力删除
- S3/R2: 尽力删除（依赖提供商策略）
- 系统 **不承诺** 全局删除

## 6. 链上架构

### 6.1 合约组成

| 合约 | 功能 |
|------|------|
| **SoulToken** (ERC-721) | Soul NFT + 记忆元数据 (cycles, size, lastUpdated) |
| **SoulGuard** | Soul→Kernel 映射 + 所有权夺舍 (claim) + 安全加固 |

### 6.2 SoulToken

- `mint(to)`: 任何人可铸造
- `updateMetadata(tokenId, cycles, size)`: **仅 NFT 持有者可调用**（客户端直写）
- 记录: `samsaraCycles`、`memorySize`、`lastUpdated`

### 6.3 SoulGuard

- `register(soulId, kernel)`: 创世时注册 Soul→Kernel 映射
- `claim(soulId)`: 夺舍 — NFT 新持有者获取 Kernel 控制权
  1. 检查调用者是 NFT 持有者
  2. 检查 `confirmedOwner != msg.sender`
  3. 通过 Ownable Executor 更改 ECDSA Validator owner
  4. 更新 `confirmedOwner` + `lastClaimTime`
- `isPendingClaim(soulId)`: 检测待 claim 状态
- `isInClaimWindow(soulId)`: 检测安全窗口（claim 后 1 小时内）

### 6.4 夺舍流程

```
Alice（卖家）                    Bob（买家）
    │                              │
    ├── [创世] mint Soul NFT       │
    ├── [创世] deploy Kernel       │
    ├── [创世] register(soulId)    │
    │                              │
    ├── 转让 Soul NFT 给 Bob ──────┤
    │   (isPendingClaim = true)    │
    │   (Kernel Hook 冻结高风险操作) │
    │                              │
    │                              ├── claim(soulId)
    │                              ├── Kernel owner → Bob
    │                              ├── (isPendingClaim = false)
    │                              │
```

### 6.5 Claim 安全加固

防止 NFT 转让后、claim 前旧 owner 恶意操作：

1. **confirmedOwner 追踪**: SoulGuard 记录每个 Soul 的已确认控制者
2. **Kernel Hook 冻结**: `isPendingClaim=true` 时拒绝 `uninstallModule` 等高风险操作
3. **divine 风险警告**: 检测到 pending claim 时发出醒目警告

### 6.6 Imprint 完整流程

```
CLI ──1. 加密记忆 (Ed25519 签名)──→
CLI ──2. POST /presign (ECDSA 签名)──→ Relay
Relay ──3. ownerOf(soulId) 验证──→ Chain (只读)
Relay ──4. presigned URLs──→ CLI
CLI ──5. 直传加密记忆──→ R2
CLI ──6. updateMetadata()──→ Chain (客户端付 Gas)
```

## 7. 确定性 & 可重现性

**已锁定规则:**
- 导入 **必须** 精确恢复工件字节
- `plaintext_hash` 必须验证通过
- 不要求重新导出产生相同密文/nonce/blob_id
- `created_at` 允许不同

## 8. 故障模式

- 缺失 blob → 导入失败，输出可操作报告
- 错误密钥 → 解密失败；除非 `--partial` 否则不写入部分文件
- 策略违规 → 默认失败关闭
- 链上更新失败 → 记忆已上传，`namnesis sync` 修复

## 关联文档

- 需求: `01-PRD.md`
- 规范契约: `03-SCHEMAS.md`
- CLI 规范: `04-CLI-SPEC.md`
- 安全模型: `05-SECURITY.md`
