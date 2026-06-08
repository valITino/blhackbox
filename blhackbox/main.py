"""Blhackbox CLI – Click-based command-line interface."""

from __future__ import annotations

import asyncio
import json

import click
from rich.table import Table

import blhackbox
from blhackbox.config import settings
from blhackbox.utils.catalog import (
    load_tools_catalog,
    search_tools_catalog,
)
from blhackbox.utils.logger import (
    console as rich_console,
)
from blhackbox.utils.logger import (
    get_logger,
    print_banner,
    print_warning_banner,
    setup_logging,
)

logger = get_logger("cli")


def _run_async(coro):  # type: ignore[no-untyped-def]
    """Run an async coroutine from synchronous Click handlers."""
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Root group
# ---------------------------------------------------------------------------


@click.group()
@click.option("--debug", is_flag=True, help="Enable debug logging.")
def cli(debug: bool) -> None:
    """Blhackbox – MCP-based Autonomous Pentesting Framework."""
    level = "DEBUG" if debug else settings.log_level
    setup_logging(level)


# ---------------------------------------------------------------------------
# version
# ---------------------------------------------------------------------------


@cli.command()
def version() -> None:
    """Show the Blhackbox version."""
    print_banner()
    rich_console.print(f"[info]Version:[/info] {blhackbox.__version__}")
    rich_console.print(f"[info]Neo4j URI:[/info] {settings.neo4j_uri}")


# ---------------------------------------------------------------------------
# catalog
# ---------------------------------------------------------------------------


@cli.command()
@click.option("--search", "search_query", help="Filter catalogue by keyword/tag.")
@click.option("--category", help="Filter by category, e.g. web or network.")
@click.option("--phase", type=click.Choice(["passive", "active"]), help="Filter by phase.")
@click.option("--json", "as_json", is_flag=True, help="Emit catalogue entries as JSON.")
def catalog(
    search_query: str | None,
    category: str | None,
    phase: str | None,
    as_json: bool,
) -> None:
    """Display or search the available tools catalogue."""
    tools = load_tools_catalog()
    if search_query or category or phase:
        tools = search_tools_catalog(
            tools,
            search_query or "",
            limit=50,
            category=category,
            phase=phase,
        )

    if as_json:
        rich_console.print(json.dumps(tools, indent=2))
        return

    table = Table(title="Tool Catalogue")
    table.add_column("Category", style="cyan")
    table.add_column("Tool", style="green")
    table.add_column("Description", style="white")
    table.add_column("Phase", style="yellow")
    table.add_column("Backend", style="magenta")

    for entry in tools:
        table.add_row(
            entry.get("category", ""),
            entry.get("tool_name", ""),
            entry.get("description", ""),
            entry.get("phase", ""),
            entry.get("backend", ""),
        )

    rich_console.print(table)


# ---------------------------------------------------------------------------
# run-tool
# ---------------------------------------------------------------------------


@cli.command("run-tool")
@click.option("--category", "-c", required=True, help="Tool category (network, web, …).")
@click.option("--tool", "-t", required=True, help="Tool name (nmap, nuclei, …).")
@click.option(
    "--params",
    "-p",
    required=True,
    help='JSON string of tool parameters, e.g. \'{"target":"example.com"}\'.',
)
def run_tool(category: str, tool: str, params: str) -> None:
    """Run a single tool via the local backend."""
    print_warning_banner()

    try:
        params_dict = json.loads(params)
    except json.JSONDecodeError as exc:
        rich_console.print(f"[error]Invalid JSON in --params: {exc}[/error]")
        raise SystemExit(1) from exc

    _run_async(_do_run_tool(category, tool, params_dict))


async def _do_run_tool(category: str, tool: str, params: dict) -> None:
    from blhackbox.backends import get_backend

    backend = await get_backend()
    try:
        result = await backend.run_tool(category, tool, params)
        rich_console.print(f"[success]Tool {category}/{tool} completed.[/success]")
        rich_console.print(json.dumps(result.model_dump(), indent=2, default=str))
    finally:
        await backend.close()


# ---------------------------------------------------------------------------
# graph (Neo4j — optional)
# ---------------------------------------------------------------------------


@cli.group()
def graph() -> None:
    """Knowledge graph operations (Neo4j)."""


@graph.command("query")
@click.argument("cypher")
def graph_query(cypher: str) -> None:
    """Execute a raw Cypher query against the knowledge graph."""
    _run_async(_do_graph_query(cypher))


async def _do_graph_query(cypher: str) -> None:
    from blhackbox.core.knowledge_graph import KnowledgeGraphClient

    async with KnowledgeGraphClient() as kg:
        records = await kg.run_query(cypher)

    if not records:
        rich_console.print("[warning]No results.[/warning]")
        return

    for record in records:
        rich_console.print(json.dumps(record, indent=2, default=str))


@graph.command("summary")
@click.option("--target", "-t", required=True, help="Target to summarize.")
def graph_summary(target: str) -> None:
    """Show a summary of knowledge graph nodes for a target."""
    _run_async(_do_graph_summary(target))


async def _do_graph_summary(target: str) -> None:
    from blhackbox.core.knowledge_graph import KnowledgeGraphClient

    async with KnowledgeGraphClient() as kg:
        summary = await kg.get_target_summary(target)

    table = Table(title=f"Knowledge Graph – {target}")
    table.add_column("Node Type", style="cyan")
    table.add_column("Count", style="green")

    for node_type, count in summary.items():
        table.add_row(node_type, str(count))

    rich_console.print(table)


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------


@cli.command()
@click.option("--session", "-s", required=True, help="Session ID or results JSON file path.")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["pdf", "html", "md"]),
    default="pdf",
    help="Report format.",
)
@click.option("--output", "-o", type=click.Path(), help="Output file path.")
@click.option(
    "--both",
    is_flag=True,
    default=False,
    help="Generate both .md and .pdf reports in the organized reports folder.",
)
def report(session: str, fmt: str, output: str | None, both: bool) -> None:
    """Generate a report from scan session results."""
    _run_async(_do_report(session, fmt, output, both))


async def _do_report(session_id: str, fmt: str, output: str | None, both: bool = False) -> None:
    import re
    from pathlib import Path

    from blhackbox.reporting import build_reports

    safe_session_id = re.sub(r"[^a-zA-Z0-9_\-]", "", session_id)
    if not safe_session_id:
        rich_console.print("[error]Invalid session ID.[/error]")
        raise SystemExit(1)

    session_path = Path(session_id)
    if session_path.exists():
        resolved = session_path.resolve()
        results_resolved = settings.results_dir.resolve()
        cwd_resolved = Path.cwd().resolve()
        if not (
            str(resolved).startswith(str(results_resolved))
            or str(resolved).startswith(str(cwd_resolved))
        ):
            rich_console.print("[error]Session file path is outside allowed directories.[/error]")
            raise SystemExit(1)
    else:
        results_dir = settings.results_dir
        matches = list(results_dir.glob(f"*{safe_session_id}*"))
        if not matches:
            rich_console.print(f"[error]Session '{safe_session_id}' not found.[/error]")
            raise SystemExit(1)
        session_path = matches[0]

    requested_fmt = "both" if both else fmt
    reports = build_reports(session_path, requested_fmt, output)
    for path, rfmt in reports:
        rich_console.print(f"[success]{rfmt.upper()} report generated: {path}[/success]")


# ---------------------------------------------------------------------------
# templates
# ---------------------------------------------------------------------------


@cli.group()
def templates() -> None:
    """Manage prompt templates for autonomous pentesting."""


@templates.command("list")
def templates_list() -> None:
    """List available prompt templates."""
    from blhackbox.prompts import list_templates

    tpl_list = list_templates()

    table = Table(title="Prompt Templates")
    table.add_column("Name", style="cyan")
    table.add_column("Title", style="white")
    table.add_column("File", style="dim")

    for tpl in tpl_list:
        table.add_row(tpl["name"], tpl["title"], tpl["file"])

    rich_console.print(table)
    rich_console.print(
        "\n[info]Use 'blhackbox templates show <name>' to view a template.[/info]"
    )


@templates.command("show")
@click.argument("name")
@click.option("--target", "-t", default=None, help="Replace [TARGET] placeholders.")
def templates_show(name: str, target: str | None) -> None:
    """Display a prompt template by name."""
    from blhackbox.prompts import load_template

    try:
        content = load_template(name, target=target)
    except (ValueError, FileNotFoundError) as exc:
        rich_console.print(f"[error]{exc}[/error]")
        raise SystemExit(1) from exc

    from rich.markdown import Markdown

    rich_console.print(Markdown(content))


# ---------------------------------------------------------------------------
# mcp serve
# ---------------------------------------------------------------------------


@cli.command("mcp")
def mcp_serve() -> None:
    """Start the Blhackbox MCP server (stdio transport).

    Connect any MCP-compatible LLM to Blhackbox for autonomous pentesting.
    """
    _run_async(_do_mcp_serve())


async def _do_mcp_serve() -> None:
    from blhackbox.mcp.server import run_server

    await run_server()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cli()
