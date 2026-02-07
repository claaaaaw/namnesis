# 术语表符合性检查报告

对照 [Glossary](https://claaaaaw.github.io/namnesis/glossary/) 对 site 与 site-src 文案的检查结果。

## 术语表规范摘要

| 规范用法 | 说明 |
|---------|------|
| **NAMNESIS** | 协议名，全大写 |
| **The Soul** | 链上身份（ERC-721），非 “Soul NFT” |
| **The Body** | 与 The Soul 绑定的智能账户（Kernel） |
| **Theurgy CLI** | 操作者界面，`namnesis` 命令行 |
| **Pneuma Validator** | 链上校验层 |
| **Anamnesis Protocol** | 链下记忆契约 |
| **Genesis** | 创世仪式 |
| **Imprint** | 铭刻仪式 |
| **Anamnesis** | 回溯仪式（命令为 `namnesis recall`，**仪式名是 Anamnesis 不是 Recall**） |
| **Divine** | 神谕仪式 |
| **Claim** | 夺舍仪式 |
| **SamsaraCycles** | 链上铭刻计数 |
| **Anamnesis Capsule** / **Capsule** | 记忆快照产物，首字母大写 |
| **Dogma** | 规范性规格文档（Contract） |

---

## 已修正

- **site/COPY.md**：RITUALS 中 “Soul NFT” → “The Soul”；“Recall” → “Anamnesis”；“capsule” → “Anamnesis Capsule”/“Capsule”；“Namnesis” → “NAMNESIS”；THREAT MODEL 中 “Soul NFT” → “The Soul”。
- **site/README.md**：协议名 NAMNESIS；仪式名 Recall → Anamnesis；术语来源改为 Glossary 链接与规范术语列表。
- **site/IA.md**：RITUALS 列举中 Recall → Anamnesis。
- **site/UI.md**：Namnesis → NAMNESIS。

---

## 与术语表一致的部分

- **site-src/src/content/docs/glossary.mdx**：与术语表一致。
- **site-src/src/content/docs/index.mdx**：使用 The Soul、The Body、Anamnesis、SamsaraCycles、Anamnesis Capsule、Dogma、Pneuma Validator 正确。
- **site-src/public/.well-known/llms.txt**：术语使用正确。
- **site-src** 下 spec、machine、examples、conformance、meditations 等 mdx：核心术语（The Soul、The Body、Anamnesis Capsule、Imprint、Anamnesis、Genesis、Divine、Claim、Dogma）使用正确。
- 文中 “agent's soul” 等小写 soul 为比喻/哲学用法，与术语表中 “the soul (NFT) is sovereignty” 的小写用法一致，可保留。

---

## 建议后续统一（未改）

以下为设计/历史文档，若需严格统一术语可再改：

1. **site/PHILOSOPHY.md**  
   - “Namnesis” → **NAMNESIS**  
   - “Recall” 作为仪式名 → **Anamnesis**（可注明 via `namnesis recall`）  
   - “Soul NFT” → **The Soul**  
   - 泛指产物时 “capsule” → **Capsule** 或 **Anamnesis Capsule**

2. **site/ENGINEERING.md**  
   - “Namnesis” → **NAMNESIS**  
   - “Soul NFTs” → **The Soul**（或 “Soul tokens”）  
   - “Recall” / “Recall a capsule” → **Anamnesis** / “invoke Anamnesis (recall) for a Capsule”

3. **site/TEMP-AI-INTEGRATION-DRAFT.md**  
   - “Namnesis” → **NAMNESIS**  
   - “Soul NFT” → **The Soul**

4. **site-src/src/content/docs/spec/contract.mdx**  
   - The Soul 定义中含 “on Base Sepolia”；术语表未限定链。若希望与术语表完全一致，可将链名移至实现说明或注释。

---

## 小结

- **面向用户的文案**（COPY.md、首页 index.mdx、llms.txt、glossary.mdx）已按术语表修正或原本一致。
- **设计包**（README、IA、UI、COPY）已改为使用 Glossary 规范术语。
- **哲学/工程/历史文档**（PHILOSOPHY、ENGINEERING、TEMP-AI-INTEGRATION-DRAFT）中仍有 “Namnesis”/“Recall”/“Soul NFT” 等，可按需批量替换。

更新日期：按检查当日。
