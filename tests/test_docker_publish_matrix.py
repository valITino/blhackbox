"""Checks that compose images are covered by Docker Hub publishing."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
COMPOSE = ROOT / "docker-compose.yml"
BUILD_WORKFLOW = ROOT / ".github" / "workflows" / "build-and-push.yml"


def test_compose_blhackbox_images_are_in_publish_matrix() -> None:
    compose = COMPOSE.read_text(encoding="utf-8")
    workflow = BUILD_WORKFLOW.read_text(encoding="utf-8")

    compose_tags = set(re.findall(r"image:\s*crhacky/blhackbox:([a-z0-9-]+)", compose))
    published_services = set(re.findall(r"service:\s*([a-z0-9-]+)", workflow))

    assert compose_tags
    assert compose_tags <= published_services


def test_build_workflow_uses_node24_ready_actions() -> None:
    workflow = BUILD_WORKFLOW.read_text(encoding="utf-8")

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
