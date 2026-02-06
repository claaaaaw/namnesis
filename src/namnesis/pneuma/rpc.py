"""
JSON-RPC Client for Base Sepolia.

Lightweight alternative to web3.py: uses httpx for HTTP + eth-abi for encoding.
Supports read-only contract calls, balance queries, and transaction receipt polling.
"""

from __future__ import annotations

import os
import time
from typing import Any, Optional

import httpx
from eth_abi import encode, decode

from .abi import load_abi

# ---------------------------------------------------------------------------
# Keccak-256 helper (NOT the same as hashlib.sha3_256 / NIST SHA-3)
# ---------------------------------------------------------------------------

def _keccak256(data: bytes) -> bytes:
    """Compute Keccak-256 hash. Tries eth_hash first, then pycryptodome."""
    try:
        from eth_hash.auto import keccak
        return keccak(data)
    except ImportError:
        pass
    try:
        from Crypto.Hash import keccak as _ck
        h = _ck.new(digest_bits=256)
        h.update(data)
        return h.digest()
    except ImportError:
        raise ImportError(
            "No Keccak-256 backend found. "
            "Install eth-hash (pip install eth-hash[pycryptodome]) "
            "or pycryptodome (pip install pycryptodome)."
        )


# Default RPC endpoint (Base Sepolia)
DEFAULT_RPC_URL = "https://sepolia.base.org"
DEFAULT_CHAIN_ID = 84532  # Base Sepolia


def get_rpc_url() -> str:
    """Get the RPC URL from environment or default."""
    return os.environ.get("BASE_SEPOLIA_RPC", DEFAULT_RPC_URL)


def get_chain_id() -> int:
    """Get the chain ID from environment or default."""
    return int(os.environ.get("CHAIN_ID", str(DEFAULT_CHAIN_ID)))


def _rpc_call(method: str, params: list, rpc_url: Optional[str] = None) -> Any:
    """
    Make a JSON-RPC call.

    Args:
        method: RPC method name (e.g., "eth_call")
        params: RPC parameters
        rpc_url: RPC endpoint URL

    Returns:
        Result field from the RPC response

    Raises:
        RuntimeError: If RPC call fails
    """
    url = rpc_url or get_rpc_url()
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": 1,
    }

    with httpx.Client(timeout=30) as client:
        response = client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()

    if "error" in data:
        raise RuntimeError(f"RPC error: {data['error']}")

    return data.get("result")


def _encode_function_call(abi: list, function_name: str, args: list) -> str:
    """
    ABI-encode a function call.

    Args:
        abi: Contract ABI
        function_name: Function name to call
        args: Function arguments

    Returns:
        0x-prefixed hex encoded calldata
    """
    # Find the function in ABI
    func = None
    for entry in abi:
        if entry.get("type") == "function" and entry.get("name") == function_name:
            func = entry
            break

    if func is None:
        raise ValueError(f"Function {function_name} not found in ABI")

    # Build function selector
    input_types = [inp["type"] for inp in func.get("inputs", [])]
    sig = f"{function_name}({','.join(input_types)})"

    # Compute selector (first 4 bytes of keccak256)
    # NOTE: Keccak-256 != SHA3-256 (NIST). Never use hashlib.sha3_256 here.
    selector = _keccak256(sig.encode("utf-8"))[:4]

    # Encode arguments
    if args:
        encoded_args = encode(input_types, args)
    else:
        encoded_args = b""

    return "0x" + selector.hex() + encoded_args.hex()


def _decode_function_result(abi: list, function_name: str, data: str) -> Any:
    """
    ABI-decode a function call result.

    Args:
        abi: Contract ABI
        function_name: Function name
        data: 0x-prefixed hex encoded return data

    Returns:
        Decoded result (single value or tuple)
    """
    func = None
    for entry in abi:
        if entry.get("type") == "function" and entry.get("name") == function_name:
            func = entry
            break

    if func is None:
        raise ValueError(f"Function {function_name} not found in ABI")

    output_types = [out["type"] for out in func.get("outputs", [])]
    if not output_types:
        return None

    raw = bytes.fromhex(data[2:]) if data.startswith("0x") else bytes.fromhex(data)
    decoded = decode(output_types, raw)

    if len(decoded) == 1:
        return decoded[0]
    return decoded


def read_contract(
    contract_address: str,
    function_name: str,
    args: Optional[list] = None,
    contract_name: Optional[str] = None,
    abi: Optional[list] = None,
    rpc_url: Optional[str] = None,
) -> Any:
    """
    Read from a smart contract (eth_call).

    Args:
        contract_address: 0x-prefixed contract address
        function_name: Function to call
        args: Function arguments (default: [])
        contract_name: Name of contract for ABI loading (e.g., "SoulToken")
        abi: Pre-loaded ABI (if not using contract_name)
        rpc_url: RPC endpoint URL

    Returns:
        Decoded return value(s)
    """
    if abi is None:
        if contract_name is None:
            raise ValueError("Either abi or contract_name must be provided")
        abi = load_abi(contract_name)

    calldata = _encode_function_call(abi, function_name, args or [])

    result = _rpc_call(
        "eth_call",
        [{"to": contract_address, "data": calldata}, "latest"],
        rpc_url=rpc_url,
    )

    if result is None or result == "0x":
        return None

    return _decode_function_result(abi, function_name, result)


def get_balance(address: str, rpc_url: Optional[str] = None) -> int:
    """
    Get ETH balance for an address.

    Args:
        address: 0x-prefixed address
        rpc_url: RPC endpoint URL

    Returns:
        Balance in wei
    """
    result = _rpc_call("eth_getBalance", [address, "latest"], rpc_url=rpc_url)
    return int(result, 16)


def get_nonce(address: str, rpc_url: Optional[str] = None) -> int:
    """
    Get transaction nonce for an address.

    Args:
        address: 0x-prefixed address
        rpc_url: RPC endpoint URL

    Returns:
        Current nonce
    """
    result = _rpc_call("eth_getTransactionCount", [address, "latest"], rpc_url=rpc_url)
    return int(result, 16)


def get_gas_price(rpc_url: Optional[str] = None) -> int:
    """
    Get current gas price.

    Returns:
        Gas price in wei
    """
    result = _rpc_call("eth_gasPrice", [], rpc_url=rpc_url)
    return int(result, 16)


def send_raw_transaction(raw_tx: str, rpc_url: Optional[str] = None) -> str:
    """
    Send a signed raw transaction.

    Args:
        raw_tx: 0x-prefixed hex encoded signed transaction

    Returns:
        Transaction hash (0x-prefixed hex)
    """
    return _rpc_call("eth_sendRawTransaction", [raw_tx], rpc_url=rpc_url)


def wait_for_receipt(
    tx_hash: str,
    timeout: int = 120,
    poll_interval: float = 2.0,
    rpc_url: Optional[str] = None,
) -> dict:
    """
    Wait for a transaction receipt.

    Args:
        tx_hash: Transaction hash
        timeout: Maximum wait time in seconds
        poll_interval: Polling interval in seconds
        rpc_url: RPC endpoint URL

    Returns:
        Transaction receipt dict

    Raises:
        TimeoutError: If receipt not found within timeout
    """
    start = time.time()
    while time.time() - start < timeout:
        receipt = _rpc_call(
            "eth_getTransactionReceipt", [tx_hash], rpc_url=rpc_url
        )
        if receipt is not None:
            return receipt
        time.sleep(poll_interval)

    raise TimeoutError(f"Transaction {tx_hash} not confirmed within {timeout}s")
