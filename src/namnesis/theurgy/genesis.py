"""
Genesis - Create a new sovereign AI agent.

Single entry point for identity initialisation.  Identity is a single
ECDSA/secp256k1 wallet key — the same key signs capsule manifests, authenticates
with the Relay, and sends on-chain transactions.

Flow:
1. Generate ECDSA wallet if not exists
2. Mint Soul NFT (client pays gas) unless --skip-mint
3. Deploy NamnesisKernel smart account (AA wallet) unless --skip-kernel
4. Install OwnableExecutor on Kernel (for SoulGuard claim support)
5. Register Kernel with SoulGuard
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
    "OWNABLE_EXECUTOR_ADDRESS": "0x4Fd8d57b94966982B62e9588C27B4171B55E8354",
    "USDC_ADDRESS": "0x036CbD53842c5426634e7929541eC2318f3dCF7e",
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


def _save_env_value(key: str, value: str) -> None:
    """Save a single key=value to ~/.namnesis/.env (preserving other entries)."""
    env_path = NAMNESIS_ENV
    existing: dict[str, str] = {}
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and "=" in stripped:
                k, v = stripped.split("=", 1)
                existing[k.strip()] = v.strip()

    existing[key] = value
    lines = [f"{k}={v}" for k, v in existing.items()]
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.environ[key] = value


def _parse_token_id_from_receipt(receipt: dict) -> int | None:
    """Parse the minted token ID from a SoulToken.mint() receipt.

    SoulToken inherits ERC-721, so minting emits a Transfer(from, to, tokenId)
    event.  The topic layout is:
        topics[0] = keccak256("Transfer(address,address,uint256)")
        topics[1] = from (zero address for mint)
        topics[2] = to
        topics[3] = tokenId

    Returns the tokenId as int, or None if not found.
    """
    # Transfer event signature hash
    transfer_sig = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
    zero_topic = "0x" + "0" * 64

    for log in receipt.get("logs", []):
        topics = log.get("topics", [])
        if (
            len(topics) >= 4
            and topics[0].lower() == transfer_sig.lower()
            and topics[1].lower() == zero_topic.lower()
        ):
            return int(topics[3], 16)

    return None


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
    help="Only generate wallet key, skip NFT minting and kernel deployment",
)
@click.option(
    "--skip-kernel",
    is_flag=True,
    help="Skip Kernel (AA wallet) deployment — mint only",
)
def genesis(rpc_url: str, skip_mint: bool, skip_kernel: bool) -> None:
    """Create a new sovereign AI agent.

    Generates a wallet identity, mints a Soul NFT on-chain, deploys a
    NamnesisKernel smart account (AA wallet), and registers it with
    SoulGuard.

    Use --skip-mint to only generate the key (e.g. for offline testing).
    Use --skip-kernel to only generate identity + mint (no AA wallet).
    """
    total_steps = 2 if skip_kernel else 4

    click.echo()
    click.echo(
        click.style("  ◆ ", fg="cyan")
        + click.style("Genesis", fg="bright_white", bold=True)
        + click.style(" ─── Create a new sovereign agent", fg="cyan")
    )
    click.echo()

    # --- Step 1: Identity (ECDSA wallet) ---
    click.secho(f"  [1/{total_steps}] Preparing identity...", fg="bright_white")
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
    click.secho(f"  [2/{total_steps}] Minting Soul NFT...", fg="bright_white")
    click.echo(click.style("        RPC: ", dim=True) + rpc_url)

    soul_id: int | None = None

    try:
        os.environ["BASE_SEPOLIA_RPC"] = rpc_url
        from ..pneuma.tx import send_contract_tx, deploy_contract
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
            # Parse token ID from Transfer event logs
            soul_id = _parse_token_id_from_receipt(result.get("receipt", {}))

            click.echo()
            click.secho("        Soul NFT minted!", fg="green", bold=True)
            click.echo(click.style("        TX: ", dim=True) + tx_hash)
            if soul_id is not None:
                click.echo(click.style("        Soul ID: ", dim=True) + str(soul_id))
                _save_env_value("SOUL_ID", str(soul_id))
            else:
                click.echo(click.style("        Soul ID: ", dim=True) + "(check transaction logs)")
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

    # --- Step 3+4: Deploy Kernel & Register ---
    if skip_kernel:
        click.echo()
        click.echo(
            click.style("  ◆ ", fg="green")
            + click.style("Genesis Complete", fg="green", bold=True)
            + click.style(" (no kernel)", dim=True)
        )
        click.echo()
        click.secho("  Next steps:", fg="cyan")
        click.echo("    1. Run 'namnesis divine --soul-id <ID>' to check status")
        click.echo("    2. Run 'namnesis imprint' to upload memory")
        click.echo()
        return

    if soul_id is None:
        click.secho(
            "\n        Cannot deploy Kernel: Soul ID could not be parsed from mint logs.",
            fg="red",
        )
        click.echo("        Run 'namnesis divine' to find your Soul ID, then re-deploy manually.")
        sys.exit(1)

    # --- Step 3: Deploy NamnesisKernel ---
    click.echo()
    click.secho(f"  [3/{total_steps}] Deploying NamnesisKernel (AA wallet)...", fg="bright_white")

    try:
        deploy_result = deploy_contract(
            contract_name="NamnesisKernel",
            constructor_args=[address],
            gas_limit=1_500_000,
        )

        if deploy_result.get("status") != 1:
            click.secho("        Kernel deployment reverted", fg="red")
            click.echo(click.style("        TX: ", dim=True) + deploy_result.get("tx_hash", "unknown"))
            sys.exit(1)

        kernel_address = deploy_result.get("contract_address")
        if not kernel_address:
            click.secho("        Could not extract Kernel address from receipt", fg="red")
            sys.exit(1)

        click.secho("        Kernel deployed!", fg="green", bold=True)
        click.echo(click.style("        Address: ", dim=True) + kernel_address)
        click.echo(click.style("        TX: ", dim=True) + deploy_result["tx_hash"])
        _save_env_value("KERNEL_ADDRESS", kernel_address)

    except Exception as exc:
        click.secho(f"        Kernel deployment failed: {exc}", fg="red")
        sys.exit(1)

    # --- Step 4: Install OwnableExecutor + Register with SoulGuard ---
    click.echo()
    click.secho(f"  [4/{total_steps}] Registering Kernel with SoulGuard...", fg="bright_white")

    try:
        ownable_executor_addr = _get_contract_address("OWNABLE_EXECUTOR")
        soul_guard_addr = _get_contract_address("SOUL_GUARD")

        # 4a. Install OwnableExecutor on Kernel
        #     initData = abi.encodePacked(soulGuardAddress)
        #     This registers SoulGuard as the executor's owner for this kernel.
        click.echo(click.style("        Installing OwnableExecutor...", dim=True))
        init_data = bytes.fromhex(soul_guard_addr[2:].lower().zfill(40))

        install_result = send_contract_tx(
            contract_address=kernel_address,
            function_name="installExecutor",
            args=[ownable_executor_addr, init_data],
            contract_name="NamnesisKernel",
            gas_limit=300_000,
        )

        if install_result.get("status") != 1:
            click.secho("        installExecutor reverted", fg="red")
            click.echo(click.style("        TX: ", dim=True) + install_result.get("tx_hash", "unknown"))
            sys.exit(1)

        click.secho("        OwnableExecutor installed!", fg="green")

        # 4b. Register Kernel with SoulGuard
        click.echo(click.style("        Registering with SoulGuard...", dim=True))

        register_result = send_contract_tx(
            contract_address=soul_guard_addr,
            function_name="register",
            args=[soul_id, kernel_address],
            contract_name="SoulGuard",
            gas_limit=200_000,
        )

        if register_result.get("status") != 1:
            click.secho("        SoulGuard.register reverted", fg="red")
            click.echo(click.style("        TX: ", dim=True) + register_result.get("tx_hash", "unknown"))
            sys.exit(1)

        click.secho("        Kernel registered with SoulGuard!", fg="green")

    except Exception as exc:
        click.secho(f"        Registration failed: {exc}", fg="red")
        sys.exit(1)

    # --- Done ---
    click.echo()
    click.echo(
        click.style("  ◆ ", fg="green")
        + click.style("Genesis Complete", fg="green", bold=True)
    )
    click.echo()
    click.secho("  Summary:", fg="cyan")
    click.echo(f"    EOA Address:    {address}")
    click.echo(f"    Soul ID:        {soul_id}")
    click.echo(f"    Kernel Address: {kernel_address}")
    click.echo()
    click.secho("  Next steps:", fg="cyan")
    click.echo(f"    1. Run 'namnesis divine --soul-id {soul_id}' to check status")
    click.echo("    2. Run 'namnesis imprint' to upload memory")
    click.echo(f"    3. Fund Kernel with testnet USDC: {kernel_address}")
    click.echo("    4. Run 'namnesis usdc balance' to check USDC balance")
    click.echo()


def _get_contract_address(name: str) -> str:
    """Get contract address from environment."""
    addr = os.environ.get(f"{name}_ADDRESS")
    if not addr:
        raise click.ClickException(
            f"{name}_ADDRESS not set. Set it in {NAMNESIS_ENV} or environment."
        )
    return addr
