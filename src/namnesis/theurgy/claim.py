"""
Theurgy Claim - Resurrection / Ownership Transfer.

When you acquire a Soul NFT through a transfer, run this command to
take control of the associated Kernel (Body).

Flow:
1. Load local EOA private key
2. Verify caller is the NFT owner
3. Call SoulGuard.claim(soulId) — pays gas
4. Kernel ECDSA Validator owner is changed to caller
"""

from __future__ import annotations

import os
import sys

import click

from ..sigil.eth import get_address, load_private_key, NAMNESIS_ENV
from ..pneuma.rpc import read_contract, get_rpc_url
from ..pneuma.tx import send_contract_tx


@click.command()
@click.option("--soul-id", required=True, type=int, help="Soul NFT token ID")
@click.option(
    "--rpc-url",
    envvar="BASE_SEPOLIA_RPC",
    default="https://sepolia.base.org",
    help="Base Sepolia RPC URL",
)
def claim(soul_id: int, rpc_url: str) -> None:
    """
    Claim ownership of a Kernel after NFT transfer.

    When you acquire a Soul NFT, run this to take control of the
    associated Body (Kernel). This changes the ECDSA Validator owner
    to your address via SoulGuard.
    """
    click.echo("=== Namnesis Claim (Resurrection) ===")
    click.echo("")

    os.environ["BASE_SEPOLIA_RPC"] = rpc_url

    # 1. Load local EOA
    try:
        private_key = load_private_key()
        address = get_address(private_key)
    except (ValueError, FileNotFoundError) as exc:
        click.secho(f"ERROR: {exc}", fg="red")
        click.echo("Run 'namnesis genesis' first.")
        sys.exit(1)

    click.echo(f"  Your address: {address}")
    click.echo(f"  Soul ID: {soul_id}")

    # 2. Check NFT ownership
    soul_token_addr = os.environ.get("SOUL_TOKEN_ADDRESS")
    soul_guard_addr = os.environ.get("SOUL_GUARD_ADDRESS")

    if not soul_token_addr or not soul_guard_addr:
        click.secho(
            "ERROR: SOUL_TOKEN_ADDRESS and SOUL_GUARD_ADDRESS must be set.",
            fg="red",
        )
        sys.exit(1)

    try:
        owner = read_contract(
            soul_token_addr,
            "ownerOf",
            [soul_id],
            contract_name="SoulToken",
        )
    except Exception as exc:
        click.secho(f"ERROR: Failed to read NFT owner: {exc}", fg="red")
        sys.exit(1)

    # Normalize address comparison
    if str(owner).lower() != address.lower():
        click.secho("ERROR: You are not the Soul owner!", fg="red")
        click.echo(f"  NFT owner: {owner}")
        click.echo(f"  Your address: {address}")
        sys.exit(1)

    # 3. Check if claim is needed
    try:
        confirmed = read_contract(
            soul_guard_addr,
            "confirmedOwner",
            [soul_id],
            contract_name="SoulGuard",
        )
        if str(confirmed).lower() == address.lower():
            click.echo("Claim not needed — you are already the confirmed owner.")
            return
    except Exception:
        pass  # Continue with claim attempt

    # 4. Execute claim
    click.echo("")
    click.echo("Claiming ownership...")

    try:
        result = send_contract_tx(
            contract_address=soul_guard_addr,
            function_name="claim",
            args=[soul_id],
            contract_name="SoulGuard",
            gas_limit=300_000,
        )

        if result.get("status") == 1:
            click.secho("SUCCESS: You now control this Body!", fg="green")
            click.echo(f"  TX: {result['tx_hash']}")
        else:
            click.secho("FAILED: Claim transaction reverted", fg="red")
            click.echo(f"  TX: {result.get('tx_hash', 'unknown')}")
            sys.exit(1)

    except Exception as exc:
        click.secho(f"Claim failed: {exc}", fg="red")
        sys.exit(1)
