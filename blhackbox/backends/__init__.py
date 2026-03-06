"""Tool execution backends – local CLI or auto-detect."""

from blhackbox.backends.base import ToolBackend, ToolResult
from blhackbox.backends.local import LocalBackend

__all__ = [
    "ToolBackend",
    "ToolResult",
    "LocalBackend",
    "get_backend",
]


async def get_backend() -> ToolBackend:
    """Return the best available backend (local CLI).

    The caller is responsible for calling ``await backend.close()`` when done.
    """
    local = LocalBackend()
    await local.connect()
    return local
