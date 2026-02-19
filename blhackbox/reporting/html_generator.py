"""Generate interactive HTML reports from scan sessions or aggregated payloads."""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from jinja2 import BaseLoader, Environment

from blhackbox.config import settings
from blhackbox.models.base import ScanSession

if TYPE_CHECKING:
    from blhackbox.models.aggregated_payload import AggregatedPayload

logger = logging.getLogger("blhackbox.reporting.html_generator")

# Allowed severity values for CSS class injection prevention
_ALLOWED_SEVERITIES = frozenset({"critical", "high", "medium", "low", "info"})
_SAFE_CSS_CLASS = re.compile(r"^[a-z]+$")

HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Blhackbox Report – {{ session.target.value }}</title>
    <style>
        :root {
            --bg: #0d1117;
            --surface: #161b22;
            --border: #30363d;
            --text: #c9d1d9;
            --text-muted: #8b949e;
            --accent: #58a6ff;
            --critical: #f85149;
            --high: #f0883e;
            --medium: #d29922;
            --low: #3fb950;
            --info: #58a6ff;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont,
                'Segoe UI', Helvetica, Arial, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
            padding: 2rem;
        }
        .container { max-width: 1100px; margin: 0 auto; }
        h1 { color: var(--accent); margin-bottom: 0.5rem; font-size: 1.8rem; }
        h2 {
            color: var(--text); margin: 2rem 0 1rem;
            border-bottom: 1px solid var(--border); padding-bottom: 0.5rem;
        }
        h3 { color: var(--text-muted); margin: 1rem 0 0.5rem; }
        .meta { color: var(--text-muted); margin-bottom: 2rem; }
        .meta span { margin-right: 2rem; }
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
            gap: 1rem;
            margin: 1.5rem 0;
        }
        .summary-card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 1rem;
            text-align: center;
        }
        .summary-card .count { font-size: 2rem; font-weight: bold; }
        .summary-card.critical .count { color: var(--critical); }
        .summary-card.high .count { color: var(--high); }
        .summary-card.medium .count { color: var(--medium); }
        .summary-card.low .count { color: var(--low); }
        .summary-card.info .count { color: var(--info); }
        .finding {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 1.25rem;
            margin-bottom: 1rem;
        }
        .finding-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.75rem;
        }
        .finding-title { font-weight: 600; font-size: 1.05rem; }
        .severity-badge {
            padding: 0.2rem 0.7rem;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
        }
        .severity-critical { background: var(--critical); color: #fff; }
        .severity-high { background: var(--high); color: #fff; }
        .severity-medium { background: var(--medium); color: #000; }
        .severity-low { background: var(--low); color: #000; }
        .severity-info { background: var(--info); color: #fff; }
        .finding-body { color: var(--text-muted); font-size: 0.9rem; }
        .finding-body pre {
            background: var(--bg);
            border: 1px solid var(--border);
            border-radius: 4px;
            padding: 0.75rem;
            overflow-x: auto;
            margin: 0.5rem 0;
            font-size: 0.82rem;
        }
        .evidence { margin-top: 0.75rem; }
        .remediation {
            margin-top: 0.75rem;
            padding: 0.75rem;
            background: rgba(63, 185, 80, 0.1);
            border-left: 3px solid var(--low);
            border-radius: 0 4px 4px 0;
        }
        .tools-list { list-style: none; padding: 0; }
        .tools-list li {
            display: inline-block;
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 4px;
            padding: 0.2rem 0.6rem;
            margin: 0.2rem;
            font-size: 0.85rem;
        }
        footer {
            margin-top: 3rem;
            padding-top: 1rem;
            border-top: 1px solid var(--border);
            color: var(--text-muted);
            font-size: 0.8rem;
            text-align: center;
        }
        @media print {
            body { background: #fff; color: #000; }
            .finding { border-color: #ddd; }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Blhackbox Security Assessment Report</h1>
        <div class="meta">
            <span>Target: <strong>{{ session.target.value }}</strong></span>
            <span>Session: <strong>{{ session.id }}</strong></span>
            <span>Date: <strong>{{ generated_at }}</strong></span>
            {% if session.duration_seconds is not none %}
            <span>Duration: <strong>{{ "%.1f"|format(session.duration_seconds) }}s</strong></span>
            {% endif %}
        </div>

        <h2>Executive Summary</h2>
        <div class="summary-grid">
            {% for sev in ['critical', 'high', 'medium', 'low', 'info'] %}
            <div class="summary-card {{ sev }}">
                <div class="count">{{ severity_counts.get(sev, 0) }}</div>
                <div>{{ sev | upper }}</div>
            </div>
            {% endfor %}
        </div>

        <h2>Tools Executed</h2>
        <ul class="tools-list">
            {% for tool in session.tools_executed %}
            <li>{{ tool }}</li>
            {% endfor %}
        </ul>

        <h2>Findings ({{ session.findings|length }})</h2>
        {% for finding in findings_sorted %}
        <div class="finding">
            <div class="finding-header">
                <span class="finding-title">{{ finding.title }}</span>
                <span class="severity-badge severity-{{ finding.severity | safe_severity }}">
                    {{ finding.severity }}</span>
            </div>
            <div class="finding-body">
                <p><strong>Tool:</strong> {{ finding.tool }}</p>
                {% if finding.description %}
                <pre>{{ finding.description | truncate_text(3000) }}</pre>
                {% endif %}
                {% if finding.evidence %}
                <div class="evidence">
                    <strong>Evidence:</strong>
                    <pre>{{ finding.evidence | truncate_text(2000) }}</pre>
                </div>
                {% endif %}
                {% if finding.remediation %}
                <div class="remediation">
                    <strong>Remediation:</strong> {{ finding.remediation }}
                </div>
                {% endif %}
            </div>
        </div>
        {% endfor %}

        <footer>
            Generated by Blhackbox v2.0.0 – MCP-based Autonomous Pentesting Framework<br>
            This report is confidential. Unauthorized distribution is prohibited.
        </footer>
    </div>
</body>
</html>
"""

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}


def generate_html_report(
    session: ScanSession,
    output_path: str | None = None,
) -> Path:
    """Generate an HTML report from a scan session.

    Args:
        session: Completed scan session with findings.
        output_path: Override output file path.

    Returns:
        Path to the generated HTML file.
    """
    env = Environment(loader=BaseLoader(), autoescape=True)

    def _safe_severity(value: str) -> str:
        """Sanitize severity for use in CSS class names."""
        val = str(value).lower().strip()
        if val in _ALLOWED_SEVERITIES and _SAFE_CSS_CLASS.match(val):
            return val
        return "info"

    def _truncate_text(value: str, max_len: int = 3000) -> str:
        """Safely truncate text content."""
        return str(value)[:max_len]

    env.filters["safe_severity"] = _safe_severity
    env.filters["truncate_text"] = _truncate_text

    template = env.from_string(HTML_TEMPLATE)

    findings_sorted = sorted(
        session.findings,
        key=lambda f: SEVERITY_ORDER.get(
            f.severity if isinstance(f.severity, str) else f.severity.value, 99
        ),
    )

    severity_counts = session.severity_counts

    html = template.render(
        session=session,
        findings_sorted=findings_sorted,
        severity_counts=severity_counts,
        generated_at=datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
    )

    if output_path:
        out = Path(output_path)
    else:
        out_dir = settings.results_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / f"report_{session.id}.html"

    out.write_text(html, encoding="utf-8")
    logger.info("HTML report generated: %s", out)
    return out


# ---------------------------------------------------------------------------
# AggregatedPayload-based report generation
# ---------------------------------------------------------------------------

AGGREGATED_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Blhackbox Report – {{ payload.target }}</title>
    <style>
        :root {
            --bg: #0d1117;
            --surface: #161b22;
            --border: #30363d;
            --text: #c9d1d9;
            --text-muted: #8b949e;
            --accent: #58a6ff;
            --critical: #f85149;
            --high: #f0883e;
            --medium: #d29922;
            --low: #3fb950;
            --info: #58a6ff;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont,
                'Segoe UI', Helvetica, Arial, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
            padding: 2rem;
        }
        .container { max-width: 1100px; margin: 0 auto; }
        h1 { color: var(--accent); margin-bottom: 0.5rem; font-size: 1.8rem; }
        h2 {
            color: var(--text); margin: 2rem 0 1rem;
            border-bottom: 1px solid var(--border); padding-bottom: 0.5rem;
        }
        h3 { color: var(--text-muted); margin: 1rem 0 0.5rem; }
        .meta { color: var(--text-muted); margin-bottom: 2rem; }
        .meta span { margin-right: 2rem; }
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
            gap: 1rem;
            margin: 1.5rem 0;
        }
        .summary-card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 1rem;
            text-align: center;
        }
        .summary-card .count { font-size: 2rem; font-weight: bold; }
        .summary-card.critical .count { color: var(--critical); }
        .summary-card.high .count { color: var(--high); }
        .summary-card.medium .count { color: var(--medium); }
        .summary-card.low .count { color: var(--low); }
        .summary-card.info .count { color: var(--info); }
        .finding {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 1.25rem;
            margin-bottom: 1rem;
        }
        .finding-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.75rem;
        }
        .finding-title { font-weight: 600; font-size: 1.05rem; }
        .severity-badge {
            padding: 0.2rem 0.7rem;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
        }
        .severity-critical { background: var(--critical); color: #fff; }
        .severity-high { background: var(--high); color: #fff; }
        .severity-medium { background: var(--medium); color: #000; }
        .severity-low { background: var(--low); color: #000; }
        .severity-info { background: var(--info); color: #fff; }
        .finding-body { color: var(--text-muted); font-size: 0.9rem; }
        .finding-body pre {
            background: var(--bg);
            border: 1px solid var(--border);
            border-radius: 4px;
            padding: 0.75rem;
            overflow-x: auto;
            margin: 0.5rem 0;
            font-size: 0.82rem;
        }
        .tools-list { list-style: none; padding: 0; }
        .tools-list li {
            display: inline-block;
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 4px;
            padding: 0.2rem 0.6rem;
            margin: 0.2rem;
            font-size: 0.85rem;
        }
        .anomaly {
            background: var(--surface);
            border-left: 3px solid var(--medium);
            border-radius: 0 8px 8px 0;
            padding: 1rem;
            margin-bottom: 0.75rem;
        }
        .stat-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin: 1rem 0;
        }
        .stat-card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 0.75rem;
        }
        .stat-card .label { color: var(--text-muted); font-size: 0.85rem; }
        .stat-card .value { font-size: 1.2rem; font-weight: 600; }
        footer {
            margin-top: 3rem;
            padding-top: 1rem;
            border-top: 1px solid var(--border);
            color: var(--text-muted);
            font-size: 0.8rem;
            text-align: center;
        }
        @media print {
            body { background: #fff; color: #000; }
            .finding { border-color: #ddd; }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Blhackbox Security Assessment Report</h1>
        <div class="meta">
            <span>Target: <strong>{{ payload.target }}</strong></span>
            <span>Session: <strong>{{ payload.session_id }}</strong></span>
            <span>Date: <strong>{{ generated_at }}</strong></span>
        </div>

        {% if payload.metadata.warning %}
        <div class="anomaly" style="border-left-color: var(--high);">
            <strong>Warning:</strong> {{ payload.metadata.warning }}
        </div>
        {% endif %}

        <h2>Executive Summary</h2>
        <div class="summary-grid">
            {% for sev in ['critical', 'high', 'medium', 'low', 'info'] %}
            <div class="summary-card {{ sev }}">
                <div class="count">{{ severity_counts.get(sev, 0) }}</div>
                <div>{{ sev | upper }}</div>
            </div>
            {% endfor %}
        </div>

        <h2>Tools &amp; Agents</h2>
        <ul class="tools-list">
            {% for tool in payload.metadata.tools_run %}
            <li>{{ tool }}</li>
            {% endfor %}
        </ul>

        <h2>Vulnerabilities ({{ vulns | length }})</h2>
        {% for vuln in vulns %}
        <div class="finding">
            <div class="finding-header">
                <span class="finding-title">{{ vuln.cve or vuln.description[:60] }}</span>
                <span class="severity-badge severity-{{ vuln.severity | safe_severity }}">
                    {{ vuln.severity }}</span>
            </div>
            <div class="finding-body">
                <p><strong>Host:</strong> {{ vuln.host }}</p>
                {% if vuln.cvss %}<p><strong>CVSS:</strong> {{ vuln.cvss }}</p>{% endif %}
                <pre>{{ vuln.description | truncate_text(3000) }}</pre>
                {% if vuln.references %}
                <p><strong>References:</strong>
                {% for ref in vuln.references %}
                    {{ ref }}{% if not loop.last %}, {% endif %}
                {% endfor %}
                </p>
                {% endif %}
            </div>
        </div>
        {% endfor %}

        {% if network_hosts %}
        <h2>Network Hosts ({{ network_hosts | length }})</h2>
        {% for host in network_hosts %}
        <div class="finding">
            <div class="finding-title">{{ host.ip }}</div>
            <div class="finding-body">
                <pre>{% for p in host.ports %}
{{ p.port }}/{{ p.state }} {{ p.service }} {{ p.version }}
{% endfor %}</pre>
            </div>
        </div>
        {% endfor %}
        {% endif %}

        {% if anomalies %}
        <h2>Anomalies &amp; Scan Artifacts</h2>
        {% for a in anomalies %}
        <div class="anomaly">
            <strong>[{{ a.type }}]</strong> Count: {{ a.count }} |
            Relevance: {{ a.security_relevance }}<br>
            {{ a.security_note }}
        </div>
        {% endfor %}
        {% endif %}

        <h2>Scan Metadata</h2>
        <div class="stat-grid">
            <div class="stat-card">
                <div class="label">Total Raw Size (bytes)</div>
                <div class="value">{{ payload.metadata.total_raw_size_bytes }}</div>
            </div>
            <div class="stat-card">
                <div class="label">Compression Ratio</div>
                <div class="value">{{ "%.2f"|format(payload.metadata.compression_ratio) }}</div>
            </div>
            <div class="stat-card">
                <div class="label">Ollama Model</div>
                <div class="value">{{ payload.metadata.ollama_model }}</div>
            </div>
            <div class="stat-card">
                <div class="label">Duration</div>
                <div class="value">
                    {{ "%.1f"|format(payload.metadata.duration_seconds) }}s
                </div>
            </div>
        </div>

        <footer>
            Generated by Blhackbox v2.0 – MCP-based Autonomous Pentesting Framework<br>
            This report is confidential. Unauthorized distribution is prohibited.
        </footer>
    </div>
</body>
</html>
"""


def generate_html_report_from_payload(
    payload: AggregatedPayload,
    output_path: str | None = None,
) -> Path:
    """Generate an HTML report from an AggregatedPayload.

    This is the v2.0 report generation path, consuming structured output
    from the Ollama preprocessing pipeline rather than raw scan results.

    Args:
        payload: Aggregated pentest data from the aggregator MCP server.
        output_path: Override output file path.

    Returns:
        Path to the generated HTML file.
    """
    env = Environment(loader=BaseLoader(), autoescape=True)
    env.filters["safe_severity"] = _safe_severity_filter
    env.filters["truncate_text"] = _truncate_text_filter

    template = env.from_string(AGGREGATED_HTML_TEMPLATE)

    vulns = sorted(
        payload.findings.vulnerabilities,
        key=lambda v: SEVERITY_ORDER.get(v.severity.lower(), 99),
    )

    severity_counts: dict[str, int] = {}
    for v in vulns:
        sev = v.severity.lower()
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    anomalies = [
        e for e in payload.error_log
        if e.security_relevance in ("medium", "high")
    ]

    html = template.render(
        payload=payload,
        vulns=vulns,
        severity_counts=severity_counts,
        network_hosts=payload.findings.hosts,
        anomalies=anomalies,
        generated_at=datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
    )

    if output_path:
        out = Path(output_path)
    else:
        out_dir = settings.results_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / f"report_{payload.session_id}.html"

    out.write_text(html, encoding="utf-8")
    logger.info("HTML report (aggregated) generated: %s", out)
    return out


def _safe_severity_filter(value: str) -> str:
    """Sanitize severity for use in CSS class names."""
    val = str(value).lower().strip()
    if val in _ALLOWED_SEVERITIES and _SAFE_CSS_CLASS.match(val):
        return val
    return "info"


def _truncate_text_filter(value: str, max_len: int = 3000) -> str:
    """Safely truncate text content."""
    return str(value)[:max_len]
