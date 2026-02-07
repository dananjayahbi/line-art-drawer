"""
Orchestration Sub-Package
============================
Coordinates multi-strategy rendering for Engine 3F (Hybrid Multi-Strategy).

Provides the orchestrator that dispatches lightweight internal strategy
renderers per region, the stroke merger that orders reveals by priority,
and the transition blender that feathers region boundaries.
"""

from .orchestrator import MultiStrategyOrchestrator
from .stroke_merger import StrokeMerger
from .transition_blender import TransitionBlender

__all__ = [
    "MultiStrategyOrchestrator",
    "StrokeMerger",
    "TransitionBlender",
]
