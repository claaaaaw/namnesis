# Namnesis — 主权智能体协议

Namnesis: 链上主权 AI Agent 身份与记忆协议 — 加密、签名、上链、复生。

## 项目概述

Namnesis 是一个 **AI-first** 的链上主权智能体协议，将 AI Agent 的身份与记忆绑定为链上 NFT (Soul)，提供加密存储、签名验证和所有权转移（夺舍/Resurrection）能力。

核心能力：
- **身份创建** (`genesis`): 生成统一身份 + 铸造 Soul NFT
- **记忆铭刻** (`imprint`): 加密 + 上传记忆到 R2 + 链上元数据更新
- **记忆回溯** (`recall`): 下载 + 验签 + 解密恢复
- **夺舍转移** (`claim`): NFT 转让后接管 Kernel 控制权
- **链上占卜** (`divine`): 查询链上状态 + 风险检测
- **状态同步** (`sync`): 修复身份/链上不一致状态

## 技术栈

| 层 | 技术 |
|----|------|
| CLI | Python 3.11+ / Click |
| 加密 | Argon2id + XChaCha20-Poly1305 / AES-256-GCM |
| 签名 | Ed25519 (capsule) + ECDSA/secp256k1 (链上) |
| 链上 | Base Sepolia / ERC-721 / ERC-4337 |
| 存储 | Cloudflare R2 (presigned URL) |
| 凭证 | Cloudflare Workers (无状态) |
| 合约 | Foundry / Solidity 0.8.20 |

## 文档阅读顺序

| # | 文档 | 内容 |
|---|------|------|
| 1 | **01-PRD.md** | 产品概述、需求、用户故事 |
| 2 | **02-ARCHITECTURE.md** | 系统架构、双密钥身份、存储后端、链上设计 |
| 3 | **03-SCHEMAS.md** | Machine Layer 规范契约（JSON Schema） |
| 4 | **04-CLI-SPEC.md** | CLI 命令规范、选项、退出码 |
| 5 | **05-SECURITY.md** | 安全模型、威胁分析、脱敏策略 |
| 6 | **06-CONFORMANCE.md** | 一致性测试要求 |
| 7 | **07-ROADMAP.md** | 路线图、开放问题 |

## 规范资源

- JSON Schemas: `docs/schemas/v1/`
- 示例 Capsule: `docs/examples/`
- 一致性测试: `conformance/`

## 快速开始

```bash
# 安装
pip install -e .

# 创建身份 + 铸造 Soul NFT
namnesis genesis

# 仅创建身份（离线测试）
namnesis genesis --skip-mint

# 查看身份
namnesis whoami

# 加密并上传记忆
namnesis imprint --workspace ./my-agent --soul-id 0

# 下载并解密记忆
namnesis recall --capsule-id <ID> --to ./restored --trusted-signer <FINGERPRINT>

# 查看链上状态
namnesis divine --soul-id 0

# 修复不一致状态
namnesis sync --soul-id 0
```

## 核心设计决策（已锁定）

1. **密文寻址 blob**: `blob_id = sha256(ciphertext_bytes)`
2. **Manifest 签名必需**: Ed25519 + RFC 8785 JCS 规范化
3. **口令派生密钥**: passphrase → Argon2id → Master Key
4. **严格脱敏策略**: 白名单制，默认拒绝
5. **字节级恢复**: 导入必须精确恢复文件内容
6. **客户端支付 Gas**: 所有链上交易由客户端直接发送
7. **统一身份**: 用户感知一个身份，底层自动管理双密钥
