"""
ECDSA / secp256k1 Key Management for Namnesis Protocol.

This module handles Ethereum-compatible ECDSA keys used for:
- On-chain transaction signing (genesis, claim, updateMetadata)
- Relay ECDSA verification (new presign endpoint)

Keys are stored in ~/.namnesis/.env as PRIVATE_KEY (hex format).

Dependencies: eth-account (lightweight, ~5MB, no full web3.py needed)
"""

from __future__ import annotations

import os
import secrets
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from eth_account import Account
from eth_account.signers.local import LocalAccount
from eth_account.messages import encode_defunct


# Default config directory
NAMNESIS_DIR = Path.home() / ".namnesis"
NAMNESIS_ENV = NAMNESIS_DIR / ".env"


def generate_eoa() -> tuple[str, str]:
    """
    Generate a new ECDSA/secp256k1 keypair (EOA).

    Returns:
        Tuple of (private_key_hex, address)
        - private_key_hex: 0x-prefixed hex private key (66 chars)
        - address: 0x-prefixed checksummed Ethereum address (42 chars)
    """
    private_key = "0x" + secrets.token_hex(32)
    account = Account.from_key(private_key)
    return private_key, account.address


def save_private_key(private_key: str, env_path: Optional[Path] = None) -> Path:
    """
    Save private key to .env file.

    Args:
        private_key: 0x-prefixed hex private key
        env_path: Path to .env file (default: ~/.namnesis/.env)

    Returns:
        Path to the saved .env file
    """
    env_path = env_path or NAMNESIS_ENV
    env_path.parent.mkdir(parents=True, exist_ok=True)

    # Read existing .env content or start fresh
    existing = {}
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                existing[k.strip()] = v.strip()

    existing["PRIVATE_KEY"] = private_key

    # Write back
    lines = [f"{k}={v}" for k, v in existing.items()]
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Set secure permissions on Unix
    if os.name != "nt":
        env_path.chmod(0o600)

    return env_path


def load_private_key(env_path: Optional[Path] = None) -> str:
    """
    Load private key from .env file or environment.

    Args:
        env_path: Path to .env file (default: ~/.namnesis/.env)

    Returns:
        0x-prefixed hex private key

    Raises:
        FileNotFoundError: If .env file doesn't exist
        ValueError: If PRIVATE_KEY not found in .env
    """
    env_path = env_path or NAMNESIS_ENV

    if env_path.exists():
        load_dotenv(env_path, override=True)

    private_key = os.environ.get("PRIVATE_KEY")
    if not private_key:
        raise ValueError(
            f"PRIVATE_KEY not found. Run 'namnesis genesis' or set "
            f"PRIVATE_KEY in {env_path}"
        )

    # Ensure 0x prefix
    if not private_key.startswith("0x"):
        private_key = "0x" + private_key

    return private_key


def get_account(private_key: Optional[str] = None) -> LocalAccount:
    """
    Get an eth-account LocalAccount from a private key.

    Args:
        private_key: 0x-prefixed hex private key.
                     If None, loads from .env.

    Returns:
        LocalAccount instance for signing transactions
    """
    if private_key is None:
        private_key = load_private_key()
    return Account.from_key(private_key)


def get_address(private_key: Optional[str] = None) -> str:
    """
    Get the Ethereum address for a private key.

    Args:
        private_key: 0x-prefixed hex private key.
                     If None, loads from .env.

    Returns:
        0x-prefixed checksummed Ethereum address
    """
    return get_account(private_key).address


def sign_message(message: str, private_key: Optional[str] = None) -> str:
    """
    Sign a message using EIP-191 personal_sign.

    Args:
        message: The message string to sign
        private_key: 0x-prefixed hex private key.
                     If None, loads from .env.

    Returns:
        0x-prefixed hex signature
    """
    account = get_account(private_key)
    signable = encode_defunct(text=message)
    signed = account.sign_message(signable)
    return signed.signature.hex()


def sign_message_bytes(message: bytes, private_key: Optional[str] = None) -> bytes:
    """
    Sign a message (bytes) using EIP-191 personal_sign.

    Args:
        message: The message bytes to sign
        private_key: 0x-prefixed hex private key.
                     If None, loads from .env.

    Returns:
        Signature as bytes (65 bytes: r + s + v)
    """
    account = get_account(private_key)
    signable = encode_defunct(primitive=message)
    signed = account.sign_message(signable)
    return bytes(signed.signature)
