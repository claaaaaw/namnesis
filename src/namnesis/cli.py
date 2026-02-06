"""
Namnesis CLI

Command-line interface for the Namnesis Sovereign AI Agent Protocol.

Identity = ECDSA/secp256k1 wallet.  No encryption — data confidentiality
is handled by Relay access control (NFT ownership gate + presigned URLs).
Manifest ECDSA signatures guarantee integrity.

Commands:
  genesis   - Create a new sovereign AI agent (wallet + NFT)
  imprint   - Upload memory
  recall    - Download memory
  divine    - Query on-chain status
  claim     - Claim kernel after NFT transfer
  invoke    - Execute arbitrary on-chain calls
  sync      - Repair chain / identity inconsistencies
  whoami    - Show current wallet address
  info      - Show system information
  validate  - Validate capsule integrity
  cache     - Manage URL cache
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

import click

from .sigil.eth import get_address, load_private_key, NAMNESIS_DIR
from .anamnesis.capsule import (
    CapsuleError,
    ValidateOptions,
    validate_capsule,
)
from .anamnesis.compression import get_compression_info
from .anamnesis.storage import LocalDirBackend, PresignedUrlBackend
from .anamnesis.url_cache import PresignedUrlCache


# ============ Constants ============

VERSION = "2.0.0"


# ============ Banner ============


def _print_banner(compact: bool = False) -> None:
    """Print the Namnesis CLI banner.

    Args:
        compact: If True, print a single-line banner (for subcommands).
    """
    if compact:
        click.echo(
            click.style("  ◆ ", fg="cyan")
            + click.style("N A M N E S I S", fg="bright_white", bold=True)
            + click.style(f"  v{VERSION}", dim=True)
        )
        click.echo()
        return

    border = click.style("  ◆ ═══════════════════════════════════════ ◆", fg="cyan")
    click.echo()
    click.echo(border)
    click.echo()
    click.echo(
        click.style("        N A M N E S I S", fg="bright_white", bold=True)
        + click.style(f"        v{VERSION}", dim=True)
    )
    click.secho("        ─── Sovereign AI Agent Protocol ───", fg="cyan")
    click.echo()
    click.echo(border)
    click.echo()


# ============ Main CLI Group ============


@click.group(invoke_without_command=True)
@click.version_option(version=VERSION, prog_name="namnesis")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Namnesis — Sovereign AI Agent Protocol."""
    if ctx.invoked_subcommand is None:
        _print_banner()
        click.echo(ctx.get_help())


# ============ Top-level Commands ============

from .theurgy.genesis import genesis
from .theurgy.claim import claim
from .theurgy.invoke import invoke
from .theurgy.imprint import imprint
from .theurgy.recall import recall
from .theurgy.divine import divine
from .theurgy.sync import sync

cli.add_command(genesis)
cli.add_command(imprint)
cli.add_command(recall)
cli.add_command(divine)
cli.add_command(claim)
cli.add_command(invoke)
cli.add_command(sync)


# ============ Identity ============


@cli.command()
def whoami() -> None:
    """Show current wallet identity."""
    try:
        pk = load_private_key()
        address = get_address(pk)
        click.echo(f"Address: {address}")
    except (ValueError, FileNotFoundError):
        click.echo("No wallet found.")
        click.echo("Run 'namnesis genesis' to create one.")
        sys.exit(1)


# ============ Validate ============


@cli.command()
@click.option("--capsule-id", required=True, help="Capsule ID to validate")
@click.option("--path", "-p", help="Local capsule path (if local)")
@click.option(
    "--trusted-signer",
    required=True,
    help="Trusted signer address (0x...) or 'self' or file:PATH",
)
@click.option(
    "--credential-service",
    default="https://namnesis-api.channing-lucchi.workers.dev",
    envvar="NAMNESIS_CREDENTIAL_SERVICE",
    help="Credential service URL",
)
def validate(
    capsule_id: str,
    path: Optional[str],
    trusted_signer: str,
    credential_service: str,
) -> None:
    """Validate capsule integrity and signature."""
    if path:
        local_path = Path(path).resolve()
        backend = LocalDirBackend(root=local_path)
    else:
        try:
            private_key_hex = load_private_key()
        except (ValueError, FileNotFoundError):
            click.echo("Wallet required for remote validation.")
            click.echo("Run 'namnesis genesis' first.")
            sys.exit(1)
        backend = PresignedUrlBackend(
            credential_service_url=credential_service,
            private_key_hex=private_key_hex,
        )

    trusted_addresses = _resolve_trusted_signer(trusted_signer)

    options = ValidateOptions(
        capsule_id=capsule_id,
        backend=backend,
        trusted_fingerprints=trusted_addresses,
    )

    try:
        validate_capsule(options)
        click.echo("Validation passed!")
        click.echo("  - Signature: valid")
        click.echo("  - Blobs: hash verified")
    except CapsuleError as exc:
        click.echo(f"Validation failed: {exc}")
        sys.exit(exc.exit_code)


# ============ Cache Management ============


@cli.group()
def cache() -> None:
    """Manage URL cache."""
    pass


@cache.command("clear")
@click.option("--capsule-id", help="Clear specific capsule cache only")
def cache_clear(capsule_id: Optional[str]) -> None:
    """Clear cached presigned URLs."""
    url_cache = PresignedUrlCache()
    url_cache.clear(capsule_id)
    if capsule_id:
        click.echo(f"Cleared cache for: {capsule_id}")
    else:
        click.echo("Cache cleared.")


@cache.command("info")
def cache_info() -> None:
    """Show cache status."""
    url_cache = PresignedUrlCache()
    entries = url_cache.list_cached()

    if not entries:
        click.echo("No cached URLs.")
        return

    click.echo(f"Cached URLs: {len(entries)}")
    for entry in entries:
        status = entry.get("status", "unknown")
        cid = entry.get("capsule_id", "unknown")
        remaining = entry.get("remaining_seconds", 0)
        if status == "valid":
            click.echo(f"  {cid}: {status} ({remaining}s remaining)")
        else:
            click.echo(f"  {cid}: {status}")


# ============ Info ============


@cli.command()
def info() -> None:
    """Show system information."""
    _print_banner()

    # ── Status ──
    click.secho("  Status ─────────────────────────────────", fg="cyan")
    click.echo()

    try:
        pk = load_private_key()
        address = get_address(pk)
        click.echo(
            click.style("  Address:     ", dim=True)
            + click.style(address, fg="bright_white")
        )
    except Exception:
        click.echo(
            click.style("  Address:     ", dim=True)
            + click.style("not initialized", fg="yellow")
            + click.style("  (run: namnesis genesis)", dim=True)
        )

    comp_info = get_compression_info()
    if comp_info["available"]:
        comp_text = click.style(
            f"available (py7zr {comp_info.get('py7zr_version', '?')})",
            fg="green",
        )
    else:
        comp_text = click.style("not available", fg="yellow") + click.style("  (pip install py7zr)", dim=True)
    click.echo(click.style("  Compression: ", dim=True) + comp_text)

    url_cache = PresignedUrlCache()
    entries = url_cache.list_cached()
    valid_count = sum(1 for e in entries if e.get("status") == "valid")
    click.echo(
        click.style("  URL Cache:   ", dim=True)
        + click.style(f"{valid_count} valid entries", fg="bright_white")
    )

    click.echo()

    # ── Commands ──
    click.secho("  Commands ───────────────────────────────", fg="cyan")
    click.echo()

    commands = [
        ("genesis ", "Create a new sovereign agent"),
        ("imprint ", "Upload memory to the cloud"),
        ("recall  ", "Restore memory from backup"),
        ("divine  ", "Query on-chain Soul status"),
        ("claim   ", "Claim kernel after NFT transfer"),
        ("invoke  ", "Execute arbitrary on-chain call"),
        ("sync    ", "Repair wallet / chain state"),
        ("validate", "Verify capsule integrity"),
        ("whoami  ", "Show current wallet address"),
    ]
    for cmd, desc in commands:
        click.echo(
            click.style("  ", dim=True)
            + click.style(cmd, fg="bright_white", bold=True)
            + click.style("  ◇  ", fg="cyan")
            + click.style(desc, dim=True)
        )

    click.echo()


# ============ Helper Functions ============


def _resolve_trusted_signer(source: str) -> set[str]:
    """Resolve trusted signer addresses."""
    if source.lower() == "self":
        try:
            pk = load_private_key()
            return {get_address(pk)}
        except (ValueError, FileNotFoundError):
            click.echo("Cannot resolve 'self' — wallet not found.")
            sys.exit(1)
    if source.startswith("file:"):
        file_path = Path(source[5:]).expanduser()
        if not file_path.exists():
            click.echo(f"Trusted signer file not found: {file_path}")
            sys.exit(1)
        content = file_path.read_text(encoding="utf-8")
        return {line.strip() for line in content.splitlines() if line.strip()}
    return {source}


# ============ Entry Points ============


def main() -> None:
    """Namnesis CLI entry point."""
    # Ensure UTF-8 output on Windows (for Unicode box-drawing / symbols)
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
            sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
        except (AttributeError, OSError):
            pass  # Fallback: old Python or non-tty
    cli()


if __name__ == "__main__":
    main()
