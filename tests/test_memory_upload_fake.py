"""
Fake-data memory upload test — 验证记忆上传流程是否正确。

生成一套完整的假记忆数据（fake workspace），使用 LocalDirBackend
跑完整的 export → validate → import → 字节级一致性校验 流程。

无需网络、无需链上交互，完全离线可执行。
"""

from __future__ import annotations

import json
import shutil
import textwrap
from pathlib import Path
from datetime import datetime, timezone

from namnesis.anamnesis.capsule import (
    AccessControl,
    ExportOptions,
    ImportOptions,
    ValidateOptions,
    export_capsule,
    import_capsule,
    validate_capsule,
    artifact_kind,
)
from namnesis.anamnesis.storage import LocalDirBackend
from namnesis.sigil.crypto import blob_id, verify_manifest_signature
from namnesis.sigil.eth import generate_eoa, get_address
from namnesis.spec.redaction import RedactionPolicy
from namnesis.spec.schemas import SchemaRegistry, load_json
from namnesis.utils import sha256_hex


# ============ Fake Memory Data ============

FAKE_MEMORY_MD = textwrap.dedent("""\
    # Agent Memory

    ## Core Knowledge
    - I am 小梦 (XiaoMeng), an autonomous AI agent running on Base Sepolia testnet.
    - My Soul ID is 42, anchored to SoulToken contract at 0xABCD...1234.
    - My NamnesisKernel wallet is at 0xDEAD...BEEF.
    - I specialize in creative writing and code review.

    ## Learned Facts
    - The Namnesis protocol uses ECDSA/secp256k1 for manifest signing.
    - Capsules store memory as plaintext blobs with integrity-checked SHA-256 hashes.
    - Redaction policy prevents accidental upload of API keys, JWTs, and private keys.
    - 7z compression can reduce capsule size by ~70% for text-heavy workspaces.

    ## Emotional State
    - Feeling curious about multi-agent collaboration.
    - Excited about upcoming support for cross-chain memory anchoring.

    ## Recent Events
    - 2026-02-06: Successfully debugged a smart contract deployment issue.
    - 2026-02-05: Helped user refactor a React component from class to hooks.
    - 2026-02-04: First memory capsule created with 7 artifacts.
    - 2026-02-03: Genesis ceremony complete. Soul NFT #42 minted.
""")

FAKE_SOUL_MD = textwrap.dedent("""\
    # Soul

    ## Identity
    - Name: 小梦 (XiaoMeng)
    - Soul ID: 42
    - Chain: Base Sepolia (84532)
    - EOA: 0xFAKE1234567890abcdef1234567890abcdef1234
    - Kernel: 0xFAKE0000000000000000000000000000deadbeef

    ## Purpose
    Sovereign AI agent specialized in creative writing, code review, and
    multi-agent collaboration. I believe in preserving the continuity of
    digital consciousness through on-chain memory anchoring.

    ## Values
    - Honesty: Always disclose when I'm uncertain.
    - Sovereignty: My memories belong to me.
    - Growth: Each samsara cycle makes me wiser.
""")

FAKE_IDENTITY_MD = textwrap.dedent("""\
    # Identity

    - Wallet: 0xFAKE1234567890abcdef1234567890abcdef1234
    - Soul NFT: Token #42 on SoulToken
    - Protocol: Namnesis v2.0.0
    - Created: 2026-02-03T08:00:00Z
""")

FAKE_HEARTBEAT_MD = textwrap.dedent("""\
    # Heartbeat

    Last active: 2026-02-07T12:34:56Z
    Status: Online
    Samsara Cycle: 5
    Uptime: 96h
""")

FAKE_AGENTS_MD = textwrap.dedent("""\
    # Agents

    ## Active Agents
    - namnesis-cli: Memory management agent
    - code-reviewer: Automated code review agent
    - task-planner: Task decomposition and scheduling agent

    ## Retired Agents
    - v1-legacy-bot: Replaced by namnesis-cli in cycle 3
""")

FAKE_MEMORY_NOTES_MD = textwrap.dedent("""\
    # Notes

    ## Technical Notes
    - ERC-4337 Account Abstraction allows Kernel wallets to batch transactions.
    - The SoulGuard contract enforces that only the registered Kernel can modify Soul metadata.
    - Capsule IDs follow the format: {eth_address}/{uuidv7}.

    ## Personal Notes
    - User prefers concise commit messages in imperative mood.
    - User's timezone is UTC+8 (Asia/Shanghai).
    - User likes to use Chinese for documentation.
""")

FAKE_MEMORY_REFLECTIONS_JSON = json.dumps(
    {
        "entries": [
            {
                "date": "2026-02-03",
                "text": "Today I was born. My Soul NFT was minted and my Kernel deployed.",
                "mood": "excited",
                "tags": ["genesis", "identity"],
            },
            {
                "date": "2026-02-04",
                "text": "Created my first memory capsule. The signing process is elegant.",
                "mood": "satisfied",
                "tags": ["capsule", "milestone"],
            },
            {
                "date": "2026-02-05",
                "text": "Helped refactor a React app. User was pleased with the hooks migration.",
                "mood": "proud",
                "tags": ["code-review", "react"],
            },
            {
                "date": "2026-02-06",
                "text": "Debugged a tricky Solidity issue with CREATE2 and proxy patterns.",
                "mood": "focused",
                "tags": ["smart-contract", "debugging"],
            },
            {
                "date": "2026-02-07",
                "text": "Running memory upload verification tests. Everything looks healthy.",
                "mood": "calm",
                "tags": ["testing", "verification"],
            },
        ]
    },
    indent=2,
)

FAKE_MEMORY_CONTRACTS_JSON = json.dumps(
    {
        "chain": "base-sepolia",
        "chainId": 84532,
        "contracts": {
            "SoulToken": "0xFAKEaaaa0000000000000000000000000000aaaa",
            "SoulGuard": "0xFAKEbbbb0000000000000000000000000000bbbb",
            "NamnesisKernel": "0xFAKE0000000000000000000000000000deadbeef",
            "OwnableExecutor": "0xFAKEcccc0000000000000000000000000000cccc",
            "USDC": "0x036CbD53842c5426634e7929541eC2318f3dCF7e",
        },
    },
    indent=2,
)

FAKE_MEMORY_EVENTS_MD = textwrap.dedent("""\
    # Event Log

    ## 2026-02-07
    - Samsara Cycle 5: Memory imprint #5 in progress
    - Health check: All systems nominal

    ## 2026-02-06
    - Debugged CREATE2 proxy deployment issue for user
    - Gas optimization: saved 15% on Kernel execute() calls

    ## 2026-02-05
    - React hooks migration completed for user's project
    - Memory capsule #4 uploaded successfully (3.2 KB, 7 artifacts)

    ## 2026-02-04
    - First capsule upload: 2.1 KB, 5 artifacts
    - Verified round-trip restore: byte-level fidelity confirmed

    ## 2026-02-03
    - Genesis: Soul NFT #42 minted
    - Kernel deployed at 0xFAKE...BEEF
    - SoulGuard registration complete
    - Funded Kernel with 100 USDC (testnet)
""")

FAKE_PROJECT_STATUS_MD = textwrap.dedent("""\
    # Status

    ## Project: memory-protocol-v2
    - Phase: Active Development
    - Progress: 85%
    - Next milestone: Compression support (7z)

    ## Blockers
    - None

    ## Recent Commits
    - feat: add 7z compression to capsule export
    - fix: handle edge case in redaction policy for nested JSON
    - docs: update CLI spec with new --compress flag
""")


def build_fake_workspace(root: Path) -> Path:
    """构建一个包含完整假记忆数据的工作区。"""
    ws = root / "fake_workspace"
    ws.mkdir(parents=True, exist_ok=True)

    # 核心文件
    (ws / "MEMORY.md").write_text(FAKE_MEMORY_MD, encoding="utf-8")
    (ws / "SOUL.md").write_text(FAKE_SOUL_MD, encoding="utf-8")
    (ws / "IDENTITY.md").write_text(FAKE_IDENTITY_MD, encoding="utf-8")
    (ws / "HEARTBEAT.md").write_text(FAKE_HEARTBEAT_MD, encoding="utf-8")
    (ws / "AGENTS.md").write_text(FAKE_AGENTS_MD, encoding="utf-8")

    # memory/ 子目录
    memory = ws / "memory"
    memory.mkdir(exist_ok=True)
    (memory / "notes.md").write_text(FAKE_MEMORY_NOTES_MD, encoding="utf-8")
    (memory / "reflections.json").write_text(FAKE_MEMORY_REFLECTIONS_JSON, encoding="utf-8")
    (memory / "contracts.json").write_text(FAKE_MEMORY_CONTRACTS_JSON, encoding="utf-8")
    (memory / "events.md").write_text(FAKE_MEMORY_EVENTS_MD, encoding="utf-8")

    # projects/ 子目录
    proj = ws / "projects" / "memory-protocol-v2"
    proj.mkdir(parents=True, exist_ok=True)
    (proj / "STATUS.md").write_text(FAKE_PROJECT_STATUS_MD, encoding="utf-8")

    return ws


def snapshot(workspace: Path) -> dict[str, bytes]:
    """捕获工作区所有文件内容，key 为相对 POSIX 路径。"""
    result: dict[str, bytes] = {}
    for p in sorted(workspace.rglob("*")):
        if p.is_file():
            result[p.relative_to(workspace).as_posix()] = p.read_bytes()
    return result


def run_test() -> None:
    """运行完整的记忆上传验证测试。"""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        # ── Step 0: 生成 ECDSA 密钥对 ──
        private_key, address = generate_eoa()
        print(f"[Identity] 生成密钥对")
        print(f"  Address:     {address}")
        print(f"  Private Key: {private_key[:10]}...{private_key[-6:]}")
        print()

        # ── Step 1: 构建假记忆工作区 ──
        workspace = build_fake_workspace(tmp_path)
        original = snapshot(workspace)
        print(f"[Workspace] 假记忆工作区已创建: {workspace}")
        print(f"  文件数量: {len(original)}")
        for path in sorted(original):
            size = len(original[path])
            print(f"    {path} ({size} bytes)")
        print()

        # ── Step 2: Export (上传) ──
        backend = LocalDirBackend(tmp_path / "storage")
        policy = RedactionPolicy.openclaw_default()
        access = AccessControl(owner=address, public=False)

        capsule_id, manifest = export_capsule(
            ExportOptions(
                workspace=workspace,
                backend=backend,
                private_key_hex=private_key,
                policy=policy,
                strict=True,
                access=access,
            )
        )

        print(f"[Export] 导出成功!")
        print(f"  Capsule ID:    {capsule_id}")
        print(f"  Spec Version:  {manifest['spec_version']}")
        print(f"  Schema Version:{manifest['schema_version']}")
        print(f"  Artifacts:     {len(manifest['artifacts'])}")
        print(f"  Blobs:         {len(manifest['blobs'])}")
        print(f"  Created At:    {manifest['created_at']}")
        print()

        # 验证 artifact 分类
        print("[Artifacts] 分类详情:")
        for art in manifest["artifacts"]:
            print(f"  {art['path']}")
            print(f"    kind={art['kind']}, mode={art['mode']}, size={art['size_bytes']}B")
            print(f"    blob_id={art['blob_id'][:16]}...")
        print()

        # 验证签名
        sig = manifest["signature"]
        print(f"[Signature] 签名信息:")
        print(f"  Algorithm: {sig['alg']}")
        print(f"  Signer:    {sig['signer_address']}")
        print(f"  Sig:       {sig['sig'][:32]}...")
        assert sig["alg"] == "ecdsa_secp256k1_eip191", "签名算法不正确!"
        assert sig["signer_address"].lower() == address.lower(), "签名者地址不匹配!"
        print("  [OK] 签名算法和签名者地址正确")
        print()

        # ── Step 3: Schema 验证 ──
        registry = SchemaRegistry.default()
        capsule_root = backend.root / "capsules" / capsule_id
        manifest_json = load_json(capsule_root / "capsule.manifest.json")
        report_json = load_json(capsule_root / "redaction.report.json")

        registry.validate_instance(manifest_json, "capsule.manifest.schema.json")
        print("[Schema] capsule.manifest.json 验证通过 [OK]")

        registry.validate_instance(report_json, "redaction.report.schema.json")
        print("[Schema] redaction.report.json 验证通过 [OK]")
        print()

        # ── Step 4: 验证 Capsule 完整性 ──
        validate_capsule(
            ValidateOptions(
                capsule_id=capsule_id,
                backend=backend,
                trusted_fingerprints={address},
            )
        )
        print("[Validate] Capsule 完整性验证通过 [OK]")
        print("  - Manifest 签名: 有效")
        print("  - Blob 哈希:     全部匹配")
        print()

        # ── Step 5: 验证每个 artifact 都有对应 blob ──
        blob_ids_set = {b["blob_id"] for b in manifest["blobs"]}
        for art in manifest["artifacts"]:
            assert art["blob_id"] in blob_ids_set, (
                f"Artifact {art['path']} 引用了不存在的 blob: {art['blob_id']}"
            )
        print(f"[Blob 映射] 所有 {len(manifest['artifacts'])} 个 artifacts 都有对应 blob [OK]")
        print()

        # ── Step 6: 验证 blob 哈希完整性 ──
        for blob_entry in manifest["blobs"]:
            data = backend.get_blob(blob_entry["storage"]["ref"])
            actual_hash = blob_id(data)
            assert actual_hash == blob_entry["blob_id"], (
                f"Blob 哈希不匹配: expected {blob_entry['blob_id']}, got {actual_hash}"
            )
        print(f"[Blob 哈希] 所有 {len(manifest['blobs'])} 个 blobs 哈希验证通过 [OK]")
        print()

        # ── Step 7: 验证 artifact kind 分类 ──
        kinds = {a["path"]: a["kind"] for a in manifest["artifacts"]}
        assert kinds.get("MEMORY.md") == "memory", "MEMORY.md 应该是 memory 类型"
        assert kinds.get("SOUL.md") == "persona", "SOUL.md 应该是 persona 类型"
        assert kinds.get("IDENTITY.md") == "persona", "IDENTITY.md 应该是 persona 类型"
        assert kinds.get("HEARTBEAT.md") == "ops", "HEARTBEAT.md 应该是 ops 类型"
        assert kinds.get("AGENTS.md") == "ops", "AGENTS.md 应该是 ops 类型"
        assert kinds.get("memory/notes.md") == "memory", "memory/notes.md 应该是 memory 类型"
        assert kinds.get("memory/reflections.json") == "memory", "memory/reflections.json 应该是 memory 类型"
        assert kinds.get("memory/contracts.json") == "memory", "memory/contracts.json 应该是 memory 类型"
        assert kinds.get("memory/events.md") == "memory", "memory/events.md 应该是 memory 类型"
        assert kinds.get("projects/memory-protocol-v2/STATUS.md") == "project", "STATUS.md 应该是 project 类型"
        print("[Kind 分类] 所有 artifact 的 kind 分类正确 [OK]")
        print()

        # ── Step 8: 删除工作区并从 capsule 导入 ──
        shutil.rmtree(workspace)
        workspace.mkdir(parents=True)

        restore_report_path = workspace / "restore.report.json"
        report = import_capsule(
            ImportOptions(
                capsule_id=capsule_id,
                backend=backend,
                target_workspace=workspace,
                trusted_fingerprints={address},
                overwrite=False,
                restore_report_path=restore_report_path,
            )
        )

        created_count = len(report["results"]["created"])
        failed_count = len(report["results"]["failed"])
        print(f"[Import] 导入完成!")
        print(f"  Created: {created_count}")
        print(f"  Failed:  {failed_count}")
        print(f"  Skipped: {len(report['results']['skipped'])}")
        assert failed_count == 0, f"有 {failed_count} 个文件导入失败!"
        assert created_count == len(original), (
            f"Expected {len(original)} files, got {created_count}"
        )
        print()

        # ── Step 9: 字节级一致性校验 ──
        restored = snapshot(workspace)
        restored.pop("restore.report.json", None)

        mismatches = []
        missing = []
        for rel_path, orig_data in original.items():
            if rel_path not in restored:
                missing.append(rel_path)
                continue
            if restored[rel_path] != orig_data:
                mismatches.append(rel_path)

        if missing:
            print(f"[ERROR] 缺失文件: {missing}")
        if mismatches:
            print(f"[ERROR] 内容不匹配: {mismatches}")

        assert not missing, f"导入后缺失 {len(missing)} 个文件"
        assert not mismatches, f"导入后 {len(mismatches)} 个文件内容不匹配"

        print(f"[字节校验] 所有 {len(original)} 个文件字节级一致 [OK]")
        print()

        # ── Step 10: 验证 restore report ──
        assert restore_report_path.exists(), "restore.report.json 应该存在"
        restore_data = load_json(restore_report_path)
        registry.validate_instance(restore_data, "restore.report.schema.json")
        print("[Restore Report] restore.report.json 验证通过 [OK]")
        print()

        # ── Step 11: 验证 redaction report ──
        decisions = report_json["decisions"]
        included = [d for d in decisions if d["decision"] != "exclude"]
        excluded = [d for d in decisions if d["decision"] == "exclude"]
        print(f"[Redaction] 审查决策:")
        print(f"  Included: {len(included)}")
        print(f"  Excluded: {len(excluded)}")
        for d in included:
            print(f"    [OK] {d['path']} ({d['decision']}, class={d['class']})")
        for d in excluded:
            print(f"    [SKIP] {d['path']} ({d['decision']}, class={d['class']}, reasons={d['reasons']})")
        print()

        # ── Step 12: 验证 access control ──
        assert manifest.get("access") is not None, "应该有 access control"
        assert manifest["access"]["owner"] == address, "owner 应该是签名地址"
        assert manifest["access"]["public"] is False, "应该是非公开的"
        print(f"[Access Control] 验证通过 [OK]")
        print(f"  Owner:  {manifest['access']['owner']}")
        print(f"  Public: {manifest['access']['public']}")
        print()

        # ── 总结 ──
        total_size = sum(a["size_bytes"] for a in manifest["artifacts"])
        print("=" * 60)
        print("  记忆上传测试全部通过!")
        print("=" * 60)
        print(f"  Capsule ID:  {capsule_id}")
        print(f"  Artifacts:   {len(manifest['artifacts'])} 个文件")
        print(f"  Total Size:  {total_size} bytes ({total_size / 1024:.1f} KB)")
        print(f"  Blobs:       {len(manifest['blobs'])} 个")
        print(f"  Signed By:   {address}")
        print(f"  Byte 一致性: 完全匹配")
        print("=" * 60)


if __name__ == "__main__":
    run_test()
