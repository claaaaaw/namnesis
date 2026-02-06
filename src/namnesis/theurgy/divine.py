"""
Theurgy Divine - Query on-chain status and detect risks.

Reads on-chain metadata from SoulToken and SoulGuard, displays
comprehensive status including:
- NFT ownership
- Kernel address
- Samsara cycles and memory size
- Pending claim detection (ownership desync warning)
- Lobotomy risk detection (high cycles, low memory)
"""

from __future__ import annotations

import os
import sys

import click

from ..sigil.eth import get_address, load_private_key


@click.command()
@click.option("--soul-id", required=True, type=int, help="Soul NFT token ID")
@click.option(
    "--rpc-url",
    envvar="BASE_SEPOLIA_RPC",
    default="https://sepolia.base.org",
    help="Base Sepolia RPC URL",
)
def divine(soul_id: int, rpc_url: str) -> None:
    """
    Query on-chain status and detect risks.

    Shows comprehensive information about a Soul including ownership,
    memory statistics, and security warnings.
    """
    click.echo("=== Namnesis Divine ===")
    click.echo("")

    os.environ["BASE_SEPOLIA_RPC"] = rpc_url

    soul_token_addr = os.environ.get("SOUL_TOKEN_ADDRESS")
    soul_guard_addr = os.environ.get("SOUL_GUARD_ADDRESS")

    if not soul_token_addr or not soul_guard_addr:
        click.secho(
            "ERROR: SOUL_TOKEN_ADDRESS and SOUL_GUARD_ADDRESS must be set.",
            fg="red",
        )
        sys.exit(1)

    from ..pneuma.rpc import read_contract, get_balance

    try:
        # Read SoulToken metadata
        owner = read_contract(
            soul_token_addr, "ownerOf", [soul_id], contract_name="SoulToken"
        )
        cycles = read_contract(
            soul_token_addr, "samsaraCycles", [soul_id], contract_name="SoulToken"
        )
        size = read_contract(
            soul_token_addr, "memorySize", [soul_id], contract_name="SoulToken"
        )
        last_updated = read_contract(
            soul_token_addr, "lastUpdated", [soul_id], contract_name="SoulToken"
        )

        # Read SoulGuard data
        kernel = read_contract(
            soul_guard_addr, "soulToKernel", [soul_id], contract_name="SoulGuard"
        )
        confirmed_owner = read_contract(
            soul_guard_addr, "confirmedOwner", [soul_id], contract_name="SoulGuard"
        )
        pending = read_contract(
            soul_guard_addr, "isPendingClaim", [soul_id], contract_name="SoulGuard"
        )
        in_window = read_contract(
            soul_guard_addr, "isInClaimWindow", [soul_id], contract_name="SoulGuard"
        )

    except Exception as exc:
        click.secho(f"ERROR: Failed to read on-chain data: {exc}", fg="red")
        sys.exit(1)

    # Display info
    click.echo(f"  Soul #{soul_id}")
    click.echo(f"  ─────────────────────────────")
    click.echo(f"  NFT Owner:        {owner}")
    click.echo(f"  Confirmed Owner:  {confirmed_owner}")

    # Kernel info
    zero_addr = "0x" + "0" * 40
    if kernel and str(kernel) != zero_addr:
        click.echo(f"  Kernel:           {kernel}")
        try:
            kernel_balance = get_balance(str(kernel))
            click.echo(f"  Kernel ETH:       {kernel_balance / 1e18:.6f} ETH")
        except Exception:
            click.echo("  Kernel ETH:       (unable to read)")

        # Show Kernel USDC balance if USDC_ADDRESS is configured
        usdc_addr = os.environ.get("USDC_ADDRESS")
        if usdc_addr:
            try:
                _erc20_balance_abi = [
                    {
                        "type": "function",
                        "name": "balanceOf",
                        "inputs": [{"name": "account", "type": "address"}],
                        "outputs": [{"name": "", "type": "uint256"}],
                        "stateMutability": "view",
                    },
                ]
                usdc_bal = read_contract(
                    usdc_addr, "balanceOf", [str(kernel)], abi=_erc20_balance_abi
                )
                usdc_bal = usdc_bal or 0
                usdc_human = usdc_bal / 1e6  # USDC has 6 decimals
                click.echo(f"  Kernel USDC:      {usdc_human:,.6f} USDC")
            except Exception:
                click.echo("  Kernel USDC:      (unable to read)")
    else:
        click.echo("  Kernel:           (not registered)")

    click.echo(f"  Samsara Cycles:   {cycles or 0}")
    click.echo(f"  Memory Size:      {size or 0} bytes")

    if last_updated and last_updated > 0:
        import datetime
        ts = datetime.datetime.fromtimestamp(last_updated, tz=datetime.timezone.utc)
        click.echo(f"  Last Updated:     {ts.isoformat()}")
    else:
        click.echo("  Last Updated:     never")

    # Security checks
    click.echo("")

    # Check if current user owns this soul
    try:
        private_key = load_private_key()
        my_address = get_address(private_key)
        if str(owner).lower() == my_address.lower():
            click.secho("  [YOU OWN THIS SOUL]", fg="green", bold=True)
        else:
            click.echo(f"  Your address: {my_address}")
    except (ValueError, FileNotFoundError):
        pass

    # Pending Claim detection
    if pending:
        click.echo("")
        click.secho("  ⚠ WARNING: Pending Claim Detected!", fg="yellow", bold=True)
        click.secho(
            "  NFT ownership has changed but claim() not yet called.",
            fg="yellow",
        )
        click.secho(
            f"  Run 'namnesis claim --soul-id {soul_id}' immediately.",
            fg="yellow",
        )

    # Claim window check
    if in_window:
        click.echo("")
        click.secho("  INFO: Within claim safety window.", fg="cyan")

    # Lobotomy risk detection
    if cycles and size is not None:
        if cycles > 5 and (size or 0) < 1024:
            click.echo("")
            click.secho(
                "  ⚠ WARNING: Lobotomy Risk Detected!",
                fg="red",
                bold=True,
            )
            click.secho(
                "  High cycle count with minimal memory.",
                fg="red",
            )
            click.secho(
                "  This Soul may have been intentionally wiped.",
                fg="red",
            )

    click.echo("")
    click.echo("=== Divine Complete ===")
