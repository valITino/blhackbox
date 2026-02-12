"""Simple runner that executes HexStrike tools and captures results."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from blhackbox.clients.hexstrike_client import HexStrikeClient
from blhackbox.config import settings
from blhackbox.models.base import Finding, ScanSession, Severity, Target

logger = logging.getLogger("blhackbox.core.runner")


class ReconRunner:
    """Runs a basic reconnaissance workflow via HexStrike."""

    def __init__(self, client: HexStrikeClient) -> None:
        self._client = client

    async def run_recon(self, target_str: str) -> ScanSession:
        """Execute a reconnaissance pass against the target.

        Steps:
            1. Analyze target via HexStrike intelligence endpoint
            2. Parse results into Findings
            3. Return a completed ScanSession
        """
        target = Target(value=target_str)
        session = ScanSession(target=target)
        logger.info("Starting recon session %s for target: %s", session.id, target)

        analysis = await self._client.analyze_target(target_str, analysis_type="comprehensive")
        session.mark_tool_done("intelligence/analyze-target")

        if analysis.results:
            finding = Finding(
                target=target_str,
                tool="hexstrike-intelligence",
                category="intelligence",
                title="AI-Driven Target Analysis",
                description=json.dumps(analysis.results, indent=2, default=str),
                severity=Severity.INFO,
                evidence=json.dumps(analysis.recommendations, default=str),
                raw_data=analysis.results,
            )
            session.add_finding(finding)

        if analysis.risk_score is not None:
            risk_finding = Finding(
                target=target_str,
                tool="hexstrike-intelligence",
                category="risk",
                title=f"Risk Score: {analysis.risk_score}",
                description=f"Overall risk assessment score: {analysis.risk_score}/10",
                severity=_risk_to_severity(analysis.risk_score),
                raw_data={"risk_score": analysis.risk_score},
            )
            session.add_finding(risk_finding)

        session.finish()
        logger.info(
            "Recon session %s completed: %d findings", session.id, len(session.findings)
        )
        return session

    async def run_single_tool(
        self,
        category: str,
        tool: str,
        params: Dict[str, Any],
    ) -> ScanSession:
        """Run a single HexStrike tool and return a session with findings."""
        target_str = params.get("target", "unknown")
        target = Target(value=target_str)
        session = ScanSession(target=target)

        result = await self._client.run_tool(category, tool, params)
        session.mark_tool_done(f"{category}/{tool}")

        finding = Finding(
            target=target_str,
            tool=f"{category}/{tool}",
            category=category,
            title=f"Tool Output: {tool}",
            description=result.raw_output or json.dumps(result.output, indent=2, default=str),
            severity=Severity.INFO,
            raw_data={"output": result.output, "errors": result.errors},
        )
        session.add_finding(finding)

        if result.has_errors:
            for err in result.errors:
                err_finding = Finding(
                    target=target_str,
                    tool=f"{category}/{tool}",
                    category="error",
                    title=f"Error from {tool}",
                    description=err,
                    severity=Severity.LOW,
                )
                session.add_finding(err_finding)

        session.finish()
        return session


def save_session(session: ScanSession, results_dir: Optional[Path] = None) -> Path:
    """Persist a scan session as JSON to the results directory."""
    out_dir = results_dir or settings.results_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"{session.target.value.replace('.', '_')}_{session.id}_{timestamp}.json"
    filepath = out_dir / filename

    filepath.write_text(
        session.model_dump_json(indent=2),
        encoding="utf-8",
    )
    logger.info("Session saved to %s", filepath)
    return filepath


def _risk_to_severity(score: float) -> Severity:
    if score >= 8.0:
        return Severity.CRITICAL
    if score >= 6.0:
        return Severity.HIGH
    if score >= 4.0:
        return Severity.MEDIUM
    if score >= 2.0:
        return Severity.LOW
    return Severity.INFO
