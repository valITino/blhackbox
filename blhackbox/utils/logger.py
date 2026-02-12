"""Rich-powered structured logging for Blhackbox."""

from __future__ import annotations

import logging

from rich.console import Console
from rich.logging import RichHandler
from rich.theme import Theme

_THEME = Theme(
    {
        "info": "cyan",
        "warning": "yellow",
        "error": "bold red",
        "success": "bold green",
        "banner": "bold magenta",
    }
)

console = Console(theme=_THEME, stderr=True)


def setup_logging(level: str = "INFO") -> logging.Logger:
    """Configure the root blhackbox logger with Rich output."""
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    handler = RichHandler(
        console=console,
        show_time=True,
        show_path=False,
        markup=True,
        rich_tracebacks=True,
        tracebacks_show_locals=False,
    )
    handler.setLevel(numeric_level)

    logger = logging.getLogger("blhackbox")
    logger.setLevel(numeric_level)
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.propagate = False

    return logger


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under the blhackbox namespace."""
    return logging.getLogger(f"blhackbox.{name}")


def print_banner() -> None:
    """Print the Blhackbox startup banner."""
    banner = r"""
[banner]
 ____  _ _                _    _
| __ )| | |__   __ _  ___| | _| |__   _____  __
|  _ \| | '_ \ / _` |/ __| |/ / '_ \ / _ \ \/ /
| |_) | | | | | (_| | (__|   <| |_) | (_) >  <
|____/|_|_| |_|\__,_|\___|_|\_\_.__/ \___/_/\_\

 HexStrike Hybrid Autonomous Pentesting Framework v1.0.0
[/banner]
"""
    console.print(banner)


def print_warning_banner() -> None:
    """Print a red warning banner before any scanning activity."""
    divider = "=" * 70
    console.print(
        f"\n[error]"
        f"{divider}\n"
        f"  WARNING: You are about to perform active security testing.\n"
        f"  Ensure you have WRITTEN AUTHORIZATION from the target owner.\n"
        f"  Unauthorized testing is ILLEGAL and may result in prosecution.\n"
        f"{divider}"
        f"[/error]\n"
    )
