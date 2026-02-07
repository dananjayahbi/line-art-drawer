"""
Zone-Based Progressive Engine (Engine 3D)
==========================================
Identifies focal points and importance zones in artwork,
then reveals the drawing radiating outward from interest centers.
Creates an engaging "unveiling" effect that naturally draws viewer attention.

Key capabilities:
- Spectral residual saliency detection
- Face/eye detection for portrait priority
- Radial zone partitioning from focal points
- Multiple animation modes (single, multi, spiral, burst)
- Smooth zone transition blending
"""

from .engine import ZoneProgressiveEngine
from .config import ZoneProgressiveConfig

__all__ = [
    "ZoneProgressiveEngine",
    "ZoneProgressiveConfig",
]
