"""Tests for CLI commands."""

from __future__ import annotations

from click.testing import CliRunner

from blhackbox.main import cli


class TestCLI:
    def test_version(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["version"])
        assert result.exit_code == 0
        assert "2.0.0" in result.output

    def test_recon_without_authorized(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["recon", "--target", "example.com"])
        assert result.exit_code != 0

    def test_run_tool_without_authorized(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "run-tool",
                "--category", "network",
                "--tool", "nmap",
                "--params", '{"target": "example.com"}',
            ],
        )
        assert result.exit_code != 0

    def test_run_tool_invalid_json(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "run-tool",
                "--category", "network",
                "--tool", "nmap",
                "--params", "not-json",
                "--authorized",
            ],
        )
        assert result.exit_code != 0

    def test_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Blhackbox" in result.output


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
    def test_recon_attacks_without_authorized(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli, ["recon", "--target", "example.com", "--attacks", "nmap"]
        )
        assert result.exit_code != 0

    def test_recon_full_without_authorized(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli, ["recon", "--target", "example.com", "--full"]
        )
        assert result.exit_code != 0

    def test_recon_mutual_exclusivity(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "recon", "--target", "example.com", "--authorized",
                "--ai", "--full",
            ],
        )
        assert result.exit_code != 0

    def test_recon_attacks_invalid_tool(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "recon", "--target", "example.com", "--authorized",
                "--attacks", "nonexistent_tool",
            ],
        )
        assert result.exit_code != 0
