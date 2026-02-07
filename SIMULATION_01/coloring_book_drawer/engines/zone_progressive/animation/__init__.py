"""
Zone-Based Progressive Engine - Animation Package
===================================================
Zone-ordered reveal animation, per-zone stroke generation,
and smooth zone transition blending.
"""

from .revealer import ZoneOrderedRevealer
from .stroke_generator import ZoneStrokeGenerator
from .transition_blender import TransitionBlender

__all__ = [
    "ZoneOrderedRevealer",
    "ZoneStrokeGenerator",
    "TransitionBlender",
]
