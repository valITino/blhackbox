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
