"""
Brush Presets
===============
Built-in brush preset definitions for common pencil drawing styles.

Presets:
  - Fine Line:   Sharp, hard pencil for outlines and detail
  - Soft Shade:  Soft pencil for smooth shading
  - Hatching:    Chisel tip for cross-hatching effects
  - Deep Shadow: Very soft, heavy pressure for dark areas
  - Sketch:      Medium pencil for loose sketching
"""

from dataclasses import dataclass
from typing import Dict
from ..config import (
    AdaptiveBrushConfig, PencilTipConfig, PaperConfig, PressureConfig,
    AccumulatorConfig, StrokeExtractionConfig,
    TipShape, PaperType
)


@dataclass
class BrushPreset:
    """A named brush preset with full configuration."""
    name: str
    description: str
    config: AdaptiveBrushConfig


class BrushPresets:
    """Registry of built-in and custom brush presets."""
    
    _presets: Dict[str, BrushPreset] = {}
    
    @classmethod
    def initialize(cls):
        """Load all built-in presets."""
        cls._presets = {}
        cls._register_fine_line()
        cls._register_soft_shade()
        cls._register_hatching()
        cls._register_deep_shadow()
        cls._register_sketch()
    
    @classmethod
    def get(cls, name: str) -> BrushPreset:
        """Get a preset by name."""
        if not cls._presets:
            cls.initialize()
        return cls._presets.get(name)
    
    @classmethod
    def list_names(cls) -> list:
        """List all available preset names."""
        if not cls._presets:
            cls.initialize()
        return list(cls._presets.keys())
    
    @classmethod
    def register(cls, preset: BrushPreset):
        """Register a custom preset."""
        cls._presets[preset.name] = preset
    
    @classmethod
    def _register_fine_line(cls):
        config = AdaptiveBrushConfig(
            tip=PencilTipConfig(
                shape=TipShape.ROUND,
                hardness=0.8,    # Hard pencil (2H-4H)
                sharpness=0.9,   # Very sharp
                graphite_load=0.6,
                base_size=5
            ),
            paper=PaperConfig(
                paper_type=PaperType.SMOOTH,
                texture_strength=0.2,
                grain_scale=0.5
            ),
            pressure=PressureConfig(
                attack_ratio=0.05,
                release_ratio=0.1,
                sustain_noise=0.02,
                tremor_frequency=25.0,
                tremor_amplitude=0.01,
                velocity_influence=0.3
            ),
            accumulator=AccumulatorConfig(
                max_density=0.7,
                saturation_curve=0.5,
                layer_blending=0.6
            )
        )
        cls._presets["fine_line"] = BrushPreset(
            name="fine_line",
            description="Sharp, hard pencil for outlines and fine detail work",
            config=config
        )
    
    @classmethod
    def _register_soft_shade(cls):
        config = AdaptiveBrushConfig(
            tip=PencilTipConfig(
                shape=TipShape.ROUND,
                hardness=0.2,    # Soft pencil (4B-6B)
                sharpness=0.4,   # Slightly dull for broad strokes
                graphite_load=0.9,
                base_size=10
            ),
            paper=PaperConfig(
                paper_type=PaperType.COLD_PRESS,
                texture_strength=0.4,
                grain_scale=1.0
            ),
            pressure=PressureConfig(
                attack_ratio=0.15,
                release_ratio=0.2,
                sustain_noise=0.03,
                tremor_frequency=15.0,
                tremor_amplitude=0.04,
                velocity_influence=0.6
            ),
            accumulator=AccumulatorConfig(
                max_density=0.9,
                saturation_curve=0.8,
                layer_blending=0.9
            )
        )
        cls._presets["soft_shade"] = BrushPreset(
            name="soft_shade",
            description="Soft pencil for smooth, even shading and tonal gradients",
            config=config
        )
    
    @classmethod
    def _register_hatching(cls):
        config = AdaptiveBrushConfig(
            tip=PencilTipConfig(
                shape=TipShape.CHISEL,
                hardness=0.5,    # Medium pencil (HB-2B)
                sharpness=0.6,
                graphite_load=0.7,
                base_size=7
            ),
            paper=PaperConfig(
                paper_type=PaperType.COLD_PRESS,
                texture_strength=0.5,
                grain_scale=1.0
            ),
            pressure=PressureConfig(
                attack_ratio=0.08,
                release_ratio=0.12,
                sustain_noise=0.04,
                tremor_frequency=20.0,
                tremor_amplitude=0.02,
                velocity_influence=0.4
            ),
            accumulator=AccumulatorConfig(
                max_density=0.8,
                saturation_curve=0.6,
                layer_blending=0.7
            )
        )
        cls._presets["hatching"] = BrushPreset(
            name="hatching",
            description="Chisel-tip pencil ideal for cross-hatching techniques",
            config=config
        )
    
    @classmethod
    def _register_deep_shadow(cls):
        config = AdaptiveBrushConfig(
            tip=PencilTipConfig(
                shape=TipShape.BLUNT,
                hardness=0.1,    # Very soft pencil (6B-8B)
                sharpness=0.3,   # Dull for maximum coverage
                graphite_load=1.0,
                base_size=12
            ),
            paper=PaperConfig(
                paper_type=PaperType.ROUGH,
                texture_strength=0.6,
                grain_scale=1.2
            ),
            pressure=PressureConfig(
                attack_ratio=0.2,
                release_ratio=0.25,
                sustain_noise=0.06,
                tremor_frequency=12.0,
                tremor_amplitude=0.05,
                velocity_influence=0.7
            ),
            accumulator=AccumulatorConfig(
                max_density=1.0,
                saturation_curve=0.9,
                layer_blending=1.0
            )
        )
        cls._presets["deep_shadow"] = BrushPreset(
            name="deep_shadow",
            description="Very soft, heavy pencil for deep shadows and dark tones",
            config=config
        )
    
    @classmethod
    def _register_sketch(cls):
        config = AdaptiveBrushConfig(
            tip=PencilTipConfig(
                shape=TipShape.ROUND,
                hardness=0.4,    # Medium pencil (HB-B)
                sharpness=0.6,
                graphite_load=0.75,
                base_size=7
            ),
            paper=PaperConfig(
                paper_type=PaperType.COLD_PRESS,
                texture_strength=0.35,
                grain_scale=0.8
            ),
            pressure=PressureConfig(
                attack_ratio=0.1,
                release_ratio=0.15,
                sustain_noise=0.05,
                tremor_frequency=20.0,
                tremor_amplitude=0.03,
                velocity_influence=0.5
            ),
            accumulator=AccumulatorConfig(
                max_density=0.85,
                saturation_curve=0.7,
                layer_blending=0.8
            )
        )
        cls._presets["sketch"] = BrushPreset(
            name="sketch",
            description="General-purpose medium pencil for loose sketching",
            config=config
        )
