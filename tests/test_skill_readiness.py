"""Static checks for mandatory blhackbox skill readiness guidance."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parent.parent
SKILL_FILES = sorted((ROOT / ".claude" / "skills").glob("*/SKILL.md"))
TEMPLATE_FILES = sorted((ROOT / "blhackbox" / "prompts" / "templates").glob("*.md"))
PROMPT_FILES = SKILL_FILES + TEMPLATE_FILES


def test_skill_and_template_files_discovered() -> None:
    assert len(SKILL_FILES) == 11
    assert len(TEMPLATE_FILES) == 11


def test_all_skills_require_tool_and_methodology_readiness() -> None:
    required_phrases = [
        "## Mandatory Tool & Methodology Readiness",
        "Do **not** start the skill's execution plan until this readiness pass is complete.",
        "Inventory 100% of usable capabilities first.",
        "Build a working tool matrix before execution",
        "closest supported profile",
        "Understand the called skill's command steps before running commands.",
        "Select the correct security framework overlays.",
        "MITRE ATT&CK",
        "OWASP Web Top 10",
        "OWASP API Security Top 10",
        "OSINT/passive recon → active discovery",
        "payload generation/adaptation",
    ]
    for path in PROMPT_FILES:
        text = path.read_text(encoding="utf-8")
        missing = [phrase for phrase in required_phrases if phrase not in text]
        assert not missing, f"{path.relative_to(ROOT)} is missing: {missing}"


def test_prompts_use_existing_mcp_status_target() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert "mcp-status:" in makefile
    for path in PROMPT_FILES:
        text = path.read_text(encoding="utf-8")
        assert "make mcp-status" in text
        assert "make health" not in text
