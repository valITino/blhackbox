"""Inject verification document into the Claude Code session context.

Reads ``verification.env`` from the project root, renders the
``verification.md`` template with the configured values, and writes
the active document to ``.claude/verification-active.md``.

The session-start hook (or ``make inject-verification``) calls this
script so that the rendered authorization document is present in
the Claude Code context before any pentest prompt templates run.

Usage::

    python -m blhackbox.prompts.inject_verification [--env PATH] [--out PATH]
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _parse_env_file(env_path: Path) -> dict[str, str]:
    """Parse a simple KEY=VALUE env file, ignoring comments and blanks."""
    values: dict[str, str] = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip()
    return values


def _validate_required_fields(env: dict[str, str]) -> list[str]:
    """Return a list of missing required fields."""
    required = [
        "AUTHORIZATION_STATUS",
        "ENGAGEMENT_ID",
        "AUTHORIZATION_DATE",
        "EXPIRATION_DATE",
        "AUTHORIZING_ORGANIZATION",
        "TESTER_NAME",
        "TARGET_1",
        "TESTING_START",
        "TESTING_END",
        "SIGNATORY_NAME",
        "SIGNATURE_DATE",
    ]
    return [f for f in required if not env.get(f)]


def _check_expiration(env: dict[str, str]) -> str | None:
    """Return an error message if the authorization has expired."""
    exp = env.get("EXPIRATION_DATE", "")
    if not exp:
        return None
    try:
        exp_date = datetime.strptime(exp, "%Y-%m-%d").replace(tzinfo=UTC)
        if exp_date < datetime.now(UTC):
            return f"Authorization expired on {exp}."
    except ValueError:
        return f"Invalid EXPIRATION_DATE format: {exp!r} (expected YYYY-MM-DD)."
    return None


def render_verification(env: dict[str, str], template_text: str) -> str:
    """Replace ``{{PLACEHOLDER}}`` tokens in the template with env values."""
    def _replace(match: re.Match[str]) -> str:
        key = match.group(1)
        return env.get(key, match.group(0))

    return re.sub(r"\{\{(\w+)\}\}", _replace, template_text)


def inject(
    env_path: Path | None = None,
    out_path: Path | None = None,
) -> dict[str, Any]:
    """Run the full injection pipeline.

    Returns:
        Dict with ``status``, ``output_path``, and optional ``warnings``.
    """
    project_root = Path(__file__).resolve().parents[2]

    if env_path is None:
        env_path = project_root / "verification.env"
    if out_path is None:
        out_path = project_root / ".claude" / "verification-active.md"

    result: dict[str, Any] = {"warnings": []}

    # --- Read env ---
    if not env_path.exists():
        return {
            "status": "error",
            "message": (
                f"verification.env not found at {env_path}. "
                "Copy verification.env and fill in your engagement details."
            ),
        }

    env = _parse_env_file(env_path)

    # --- Check status ---
    status = env.get("AUTHORIZATION_STATUS", "PENDING").upper()
    if status != "ACTIVE":
        return {
            "status": "inactive",
            "message": (
                "AUTHORIZATION_STATUS is not ACTIVE. "
                "Set AUTHORIZATION_STATUS=ACTIVE in verification.env "
                "after filling in all fields."
            ),
        }

    # --- Validate required fields ---
    missing = _validate_required_fields(env)
    if missing:
        return {
            "status": "error",
            "message": (
                f"Missing required fields in verification.env: {', '.join(missing)}. "
                "Fill in all required fields before activating."
            ),
        }

    # --- Check expiration ---
    exp_err = _check_expiration(env)
    if exp_err:
        return {"status": "expired", "message": exp_err}

    # --- Read template ---
    template_path = Path(__file__).parent / "verification.md"
    if not template_path.exists():
        return {
            "status": "error",
            "message": f"Verification template not found: {template_path}",
        }

    template_text = template_path.read_text(encoding="utf-8")

    # --- Render ---
    rendered = render_verification(env, template_text)

    # --- Write active document ---
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(rendered, encoding="utf-8")

    result["status"] = "active"
    result["output_path"] = str(out_path)
    targets = ", ".join(
        env.get(f"TARGET_{i}", "")
        for i in range(1, 4)
        if env.get(f"TARGET_{i}")
    )
    result["message"] = (
        f"Verification document activated → {out_path}\n"
        f"Engagement: {env.get('ENGAGEMENT_ID', 'N/A')}\n"
        f"Targets: {targets}\n"
        f"Window: {env.get('TESTING_START', '?')} — "
        f"{env.get('TESTING_END', '?')} {env.get('TIMEZONE', 'UTC')}\n"
        f"Authorized by: {env.get('SIGNATORY_NAME', 'N/A')}"
    )
    return result


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Inject pentest verification into Claude Code session."
    )
    parser.add_argument(
        "--env",
        type=Path,
        default=None,
        help="Path to verification.env (default: <project_root>/verification.env)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output path (default: <project_root>/.claude/verification-active.md)",
    )
    args = parser.parse_args()

    result = inject(env_path=args.env, out_path=args.out)
    print(result["message"])

    if result["status"] not in ("active",):
        sys.exit(1)


if __name__ == "__main__":
    main()
