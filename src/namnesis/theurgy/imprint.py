"""
Imprint - Upload memory to R2 + update on-chain metadata.

No client-side encryption.  Files are stored as signed plaintext blobs.
The Relay enforces access control via NFT ownership verification.

Flow:
1. Package memory (sign manifest with ECDSA wallet)
2. Authenticate with Relay (ECDSA-signed presigned URLs)
3. Upload blobs to R2
4. Update SoulToken metadata on-chain (client pays gas)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import click

from ..sigil.eth import get_address, load_private_key
from ..anamnesis.capsule import (
    AccessControl,
    CapsuleError,
    ExportOptions,
    export_capsule,
)
from ..anamnesis.compression import CompressionOptions, get_compression_info
from ..anamnesis.storage import PresignedUrlBackend
from ..spec.redaction import RedactionPolicy


@click.command()
@click.option("--workspace", "-w", default=".", help="Workspace path to export")
@click.option("--soul-id", required=True, type=int, help="Soul NFT token ID")
@click.option(
    "--credential-service",
    default="https://namnesis-api.channing-lucchi.workers.dev",
    envvar="NAMNESIS_CREDENTIAL_SERVICE",
    help="Credential service URL",
)
@click.option("--compress/--no-compress", default=False, help="Enable 7z compression")
@click.option(
    "--rpc-url",
    envvar="BASE_SEPOLIA_RPC",
    default="https://sepolia.base.org",
    help="Base Sepolia RPC URL",
)
@click.option("--skip-chain-update", is_flag=True, help="Skip on-chain metadata update")
def imprint(
    workspace: str,
    soul_id: int,
    credential_service: str,
    compress: bool,
    rpc_url: str,
    skip_chain_update: bool,
) -> None:
    """Upload memory to R2 and update on-chain metadata."""
    click.echo("=== Namnesis Imprint ===")
    click.echo("")

    os.environ["BASE_SEPOLIA_RPC"] = rpc_url
    workspace_path = Path(workspace).resolve()

    if not workspace_path.exists():
        click.secho(f"Workspace not found: {workspace_path}", fg="red")
        sys.exit(1)

    # Load wallet
    try:
        private_key_hex = load_private_key()
        address = get_address(private_key_hex)
    except (ValueError, FileNotFoundError) as exc:
        click.secho(f"ERROR: {exc}", fg="red")
        click.echo("Run 'namnesis genesis' first.")
        sys.exit(1)

    click.echo(f"  Address:   {address}")
    click.echo(f"  Soul ID:   {soul_id}")
    click.echo(f"  Workspace: {workspace_path}")
    click.echo("")

    # Storage backend
    backend = PresignedUrlBackend(
        credential_service_url=credential_service,
        private_key_hex=private_key_hex,
    )

    compression_opts = CompressionOptions(enabled=compress, algorithm="7z", level=9)

    if compress:
        comp_info = get_compression_info()
        if not comp_info["available"]:
            click.secho("7z compression requires py7zr.", fg="red")
            sys.exit(1)

    access = AccessControl(owner=address, public=False)

    options = ExportOptions(
        workspace=workspace_path,
        backend=backend,
        private_key_hex=private_key_hex,
        policy=RedactionPolicy.openclaw_default(),
        strict=True,
        compression=compression_opts,
        access=access,
    )

    # Export
    click.echo("[Upload] Packaging and uploading memory...")
    try:
        capsule_id, manifest = export_capsule(options)
        artifact_count = len(manifest.get("artifacts", []))
        click.secho(f"  Capsule ID: {capsule_id}", fg="green")
        click.echo(f"  Artifacts:  {artifact_count}")
    except CapsuleError as exc:
        click.secho(f"Export failed: {exc}", fg="red")
        sys.exit(exc.exit_code)

    # On-chain metadata update
    if not skip_chain_update:
        click.echo("")
        click.echo("[On-chain] Updating SoulToken metadata...")
        try:
            total_size = sum(a.get("size_bytes", 0) for a in manifest.get("artifacts", []))
            from ..pneuma.rpc import read_contract

            soul_token_addr = os.environ.get("SOUL_TOKEN_ADDRESS")
            if not soul_token_addr:
                click.secho("WARNING: SOUL_TOKEN_ADDRESS not set, skipping chain update", fg="yellow")
            else:
                current_cycles = read_contract(
                    soul_token_addr, "samsaraCycles", [soul_id], contract_name="SoulToken",
                )
                new_cycles = (current_cycles or 0) + 1
                from ..pneuma.tx import send_contract_tx

                result = send_contract_tx(
                    contract_address=soul_token_addr,
                    function_name="updateMetadata",
                    args=[soul_id, new_cycles, total_size],
                    contract_name="SoulToken",
                    gas_limit=100_000,
                )
                if result.get("status") == 1:
                    click.secho("  Metadata updated on-chain!", fg="green")
                    click.echo(f"  TX: {result['tx_hash']}")
                    click.echo(f"  Cycles: {new_cycles}, Size: {total_size}")
                else:
                    click.secho("  WARNING: Metadata update failed", fg="yellow")
        except Exception as exc:
            click.secho(f"  WARNING: Chain update failed: {exc}", fg="yellow")
            click.echo("  Memory was uploaded successfully, but on-chain metadata not updated.")
            click.echo("  Run 'namnesis sync' to retry.")

    click.echo("")
    click.echo("=== Imprint Complete ===")
