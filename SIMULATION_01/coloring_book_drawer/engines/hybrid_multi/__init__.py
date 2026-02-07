"""
Hybrid Multi-Strategy Engine (Engine 3F)
==========================================
The most complex engine in the system. Analyses image regions,
classifies visual characteristics, assigns optimal rendering
strategies per region, and orchestrates a coordinated reveal.

Exports:
    HybridMultiEngine  - Main engine class
    HybridMultiConfig  - Configuration dataclass
"""

from .engine import HybridMultiEngine
from .config import HybridMultiConfig

__all__ = [
    "HybridMultiEngine",
    "HybridMultiConfig",
]
