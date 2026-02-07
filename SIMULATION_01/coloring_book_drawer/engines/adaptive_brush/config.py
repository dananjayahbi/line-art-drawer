"""
Adaptive Brush Simulation Engine - Configuration
==================================================
Dataclass configurations for Engine 3E parameters.
Simulates physical pencil properties: tip shape, paper texture,
pressure dynamics, and graphite accumulation.
"""

from dataclasses import dataclass, field
from typing import Tuple
from enum import Enum


class TipShape(Enum):
    """Pencil tip shape types."""
    ROUND = "round"      # Standard sharpened pencil
    CHISEL = "chisel"    # Worn, flat tip
    BLUNT = "blunt"      # Very worn, soft marks


class PaperType(Enum):
    """Paper texture types."""
    SMOOTH = "smooth"        # Minimal texture variation
    COLD_PRESS = "cold_press"  # Medium texture with grain
    ROUGH = "rough"          # Heavy texture, lots of grain


@dataclass
class PencilTipConfig:
    """Configuration for pencil tip physics."""
    shape: TipShape = TipShape.ROUND
    hardness: float = 0.5       # 0=soft (6B), 1=hard (4H)
    sharpness: float = 0.7      # 0=dull, 1=sharp
    graphite_load: float = 0.8  # Current graphite on tip (0-1)
    base_size: int = 8          # Base kernel size for tip


@dataclass
class PaperConfig:
    """Configuration for paper texture simulation."""
    paper_type: PaperType = PaperType.COLD_PRESS
    texture_strength: float = 0.5   # How much texture affects deposit (0-1)
    grain_scale: float = 1.0        # Scale of paper grain pattern


@dataclass
class PressureConfig:
    """Configuration for pressure dynamics."""
    attack_ratio: float = 0.1     # Fraction of stroke for attack ramp
    release_ratio: float = 0.15   # Fraction of stroke for release ramp
    sustain_noise: float = 0.05   # Random noise in sustain phase
    tremor_frequency: float = 20.0  # Hand tremor oscillation frequency
    tremor_amplitude: float = 0.03  # Hand tremor strength
    velocity_influence: float = 0.5 # How much velocity affects pressure


@dataclass 
class AccumulatorConfig:
    """Configuration for graphite accumulation."""
    max_density: float = 1.0       # Maximum darkness achievable
    saturation_curve: float = 0.7  # How quickly graphite saturates (0-1)
    layer_blending: float = 0.8    # Blending factor for overlapping strokes


@dataclass
class StrokeExtractionConfig:
    """Configuration for stroke path extraction."""
    min_stroke_length: int = 5     # Minimum pixels for a stroke
    skeleton_method: str = "skeletonize"  # "skeletonize" or "medial_axis"
    dark_threshold: int = 200      # Pixels darker than this are ink
    edge_threshold_low: int = 50   # Canny edge detection low threshold
    edge_threshold_high: int = 150 # Canny edge detection high threshold


@dataclass
class AdaptiveBrushConfig:
    """Master configuration for Adaptive Brush Simulation Engine."""
    tip: PencilTipConfig = field(default_factory=PencilTipConfig)
    paper: PaperConfig = field(default_factory=PaperConfig)
    pressure: PressureConfig = field(default_factory=PressureConfig)
    accumulator: AccumulatorConfig = field(default_factory=AccumulatorConfig)
    extraction: StrokeExtractionConfig = field(default_factory=StrokeExtractionConfig)
    
    # GPU acceleration
    use_gpu: bool = False
    
    @classmethod
    def from_params(cls,
                    tip_shape: str = "round",
                    pencil_hardness: float = 0.5,
                    pencil_sharpness: float = 0.7,
                    paper_type: str = "cold_press",
                    paper_texture_strength: float = 0.5,
                    pressure_variation: float = 0.5,
                    graphite_buildup: float = 0.7,
                    use_gpu: bool = False) -> 'AdaptiveBrushConfig':
        """Create config from flat parameter list (for CLI/UI integration)."""
        config = cls()
        
        # Map tip shape string to enum
        tip_map = {"round": TipShape.ROUND, "chisel": TipShape.CHISEL, "blunt": TipShape.BLUNT}
        config.tip.shape = tip_map.get(tip_shape, TipShape.ROUND)
        config.tip.hardness = pencil_hardness
        config.tip.sharpness = pencil_sharpness
        
        # Map paper type string to enum
        paper_map = {"smooth": PaperType.SMOOTH, "cold_press": PaperType.COLD_PRESS, "rough": PaperType.ROUGH}
        config.paper.paper_type = paper_map.get(paper_type, PaperType.COLD_PRESS)
        config.paper.texture_strength = paper_texture_strength
        
        # Pressure variation controls tremor and sustain noise
        config.pressure.tremor_amplitude = pressure_variation * 0.06
        config.pressure.sustain_noise = pressure_variation * 0.1
        
        # Graphite buildup maps to saturation curve
        config.accumulator.saturation_curve = graphite_buildup
        
        config.use_gpu = use_gpu
        return config
