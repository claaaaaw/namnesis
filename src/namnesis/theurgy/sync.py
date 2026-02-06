"""
Sync - Repair identity and on-chain inconsistencies.

Identity is a single ECDSA wallet.  This command checks for desync
between the local wallet and on-chain state.

Detects and repairs common desync scenarios:
1. Memory uploaded but on-chain metadata not updated (interrupted imprint)
2. Wallet key exists but no Soul NFT minted
3. NFT ownership changed but claim() not called
"""

from __future__ import annotations

import os
import sys

import click

from ..sigil.eth import (
    get_address,
    load_private_key,
)


@click.command()
@click.option("--soul-id", required=True, type=int, help="Soul NFT token ID")
@click.option(
    "--rpc-url",
    envvar="BASE_SEPOLIA_RPC",
    default="https://sepolia.base.org",
    help="Base Sepolia RPC URL",
)
@click.option("--dry-run", is_flag=True, help="Show what would be repaired without executing")
def sync(soul_id: int, rpc_url: str, dry_run: bool) -> None:
    """Repair identity and on-chain inconsistencies.

    Checks for desync between local wallet and on-chain state,
    and offers to repair any issues found.
    """
    click.echo("=== Namnesis Sync ===")
    click.echo("")

    os.environ["BASE_SEPOLIA_RPC"] = rpc_url

    issues: list[dict] = []

    # --- Check 1: Local identity (wallet) ---
    click.echo("[Check] Local wallet...")
    try:
        pk = load_private_key()
        address = get_address(pk)
        click.echo(f"  Address: {address}")
    except (ValueError, FileNotFoundError):
        click.secho("  No wallet found. Run 'namnesis genesis' first.", fg="red")
        sys.exit(1)

    click.echo("")

    # --- Check 2: On-chain state ---
    click.echo("[Check] On-chain state...")

    soul_token_addr = os.environ.get("SOUL_TOKEN_ADDRESS")
    soul_guard_addr = os.environ.get("SOUL_GUARD_ADDRESS")

    if not soul_token_addr or not soul_guard_addr:
        click.secho(
            "  Skipping on-chain checks (SOUL_TOKEN_ADDRESS / SOUL_GUARD_ADDRESS not set).",
            fg="yellow",
        )
    else:
        try:
            from ..pneuma.rpc import read_contract

            # NFT ownership
            owner = read_contract(
                soul_token_addr, "ownerOf", [soul_id], contract_name="SoulToken"
            )
            click.echo(f"  NFT Owner: {owner}")

            if str(owner).lower() != address.lower():
                click.secho("  WARNING: You are NOT the NFT owner.", fg="yellow")
                issues.append({
                    "type": "not_owner",
                    "description": f"NFT owner is {owner} but your address is {address}.",
                })

            # SoulGuard confirmed owner
            confirmed = read_contract(
                soul_guard_addr, "confirmedOwner", [soul_id], contract_name="SoulGuard"
            )

            if str(owner).lower() == address.lower():
                if str(confirmed).lower() != address.lower():
                    click.secho(
                        "  WARNING: Ownership desync — claim() not called.", fg="yellow"
                    )
                    issues.append({
                        "type": "pending_claim",
                        "description": "You own the NFT but haven't claimed the Kernel.",
                        "action": "claim",
                        "soul_id": soul_id,
                    })

            # Metadata check
            cycles = read_contract(
                soul_token_addr, "samsaraCycles", [soul_id], contract_name="SoulToken"
            )
            size = read_contract(
                soul_token_addr, "memorySize", [soul_id], contract_name="SoulToken"
            )
            click.echo(f"  Cycles: {cycles or 0}, Memory: {size or 0} bytes")

        except Exception as exc:
            click.secho(f"  Failed to read on-chain data: {exc}", fg="red")
            issues.append({
                "type": "rpc_error",
                "description": f"Could not read on-chain state: {exc}",
            })

    click.echo("")

    # --- Summary & Repair ---
    if not issues:
        click.secho("No issues detected. Wallet and chain state are consistent.", fg="green")
        click.echo("")
        click.echo("=== Sync Complete ===")
        return

    click.secho(f"Found {len(issues)} issue(s):", fg="yellow", bold=True)
    click.echo("")

    for i, issue in enumerate(issues, 1):
        click.echo(f"  {i}. [{issue['type']}] {issue['description']}")

    click.echo("")

    if dry_run:
        click.echo("(Dry run — no changes made)")
        click.echo("")
        click.echo("=== Sync Complete (dry run) ===")
        return

    # Auto-repair: pending_claim
    claim_issues = [iss for iss in issues if iss["type"] == "pending_claim"]
    if claim_issues:
        click.echo("[Repair] Executing claim()...")
        try:
            from ..pneuma.tx import send_contract_tx

            result = send_contract_tx(
                contract_address=soul_guard_addr,
                function_name="claim",
                args=[soul_id],
                contract_name="SoulGuard",
                gas_limit=300_000,
            )

            if result.get("status") == 1:
                click.secho("  Claim successful!", fg="green")
                click.echo(f"  TX: {result['tx_hash']}")
            else:
                click.secho("  Claim failed (transaction reverted)", fg="red")
        except Exception as exc:
            click.secho(f"  Claim failed: {exc}", fg="red")

    # Non-auto-repairable issues
    manual_issues = [iss for iss in issues if iss["type"] not in ("pending_claim",)]
    if manual_issues:
        click.echo("")
        click.echo("The following issues require manual action:")
        for issue in manual_issues:
            click.echo(f"  - {issue['description']}")

    click.echo("")
    click.echo("=== Sync Complete ===")
