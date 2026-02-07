"""
Advanced Gradient Shading Engine (Engine 3)
============================================
Handles complex, high-contrast pencil artwork with natural-looking shading
and shadows using progressive gradient reveal techniques.

Key capabilities:
- Structure tensor orientation analysis
- Multi-scale edge detection
- Superpixel-based region segmentation
- Continuous intensity mapping with perceptual correction
- Contour-aware stroke path generation
- Multi-pass shadow accumulation
- Phase-based brush presets
"""

from .engine import AdvancedGradientEngine
from .config import AdvancedGradientConfig

__all__ = [
    "AdvancedGradientEngine",
    "AdvancedGradientConfig",
]
