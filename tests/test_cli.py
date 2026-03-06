"""Tests for CLI commands (v2 architecture).

v2 changes:
  - The ``recon`` command has been removed (used deprecated backend).
  - The ``exploit`` command has been removed entirely.
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
