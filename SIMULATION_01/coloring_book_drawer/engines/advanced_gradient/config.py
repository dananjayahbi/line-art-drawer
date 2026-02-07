"""
Advanced Gradient Engine - Configuration
==========================================
Dataclasses and presets for the Advanced Gradient Shading Engine.
"""

from dataclasses import dataclass, field
from typing import Tuple, Dict


@dataclass
class BrushConfig:
    """Configuration for different brush behaviors."""
    softness: float = 0.5           # 0.0 = hard edge, 1.0 = very soft
    opacity_base: float = 0.8       # Base opacity (0.0-1.0)
    pressure_range: Tuple[float, float] = (0.5, 1.0)  # (min, max) pressure
    size_multiplier: float = 1.0    # Relative to detected stroke width
    texture_overlay: bool = False   # Use pencil texture
    edge_jitter: float = 0.0       # Randomize position slightly


# Preset brush configurations for different drawing phases
BRUSH_PRESETS: Dict[str, BrushConfig] = {
    'contour': BrushConfig(
        softness=0.2,
        opacity_base=0.95,
        pressure_range=(0.8, 1.0),
        size_multiplier=1.0,
        texture_overlay=False,
        edge_jitter=0.0
    ),
    'gradient': BrushConfig(
        softness=0.8,
        opacity_base=0.6,
        pressure_range=(0.4, 0.8),
        size_multiplier=1.5,
        texture_overlay=True,
        edge_jitter=0.5
    ),
    'texture': BrushConfig(
        softness=0.4,
        opacity_base=0.7,
        pressure_range=(0.5, 0.9),
        size_multiplier=0.8,
        texture_overlay=True,
        edge_jitter=0.3
    ),
    'shadow': BrushConfig(
        softness=0.6,
        opacity_base=0.8,
        pressure_range=(0.7, 1.0),
        size_multiplier=1.2,
        texture_overlay=True,
        edge_jitter=0.2
    ),
    'detail': BrushConfig(
        softness=0.3,
        opacity_base=0.85,
        pressure_range=(0.6, 0.9),
        size_multiplier=0.6,
        texture_overlay=False,
        edge_jitter=0.1
    )
}


@dataclass
class PhaseSpeedConfig:
    """Speed multipliers for each drawing phase (for animation pacing)."""
    phase_1_speed: float = 1.2    # Quick Sketch (faster for outline)
    phase_2_speed: float = 1.0    # Form Building (normal)
    phase_3_speed: float = 0.9    # Texture Work (slightly slower)
    phase_4_speed: float = 0.8    # Shadow Depth (slow for shadows)
    phase_5_speed: float = 0.7    # Final Details (slowest for details)
    phase_6_speed: float = 1.5    # Enhancement (quick final pass)


@dataclass
class AdvancedGradientConfig:
    """Full configuration for the Advanced Gradient Shading Engine."""
    # Stroke Generation
    contour_sensitivity: float = 0.5       # (0.1-1.0) Edge detection sensitivity
    gradient_smoothness: float = 0.7       # (0.1-1.0) How smooth gradient reveals are
    texture_detection_strength: float = 0.6  # (0.0-1.0) Texture region detection

    # Multi-pass Control
    shadow_passes: int = 3                 # Number of shadow passes (1-5)
    shadow_angle_variation: float = 30.0   # Degrees between shadow passes

    # Brush Behavior
    brush_softness_contour: float = 0.3    # Softness for contour strokes
    brush_softness_shading: float = 0.7    # Softness for shading strokes
    pressure_variation: float = 0.5        # Amount of pressure variation

    # Animation Pacing
    phase_speeds: PhaseSpeedConfig = field(default_factory=PhaseSpeedConfig)

    # Output Quality
    gradient_fidelity: float = 0.98        # How close to original (0.8-1.0)
    texture_preservation: float = 0.9      # Texture detail preservation

    # Phase allocation (percentage of total animation)
    phase_1_pct: float = 0.05   # Quick Sketch (5%)
    phase_2_pct: float = 0.35   # Form Building (35%)
    phase_3_pct: float = 0.25   # Texture Work (25%)
    phase_4_pct: float = 0.25   # Shadow Depth (25%)
    phase_5_pct: float = 0.08   # Final Details (8%)
    phase_6_pct: float = 0.02   # Enhancement (2%)

    def get_brush_preset(self, phase_name: str) -> BrushConfig:
        """Get brush preset for a named phase."""
        return BRUSH_PRESETS.get(phase_name, BRUSH_PRESETS['contour'])
