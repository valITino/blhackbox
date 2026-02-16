"""Tool execution backends – HexStrike API, local CLI, or auto-detect."""

from blhackbox.backends.base import ToolBackend, ToolResult
from blhackbox.backends.hexstrike import HexStrikeBackend
from blhackbox.backends.local import LocalBackend

__all__ = [
    "ToolBackend",
    "ToolResult",
    "HexStrikeBackend",
    "LocalBackend",
    "get_backend",
]


async def get_backend() -> ToolBackend:
    """Return the best available backend (HexStrike if reachable, else local).

    The caller is responsible for calling ``await backend.close()`` when done.
    """
    try:
        hs = HexStrikeBackend()
        await hs.connect()
        if await hs.health_check():
            return hs
        await hs.close()
    except Exception:
        pass

    local = LocalBackend()
    await local.connect()
    return local
