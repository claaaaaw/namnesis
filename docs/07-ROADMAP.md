# Namnesis — 路线图与开放问题

**受众:** AI 工程师 / 维护者  
**版本:** v2.0

## 1. 已锁定决策

以下决策为规范性要求，不再变更:

- `blob_id` 从密文字节派生 (`sha256(ciphertext_bytes)`, hex)
- Manifest 签名必需 (Ed25519) + 固定/受信签名者模型
- 签名字节: RFC 8785 JCS, manifest 移除 `signature`, UTF-8, 无尾换行
- 密钥来源: passphrase → Argon2id
- 严格默认白名单/导出策略
- 确定性: 字节级恢复（不要求稳定密文/blob_id）
- 编码约定: 哈希 hex; nonce/key/sig base64url; capsule_id UUIDv7
- 客户端付 Gas，Relay 无状态
- 统一身份（Ed25519 + ECDSA 双密钥，用户感知为一个身份）

## 2. 当前版本 (v2.0) — 已实现

- 统一 CLI（genesis / imprint / recall / divine / claim / invoke / sync）
- 双密钥身份系统（对用户隐藏）
- Soul NFT 铸造 + 链上元数据更新
- SoulGuard claim 安全加固
- R2 presigned URL 后端
- 7z 压缩支持
- 一致性测试框架

## 3. 近期扩展 (v2.1)

- [ ] 从 mint 事件日志自动解析 tokenId（genesis 流程优化）
- [ ] `--trusted-signer self` 快捷方式（自动使用自身指纹）
- [ ] `imprint` 支持 `--local` 模式（不上传远程，仅本地导出）
- [ ] Kernel 部署集成到 genesis 流程
- [ ] Paymaster 配置（可选免 Gas 操作）
- [ ] 链上 lineage: manifest 中增加 `parents[]` 字段

## 4. 中期规划 (v2.2+)

- [ ] 可选分块打包（大文件/跨快照去重）
- [ ] 合并语义（双 parent merge + 冲突标记）
- [ ] 多 Agent capsule 图（capsule 间引用）
- [ ] 可选路径加密（减少元数据泄露）
- [ ] 向量索引封装（加密存储）

## 5. 长期方向 (v3)

- IPFS 冷备份（仅加密 blob + 签名 manifest 指针）
- 更强的规范化规则 / 新 manifest 模型 / 新加密信封
- 硬件钱包支持
- 多链部署

## 6. 开放问题

| # | 问题 | 状态 |
|---|------|------|
| 1 | **路径隐私**: 是否加密路径/文件名以减少元数据泄露？ | 未定 |
| 2 | **未加密允许**: 未来版本是否允许未加密工件？ | 未定 |
| 3 | **确定性导出模式**: 是否增加可选的确定性模式（稳定密文/nonce/blob_id）？ | 推迟 |
| 4 | **PII 检测**: 是否增加更强的 PII 探测器（姓名/地址）？如何管理误报？ | 未定 |
| 5 | **密钥恢复 UX**: 恢复短语 / 密钥托管选项（不违反安全边界） | 未定 |
| 6 | **索引**: 是否封装向量索引（加密）还是总是本地重建？ | 未定 |
| 7 | **ECDSA 统一**: 未来是否完全统一为 ECDSA？（需要新的 capsule 签名方案） | v3 讨论 |

## 关联文档

- 需求: `01-PRD.md`
- 架构: `02-ARCHITECTURE.md`
- 安全模型: `05-SECURITY.md`
