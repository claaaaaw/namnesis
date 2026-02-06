"""
CLI integration tests using Click's test runner.

Tests verify that the CLI commands work end-to-end via the Click
CliRunner, without requiring network access or chain interaction.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from namnesis.cli import cli
from namnesis.sigil.eth import generate_eoa, save_private_key


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture()
def namnesis_home(tmp_path: Path) -> Path:
    """Create a temporary ~/.namnesis directory."""
    home = tmp_path / ".namnesis"
    home.mkdir()
    return home


@pytest.fixture()
def wallet(namnesis_home: Path) -> tuple[str, str]:
    """Generate and save a wallet to the temp namnesis home."""
    private_key, address = generate_eoa()
    save_private_key(private_key, namnesis_home / ".env")
    return private_key, address


@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    """Create a minimal workspace for CLI testing."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    (ws / "MEMORY.md").write_text("# Memory\n\nTest memory.\n", encoding="utf-8")
    memory_dir = ws / "memory"
    memory_dir.mkdir()
    (memory_dir / "notes.md").write_text("# Notes\n", encoding="utf-8")
    return ws


class TestVersionAndInfo:
    """Test basic CLI commands that don't require wallet."""

    def test_version(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "2.0.0" in result.output

    def test_info(self, runner: CliRunner, wallet: tuple[str, str], namnesis_home: Path) -> None:
        env_path = str(namnesis_home / ".env")
        with patch("namnesis.sigil.eth.NAMNESIS_ENV", namnesis_home / ".env"):
            with patch.dict(os.environ, {"PRIVATE_KEY": wallet[0]}):
                result = runner.invoke(cli, ["info"])
                assert result.exit_code == 0
                assert "Namnesis v2.0.0" in result.output


class TestWhoami:
    """Test wallet identity display."""

    def test_whoami_with_wallet(self, runner: CliRunner, wallet: tuple[str, str], namnesis_home: Path) -> None:
        with patch("namnesis.sigil.eth.NAMNESIS_ENV", namnesis_home / ".env"):
            with patch.dict(os.environ, {"PRIVATE_KEY": wallet[0]}):
                result = runner.invoke(cli, ["whoami"])
                assert result.exit_code == 0
                assert "Address:" in result.output

    def test_whoami_without_wallet(self, runner: CliRunner) -> None:
        env = {k: v for k, v in os.environ.items() if k != "PRIVATE_KEY"}
        with patch.dict(os.environ, env, clear=True):
            with patch("namnesis.sigil.eth.NAMNESIS_ENV", Path("/nonexistent/.env")):
                result = runner.invoke(cli, ["whoami"])
                assert result.exit_code != 0
                assert "No wallet found" in result.output


class TestGenesis:
    """Test genesis command (skip-mint mode only, no chain)."""

    def test_genesis_skip_mint(self, runner: CliRunner, tmp_path: Path) -> None:
        namnesis_dir = tmp_path / ".namnesis"
        env_path = namnesis_dir / ".env"

        with patch("namnesis.sigil.eth.NAMNESIS_DIR", namnesis_dir):
            with patch("namnesis.sigil.eth.NAMNESIS_ENV", env_path):
                with patch("namnesis.theurgy.genesis.NAMNESIS_DIR", namnesis_dir):
                    with patch("namnesis.theurgy.genesis.NAMNESIS_ENV", env_path):
                        result = runner.invoke(cli, ["genesis", "--skip-mint"])
                        assert result.exit_code == 0
                        assert "Genesis Complete" in result.output
                        assert "Address:" in result.output
                        assert env_path.exists()


class TestValidate:
    """Test validate command with local capsules."""

    def test_validate_local_capsule(
        self, runner: CliRunner, workspace: Path, wallet: tuple[str, str], tmp_path: Path
    ) -> None:
        from namnesis.anamnesis.capsule import ExportOptions, export_capsule
        from namnesis.anamnesis.storage import LocalDirBackend
        from namnesis.spec.redaction import RedactionPolicy

        private_key, address = wallet
        backend_root = tmp_path / "backend"
        backend = LocalDirBackend(backend_root)

        capsule_id, _ = export_capsule(
            ExportOptions(
                workspace=workspace,
                backend=backend,
                private_key_hex=private_key,
                policy=RedactionPolicy.openclaw_default(),
                strict=True,
            )
        )

        with patch.dict(os.environ, {"PRIVATE_KEY": private_key}):
            result = runner.invoke(
                cli,
                [
                    "validate",
                    "--capsule-id", capsule_id,
                    "--path", str(backend_root),
                    "--trusted-signer", address,
                ],
            )
            assert result.exit_code == 0
            assert "Validation passed" in result.output


class TestCacheCommands:
    """Test cache management commands."""

    def test_cache_clear(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["cache", "clear"])
        assert result.exit_code == 0
        assert "cleared" in result.output.lower() or "Cache" in result.output

    def test_cache_info(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["cache", "info"])
        assert result.exit_code == 0
