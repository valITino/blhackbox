"""Prompt management for blhackbox agents and templates."""

from __future__ import annotations

from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent
_TEMPLATES_DIR = _PROMPTS_DIR / "templates"
# Template registry: slug -> filename
TEMPLATES = {
    "full-pentest": "full-pentest.md",
    "full-attack-chain": "full-attack-chain.md",
    "quick-scan": "quick-scan.md",
    "recon-deep": "recon-deep.md",
    "web-app-assessment": "web-app-assessment.md",
    "network-infrastructure": "network-infrastructure.md",
    "osint-gathering": "osint-gathering.md",
    "vuln-assessment": "vuln-assessment.md",
    "api-security": "api-security.md",
    "bug-bounty": "bug-bounty.md",
}


def load_template(name: str, target: str | None = None) -> str:
    """Load a prompt template by name.

    Args:
        name: Template slug (e.g. ``"full-pentest"``).
        target: If provided, replaces ``[TARGET]`` placeholders in the template.

    Returns:
        The template content as a string.

    Raises:
        FileNotFoundError: If the template does not exist.
        ValueError: If the template name is unknown.
    """
    filename = TEMPLATES.get(name)
    if filename is None:
        available = ", ".join(sorted(TEMPLATES.keys()))
        raise ValueError(f"Unknown template: {name!r}. Available: {available}")

    path = _TEMPLATES_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Template file not found: {path}")

    content = path.read_text(encoding="utf-8")
    if target is not None:
        content = content.replace("[TARGET]", target)
        content = content.replace("[TARGET_API_BASE_URL]", target)
    return content


def list_templates() -> list[dict[str, str]]:
    """Return metadata for all available prompt templates.

    Returns:
        List of dicts with ``name``, ``file``, and ``title`` keys.
    """
    templates = []
    for slug, filename in sorted(TEMPLATES.items()):
        path = _TEMPLATES_DIR / filename
        title = slug.replace("-", " ").title()
        if path.exists():
            first_line = path.read_text(encoding="utf-8").split("\n")[0]
            if first_line.startswith("# "):
                title = first_line[2:].strip()
        templates.append({"name": slug, "file": filename, "title": title})
    return templates



def load_playbook() -> str:
    """Load the Claude pentest playbook."""
    path = _PROMPTS_DIR / "claude_playbook.md"
    return path.read_text(encoding="utf-8")


def load_verification() -> str | None:
    """Load the active verification document if it exists.

    Returns:
        The rendered verification document content, or ``None`` if no
        active verification document has been generated yet.
    """
    active_path = _PROMPTS_DIR.parent.parent / ".claude" / "verification-active.md"
    if active_path.exists():
        return active_path.read_text(encoding="utf-8")
    return None
