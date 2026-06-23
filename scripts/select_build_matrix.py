"""Select which Docker images to (re)build from a set of changed files.

Reads the canonical component registry (.github/build-matrix.json) and prints a
compact JSON object ``{"matrix": [...components...], "any_changed": <bool>}`` for
the GitHub Actions build matrix.

Modes:
  --all              select every component (release tags / manual "build all")
  --service NAME     select a single component by service name (manual dispatch)
  --changed FILE     read changed paths (one per line) from FILE, or '-' for stdin,
                     and select the components whose ``paths`` globs match

Used by .github/workflows/ci.yml (per-component builds on push to main) and
.github/workflows/build-and-push.yml (release/manual builds).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / ".github" / "build-matrix.json"


def load_components() -> list[dict]:
    """Return the component objects from the canonical registry."""
    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    return data["components"]


def path_matches(glob: str, changed: str) -> bool:
    """Match a registry glob against a single changed file path.

    Two forms are supported: an exact path (``docker/kali-mcp.Dockerfile``) or a
    recursive directory prefix ending in ``/**`` (``kali-mcp/**``).
    """
    if glob.endswith("/**"):
        prefix = glob[:-2]  # "kali-mcp/**" -> "kali-mcp/"
        return changed == prefix.rstrip("/") or changed.startswith(prefix)
    return changed == glob


def select_changed(components: list[dict], changed_files: list[str]) -> list[dict]:
    """Return components with at least one ``paths`` glob matching a changed file."""
    return [
        comp
        for comp in components
        if any(path_matches(glob, changed) for glob in comp["paths"] for changed in changed_files)
    ]


def emit(selected: list[dict]) -> None:
    """Print the compact matrix payload to stdout."""
    payload = {"matrix": selected, "any_changed": bool(selected)}
    print(json.dumps(payload, separators=(",", ":")))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Select Docker images to rebuild.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true", help="Select every component.")
    group.add_argument("--service", metavar="NAME", help="Select one component by service name.")
    group.add_argument(
        "--changed",
        metavar="FILE",
        help="Read changed paths from FILE (or '-' for stdin) and select matching components.",
    )
    args = parser.parse_args(argv)

    components = load_components()

    if args.all:
        emit(components)
        return 0

    if args.service:
        match = [comp for comp in components if comp["service"] == args.service]
        if not match:
            valid = ", ".join(comp["service"] for comp in components)
            parser.error(f"unknown service '{args.service}'. Valid services: {valid}")
        emit(match)
        return 0

    if args.changed == "-":
        text = sys.stdin.read()
    else:
        text = Path(args.changed).read_text(encoding="utf-8")
    changed_files = [line.strip() for line in text.splitlines() if line.strip()]
    emit(select_changed(components, changed_files))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
