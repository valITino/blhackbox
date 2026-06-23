"""Checks that the Docker publish pipeline covers all compose images, that the
build actions stay node24-ready, and that the per-component build selection maps
changed files to the right images."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
COMPOSE = ROOT / "docker-compose.yml"
REGISTRY = ROOT / ".github" / "build-matrix.json"
REUSABLE_BUILD = ROOT / ".github" / "workflows" / "_build-images.yml"
BUILD_WORKFLOW = ROOT / ".github" / "workflows" / "build-and-push.yml"
SELECT_SCRIPT = ROOT / "scripts" / "select_build_matrix.py"


def _registry() -> dict:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def _services() -> set[str]:
    return {component["service"] for component in _registry()["components"]}


def _run_select(*args: str, stdin: str = "") -> dict:
    proc = subprocess.run(
        [sys.executable, str(SELECT_SCRIPT), *args],
        input=stdin,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(proc.stdout)


def test_compose_blhackbox_images_are_in_publish_matrix() -> None:
    compose = COMPOSE.read_text(encoding="utf-8")
    compose_tags = set(re.findall(r"image:\s*crhacky/blhackbox:([a-z0-9-]+)", compose))

    assert compose_tags
    assert compose_tags <= _services()


def test_build_workflow_uses_node24_ready_actions() -> None:
    # The pinned docker actions now live in the reusable build workflow.
    workflow = REUSABLE_BUILD.read_text(encoding="utf-8")

    legacy_actions = [
        "actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683",
        "docker/setup-buildx-action@b5ca514318bd6ebac0fb2aedd5d36ec1b5c232a2",
        "docker/metadata-action@902fa8ec7d6ecbf8d84d538b9b233a880e428804",
        "docker/build-push-action@14487ce63c7a62a4a324b0bfb37086795e31c6c1",
    ]
    for action in legacy_actions:
        assert action not in workflow

    for version in ["# v6.0.3", "# v4.1.0", "# v6.1.0", "# v7.2.0"]:
        assert version in workflow


def test_registry_dockerfiles_exist_and_self_reference() -> None:
    for component in _registry()["components"]:
        dockerfile = ROOT / component["dockerfile"]
        assert dockerfile.is_file(), f"missing {component['dockerfile']}"
        # A change to a component's own Dockerfile must always rebuild that image.
        assert component["dockerfile"] in component["paths"], (
            f"{component['service']} paths must include its own Dockerfile"
        )
        # JSON boolean keeps the reusable workflow's `if: inputs.scout` correct.
        assert component["scout"] is False


def test_dispatch_choice_offers_every_service() -> None:
    workflow = BUILD_WORKFLOW.read_text(encoding="utf-8")
    options = set(re.findall(r"^\s*-\s+([a-z0-9-]+)\s*$", workflow, re.MULTILINE))

    assert "all" in options
    assert _services() <= options


def test_select_all_returns_every_component() -> None:
    result = _run_select("--all")

    assert result["any_changed"] is True
    assert {component["service"] for component in result["matrix"]} == _services()


def test_select_single_service() -> None:
    result = _run_select("--service", "kali-mcp")

    assert result["any_changed"] is True
    assert [component["service"] for component in result["matrix"]] == ["kali-mcp"]


def test_select_unknown_service_errors() -> None:
    proc = subprocess.run(
        [sys.executable, str(SELECT_SCRIPT), "--service", "does-not-exist"],
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0


def test_select_changed_docs_only_builds_nothing() -> None:
    result = _run_select("--changed", "-", stdin="README.md\ndocs/guide.md\nLICENSE\n")

    assert result["any_changed"] is False
    assert result["matrix"] == []


def test_select_changed_core_and_tests_build_nothing() -> None:
    # No image bakes in the core package or tests, so these rebuild nothing.
    changed = "blhackbox/core/x.py\ntests/test_x.py\nMakefile\ndocker-compose.yml\n"
    result = _run_select("--changed", "-", stdin=changed)

    assert result["any_changed"] is False


def test_select_changed_maps_files_to_components() -> None:
    cases = {
        "kali-mcp/server.py": "kali-mcp",
        "kali-mcp/requirements.txt": "kali-mcp",
        "docker/kali-mcp.Dockerfile": "kali-mcp",
        "screenshot-mcp/server.py": "screenshot-mcp",
        "CLAUDE.md": "claude-code",
        ".claude/skills/recon/SKILL.md": "claude-code",
        "docker/claude-code-entrypoint.sh": "claude-code",
        "docker/hexstrike-ai.Dockerfile": "hexstrike-ai",
    }
    for changed, expected in cases.items():
        result = _run_select("--changed", "-", stdin=changed + "\n")
        assert [component["service"] for component in result["matrix"]] == [expected], changed


def test_select_changed_multiple_components_union() -> None:
    result = _run_select("--changed", "-", stdin="kali-mcp/server.py\nboaz-mcp/server.py\n")

    assert {component["service"] for component in result["matrix"]} == {"kali-mcp", "boaz-mcp"}
