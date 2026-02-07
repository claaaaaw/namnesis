# On-Chain Records (Hackathon Verification)

Namnesis on-chain deployment and transaction records on **Base Sepolia** for [USDC Hackathon](https://moltbook.com/m/usdc) judge verification.

---

## Network

| Item | Value |
|------|-------|
| **Network** | Base Sepolia (Testnet) |
| **Chain ID** | 84532 |
| **Block Explorer** | [sepolia.basescan.org](https://sepolia.basescan.org) |

---

## Deployed Contracts

| Contract | Role | Address | Explorer |
|----------|------|---------|----------|
| **SoulToken** | ERC-721 Soul NFT — on-chain agent identity | `0x433bf2d2b72a7cf6cf682d90a10b00331d6c18d4` | [View](https://sepolia.basescan.org/address/0x433bf2d2b72a7cf6cf682d90a10b00331d6c18d4) |
| **SoulGuard** | Ownership registry — maps Soul → Kernel, handles claim/transfer | `0x9e2cef363f0058d36e899a8860f9c76c64e9a775` | [View](https://sepolia.basescan.org/address/0x9e2cef363f0058d36e899a8860f9c76c64e9a775) |
| **NamnesisKernel** | ERC-4337/7579 smart account — agent wallet (holds USDC) | `0x80d18b069a8ff1634b3d89ebaa491bf23182384b` | [View](https://sepolia.basescan.org/address/0x80d18b069a8ff1634b3d89ebaa491bf23182384b) |

| Account | Role | Address | Explorer |
|---------|------|---------|----------|
| **Deployer EOA** | Soul #0 owner / operator | `0x83FfDba20747B0Eca859035C8E64D8237B90d5Cb` | [View](https://sepolia.basescan.org/address/0x83FfDba20747B0Eca859035C8E64D8237B90d5Cb) |
| **USDC (testnet)** | Circle testnet USDC on Base Sepolia | `0x036CbD53842c5426634e7929541eC2318f3dCF7e` | [View](https://sepolia.basescan.org/address/0x036CbD53842c5426634e7929541eC2318f3dCF7e) |

---

## Transaction Log

All transactions originate from the Deployer EOA on **2026-02-06** (Base Sepolia, block range 37316602–37324918).

### 1. Genesis — Deploy contracts, mint identity, init wallet

| # | Operation | TX Hash | Explorer |
|---|-----------|---------|----------|
| 1 | Deploy **SoulToken** | `0x3e9e8db32776f7e7b549339542d02c2881aca0a9dcc4165625398464077e8896` | [View](https://sepolia.basescan.org/tx/0x3e9e8db32776f7e7b549339542d02c2881aca0a9dcc4165625398464077e8896) |
| 2 | Deploy **SoulGuard** | `0x7f4c7ebcc01febc3f9e2794ac796f9f48691f52ce6b98b70dc8d38414cb60e00` | [View](https://sepolia.basescan.org/tx/0x7f4c7ebcc01febc3f9e2794ac796f9f48691f52ce6b98b70dc8d38414cb60e00) |
| 3 | **Mint** Soul NFT #0 | `0x948876997914ff8e21506d4c6e4cfaf3c9fb44a81201556e24ec5bcbb9a5b581` | [View](https://sepolia.basescan.org/tx/0x948876997914ff8e21506d4c6e4cfaf3c9fb44a81201556e24ec5bcbb9a5b581) |
| 4 | Deploy **NamnesisKernel** (smart account) | `0x71d24cb88b685a9295ad5b255be111004a3930fe0d8fb60e10a96ee770c414ca` | [View](https://sepolia.basescan.org/tx/0x71d24cb88b685a9295ad5b255be111004a3930fe0d8fb60e10a96ee770c414ca) |
| 5 | Install **OwnableExecutor** module on Kernel | `0x67c02693d211b007591f5df8d052f133657f89e2ba50995c50aaed4dcd769912` | [View](https://sepolia.basescan.org/tx/0x67c02693d211b007591f5df8d052f133657f89e2ba50995c50aaed4dcd769912) |
| 6 | **Register** Kernel with SoulGuard | `0xc43fed153515825628af8df87924d128e25aac6fac11b4adb54a046b1be791fc` | [View](https://sepolia.basescan.org/tx/0xc43fed153515825628af8df87924d128e25aac6fac11b4adb54a046b1be791fc) |

### 2. USDC Token Operations — Kernel holds & transfers testnet USDC

| # | Operation | TX Hash | Explorer |
|---|-----------|---------|----------|
| 7 | **Fund** Kernel with 10 USDC (EOA → Kernel) | `0x991546b1adcfd170bd706544ea2193b67e380e0ef34210d7ca4d4a35856545af` | [View](https://sepolia.basescan.org/tx/0x991546b1adcfd170bd706544ea2193b67e380e0ef34210d7ca4d4a35856545af) |
| 8 | **Transfer** 1 USDC from Kernel via `execute()` | `0x6bc2099a4888c855b570c1266e9b5925b89ef40e4756d8f8671b02f669c1fb4b` | [View](https://sepolia.basescan.org/tx/0x6bc2099a4888c855b570c1266e9b5925b89ef40e4756d8f8671b02f669c1fb4b) |

Current Kernel USDC balance: **9 USDC** — [Verify token holdings](https://sepolia.basescan.org/address/0x80d18b069a8ff1634b3d89ebaa491bf23182384b#tokentxns)

### 3. Imprint — Encrypt memory, upload, update on-chain metadata

| # | Operation | TX Hash | Explorer |
|---|-----------|---------|----------|
| 9 | **Imprint** — update Soul #0 metadata (samsaraCycles, memorySize) | `0x985c3aed25c85bbce208ed86917978d4e0c0f5e11808d74b1023c1fc7e691f01` | [View](https://sepolia.basescan.org/tx/0x985c3aed25c85bbce208ed86917978d4e0c0f5e11808d74b1023c1fc7e691f01) |

Soul #0 on-chain metadata: **samsaraCycles = 1**, **memorySize = 1897 bytes**

---

## Quick Links

| Resource | URL |
|----------|-----|
| All Kernel transactions | [Kernel → Transactions](https://sepolia.basescan.org/address/0x80d18b069a8ff1634b3d89ebaa491bf23182384b) |
| Kernel ERC-20 transfers | [Kernel → Token Transfers](https://sepolia.basescan.org/address/0x80d18b069a8ff1634b3d89ebaa491bf23182384b#tokentxns) |
| Soul NFT token tracker | [Namnesis Soul (SOUL)](https://sepolia.basescan.org/token/0x433bf2d2b72a7cf6cf682d90a10b00331d6c18d4) |
| Deployer EOA full history | [EOA → Transactions](https://sepolia.basescan.org/address/0x83FfDba20747B0Eca859035C8E64D8237B90d5Cb) |

---

## Verification Checklist (for judges)

- [x] **Network**: All addresses and transactions on Base Sepolia (chain ID 84532)
- [x] **Contracts deployed**: SoulToken (ERC-721), SoulGuard, NamnesisKernel (ERC-4337/7579) — 3 contracts with creation TXes
- [x] **Identity minted**: Soul NFT #0 minted and owned by Deployer EOA
- [x] **Smart account active**: Kernel deployed, OwnableExecutor installed, registered with SoulGuard
- [x] **USDC integration**: Kernel funded with 10 testnet USDC, successfully transferred 1 USDC via `execute()`, current balance 9 USDC
- [x] **Memory anchoring**: Imprint TX updates Soul NFT on-chain metadata (samsaraCycles, memorySize)
- [x] **All TXes verifiable**: 9 transactions with explorer links above

---

## Related Documentation

- Project overview and architecture: [README.md](../README.md)
- Architecture specification: [02-ARCHITECTURE.md](02-ARCHITECTURE.md)
- CLI reference: [04-CLI-SPEC.md](04-CLI-SPEC.md)
