# Namnesis — 安全模型与脱敏策略

**受众:** AI 工程师 / 安全审计人员  
**版本:** v2.0

## 1. 摘要

Namnesis 假设 **远程存储不可信**，通过以下机制提供安全保障：

- **E2EE 加密** (AEAD) 保护所有导出载荷
- **密文寻址 blob** (`blob_id = sha256(ciphertext_bytes)`) 避免明文哈希关联
- **Manifest 签名** (Ed25519, 必需) 保证来源可验证、防篡改
- **严格脱敏策略** 防止默认导出秘密/PII
- **链上所有权** NFT 持有者鉴权，防止未授权操作

## 2. 资产保护

- Agent 持久状态（记忆/人格/操作手册）
- 文件中嵌入的秘密（API Key、Token、Cookie）
- 用户 PII（可能出现在日志中）
- 来源: "谁生成了这个 Capsule" + "是否被篡改"
- 链上资产: Soul NFT 所有权、Kernel 控制权

## 3. 对手模型

假设攻击者能:
- 读取远程存储的所有对象
- 修改/替换/重放旧 blob 和 manifest
- 删除对象或部分扣留
- 观察访问模式

假设攻击者不能:
- 破解现代密码学 (AEAD, Argon2id, Ed25519, ECDSA)
- 在导出时入侵本地机器

超出范围:
- 完全被入侵的客户端设备
- TEE / 远程执行证明
- 防止已解密数据被协作者复制

## 4. 安全属性

### 4.1 机密性

- 所有工件载荷 **必须** 加密 (AEAD)
- `include_plaintext` 指未脱敏字节，不是未加密存储
- Manifest / 脱敏报告 **不得** 包含秘密值
- AEAD nonce **必须** 唯一且由 CSPRNG 生成

### 4.2 完整性

- 每个 blob 通过密文哈希 (`blob_id`) 验证
- 解密后明文通过 `plaintext_hash` 验证

### 4.3 真实性 / 来源

- Manifest **必须** 签名 (Ed25519)
- 验证通过 RFC 8785 JCS 字节进行
- 验证者 **必须** 固定/信任预期签名者

### 4.4 安全默认

- 默认策略: 严格/失败关闭
- Forbidden 发现 **必须** 阻止导出（除非显式覆盖）

## 5. 密钥管理

### 5.1 密钥来源

| 密钥 | 来源 | 用途 |
|------|------|------|
| Master Key | passphrase → Argon2id | 加密 blob |
| Ed25519 | 本地生成 (genesis) | 签名 manifest |
| ECDSA | 本地生成 (genesis) | 链上交易 + Relay 认证 |

### 5.2 Argon2id 推荐参数

- `mem_kib`: 65536 (64 MiB)
- `iterations`: 3
- `parallelism`: 1
- `hash_len`: 32

实现 **必须** 在 manifest 中记录实际使用的参数和 salt。

### 5.3 恢复

- 口令丢失 → Capsule 不可恢复（预期行为）
- 私钥丢失 → 无法签名新 Capsule、无法操作链上资产
- 建议: 密码管理器 + 离线备份 `~/.namnesis/`

## 6. 常见攻击 & 缓解

| 攻击 | 缓解 |
|------|------|
| 存储读取 | E2EE |
| Blob 替换/篡改 | 密文哈希 + 签名 manifest |
| 回滚攻击 | manifest `created_at` + 链上 `samsaraCycles` |
| 元数据泄露 | 路径在 manifest 中可见（未来考虑加密） |
| 秘密渗出 | 脱敏报告中永不包含原始秘密子串 |
| NFT 所有权攻击 | SoulGuard claim 安全加固 + Kernel Hook 冻结 |

---

## 7. 脱敏策略

### 7.1 原则

- **默认失败关闭**
- **白名单制**: 仅包含已知安全路径
- **报告中永不泄露秘密**: findings 只含类型/规则ID/位置
- **确定性决策**: 相同输入 + 相同策略 → 相同决策

### 7.2 数据分级

| 等级 | 说明 | 默认操作 |
|------|------|---------|
| Public | 可存明文（罕见） | include_plaintext |
| Private | 加密后导出 | include_encrypted |
| Sensitive | 需显式开启 | exclude |
| Forbidden | 永不导出 | exclude + 阻止导出 |

### 7.3 默认白名单

- `MEMORY.md`
- `memory/**` (md/json)
- `SOUL.md`、`USER.md`、`IDENTITY.md`
- `AGENTS.md`、`TOOLS.md`、`HEARTBEAT.md`
- `projects/**/STATUS.md`

其他一切默认排除。

### 7.4 默认黑名单 (Forbidden)

- `.env`
- `**/*.pem`、`**/*id_rsa*`、`**/*private_key*`
- `**/*token*`、`**/*secret*`
- `**/*cookies*.json`、`**/*_cookies.json`
- `memory/moltbook.json`（凭据）
- 浏览器配置文件 / 会话存储 / SQLite cookie jar
- 超过大小阈值的文件

### 7.5 探测器（启发式）

| 探测器 | 检测内容 |
|--------|---------|
| API Key | `sk-`、`ghp_` 等模式 |
| JWT | JWT Token 模式 |
| 私钥块 | `-----BEGIN ... PRIVATE KEY-----` |
| Cookie/Session | `session`、`csrf`、`auth` 字段 |

输出: `rule_id`、`severity`、`locations`（行号/字节偏移）。
**永不包含匹配字符串。**

### 7.6 决策 & 操作

每个工件选择一个:
- `exclude` — Forbidden 默认
- `include_encrypted` — 白名单文件默认
- `include_redacted` — 重写内容，仅存脱敏版本
- `include_plaintext` — 不鼓励，需显式允许

### 7.7 脱敏报告

导出 **必须** 产生 `redaction.report.json`，包含:
- 策略版本
- Schema 版本 + capsule_id
- 运行的探测器 + config_hash
- 每文件决策 + 原因
- findings 摘要

覆盖规则: `decisions` **必须** 包含策略考虑的所有候选文件（包括排除的）。

### 7.8 探测器配置哈希

每个探测器条目 **必须** 包含 `config_hash`:
```
config_hash = sha256(JCS(detector_config))  // 小写 hex
```
无配置时使用空对象 `{}` 的 JCS。

### 7.9 CLI 安全护栏

- `--dry-run`: 仅产生脱敏报告
- `--strict`（默认开启）: Forbidden 发现阻止导出
- `--i-know-what-im-doing`: 包含 Forbidden 类（需配合 `--no-strict`）

## 8. 安全检查清单

- [ ] 所有载荷使用 AEAD 加密
- [ ] blob_id 从密文字节派生
- [ ] manifest 签名在恢复前验证
- [ ] 默认强制严格脱敏策略
- [ ] 脱敏报告不含秘密子串
- [ ] 一致性测试覆盖: 篡改、错误口令、Forbidden 发现
- [ ] manifest 记录 Argon2id 参数 + salt
- [ ] 链上操作验证 NFT 所有权
- [ ] claim 安全加固正常工作

## 关联文档

- 需求: `01-PRD.md`
- 架构: `02-ARCHITECTURE.md`
- Schema 规范: `03-SCHEMAS.md`
- CLI 规范: `04-CLI-SPEC.md`
- 一致性测试: `06-CONFORMANCE.md`
