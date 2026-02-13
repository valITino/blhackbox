"""Blhackbox CLI – Click-based command-line interface."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import click
from rich.table import Table

import blhackbox
from blhackbox.config import settings
from blhackbox.utils.catalog import (
    get_full_pentest_order,
    load_tools_catalog,
    resolve_tool_names,
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
    """Blhackbox – HexStrike Hybrid Autonomous Pentesting Framework."""
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
    rich_console.print(f"[info]HexStrike URL:[/info] {settings.hexstrike_url}")
    rich_console.print(f"[info]Neo4j URI:[/info] {settings.neo4j_uri}")


# ---------------------------------------------------------------------------
# catalog
# ---------------------------------------------------------------------------


@cli.command()
def catalog() -> None:
    """Display the available HexStrike tools catalogue."""
    tools = load_tools_catalog()

    table = Table(title="HexStrike Tool Catalogue")
    table.add_column("Category", style="cyan")
    table.add_column("Tool", style="green")
    table.add_column("Description", style="white")
    table.add_column("Phase", style="yellow")

    for entry in tools:
        table.add_row(
            entry.get("category", ""),
            entry.get("tool_name", ""),
            entry.get("description", ""),
            entry.get("phase", ""),
        )

    rich_console.print(table)


# ---------------------------------------------------------------------------
# recon
# ---------------------------------------------------------------------------


@cli.command()
@click.option("--target", "-t", required=True, help="Target domain, IP, or URL.")
@click.option(
    "--authorized",
    is_flag=True,
    default=False,
    help="Confirm you have written authorization to test this target.",
)
@click.option(
    "--ai",
    is_flag=True,
    default=False,
    help="Use the AI orchestrator (LangGraph) for autonomous planning.",
)
@click.option(
    "--attacks",
    default=None,
    help="Comma-separated tool or category names to run (bypasses planner).",
)
@click.option(
    "--full",
    "full_pentest",
    is_flag=True,
    default=False,
    help="Run all catalogue tools in order (passive first, then active).",
)
@click.option("--output", "-o", type=click.Path(), help="Override output file path.")
def recon(
    target: str,
    authorized: bool,
    ai: bool,
    attacks: str | None,
    full_pentest: bool,
    output: str | None,
) -> None:
    """Run reconnaissance against a target via HexStrike."""
    if not authorized:
        rich_console.print(
            "[error]ERROR: You must pass --authorized to confirm you have written "
            "permission to test this target.[/error]"
        )
        raise SystemExit(1)

    # Mutual exclusivity: --ai, --attacks, --full
    mode_count = sum([ai, attacks is not None, full_pentest])
    if mode_count > 1:
        rich_console.print(
            "[error]ERROR: --ai, --attacks, and --full are mutually exclusive.[/error]"
        )
        raise SystemExit(1)

    print_banner()
    print_warning_banner()

    if attacks is not None:
        # Resolve tool names from the catalogue
        cat = load_tools_catalog()
        names = [n.strip() for n in attacks.split(",") if n.strip()]
        try:
            tool_list = resolve_tool_names(cat, names)
        except ValueError as exc:
            rich_console.print(f"[error]{exc}[/error]")
            raise SystemExit(1) from exc
        _run_async(_do_multi_tool_recon(target, tool_list, output))
    elif full_pentest:
        cat = load_tools_catalog()
        tool_list = get_full_pentest_order(cat)
        # Cap at max_iterations to avoid unbounded runs
        cap = settings.max_iterations
        if len(tool_list) > cap:
            rich_console.print(
                f"[warning]Capping full pentest to {cap} tools "
                f"(max_iterations setting).[/warning]"
            )
            tool_list = tool_list[:cap]
        _run_async(_do_multi_tool_recon(target, tool_list, output))
    else:
        _run_async(_do_recon(target, ai, output))


async def _do_multi_tool_recon(
    target: str,
    tool_list: list[dict[str, str]],
    output: str | None,
) -> None:
    """Run multiple tools sequentially with a progress display."""
    from rich.progress import Progress, SpinnerColumn, TextColumn

    from blhackbox.clients.hexstrike_client import HexStrikeClient
    from blhackbox.core.runner import ReconRunner
    from blhackbox.models.base import ScanSession, Target

    session = ScanSession(target=Target(value=target))

    async with HexStrikeClient() as client:
        healthy = await client.health_check()
        if not healthy:
            rich_console.print(
                "[error]Cannot reach HexStrike at "
                f"{settings.hexstrike_url}. Is it running?[/error]"
            )
            raise SystemExit(1)

        runner = ReconRunner(client)
        total = len(tool_list)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=rich_console,
        ) as progress:
            task = progress.add_task("Running tools…", total=total)
            for i, entry in enumerate(tool_list, 1):
                cat = entry["category"]
                tool = entry["tool_name"]
                progress.update(task, description=f"[{i}/{total}] {cat}/{tool}")
                try:
                    single = await runner.run_single_tool(
                        cat, tool, {"target": target}
                    )
                    for finding in single.findings:
                        session.add_finding(finding)
                    session.mark_tool_done(f"{cat}/{tool}")
                except Exception as exc:
                    logger.warning("Tool %s/%s failed: %s", cat, tool, exc)
                    rich_console.print(
                        f"[warning]Tool {cat}/{tool} failed: {exc}[/warning]"
                    )
                progress.advance(task)

    session.finish()
    _save_and_summarize(session, target, output)


async def _do_recon(target: str, ai: bool, output: str | None) -> None:
    from blhackbox.clients.hexstrike_client import HexStrikeClient
    from blhackbox.core.runner import ReconRunner

    if ai:
        # Phase 3 – AI orchestrator
        from blhackbox.core.orchestrator import run_orchestrated_recon

        session = await run_orchestrated_recon(target)
    else:
        async with HexStrikeClient() as client:
            healthy = await client.health_check()
            if not healthy:
                rich_console.print(
                    "[error]Cannot reach HexStrike at "
                    f"{settings.hexstrike_url}. Is it running?[/error]"
                )
                raise SystemExit(1)

            runner = ReconRunner(client)
            session = await runner.run_recon(target)

    _save_and_summarize(session, target, output)


def _save_and_summarize(
    session: Any,
    target: str,
    output: str | None,
) -> None:
    """Save the session to disk and print a summary table."""
    from pathlib import Path

    from blhackbox.core.runner import save_session

    if output:
        out_path = save_session(session)
        target_path = Path(output)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.rename(target_path)
        out_path = target_path
    else:
        out_path = save_session(session)

    # --- summary table ---
    table = Table(title=f"Recon Summary – {target}")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Session ID", session.id)
    table.add_row("Target", str(session.target))
    table.add_row("Tools Executed", ", ".join(session.tools_executed) or "—")
    table.add_row("Total Findings", str(len(session.findings)))
    for sev, count in session.severity_counts.items():
        table.add_row(f"  {sev.upper()}", str(count))
    if session.duration_seconds is not None:
        table.add_row("Duration", f"{session.duration_seconds:.1f}s")
    table.add_row("Results File", str(out_path))
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
@click.option("--authorized", is_flag=True, default=False, help="Confirm authorization.")
def run_tool(category: str, tool: str, params: str, authorized: bool) -> None:
    """Run a single HexStrike tool."""
    if not authorized:
        rich_console.print("[error]ERROR: --authorized flag required.[/error]")
        raise SystemExit(1)

    print_warning_banner()

    try:
        params_dict = json.loads(params)
    except json.JSONDecodeError as exc:
        rich_console.print(f"[error]Invalid JSON in --params: {exc}[/error]")
        raise SystemExit(1) from exc

    _run_async(_do_run_tool(category, tool, params_dict))


async def _do_run_tool(category: str, tool: str, params: dict) -> None:
    from blhackbox.clients.hexstrike_client import HexStrikeClient
    from blhackbox.core.runner import ReconRunner, save_session

    async with HexStrikeClient() as client:
        runner = ReconRunner(client)
        session = await runner.run_single_tool(category, tool, params)

    out_path = save_session(session)
    rich_console.print(f"[success]Tool {category}/{tool} completed.[/success]")
    rich_console.print(f"Results saved to: {out_path}")

    for finding in session.findings:
        rich_console.print(f"\n[info]{finding.title}[/info]")
        if finding.description:
            rich_console.print(finding.description[:2000])


# ---------------------------------------------------------------------------
# agents
# ---------------------------------------------------------------------------


@cli.group()
def agents() -> None:
    """Manage HexStrike AI agents."""


@agents.command("list")
def agents_list() -> None:
    """List available HexStrike AI agents."""
    _run_async(_do_list_agents())


async def _do_list_agents() -> None:
    from blhackbox.clients.hexstrike_client import HexStrikeClient

    async with HexStrikeClient() as client:
        agent_list = await client.list_agents()

    table = Table(title="HexStrike AI Agents")
    table.add_column("Name", style="cyan")
    table.add_column("Description", style="white")
    table.add_column("Status", style="green")

    for agent in agent_list:
        table.add_row(agent.name, agent.description, agent.status)

    rich_console.print(table)


@agents.command("run")
@click.option("--name", "-n", required=True, help="Agent name.")
@click.option("--target", "-t", required=True, help="Target for the agent.")
@click.option("--authorized", is_flag=True, default=False, help="Confirm authorization.")
def agents_run(name: str, target: str, authorized: bool) -> None:
    """Run a HexStrike AI agent against a target."""
    if not authorized:
        rich_console.print("[error]ERROR: --authorized flag required.[/error]")
        raise SystemExit(1)

    print_warning_banner()
    _run_async(_do_run_agent(name, target))


async def _do_run_agent(name: str, target: str) -> None:
    from blhackbox.clients.hexstrike_client import HexStrikeClient
    from blhackbox.core.runner import save_session
    from blhackbox.models.base import Finding, ScanSession, Severity
    from blhackbox.models.base import Target as TargetModel

    async with HexStrikeClient() as client:
        result = await client.run_agent(name, target)

    session = ScanSession(target=TargetModel(value=target))
    session.mark_tool_done(f"agent/{name}")

    finding = Finding(
        target=target,
        tool=f"agent/{name}",
        category="agent",
        title=f"Agent Output: {name}",
        description=json.dumps(result.results, indent=2, default=str),
        severity=Severity.INFO,
        raw_data=result.results,
    )
    session.add_finding(finding)
    session.finish()

    out_path = save_session(session)
    rich_console.print(f"[success]Agent '{name}' completed.[/success]")
    rich_console.print(f"Results saved to: {out_path}")


# ---------------------------------------------------------------------------
# graph (Phase 2)
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
# report (Phase 4)
# ---------------------------------------------------------------------------


@cli.command()
@click.option("--session", "-s", required=True, help="Session ID or results JSON file path.")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["pdf", "html"]),
    default="pdf",
    help="Report format.",
)
@click.option("--output", "-o", type=click.Path(), help="Output file path.")
def report(session: str, fmt: str, output: str | None) -> None:
    """Generate a report from scan session results."""
    _run_async(_do_report(session, fmt, output))


async def _do_report(session_id: str, fmt: str, output: str | None) -> None:
    import re
    from pathlib import Path

    from blhackbox.models.base import ScanSession

    # Sanitize session_id to prevent path traversal and glob injection
    safe_session_id = re.sub(r"[^a-zA-Z0-9_\-]", "", session_id)
    if not safe_session_id:
        rich_console.print("[error]Invalid session ID.[/error]")
        raise SystemExit(1)

    # Try to load session from file
    session_path = Path(session_id)
    if session_path.exists():
        # Verify the resolved path is within an expected directory
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
        # Search results dir using sanitized session ID
        results_dir = settings.results_dir
        matches = list(results_dir.glob(f"*{safe_session_id}*"))
        if not matches:
            rich_console.print(f"[error]Session '{safe_session_id}' not found.[/error]")
            raise SystemExit(1)
        session_path = matches[0]

    session_data = ScanSession.model_validate_json(session_path.read_text())

    if fmt == "pdf":
        from blhackbox.reporting.pdf_generator import generate_pdf_report

        out = generate_pdf_report(session_data, output)
    else:
        from blhackbox.reporting.html_generator import generate_html_report

        out = generate_html_report(session_data, output)

    rich_console.print(f"[success]Report generated: {out}[/success]")


# ---------------------------------------------------------------------------
# exploit (post-report guidance)
# ---------------------------------------------------------------------------


@cli.command()
@click.option(
    "--session",
    "-s",
    required=True,
    help="Session ID or results JSON file path.",
)
@click.option(
    "--authorized",
    is_flag=True,
    default=False,
    help="Confirm you have written authorization for this assessment.",
)
@click.option(
    "--allow-poc",
    is_flag=True,
    default=False,
    help="Include descriptive proof-of-concept approaches (not raw exploit code).",
)
@click.option("--output", "-o", type=click.Path(), help="Output file path for guidance JSON.")
def exploit(session: str, authorized: bool, allow_poc: bool, output: str | None) -> None:
    """Generate post-report exploit guidance for session findings.

    Requires --authorized.  Default mode produces risk descriptions and
    remediation advice only.  Pass --allow-poc for descriptive PoC approaches
    (still not raw exploit code).

    This feature is opt-in and intended for authorized penetration testers.
    """
    if not authorized:
        rich_console.print(
            "[error]ERROR: You must pass --authorized to confirm you have written "
            "permission for this assessment.[/error]"
        )
        raise SystemExit(1)

    rich_console.print(
        "\n[warning]"
        "========================================================================\n"
        "  EXPLOIT GUIDANCE – AUTHORIZED USE ONLY\n"
        "  This feature generates vulnerability exploitation guidance.\n"
        "  You have confirmed written authorization for this assessment.\n"
        "  Misuse of this output may violate applicable laws.\n"
        "========================================================================\n"
        "[/warning]"
    )

    _run_async(_do_exploit(session, allow_poc, output))


async def _do_exploit(session_id: str, allow_poc: bool, output: str | None) -> None:
    import re
    from pathlib import Path

    from blhackbox.core.exploit_generator import ExploitGenerator
    from blhackbox.models.base import ScanSession

    # --- load session (same logic as report command) ---
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

    session_data = ScanSession.model_validate_json(session_path.read_text())

    if not session_data.findings:
        rich_console.print("[warning]No findings in session – nothing to analyse.[/warning]")
        return

    # --- generate guidance ---
    generator = ExploitGenerator(allow_poc=allow_poc)
    rich_console.print("[info]Generating exploit guidance via LLM…[/info]")

    guidance = await generator.generate(session_data.findings)

    if not guidance:
        rich_console.print("[warning]LLM returned no actionable guidance.[/warning]")
        return

    # --- save output ---
    guidance_json = json.dumps(guidance, indent=2)

    if output:
        out_path = Path(output)
    else:
        out_path = session_path.with_name(
            session_path.stem + "_exploit_guidance.json"
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Verify path stays within expected directories
    resolved = out_path.resolve()
    results_resolved = settings.results_dir.resolve()
    cwd_resolved = Path.cwd().resolve()
    if not (
        str(resolved).startswith(str(results_resolved))
        or str(resolved).startswith(str(cwd_resolved))
    ):
        rich_console.print("[error]Output path is outside allowed directories.[/error]")
        raise SystemExit(1)

    out_path.write_text(guidance_json, encoding="utf-8")

    # --- display summary ---
    table = Table(title="Exploit Guidance Summary")
    table.add_column("Finding", style="cyan")
    table.add_column("Exploitability", style="yellow")
    table.add_column("Remediation", style="green", max_width=60)

    for entry in guidance:
        table.add_row(
            entry.get("title", "?")[:50],
            entry.get("exploitability", "?"),
            entry.get("remediation", "?")[:60],
        )

    rich_console.print(table)
    rich_console.print(f"\n[success]Guidance saved to: {out_path}[/success]")
    if allow_poc:
        rich_console.print(
            "[warning]PoC approaches included – handle this output securely.[/warning]"
        )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cli()
