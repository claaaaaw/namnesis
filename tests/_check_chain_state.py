"""Check current wallet and on-chain state before imprint test."""
import os

os.environ["SOUL_TOKEN_ADDRESS"] = "0x433bf2d2b72a7cf6cf682d90a10b00331d6c18d4"
os.environ["SOUL_GUARD_ADDRESS"] = "0x9e2cef363f0058d36e899a8860f9c76c64e9a775"
os.environ["BASE_SEPOLIA_RPC"] = "https://sepolia.base.org"
os.environ["CHAIN_ID"] = "84532"

from namnesis.sigil.eth import load_private_key, get_address
from namnesis.pneuma.rpc import read_contract, get_balance

pk = load_private_key()
addr = get_address(pk)
print(f"EOA Address: {addr}")

# Check ETH balance
balance_wei = get_balance(addr)
balance_eth = balance_wei / 1e18
print(f"ETH Balance: {balance_eth:.6f} ETH ({balance_wei} wei)")

# Check current on-chain state
soul_token = os.environ["SOUL_TOKEN_ADDRESS"]
soul_id = 0

owner = None
try:
    owner = read_contract(soul_token, "ownerOf", [soul_id], contract_name="SoulToken")
    print(f"Soul NFT #0 Owner: {owner}")
except Exception as e:
    print(f"ownerOf failed: {e}")

try:
    cycles = read_contract(soul_token, "samsaraCycles", [soul_id], contract_name="SoulToken")
    print(f"Current samsaraCycles: {cycles}")
except Exception as e:
    print(f"samsaraCycles failed: {e}")

try:
    size = read_contract(soul_token, "memorySize", [soul_id], contract_name="SoulToken")
    print(f"Current memorySize: {size}")
except Exception as e:
    print(f"memorySize failed: {e}")

try:
    updated = read_contract(soul_token, "lastUpdated", [soul_id], contract_name="SoulToken")
    print(f"Last Updated (block.timestamp): {updated}")
    if updated:
        from datetime import datetime, timezone
        dt = datetime.fromtimestamp(updated, tz=timezone.utc)
        print(f"Last Updated (UTC): {dt.isoformat()}")
except Exception as e:
    print(f"lastUpdated failed: {e}")

print()
owner_match = str(owner).lower() == addr.lower() if owner else False
print(f"Owner matches EOA: {owner_match}")
print(f"Has enough gas: {balance_eth > 0.0001}")
