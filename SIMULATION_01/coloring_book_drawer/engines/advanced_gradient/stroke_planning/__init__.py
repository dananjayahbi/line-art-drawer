"""
Advanced Gradient Engine - Stroke Planning Package
====================================================
Modules for generating, ordering, and planning stroke paths
from image analysis results.
"""

from .contour_strokes import ContourStrokeGenerator
from .gradient_strokes import GradientStrokeGenerator
from .texture_strokes import TextureStrokeGenerator
from .shadow_strokes import ShadowStrokeGenerator
from .ordering_system import StrokeOrderingSystem

__all__ = [
    'ContourStrokeGenerator',
    'GradientStrokeGenerator',
    'TextureStrokeGenerator',
    'ShadowStrokeGenerator',
    'StrokeOrderingSystem',
]
