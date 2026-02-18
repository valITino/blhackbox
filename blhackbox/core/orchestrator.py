"""LangGraph-based state machine for autonomous reconnaissance.

The orchestrator tracks scan stages (recon -> scan -> enumerate -> aggregate
-> report) as a pure state machine.  It does NOT make LLM decisions internally
— Claude operates externally as the MCP Host orchestrator, and Ollama is the
local preprocessor accessed via the blhackbox aggregator MCP server.

State graph nodes:
  1. gather_state  – query the knowledge graph for current findings
  2. plan          – select the next tool from the predefined tool sequence
  3. execute       – call HexStrike to run the selected tool/agent
  4. analyze       – store results in the knowledge graph, update state
  *  decide        – conditional edge: continue or stop
"""

from __future__ import annotations

import json
import logging
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from blhackbox.clients.hexstrike_client import HexStrikeClient
from blhackbox.config import settings
from blhackbox.core.graph_exporter import GraphExporter
from blhackbox.core.knowledge_graph import KnowledgeGraphClient
from blhackbox.core.runner import save_session
from blhackbox.exceptions import (
    BlhackboxError,
    GraphError,
    HexStrikeAPIError,
    HexStrikeConnectionError,
    HexStrikeTimeoutError,
)
from blhackbox.models.base import Finding, ScanSession, Severity, Target
from blhackbox.utils.catalog import get_full_pentest_order, load_tools_catalog

logger = logging.getLogger("blhackbox.core.orchestrator")


# ---------------------------------------------------------------------------
# Default tool sequence for autonomous scanning
# ---------------------------------------------------------------------------

def _get_default_tool_sequence() -> list[dict[str, str]]:
    """Build the default tool execution sequence from the catalogue.

    Falls back to a minimal hardcoded sequence if the catalogue is unavailable.
    """
    try:
        catalog = load_tools_catalog()
        return get_full_pentest_order(catalog)
    except Exception:
        logger.warning("Could not load tools catalogue; using minimal fallback sequence")
        return [
            {"category": "dns", "tool_name": "subfinder"},
            {"category": "network", "tool_name": "nmap"},
            {"category": "web", "tool_name": "nikto"},
            {"category": "web", "tool_name": "gobuster"},
            {"category": "intelligence", "tool_name": "analyze-target"},
        ]


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

class OrchestratorState(TypedDict):
    target: str
    session: ScanSession
    findings_summary: str
    completed_tools: list[str]
    pending_action: dict[str, Any]
    iteration: int
    max_iterations: int
    should_stop: bool
    error: str
    tool_sequence: list[dict[str, str]]


# ---------------------------------------------------------------------------
# Graph nodes
# ---------------------------------------------------------------------------

async def gather_state(state: OrchestratorState) -> OrchestratorState:
    """Query Neo4j for the current target summary."""
    target = state["target"]

    try:
        async with KnowledgeGraphClient() as kg:
            summary = await kg.get_target_summary(target)
            findings = await kg.get_findings_for_target(target)

        summary_parts = [f"Graph nodes: {summary}"] if summary else []
        if findings:
            for f in findings[:20]:
                title = f.get("title", "untitled")
                sev = f.get("severity", "info")
                summary_parts.append(f"  - [{sev}] {title}")

        state["findings_summary"] = (
            "\n".join(summary_parts) if summary_parts else "No findings yet."
        )
    except GraphError as exc:
        logger.warning("Graph query failed (continuing without): %s", exc)
        state["findings_summary"] = _session_findings_summary(state["session"])
    except OSError as exc:
        logger.warning("Graph connection failed (continuing without): %s", exc)
        state["findings_summary"] = _session_findings_summary(state["session"])

    return state


async def plan(state: OrchestratorState) -> OrchestratorState:
    """Select the next tool from the predefined tool sequence.

    No LLM is involved — the state machine walks through the tool sequence
    in order, skipping tools that have already been executed or failed.
    """
    iteration = state["iteration"]
    tool_sequence = state["tool_sequence"]
    completed = set(state["completed_tools"])

    # Find the next tool that hasn't been run yet
    action: dict[str, Any] | None = None
    for entry in tool_sequence:
        tool_id = f"{entry['category']}/{entry['tool_name']}"
        # Skip already completed or failed tools
        if any(tool_id in c for c in completed):
            continue
        action = {
            "action": "run_tool",
            "category": entry["category"],
            "tool": entry["tool_name"],
            "params": {},
            "reasoning": f"Next tool in sequence: {tool_id}",
        }
        break

    if action is None or iteration >= state["max_iterations"]:
        state["pending_action"] = {
            "action": "stop",
            "reasoning": "All tools in sequence completed or max iterations reached",
        }
        state["should_stop"] = True
    else:
        state["pending_action"] = action

    logger.info(
        "Plan (iter %d): %s – %s",
        iteration,
        state["pending_action"].get("action"),
        state["pending_action"].get("reasoning", ""),
    )
    return state


async def execute(state: OrchestratorState) -> OrchestratorState:
    """Execute the planned action via HexStrike."""
    action = state["pending_action"]
    if action.get("action") == "stop":
        return state

    session = state["session"]

    async with HexStrikeClient() as client:
        try:
            if action["action"] == "run_tool":
                category = action.get("category", "network")
                tool = action.get("tool", "nmap")
                params = action.get("params", {})
                if "target" not in params:
                    params["target"] = state["target"]

                tool_id = f"{category}/{tool}"

                # Route intelligence/analyze-target to the dedicated endpoint
                if category == "intelligence" and tool == "analyze-target":
                    analysis = await client.analyze_target(
                        target=state["target"],
                        analysis_type=params.get("analysis_type", "comprehensive"),
                    )
                    state["completed_tools"].append(tool_id)
                    session.mark_tool_done(tool_id)
                    finding = Finding(
                        target=state["target"],
                        tool=tool_id,
                        category=category,
                        title=f"AI Analysis: {state['target']}",
                        description=json.dumps(
                            analysis.results, indent=2, default=str
                        )[:5000],
                        severity=Severity.INFO,
                        raw_data={
                            "results": analysis.results,
                            "recommendations": analysis.recommendations,
                            "risk_score": analysis.risk_score,
                            "errors": analysis.errors,
                        },
                    )
                    session.add_finding(finding)
                else:
                    result = await client.run_tool(category, tool, params)
                    state["completed_tools"].append(tool_id)
                    session.mark_tool_done(tool_id)
                    finding = Finding(
                        target=state["target"],
                        tool=tool_id,
                        category=category,
                        title=f"Tool Output: {tool}",
                        description=(
                            result.raw_output
                            or json.dumps(result.output, indent=2, default=str)
                        )[:5000],
                        severity=Severity.INFO,
                        raw_data={"output": result.output, "errors": result.errors},
                    )
                    session.add_finding(finding)

        except (
            HexStrikeAPIError,
            HexStrikeConnectionError,
            HexStrikeTimeoutError,
            BlhackboxError,
            ValueError,
            OSError,
        ) as exc:
            # Distinguish 404 (tool not available) from other errors
            is_not_found = (
                isinstance(exc, HexStrikeAPIError) and exc.status_code == 404
            )
            if is_not_found:
                error_msg = f"Tool not available on server: {exc}"
                logger.warning(error_msg)
            else:
                error_msg = f"Execution error: {exc}"
                logger.error(error_msg)
            state["error"] = error_msg
            # Track the failed tool so the planner doesn't retry it
            failed_id = f"{action.get('category', 'unknown')}/{action.get('tool', 'unknown')}"
            fail_tag = "NOT AVAILABLE" if is_not_found else "FAILED"
            state["completed_tools"].append(f"{failed_id} ({fail_tag})")
            finding = Finding(
                target=state["target"],
                tool=action.get("tool", "unknown"),
                category="error",
                title="Execution Error",
                description=error_msg,
                severity=Severity.LOW,
            )
            session.add_finding(finding)

    return state


async def analyze(state: OrchestratorState) -> OrchestratorState:
    """Store execution results in the knowledge graph."""
    session = state["session"]

    try:
        async with KnowledgeGraphClient() as kg:
            exporter = GraphExporter(kg)
            # Export only the latest finding(s)
            if session.findings:
                latest = session.findings[-1]
                await exporter.export_finding(state["target"], latest)
    except (GraphError, OSError) as exc:
        logger.warning("Graph export failed (non-fatal): %s", exc)

    state["iteration"] += 1
    return state


def decide_continue(state: OrchestratorState) -> str:
    """Conditional edge: continue planning or stop."""
    if state["should_stop"]:
        return "end"
    max_iter = state["max_iterations"]
    if state["iteration"] >= max_iter:
        logger.info("Max iterations (%d) reached, stopping", max_iter)
        return "end"
    # Stop early if the last 3 actions all failed
    recent = state["session"].findings[-3:]
    if len(recent) >= 3 and all(f.category == "error" for f in recent):
        logger.info("Stopping after 3 consecutive tool failures")
        return "end"
    return "continue"


# ---------------------------------------------------------------------------
# Build the graph
# ---------------------------------------------------------------------------

def build_orchestrator_graph() -> StateGraph:
    """Construct the LangGraph state machine for autonomous recon."""
    graph = StateGraph(OrchestratorState)

    graph.add_node("gather_state", gather_state)
    graph.add_node("plan", plan)
    graph.add_node("execute", execute)
    graph.add_node("analyze", analyze)

    graph.set_entry_point("gather_state")
    graph.add_edge("gather_state", "plan")
    graph.add_conditional_edges(
        "plan",
        decide_continue,
        {"continue": "execute", "end": END},
    )
    graph.add_edge("execute", "analyze")
    graph.add_edge("analyze", "gather_state")

    return graph


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

async def run_orchestrated_recon(target: str) -> ScanSession:
    """Run the full autonomous recon workflow.

    Uses a predefined tool sequence (from the catalogue) instead of an LLM
    planner.  Claude operates as the external MCP Host orchestrator.

    Returns a completed ScanSession with all findings.
    """
    session = ScanSession(target=Target(value=target))
    tool_sequence = _get_default_tool_sequence()

    # Cap to max_iterations
    cap = settings.max_iterations
    if len(tool_sequence) > cap:
        tool_sequence = tool_sequence[:cap]

    initial_state: OrchestratorState = {
        "target": target,
        "session": session,
        "findings_summary": "",
        "completed_tools": [],
        "pending_action": {},
        "iteration": 0,
        "max_iterations": cap,
        "should_stop": False,
        "error": "",
        "tool_sequence": tool_sequence,
    }

    graph = build_orchestrator_graph()
    app = graph.compile()

    logger.info("Starting orchestrated recon for %s", target)

    final_state = await app.ainvoke(initial_state)

    session = final_state["session"]
    session.finish()

    out_path = save_session(session)
    logger.info(
        "Orchestrated recon complete: %d findings, saved to %s",
        len(session.findings),
        out_path,
    )

    return session


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _session_findings_summary(session: ScanSession) -> str:
    """Build a text summary from session findings (fallback when graph is unavailable)."""
    if not session.findings:
        return "No findings yet."
    parts = []
    for f in session.findings[-15:]:
        sev = f.severity if isinstance(f.severity, str) else f.severity.value
        parts.append(f"  - [{sev}] {f.title}")
    return "\n".join(parts)
