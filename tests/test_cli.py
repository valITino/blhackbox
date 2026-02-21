"""Tests for CLI commands (v2 architecture).

v2 changes:
  - The ``recon`` command no longer has an ``--ai`` flag.
  - The ``exploit`` command has been removed entirely.
  - The ``agents`` command still exists but refers to HexStrike agents.
"""

from __future__ import annotations

from click.testing import CliRunner

from blhackbox.main import cli


class TestCLI:
    def test_version(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["version"])
        assert result.exit_code == 0
        assert "2.0.0" in result.output

    def test_run_tool_invalid_json(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "run-tool",
                "--category", "network",
                "--tool", "nmap",
                "--params", "not-json",
            ],
        )
        assert result.exit_code != 0

    def test_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Blhackbox" in result.output

    def test_help_lists_recon(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert "recon" in result.output

    def test_help_does_not_list_exploit(self) -> None:
        """The exploit command was removed in v2."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert "exploit" not in result.output


class TestCatalogCommand:
    def test_catalog_displays_tools(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["catalog"])
        assert result.exit_code == 0
        assert "nmap" in result.output
        assert "nuclei" in result.output

    def test_catalog_shows_categories(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["catalog"])
        assert result.exit_code == 0
        assert "network" in result.output
        assert "web" in result.output
        assert "dns" in result.output


class TestReconFlags:
    def test_recon_attacks_and_full_mutual_exclusivity(self) -> None:
        """--attacks and --full are mutually exclusive."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "recon", "--target", "example.com",
                "--attacks", "nmap", "--full",
            ],
        )
        assert result.exit_code != 0

    def test_recon_no_ai_flag(self) -> None:
        """The --ai flag was removed in v2. Passing it should cause an error."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "recon", "--target", "example.com",
                "--ai",
            ],
        )
        # --ai is not a recognized option, so Click should reject it
        assert result.exit_code != 0

    def test_recon_attacks_invalid_tool(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "recon", "--target", "example.com",
                "--attacks", "nonexistent_tool",
            ],
        )
        assert result.exit_code != 0
