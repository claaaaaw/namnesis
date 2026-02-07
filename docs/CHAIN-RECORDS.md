# On-Chain Records (Hackathon Verification)

This document provides **Namnesis** on-chain deployment and key transaction records on Base Sepolia for judge verification (e.g. [ClawHub USDC Hackathon](https://clawhub.ai/swairshah/usdc-hackathon)).

---

## Network Info

| Item | Value |
|------|--------|
| **Network** | Base Sepolia (Testnet) |
| **Chain ID** | 84532 |
| **Block Explorer** | [sepolia.basescan.org](https://sepolia.basescan.org) |
| **RPC (example)** | `https://sepolia.base.org` |

---

## Contracts & Accounts

| Role | Description | Address | BaseScan |
|------|-------------|---------|----------|
| **SoulToken** | The Soul NFT (on-chain identity) | `0x433bf2d2b72a7cf6cf682d90a10b00331d6c18d4` | [Contract](https://sepolia.basescan.org/address/0x433bf2d2b72a7cf6cf682d90a10b00331d6c18d4) |
| **SoulGuard** | Pneuma validator (Capsule signature verification) | `0x9e2cef363f0058d36e899a8860f9c76c64e9a775` | [Contract](https://sepolia.basescan.org/address/0x9e2cef363f0058d36e899a8860f9c76c64e9a775) |
| **NamnesisKernel** | The Body (ERC-4337 smart account) | `0x80d18b069a8ff1634b3d89ebaa491bf23182384b` | [Contract](https://sepolia.basescan.org/address/0x80d18b069a8ff1634b3d89ebaa491bf23182384b) |
| **Demo EOA** | Soul #0 holder / operator wallet | `0x83FfDba20747B0Eca859035C8E64D8237B90d5Cb` | [Account](https://sepolia.basescan.org/address/0x83FfDba20747B0Eca859035C8E64D8237B90d5Cb) |

---

## Key On-Chain Transactions

### Imprint (memory on-chain)

| Description | TX Hash | BaseScan |
|-------------|---------|----------|
| Imprint — package memory, upload, and update Soul #0 on-chain metadata | `0x985c3aed25c85bbce208ed86917978d4e0c0f5e11808d74b1023c1fc7e691f01` | [View tx](https://sepolia.basescan.org/tx/0x985c3aed25c85bbce208ed86917978d4e0c0f5e11808d74b1023c1fc7e691f01) |

- **Soul #0** · SamsaraCycles: 1 · Memory size: 1897 bytes

---

## Verification Checklist (for judges)

1. **Network:** All addresses and transactions are on **Base Sepolia (84532)** and can be looked up at [sepolia.basescan.org](https://sepolia.basescan.org).
2. **Contracts:** SoulToken, SoulGuard, and NamnesisKernel are deployed contracts; the demo EOA is an externally owned account.
3. **Imprint tx:** The transaction above completes the flow “package memory → store → update Soul NFT metadata”, demonstrating on-chain verifiable memory updates.

---

## Relation to README

- This list matches the “On-Chain Record (Hackathon Verification)” section in [README.md](../README.md).
- For architecture and CLI usage, see [02-ARCHITECTURE.md](02-ARCHITECTURE.md) and [04-CLI-SPEC.md](04-CLI-SPEC.md).
