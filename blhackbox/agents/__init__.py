"""Ollama preprocessing agent classes for the blhackbox aggregator pipeline."""

from blhackbox.agents.base_agent import BaseAgent
from blhackbox.agents.error_log_agent import ErrorLogAgent
from blhackbox.agents.network_agent import NetworkAgent
from blhackbox.agents.recon_agent import ReconAgent
from blhackbox.agents.structure_agent import StructureAgent
from blhackbox.agents.vuln_agent import VulnAgent
from blhackbox.agents.web_agent import WebAgent

__all__ = [
    "BaseAgent",
    "ErrorLogAgent",
    "NetworkAgent",
    "ReconAgent",
    "StructureAgent",
    "VulnAgent",
    "WebAgent",
]
