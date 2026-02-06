# Namnesis — 一致性测试

**受众:** AI 工程师  
**版本:** v2.0（规范性文档）

## 0. 目标

定义兼容性标准，使任何实现都可通过验证确认为: 安全默认、Machine Layer 契约正确。

## 1. 测试 Fixture 约定

Fixtures 位于 `conformance/fixtures/`:
- `workspace_minimal/` — 最小工作区样本
- `workspace_with_secrets/` — 含 Forbidden 文件 + 秘密字符串
- `expected_capsule_minimal/` — 黄金标准 manifest/report

## 2. 必测项

### 2.1 往返测试（字节相同）

**给定** fixture 工作区
- 运行 `imprint`（或 export 流程）生成 Capsule
- 删除工作区
- 运行 `recall`（或 import 流程）恢复到空目录

**断言:**
- 恢复文件与原始文件字节相同（白名单工件）
- `capsule.manifest.json` 有效
- `redaction.report.json` 存在且有效
- manifest 包含 `schema_version`、`crypto.kdf_params`、`crypto.hkdf_info`

### 2.2 策略严格模式（失败关闭）

Fixture 包含:
- `.env`
- `memory/moltbook.json`
- `*_cookies.json`

**断言:**
- 导出（strict 模式）退出码 `2`
- 脱敏报告中 Forbidden 项的决策为 `exclude`
- 报告 findings 仅含类型/规则ID（无秘密子串）

### 2.3 Dry Run

**断言:**
- `--dry-run` 仅产生 `redaction.report.json`
- 不写入 blob
- 不写入 manifest
- report 包含 `capsule_id`

### 2.4 篡改检测

导出后修改一个 blob。

**断言:**
- `validate` 退出码 `5`

### 2.5 签名 + 规范化

导出后移除 `signature` 字段或修改任何签名字段。

**断言:**
- `validate` 退出码 `4`

额外验证:
- 验证器使用 **RFC 8785 JCS**（无 `signature` 字段）+ UTF-8 + 无尾换行重新计算签名字节
- 签名 **必须** 仅对这些字节验证

### 2.6 错误口令

**断言:**
- `recall` 退出码 `6`
- 除非 `--partial`，否则不写入任何文件

### 2.7 受信签名者固定

使用不受信的签名者进行 validate/recall。

**断言:**
- `validate` 退出码 `4`
- `recall` 在解密/恢复前失败

### 2.8 Manifest 一致性

**断言:**
- `artifacts[].path` 值唯一
- `blobs[].blob_id` 值唯一
- 每个 `artifacts[].blob_id` 在 `blobs[]` 中存在
- `signature.signer_fingerprint` 匹配 `sha256(public_key_bytes)`

### 2.9 脱敏报告覆盖 & 摘要一致性

**断言:**
- `decisions` 包含所有候选文件（包括排除的）
- `findings_summary` 总计匹配实际 findings 和 decisions

## 3. 兼容性定义

实现兼容条件:
- 可导出/导入工作区文件且不改变其格式
- `memory/` 作为可扩展命名空间，不硬编码文件名
- 应用严格脱敏默认，永不以明文导出秘密

## 4. 测试资源

- 黄金标准示例: `docs/examples/`（minimal / typical / redaction）
- JSON Schema: `docs/schemas/v1/`
- 建议在 CI 中运行 schema 校验 + 上述所有测试

## 关联文档

- 需求: `01-PRD.md`
- Schema 规范: `03-SCHEMAS.md`
- CLI 规范: `04-CLI-SPEC.md`
- 安全模型: `05-SECURITY.md`
