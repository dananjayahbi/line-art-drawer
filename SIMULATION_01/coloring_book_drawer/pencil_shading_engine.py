"""
Pencil Shading Engine - Backward compatibility stub.
=====================================================
This module has been moved to engines/pencil_shading/.
This file re-exports all public symbols for backward compatibility.
"""

# Re-export from new location
from engines.pencil_shading.engine import (
    PencilShadingEngine,
    DrawingPhase,
    StrokePoint,
    SpeedConfig,
    AdvancedPixelRevealEngine,
)

__all__ = [
    'PencilShadingEngine',
    'DrawingPhase',
    'StrokePoint',
    'SpeedConfig',
    'AdvancedPixelRevealEngine',
]
