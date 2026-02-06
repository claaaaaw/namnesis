"""
Transaction Builder - Build, sign, and send Ethereum transactions.

Uses eth-account for signing and httpx-based JSON-RPC for sending.
All gas is paid by the client EOA.
"""

from __future__ import annotations

from typing import Any, Optional

from eth_account import Account
from eth_abi import encode

from ..sigil.eth import get_account, load_private_key
from .abi import load_abi, load_bytecode
from .rpc import (
    _keccak256,
    get_chain_id,
    get_gas_price,
    get_nonce,
    get_rpc_url,
    send_raw_transaction,
    wait_for_receipt,
)


def _to_checksum_address(address: str) -> str:
    """Convert an address to EIP-55 checksummed format.

    eth-account requires checksummed addresses in transaction fields.
    """
    addr = address.lower().replace("0x", "")
    addr_hash = _keccak256(addr.encode("utf-8")).hex()
    result = "0x"
    for i, c in enumerate(addr):
        if c in "abcdef":
            result += c.upper() if int(addr_hash[i], 16) >= 8 else c
        else:
            result += c
    return result


def build_contract_tx(
    contract_address: str,
    function_name: str,
    args: list,
    contract_name: Optional[str] = None,
    abi: Optional[list] = None,
    value: int = 0,
    gas_limit: Optional[int] = None,
    private_key: Optional[str] = None,
) -> dict:
    """
    Build a contract call transaction (unsigned).

    Args:
        contract_address: 0x-prefixed contract address
        function_name: Function to call
        args: Function arguments
        contract_name: For ABI loading
        abi: Pre-loaded ABI
        value: ETH value in wei (default: 0)
        gas_limit: Gas limit (default: auto-estimate)
        private_key: For nonce lookup

    Returns:
        Unsigned transaction dict
    """
    if abi is None:
        if contract_name is None:
            raise ValueError("Either abi or contract_name must be provided")
        abi = load_abi(contract_name)

    calldata = _encode_call(abi, function_name, args)

    account = get_account(private_key)
    nonce = get_nonce(account.address)
    gas_price = get_gas_price()

    tx = {
        "to": _to_checksum_address(contract_address),
        "data": calldata,
        "value": value,
        "nonce": nonce,
        "gas": gas_limit or 500_000,  # Default gas limit
        "gasPrice": gas_price,
        "chainId": get_chain_id(),
    }

    return tx


def sign_and_send(
    tx: dict,
    private_key: Optional[str] = None,
    wait: bool = True,
    timeout: int = 120,
) -> dict:
    """
    Sign a transaction and send it.

    Args:
        tx: Unsigned transaction dict
        private_key: 0x-prefixed hex private key
        wait: Whether to wait for receipt
        timeout: Receipt wait timeout

    Returns:
        Dict with tx_hash and optionally receipt
    """
    account = get_account(private_key)
    signed = account.sign_transaction(tx)
    raw_tx = "0x" + signed.raw_transaction.hex()

    tx_hash = send_raw_transaction(raw_tx)
    result: dict[str, Any] = {"tx_hash": tx_hash}

    if wait:
        receipt = wait_for_receipt(tx_hash, timeout=timeout)
        result["receipt"] = receipt
        result["status"] = int(receipt.get("status", "0x0"), 16)

    return result


def send_contract_tx(
    contract_address: str,
    function_name: str,
    args: list,
    contract_name: Optional[str] = None,
    abi: Optional[list] = None,
    value: int = 0,
    gas_limit: Optional[int] = None,
    private_key: Optional[str] = None,
    wait: bool = True,
) -> dict:
    """
    Build, sign, and send a contract call transaction.

    Convenience function combining build + sign + send.

    Args:
        contract_address: 0x-prefixed contract address
        function_name: Function to call
        args: Function arguments
        contract_name: For ABI loading
        abi: Pre-loaded ABI
        value: ETH value in wei
        gas_limit: Gas limit
        private_key: Private key for signing
        wait: Whether to wait for receipt

    Returns:
        Dict with tx_hash, receipt, status
    """
    tx = build_contract_tx(
        contract_address=contract_address,
        function_name=function_name,
        args=args,
        contract_name=contract_name,
        abi=abi,
        value=value,
        gas_limit=gas_limit,
        private_key=private_key,
    )
    return sign_and_send(tx, private_key=private_key, wait=wait)


def deploy_contract(
    contract_name: str,
    constructor_args: Optional[list] = None,
    gas_limit: int = 3_000_000,
    private_key: Optional[str] = None,
    wait: bool = True,
    timeout: int = 180,
) -> dict:
    """
    Deploy a contract to the chain.

    Builds a creation transaction (to=None), signs, sends, and extracts
    the deployed contract address from the receipt.

    Args:
        contract_name: Foundry contract name (e.g., "NamnesisKernel")
        constructor_args: Constructor arguments (default: none)
        gas_limit: Gas limit for deployment
        private_key: Private key for signing
        wait: Whether to wait for receipt
        timeout: Receipt wait timeout

    Returns:
        Dict with tx_hash, status, contract_address, receipt
    """
    bytecode = load_bytecode(contract_name)

    # Append ABI-encoded constructor args if provided
    deploy_data = bytecode
    if constructor_args:
        abi = load_abi(contract_name)
        constructor = None
        for entry in abi:
            if entry.get("type") == "constructor":
                constructor = entry
                break

        if constructor is None:
            raise ValueError(
                f"Constructor not found in ABI for {contract_name}, "
                f"but constructor_args were provided."
            )

        input_types = [inp["type"] for inp in constructor.get("inputs", [])]
        encoded_args = encode(input_types, constructor_args)
        deploy_data = bytecode + encoded_args.hex()

    # Ensure 0x prefix
    if not deploy_data.startswith("0x"):
        deploy_data = "0x" + deploy_data

    account = get_account(private_key)
    nonce = get_nonce(account.address)
    gas_price = get_gas_price()

    tx: dict[str, Any] = {
        "data": deploy_data,
        "value": 0,
        "nonce": nonce,
        "gas": gas_limit,
        "gasPrice": gas_price,
        "chainId": get_chain_id(),
    }

    result = sign_and_send(tx, private_key=private_key, wait=wait, timeout=timeout)

    # Extract deployed contract address from receipt
    if wait and result.get("receipt"):
        contract_address = result["receipt"].get("contractAddress")
        if contract_address:
            result["contract_address"] = contract_address

    return result


def _encode_call(abi: list, function_name: str, args: list) -> str:
    """ABI-encode a function call to hex calldata."""
    func = None
    for entry in abi:
        if entry.get("type") == "function" and entry.get("name") == function_name:
            func = entry
            break

    if func is None:
        raise ValueError(f"Function {function_name} not found in ABI")

    input_types = [inp["type"] for inp in func.get("inputs", [])]
    sig = f"{function_name}({','.join(input_types)})"

    # Compute keccak256 selector
    # NOTE: Keccak-256 != SHA3-256 (NIST). Never use hashlib.sha3_256 here.
    selector = _keccak256(sig.encode("utf-8"))[:4]

    if args:
        encoded_args = encode(input_types, args)
    else:
        encoded_args = b""

    return "0x" + selector.hex() + encoded_args.hex()
