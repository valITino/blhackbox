"""Argus-inspired modules that run through HexStrike."""

from blhackbox.modules.argus_bridge.port_scan import PortScanModule
from blhackbox.modules.argus_bridge.subdomain_enum import SubdomainEnumModule
from blhackbox.modules.argus_bridge.tech_detect import TechDetectModule

__all__ = ["SubdomainEnumModule", "TechDetectModule", "PortScanModule"]
