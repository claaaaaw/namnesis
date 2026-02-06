"""
ABI Loader - Loads contract ABIs from Foundry build output.

Single source of truth: contracts/out/*.json (Foundry compilation artifacts).
Python loads ABIs at runtime from these JSON files.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


def _find_contracts_out() -> Path:
    """
    Locate the contracts/out/ directory.

    Searches from the current file upward to find the project root.
    """
    current = Path(__file__).resolve()
    for parent in [current, *current.parents]:
        candidate = parent / "contracts" / "out"
        if candidate.is_dir():
            return candidate
    raise FileNotFoundError(
        "Cannot find contracts/out/. Run 'forge build' in the contracts/ directory."
    )


@lru_cache(maxsize=16)
def load_abi(contract_name: str) -> list[dict[str, Any]]:
    """
    Load ABI for a contract from Foundry output.

    Args:
        contract_name: Contract name (e.g., "SoulToken", "SoulGuard")

    Returns:
        ABI as a list of dicts

    Raises:
        FileNotFoundError: If ABI file not found
    """
    out_dir = _find_contracts_out()
    abi_path = out_dir / f"{contract_name}.sol" / f"{contract_name}.json"

    if not abi_path.exists():
        raise FileNotFoundError(
            f"ABI not found: {abi_path}. "
            f"Run 'forge build' in the contracts/ directory."
        )

    with abi_path.open("r", encoding="utf-8") as f:
        artifact = json.load(f)

    return artifact["abi"]


@lru_cache(maxsize=16)
def load_bytecode(contract_name: str) -> str:
    """
    Load deployment bytecode for a contract from Foundry output.

    Args:
        contract_name: Contract name (e.g., "SoulToken", "SoulGuard")

    Returns:
        Hex-encoded bytecode string (0x-prefixed)
    """
    out_dir = _find_contracts_out()
    abi_path = out_dir / f"{contract_name}.sol" / f"{contract_name}.json"

    if not abi_path.exists():
        raise FileNotFoundError(f"Bytecode not found: {abi_path}")

    with abi_path.open("r", encoding="utf-8") as f:
        artifact = json.load(f)

    bytecode = artifact.get("bytecode", {}).get("object", "")
    if not bytecode:
        raise ValueError(f"No bytecode in artifact for {contract_name}")

    return bytecode


def soul_token_abi() -> list[dict[str, Any]]:
    """Load SoulToken ABI."""
    return load_abi("SoulToken")


def soul_guard_abi() -> list[dict[str, Any]]:
    """Load SoulGuard ABI."""
    return load_abi("SoulGuard")
