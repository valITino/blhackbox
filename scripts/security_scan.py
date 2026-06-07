"""Small offline security scanner for blhackbox CI/dev sandboxes.

This is not a replacement for Bandit or pip-audit. It provides a dependency-free
baseline when network restrictions prevent installing dedicated security tools.
"""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCAN_PATHS = [
    ROOT / "blhackbox",
    ROOT / "kali-mcp",
    ROOT / "screenshot-mcp",
    ROOT / "wire-mcp",
    ROOT / "boaz-mcp",
    ROOT / "hexstrike-mcp",
    ROOT / "scripts",
]
RISKY_CALLS = {
    "eval": "dynamic code execution",
    "exec": "dynamic code execution",
    "os.system": "shell execution",
    "subprocess.Popen": "subprocess Popen usage",
    "subprocess.run": "subprocess.run usage requires shell=False review",
    "asyncio.create_subprocess_shell": "shell subprocess execution",
    "yaml.load": "unsafe YAML loading",
    "pickle.load": "pickle deserialization",
    "pickle.loads": "pickle deserialization",
}


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


def _has_shell_true(node: ast.Call) -> bool:
    for keyword in node.keywords:
        if keyword.arg == "shell" and isinstance(keyword.value, ast.Constant):
            return keyword.value.value is True
    return False


def scan_file(path: Path) -> list[str]:
    findings: list[str] = []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        return [f"{path}: syntax error during security scan: {exc}"]

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node.func)
        if name in RISKY_CALLS:
            findings.append(f"{path}:{node.lineno}: {name} ({RISKY_CALLS[name]})")
        if _has_shell_true(node):
            findings.append(f"{path}:{node.lineno}: shell=True subprocess execution")
    return findings


def main() -> int:
    findings: list[str] = []
    for base in SCAN_PATHS:
        if base.is_file() and base.suffix == ".py":
            findings.extend(scan_file(base))
            continue
        if base.is_dir():
            for path in sorted(base.rglob("*.py")):
                findings.extend(scan_file(path))

    if findings:
        print("Security scan findings:")
        for finding in findings:
            print(f"- {finding}")
        return 1

    print("Security scan passed: no high-risk Python patterns detected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
