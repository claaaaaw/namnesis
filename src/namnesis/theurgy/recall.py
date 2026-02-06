"""
Recall - Download memory from R2.

No client-side decryption — data is plaintext.  Relay enforces access
control via ECDSA authentication + NFT ownership verification.

Flow:
1. Authenticate with Relay (ECDSA-signed presigned URLs)
2. Download blobs from R2
3. Verify manifest ECDSA signature against trusted address
4. Restore files to target workspace
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import click

from ..sigil.eth import load_private_key
from ..anamnesis.capsule import (
    CapsuleError,
    ImportOptions,
    import_capsule,
)
from ..anamnesis.storage import PresignedUrlBackend, LocalDirBackend


@click.command()
@click.option("--capsule-id", required=True, help="Capsule ID (address/uuid)")
@click.option("--to", "target", required=True, help="Target workspace path")
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
@click.option("--overwrite", is_flag=True, help="Overwrite existing files")
@click.option("--partial", is_flag=True, help="Continue on errors")
@click.option("--local-path", default=None, help="Local capsule path (skip remote)")
def recall(
    capsule_id: str,
    target: str,
    trusted_signer: str,
    credential_service: str,
    overwrite: bool,
    partial: bool,
    local_path: str,
) -> None:
    """Download and restore memory.

    Retrieves a capsule, verifies the ECDSA signature against a trusted
    wallet address, and restores files into the target workspace.
    """
    click.echo("=== Namnesis Recall ===")
    click.echo("")

    target_path = Path(target).resolve()

    # Resolve trusted signer
    if trusted_signer.startswith("file:"):
        fp_path = Path(trusted_signer[5:]).expanduser()
        if not fp_path.exists():
            click.secho(f"Trusted signer file not found: {fp_path}", fg="red")
            sys.exit(1)
        content = fp_path.read_text(encoding="utf-8")
        trusted_addresses = {line.strip() for line in content.splitlines() if line.strip()}
    elif trusted_signer.lower() == "self":
        try:
            from ..sigil.eth import get_address
            pk = load_private_key()
            trusted_addresses = {get_address(pk)}
        except (ValueError, FileNotFoundError):
            click.secho("Cannot resolve 'self' — wallet not found.", fg="red")
            sys.exit(1)
    else:
        trusted_addresses = {trusted_signer}

    # Select backend
    if local_path:
        lp = Path(local_path).resolve()
        backend = LocalDirBackend(root=lp.parent.parent)
        click.echo(f"  Source: local ({lp})")
    else:
        try:
            private_key_hex = load_private_key()
        except (ValueError, FileNotFoundError):
            click.secho("ERROR: Wallet not found.", fg="red")
            click.echo("Run 'namnesis genesis' first.")
            sys.exit(1)
        backend = PresignedUrlBackend(
            credential_service_url=credential_service,
            private_key_hex=private_key_hex,
        )
        click.echo(f"  Source: remote ({credential_service})")

    click.echo(f"  Capsule: {capsule_id}")
    click.echo(f"  Target:  {target_path}")
    click.echo("")

    options = ImportOptions(
        capsule_id=capsule_id,
        backend=backend,
        target_workspace=target_path,
        trusted_fingerprints=trusted_addresses,
        overwrite=overwrite,
        partial=partial,
    )

    click.echo("[Download] Retrieving memory...")
    try:
        report = import_capsule(options)
        results = report.get("results", {})
        created = len(results.get("created", []))
        skipped = len(results.get("skipped", []))
        failed = len(results.get("failed", []))

        click.echo("")
        click.secho(
            f"  Recall complete! Created: {created}, Skipped: {skipped}, Failed: {failed}",
            fg="green",
        )

        if failed > 0:
            click.secho(f"  WARNING: {failed} files failed to restore", fg="yellow")
            for f in results.get("failed", []):
                click.echo(f"    - {f.get('path')}: {f.get('error')}")

    except CapsuleError as exc:
        click.secho(f"Recall failed: {exc}", fg="red")
        sys.exit(exc.exit_code)

    click.echo("")
    click.echo("=== Recall Complete ===")
