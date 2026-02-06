# Namnesis — 产品需求文档 (PRD)

**受众:** AI 工程师  
**版本:** v2.0  
**状态:** 确定

## 1. 背景

AI Agent 的持久状态（记忆、人格、操作手册）散落在本地文件系统中。我们需要一个正式的、可移植的表示方式，使其可以被安全地存储、传输、版本化和恢复——并且绑定链上 NFT 所有权。

## 2. 问题

- 缺少"Agent 状态"的 **机器可读契约**
- 缺少带完整性、机密性和来源验证的 **安全导出/导入** 机制
- 缺少 **脱敏边界**，使得秘密/PII 不会被默认捕获
- 缺少 **链上身份锚点**，Agent 的所有权无法转移或验证

## 3. 目标

### 3.1 主要目标

1. **创世** — 创建统一身份 + 铸造 Soul NFT
2. **铭刻** — 加密导出工作区为 Capsule 并上传 + 更新链上元数据
3. **回溯** — 下载 Capsule 并解密恢复为工作区
4. **验证** — 提供完整性验证（哈希）和 Schema 校验
5. **端到端加密** — 远程存储可以是不可信的
6. **脱敏框架** — 机器可读的脱敏报告
7. **链上所有权** — NFT 所有权即身份权限
8. **夺舍** — NFT 转让后接管 Kernel 控制权

### 3.2 次要目标

- 支持 "热存储 + 冷备份" 模式
- 7z 压缩节省存储空间

## 4. 非目标

- 通用跨框架 Agent 可移植格式
- 自动多设备冲突解决
- 服务端搜索/索引明文
- UI 产品（仅 CLI + 库）

## 5. 用户 / 角色

- **AI 工程师**: 实现 Capsule 规范和工具链
- **运维工程师**: 在自动化中运行导出/导入，需要验证和审计能力
- **Agent 运行时**: 消费恢复的文件

## 6. 核心用户故事

1. 作为工程师，我运行 `namnesis genesis` 创建一个拥有链上身份的 Agent
2. 作为工程师，我运行 `namnesis imprint` 将 Agent 记忆加密上传
3. 作为工程师，我运行 `namnesis recall` 将记忆恢复到新环境
4. 作为安全审计人员，我可以审查什么被包含/排除及其原因（脱敏报告）
5. 作为买家，我通过 NFT 转让获得 Soul 后，运行 `namnesis claim` 接管 Kernel

## 7. 功能需求

### 7.1 Capsule 组成

支持包含的默认路径（OpenClaw 兼容）：
- `MEMORY.md`、`memory/**`（md/json）
- `SOUL.md`、`USER.md`、`IDENTITY.md`
- `AGENTS.md`、`TOOLS.md`、`HEARTBEAT.md`
- `projects/**/STATUS.md`（可选）

### 7.2 Manifest (Machine Layer)

导出产生 `capsule.manifest.json`，包含：
- `capsule_id`（`{owner_fingerprint}/{uuid}` 格式）
- `schema_version`、`spec_version`
- 工件列表（路径、类型、大小、哈希、加密引用）
- 加密参数（AEAD + Argon2id + HKDF）
- **必需的签名**（Ed25519 + RFC 8785 JCS）
- 可选的链上元数据（`soul_id`、`chain_id`）

参见 `03-SCHEMAS.md`（规范）和 `04-CLI-SPEC.md`（规范）。

### 7.3 加密 + 密钥来源

- AEAD 加密: XChaCha20-Poly1305（首选）或 AES-256-GCM
- 按工件粒度加密
- **密钥来源: passphrase → Argon2id → Master Key (MK)**
  - MK 通过 HKDF 派生 per-blob 密钥
  - Argon2id 参数 + salt 记录在 manifest 中
  - HKDF `info` 固定为 `capsule:blob`（UTF-8）

### 7.4 导入语义

- 重建目录树并精确恢复文件字节
- 默认不覆盖现有文件
- 可选写入恢复报告

### 7.5 验证

`validate` 检查：
- Schema 有效性
- 载荷哈希完整性
- 签名有效性（RFC 8785 JCS）
- 受信签名者验证
- 策略合规性

### 7.6 链上操作

- **genesis**: 铸造 Soul NFT（客户端付 Gas）
- **imprint**: 上传后更新 SoulToken.updateMetadata()
- **claim**: 调用 SoulGuard.claim() 接管 Kernel
- **divine**: 链上只读查询 + 风险检测

## 8. 脱敏策略（硬性要求）

### 8.1 威胁模型

假设远程存储是敌对的：可以读取、复制、删除、篡改数据。

### 8.2 数据分级

| 等级 | 说明 |
|------|------|
| Public | 可存明文（罕见） |
| Private | 加密后导出 |
| Sensitive | 需显式开启，加密导出 |
| Forbidden | 永不导出（除非显式覆盖） |

### 8.3 默认策略 — 严格模式

- 白名单制：仅包含已知安全的工作区路径
- 黑名单：`.env`、`*.pem`、`*id_rsa*`、`*token*`、`*cookies*.json`
- 探测器：API Key 模式、JWT、私钥块、Cookie/Session 字段
- 脱敏报告中 **永不包含** 原始敏感值

## 9. 存储后端

| 后端 | 状态 |
|------|------|
| 本地目录 | 必需 |
| S3/MinIO | 推荐 |
| Presigned URL (R2) | 主要方式 |
| IPFS | 未来扩展 |

## 10. 验收标准

- **往返测试**: 导出 → 清空 → 导入 → 文件字节相同
- **策略测试**: `.env` 和私钥被默认排除
- **篡改测试**: 修改载荷 → 验证失败
- **签名测试**: manifest 签名必须验证通过后才解密
- **链上测试**: genesis 铸造成功，imprint 更新元数据成功

## 关联文档

- 架构: `02-ARCHITECTURE.md`
- 规范契约: `03-SCHEMAS.md`
- CLI 规范: `04-CLI-SPEC.md`
- 安全模型: `05-SECURITY.md`
- 一致性测试: `06-CONFORMANCE.md`
