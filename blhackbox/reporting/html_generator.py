"""Generate interactive HTML reports from scan sessions."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

from jinja2 import BaseLoader, Environment

from blhackbox.config import settings
from blhackbox.models.base import ScanSession

logger = logging.getLogger("blhackbox.reporting.html_generator")

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
                <span class="severity-badge severity-{{ finding.severity }}">
                    {{ finding.severity }}</span>
            </div>
            <div class="finding-body">
                <p><strong>Tool:</strong> {{ finding.tool }}</p>
                {% if finding.description %}
                <pre>{{ finding.description[:3000] }}</pre>
                {% endif %}
                {% if finding.evidence %}
                <div class="evidence">
                    <strong>Evidence:</strong>
                    <pre>{{ finding.evidence[:2000] }}</pre>
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
            Generated by Blhackbox v1.0.0 – HexStrike Hybrid Autonomous Pentesting Framework<br>
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
