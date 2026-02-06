"""
Theurgy Token - ERC-20 token operations via NamnesisKernel.

Generic commands for any ERC-20 token.  The user supplies the token
contract address with --token (or relies on the USDC_ADDRESS default).

Commands:
- balance:  Show token balance for Kernel and/or EOA
- transfer: Send tokens from Kernel to a recipient
"""

from __future__ import annotations

import os
import sys
from typing import Optional

import click

from ..sigil.eth import get_address, load_private_key, NAMNESIS_ENV

# ---------------------------------------------------------------------------
# Minimal ERC-20 ABI (balanceOf, transfer, decimals, symbol)
# ---------------------------------------------------------------------------
_ERC20_ABI: list[dict] = [
    {
        "type": "function",
        "name": "balanceOf",
        "inputs": [{"name": "account", "type": "address"}],
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
    },
    {
        "type": "function",
        "name": "transfer",
        "inputs": [
            {"name": "to", "type": "address"},
            {"name": "amount", "type": "uint256"},
        ],
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "nonpayable",
    },
    {
        "type": "function",
        "name": "decimals",
        "inputs": [],
        "outputs": [{"name": "", "type": "uint8"}],
        "stateMutability": "view",
    },
    {
        "type": "function",
        "name": "symbol",
        "inputs": [],
        "outputs": [{"name": "", "type": "string"}],
        "stateMutability": "view",
    },
]

# NamnesisKernel.execute(address,uint256,bytes)
_KERNEL_EXECUTE_ABI: list[dict] = [
    {
        "type": "function",
        "name": "execute",
        "inputs": [
            {"name": "target", "type": "address"},
            {"name": "value", "type": "uint256"},
            {"name": "data", "type": "bytes"},
        ],
        "outputs": [{"name": "", "type": "bytes"}],
        "stateMutability": "nonpayable",
    },
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_kernel_address() -> str:
    """Get Kernel contract address from environment."""
    addr = os.environ.get("KERNEL_ADDRESS")
    if not addr:
        raise click.ClickException(
            "KERNEL_ADDRESS not set. Run 'namnesis genesis' to deploy a kernel, "
            f"or set KERNEL_ADDRESS in {NAMNESIS_ENV}."
        )
    return addr


def _resolve_token(token: Optional[str]) -> str:
    """Resolve the token address.

    Priority: --token flag  >  USDC_ADDRESS env var.
    """
    if token:
        return token

    usdc = os.environ.get("USDC_ADDRESS")
    if usdc:
        return usdc

    raise click.ClickException(
        "Token address not specified. Use --token <address> or set USDC_ADDRESS "
        f"in {NAMNESIS_ENV}."
    )


def _query_token_meta(token_address: str) -> tuple[str, int]:
    """Read symbol and decimals from an ERC-20 contract.

    Returns (symbol, decimals).  Falls back to ("???", 18) on error.
    """
    from ..pneuma.rpc import read_contract

    symbol = "???"
    decimals = 18

    try:
        sym = read_contract(token_address, "symbol", [], abi=_ERC20_ABI)
        if sym:
            symbol = str(sym)
    except Exception:
        pass

    try:
        dec = read_contract(token_address, "decimals", [], abi=_ERC20_ABI)
        if dec is not None:
            decimals = int(dec)
    except Exception:
        pass

    return symbol, decimals


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------

@click.group()
@click.option(
    "--rpc-url",
    envvar="BASE_SEPOLIA_RPC",
    default="https://sepolia.base.org",
    help="Base Sepolia RPC URL",
)
@click.pass_context
def token(ctx: click.Context, rpc_url: str) -> None:
    """ERC-20 token operations via NamnesisKernel.

    Query balances or transfer any ERC-20 token through the Kernel smart
    account.  Use --token to specify the token contract address; if omitted
    it defaults to USDC_ADDRESS from config.

    \b
    Examples:
      namnesis token balance
      namnesis token balance --token 0xAbC...
      namnesis token transfer --to 0x... --amount 10
      namnesis token transfer --token 0xAbC... --to 0x... --amount 5.5
    """
    os.environ["BASE_SEPOLIA_RPC"] = rpc_url
    ctx.ensure_object(dict)


# ---------------------------------------------------------------------------
# balance
# ---------------------------------------------------------------------------

@token.command()
@click.option("--token", "token_address", default=None,
              help="ERC-20 token contract address (default: USDC_ADDRESS)")
def balance(token_address: Optional[str]) -> None:
    """Show ERC-20 token balance for Kernel and EOA."""
    from ..pneuma.rpc import read_contract

    try:
        private_key = load_private_key()
        eoa_address = get_address(private_key)
    except (ValueError, FileNotFoundError) as exc:
        click.secho(f"ERROR: {exc}", fg="red")
        click.echo("Run 'namnesis genesis' first.")
        sys.exit(1)

    resolved = _resolve_token(token_address)
    symbol, decimals = _query_token_meta(resolved)

    click.echo(f"=== {symbol} Balance (Base Sepolia) ===")
    click.echo()
    click.echo(click.style("  Token:    ", dim=True) + resolved)
    click.echo(click.style("  Symbol:   ", dim=True) + symbol)
    click.echo(click.style("  Decimals: ", dim=True) + str(decimals))
    click.echo()

    # EOA balance
    try:
        eoa_bal = read_contract(
            resolved, "balanceOf", [eoa_address], abi=_ERC20_ABI
        )
        eoa_bal = eoa_bal or 0
        eoa_human = eoa_bal / (10 ** decimals)
        click.echo(
            click.style("  EOA (", dim=True)
            + click.style(eoa_address[:10] + "...", fg="bright_white")
            + click.style("): ", dim=True)
            + click.style(f"{eoa_human:,.{decimals}f} {symbol}", fg="bright_white")
        )
    except Exception as exc:
        click.echo(
            click.style("  EOA: ", dim=True)
            + click.style(f"(error: {exc})", fg="red")
        )

    # Kernel balance
    try:
        kernel_address = _get_kernel_address()
        kernel_bal = read_contract(
            resolved, "balanceOf", [kernel_address], abi=_ERC20_ABI
        )
        kernel_bal = kernel_bal or 0
        kernel_human = kernel_bal / (10 ** decimals)
        click.echo(
            click.style("  Kernel (", dim=True)
            + click.style(kernel_address[:10] + "...", fg="bright_white")
            + click.style("): ", dim=True)
            + click.style(f"{kernel_human:,.{decimals}f} {symbol}", fg="green", bold=True)
        )
    except click.ClickException:
        click.echo(
            click.style("  Kernel: ", dim=True)
            + click.style("(not deployed — run 'namnesis genesis')", fg="yellow")
        )
    except Exception as exc:
        click.echo(
            click.style("  Kernel: ", dim=True)
            + click.style(f"(error: {exc})", fg="red")
        )

    click.echo()


# ---------------------------------------------------------------------------
# transfer
# ---------------------------------------------------------------------------

@token.command()
@click.option("--token", "token_address", default=None,
              help="ERC-20 token contract address (default: USDC_ADDRESS)")
@click.option("--to", "recipient", required=True,
              help="Recipient address (0x...)")
@click.option("--amount", required=True, type=float,
              help="Amount in human-readable units (e.g. 1.5)")
@click.option("--gas-limit", default=300_000, type=int, help="Gas limit")
def transfer(
    token_address: Optional[str],
    recipient: str,
    amount: float,
    gas_limit: int,
) -> None:
    """Transfer ERC-20 tokens from Kernel to a recipient.

    The Kernel smart account holds tokens and executes the ERC-20
    transfer(to, amount) call on behalf of the owner (EOA).
    The EOA signs the outer transaction and pays gas.

    \b
    Examples:
      namnesis token transfer --to 0xAbc... --amount 10
      namnesis token transfer --token 0xDEF... --to 0xAbc... --amount 5.5
    """
    from ..pneuma.tx import send_contract_tx
    from ..pneuma.rpc import read_contract
    from eth_abi import encode as abi_encode

    try:
        private_key = load_private_key()
        eoa_address = get_address(private_key)
    except (ValueError, FileNotFoundError) as exc:
        click.secho(f"ERROR: {exc}", fg="red")
        sys.exit(1)

    kernel_address = _get_kernel_address()
    resolved = _resolve_token(token_address)
    symbol, decimals = _query_token_meta(resolved)

    # Convert human amount → raw
    raw_amount = int(amount * (10 ** decimals))
    if raw_amount <= 0:
        click.secho("ERROR: Amount must be positive", fg="red")
        sys.exit(1)

    click.echo(f"=== {symbol} Transfer (Base Sepolia) ===")
    click.echo()
    click.echo(click.style("  Token:  ", dim=True) + f"{symbol} ({resolved})")
    click.echo(click.style("  From:   ", dim=True) + f"Kernel ({kernel_address})")
    click.echo(click.style("  To:     ", dim=True) + recipient)
    click.echo(
        click.style("  Amount: ", dim=True)
        + f"{amount} {symbol} ({raw_amount} raw, {decimals} decimals)"
    )
    click.echo(click.style("  Signer: ", dim=True) + f"EOA ({eoa_address})")
    click.echo()

    # Pre-flight: check Kernel balance
    try:
        kernel_bal = read_contract(
            resolved, "balanceOf", [kernel_address], abi=_ERC20_ABI
        )
        kernel_bal = kernel_bal or 0
        if kernel_bal < raw_amount:
            human_bal = kernel_bal / (10 ** decimals)
            click.secho(
                f"  Insufficient balance: {human_bal:,.{decimals}f} {symbol} "
                f"< {amount} {symbol}",
                fg="red",
            )
            click.echo(f"  Fund your Kernel: {kernel_address}")
            sys.exit(1)
    except Exception as exc:
        click.secho(f"  Warning: Could not check balance: {exc}", fg="yellow")

    # Build inner ERC-20 transfer(address,uint256) calldata
    from ..pneuma.rpc import _keccak256

    transfer_selector = _keccak256(b"transfer(address,uint256)")[:4]
    encoded_args = abi_encode(["address", "uint256"], [recipient, raw_amount])
    inner_calldata = transfer_selector + encoded_args

    # Call Kernel.execute(token, 0, inner_calldata) from EOA
    click.echo("  Sending transaction...")

    try:
        result = send_contract_tx(
            contract_address=kernel_address,
            function_name="execute",
            args=[resolved, 0, inner_calldata],
            abi=_KERNEL_EXECUTE_ABI,
            gas_limit=gas_limit,
        )

        if result.get("status") == 1:
            click.echo()
            click.secho("  Transfer successful!", fg="green", bold=True)
            click.echo(click.style("  TX: ", dim=True) + result["tx_hash"])
        else:
            click.secho("  Transfer failed (reverted)", fg="red")
            click.echo(
                click.style("  TX: ", dim=True)
                + result.get("tx_hash", "unknown")
            )
            sys.exit(1)

    except Exception as exc:
        click.secho(f"  Transfer failed: {exc}", fg="red")
        sys.exit(1)

    click.echo()
