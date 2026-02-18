"""ErrorLogAgent — compresses noise into structured error logs with security annotations."""

from __future__ import annotations

from blhackbox.agents.base_agent import BaseAgent


class ErrorLogAgent(BaseAgent):
    """Processes all noise/errors from raw scan output.

    Never discards data — only categorizes and compresses it.  Assesses
    security relevance so Claude can decide whether scan artifacts belong
    in the final report.
    """

    agent_name: str = "error_log_agent"
