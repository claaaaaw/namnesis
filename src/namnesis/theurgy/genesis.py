"""
Genesis - Create a new sovereign AI agent.

Single entry point for identity initialisation.  Identity is a single
ECDSA/secp256k1 wallet key — the same key signs capsule manifests, authenticates
with the Relay, and sends on-chain transactions.

Flow:
1. Generate ECDSA wallet if not exists
2. Mint Soul NFT (client pays gas) unless --skip-mint
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import click

from ..sigil.eth import (
    NAMNESIS_DIR,
    NAMNESIS_ENV,
    generate_eoa,
    get_address,
    load_private_key,
    save_private_key,
)

# ---- Hardcoded defaults (Base Sepolia testnet, MVP) ----
# These are baked into genesis so that `namnesis genesis` produces a
# fully-functional ~/.namnesis/.env without any manual editing.
_DEFAULTS: dict[str, str] = {
    "SOUL_TOKEN_ADDRESS": "0x7da34a285b8bc5def26a7204d576ad331f405200",
    "SOUL_GUARD_ADDRESS": "0x433bf2d2b72a7cf6cf682d90a10b00331d6c18d4",
    "BASE_SEPOLIA_RPC": "https://sepolia.base.org",
    "CHAIN_ID": "84532",
    "NAMNESIS_CREDENTIAL_SERVICE": "https://namnesis-api.channing-lucchi.workers.dev",
}


def _ensure_identity() -> tuple[str, Path]:
    """Ensure ECDSA wallet exists.  Returns (eth_address, key_dir).

    Creates the wallet if missing.
    """
    NAMNESIS_DIR.mkdir(parents=True, exist_ok=True)

    try:
        pk = load_private_key()
        address = get_address(pk)
    except (ValueError, FileNotFoundError):
        pk, address = generate_eoa()
        save_private_key(pk)

    # Populate default config values (contract addresses, RPC, etc.)
    _ensure_defaults()

    return address, NAMNESIS_DIR


def _ensure_defaults() -> None:
    """Ensure default config values exist in ~/.namnesis/.env.

    Only adds keys that are not already present, so user overrides are
    preserved.
    """
    env_path = NAMNESIS_ENV
    existing: dict[str, str] = {}
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and "=" in stripped:
                k, v = stripped.split("=", 1)
                existing[k.strip()] = v.strip()

    updated = False
    for key, value in _DEFAULTS.items():
        if key not in existing:
            existing[key] = value
            updated = True

    if updated:
        lines = [f"{k}={v}" for k, v in existing.items()]
        env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        # Also inject into current process env so subsequent commands work
        for key, value in _DEFAULTS.items():
            os.environ.setdefault(key, value)


@click.command()
@click.option(
    "--rpc-url",
    envvar="BASE_SEPOLIA_RPC",
    default="https://sepolia.base.org",
    help="Base Sepolia RPC URL",
)
@click.option(
    "--skip-mint",
    is_flag=True,
    help="Only generate wallet key, skip NFT minting",
)
def genesis(rpc_url: str, skip_mint: bool) -> None:
    """Create a new sovereign AI agent.

    Generates a wallet identity and mints a Soul NFT on-chain.
    Use --skip-mint to only generate the key (e.g. for offline testing).
    """
    click.echo()
    click.echo(
        click.style("  ◆ ", fg="cyan")
        + click.style("Genesis", fg="bright_white", bold=True)
        + click.style(" ─── Create a new sovereign agent", fg="cyan")
    )
    click.echo()

    # --- Step 1: Identity (ECDSA wallet) ---
    click.secho("  [1/2] Preparing identity...", fg="bright_white")
    address, key_dir = _ensure_identity()

    click.echo(click.style("        Address: ", dim=True) + click.style(address, fg="bright_white"))
    click.echo(click.style("        Config:  ", dim=True) + click.style(str(NAMNESIS_ENV), fg="bright_white"))
    click.echo()
    click.secho("        IMPORTANT: Back up ~/.namnesis/.env — loss is irreversible.", fg="yellow", bold=True)
    click.echo()

    if skip_mint:
        click.secho("  Skipping NFT mint (--skip-mint).", dim=True)
        click.echo()
        click.echo(
            click.style("  ◆ ", fg="green")
            + click.style("Genesis Complete", fg="green", bold=True)
            + click.style(" (identity only)", dim=True)
        )
        click.echo()
        click.secho("  Next steps:", fg="cyan")
        click.echo(f"    1. Fund your address with testnet ETH: {address}")
        click.echo("    2. Run 'namnesis genesis' again (without --skip-mint) to mint")
        click.echo()
        return

    # --- Step 2: Mint Soul NFT ---
    click.secho("  [2/2] Minting Soul NFT...", fg="bright_white")
    click.echo(click.style("        RPC: ", dim=True) + rpc_url)

    try:
        os.environ["BASE_SEPOLIA_RPC"] = rpc_url
        from ..pneuma.tx import send_contract_tx
        from ..pneuma.rpc import get_balance

        balance = get_balance(address)
        if balance == 0:
            click.secho(
                f"        Address has zero balance. Fund it first: {address}",
                fg="red",
            )
            click.echo(
                "        Get testnet ETH from: https://www.coinbase.com/faucets/base-ethereum-goerli-faucet"
            )
            sys.exit(1)

        click.echo(click.style("        Balance: ", dim=True) + f"{balance / 1e18:.6f} ETH")

        soul_token_addr = _get_contract_address("SOUL_TOKEN")

        result = send_contract_tx(
            contract_address=soul_token_addr,
            function_name="mint",
            args=[address],
            contract_name="SoulToken",
            gas_limit=200_000,
        )

        if result.get("status") == 1:
            tx_hash = result["tx_hash"]
            click.echo()
            click.secho("        Soul NFT minted!", fg="green", bold=True)
            click.echo(click.style("        TX: ", dim=True) + tx_hash)
            click.echo(click.style("        Token ID: ", dim=True) + "check transaction logs")
        else:
            click.secho("        Mint transaction reverted", fg="red")
            click.echo(click.style("        TX: ", dim=True) + result.get("tx_hash", "unknown"))
            sys.exit(1)

    except Exception as exc:
        click.secho(f"        Mint failed: {exc}", fg="red")
        click.echo()
        click.secho("  Ensure:", fg="yellow")
        click.echo("    - SOUL_TOKEN_ADDRESS is set correctly")
        click.echo(f"    - Address has sufficient ETH: {address}")
        sys.exit(1)

    click.echo()
    click.echo(
        click.style("  ◆ ", fg="green")
        + click.style("Genesis Complete", fg="green", bold=True)
    )
    click.echo()
    click.secho("  Next steps:", fg="cyan")
    click.echo("    1. Run 'namnesis divine --soul-id <ID>' to check status")
    click.echo("    2. Run 'namnesis imprint' to upload memory")
    click.echo()


def _get_contract_address(name: str) -> str:
    """Get contract address from environment."""
    addr = os.environ.get(f"{name}_ADDRESS")
    if not addr:
        raise click.ClickException(
            f"{name}_ADDRESS not set. Set it in {NAMNESIS_ENV} or environment."
        )
    return addr
