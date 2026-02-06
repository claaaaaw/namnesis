"""
Theurgy Invoke - Execute on-chain operations.

Generic command for executing contract calls through the Kernel
or directly from the EOA.
"""

from __future__ import annotations

import os
import sys
import json

import click

from ..sigil.eth import get_address, load_private_key
from ..pneuma.tx import send_contract_tx


@click.command()
@click.option("--contract", required=True, help="Target contract address")
@click.option("--function", "func_name", required=True, help="Function name to call")
@click.option("--args", "args_json", default="[]", help="Function args as JSON array")
@click.option("--abi-name", default=None, help="Contract name for ABI loading")
@click.option("--value", default=0, type=int, help="ETH value in wei")
@click.option("--gas-limit", default=500_000, type=int, help="Gas limit")
@click.option(
    "--rpc-url",
    envvar="BASE_SEPOLIA_RPC",
    default="https://sepolia.base.org",
    help="Base Sepolia RPC URL",
)
def invoke(
    contract: str,
    func_name: str,
    args_json: str,
    abi_name: str,
    value: int,
    gas_limit: int,
    rpc_url: str,
) -> None:
    """
    Execute an on-chain contract call.

    Sends a transaction from your EOA to the specified contract.
    Client pays gas.
    """
    click.echo("=== Namnesis Invoke ===")
    click.echo("")

    os.environ["BASE_SEPOLIA_RPC"] = rpc_url

    # Parse args
    try:
        args = json.loads(args_json)
        if not isinstance(args, list):
            raise ValueError("Args must be a JSON array")
    except (json.JSONDecodeError, ValueError) as exc:
        click.secho(f"ERROR: Invalid args: {exc}", fg="red")
        sys.exit(1)

    # Load account
    try:
        private_key = load_private_key()
        address = get_address(private_key)
    except (ValueError, FileNotFoundError) as exc:
        click.secho(f"ERROR: {exc}", fg="red")
        sys.exit(1)

    click.echo(f"  Sender: {address}")
    click.echo(f"  Target: {contract}")
    click.echo(f"  Function: {func_name}")
    click.echo(f"  Args: {args}")
    if value > 0:
        click.echo(f"  Value: {value} wei")
    click.echo("")

    # Send transaction
    try:
        result = send_contract_tx(
            contract_address=contract,
            function_name=func_name,
            args=args,
            contract_name=abi_name,
            value=value,
            gas_limit=gas_limit,
        )

        if result.get("status") == 1:
            click.secho("SUCCESS: Transaction confirmed!", fg="green")
            click.echo(f"  TX: {result['tx_hash']}")
        else:
            click.secho("FAILED: Transaction reverted", fg="red")
            click.echo(f"  TX: {result.get('tx_hash', 'unknown')}")
            sys.exit(1)

    except Exception as exc:
        click.secho(f"Transaction failed: {exc}", fg="red")
        sys.exit(1)
