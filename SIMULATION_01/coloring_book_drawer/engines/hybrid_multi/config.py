"""
Hybrid Multi-Strategy Engine - Configuration
===============================================
Dataclass configurations for Engine 3F parameters.
The most complex engine: analyzes regions and assigns optimal
rendering strategies per region, combining all engine approaches.
"""

from dataclasses import dataclass, field
from typing import List, Set
from enum import Enum


class RegionType(Enum):
    """Types of image regions based on visual characteristics."""
    SMOOTH_GRADIENT = "smooth_gradient"   # Low variance, smooth tones
    TEXTURE = "texture"                   # High variance, patterns
    EDGE = "edge"                         # Strong gradients, contours
    DEEP_SHADOW = "deep_shadow"           # Very dark areas
    HIGHLIGHT = "highlight"               # Very bright areas
    FOCAL = "focal"                       # Detected as visually important


class StrategyType(Enum):
    """Available rendering strategies (maps to sub-engine approaches)."""
    GRADIENT_REVEAL = "gradient"          # Engine 3/3A gradient approach
    ZONE_PROGRESSIVE = "zone"             # Engine 3D zone approach
    BRUSH_SIMULATION = "brush"            # Engine 3E adaptive brush approach
    PIXEL_REVEAL = "pixel"                # Engine 1 simple reveal


@dataclass
class SegmentationConfig:
    """Configuration for image segmentation."""
    num_segments: int = 100         # Target number of superpixels/segments
    min_region_area: int = 500      # Minimum region size in pixels
    compactness: float = 10.0       # SLIC compactness parameter
    merge_threshold: float = 0.15   # Similarity threshold for merging small regions


@dataclass
class ClassificationConfig:
    """Configuration for region classification."""
    highlight_threshold: int = 230  # Brightness above this = highlight
    shadow_threshold: int = 50      # Brightness below this = shadow
    edge_density_threshold: float = 0.3   # Edge density above this = edge region
    variance_threshold: float = 500.0     # Variance above this = texture
    focal_detection: bool = True    # Enable face/saliency-based focal detection


@dataclass
class AssignmentConfig:
    """Configuration for strategy assignment."""
    available_strategies: List[str] = field(
        default_factory=lambda: ["gradient", "brush", "zone", "pixel"]
    )
    default_strategy: str = "gradient"
    prefer_brush_for_texture: bool = True
    prefer_zone_for_focal: bool = True


@dataclass
class TransitionConfig:
    """Configuration for region boundary transitions."""
    transition_width: int = 10      # Pixel width of blending zone
    blend_smoothness: float = 0.7   # Gaussian smoothness for blending
    feather_edges: bool = True      # Enable edge feathering


@dataclass
class RenderingConfig:
    """Configuration for the unified renderer."""
    stroke_ordering: str = "priority"  # "priority", "spatial", "random"
    mask_feather_radius: int = 3       # Feathering on reveal mask


@dataclass
class HybridMultiConfig:
    """Master configuration for Hybrid Multi-Strategy Engine."""
    segmentation: SegmentationConfig = field(default_factory=SegmentationConfig)
    classification: ClassificationConfig = field(default_factory=ClassificationConfig)
    assignment: AssignmentConfig = field(default_factory=AssignmentConfig)
    transition: TransitionConfig = field(default_factory=TransitionConfig)
    rendering: RenderingConfig = field(default_factory=RenderingConfig)
    
    # GPU acceleration
    use_gpu: bool = False
    
    @classmethod
    def from_params(cls,
                    num_segments: int = 100,
                    min_region_area: int = 500,
                    transition_width: int = 10,
                    blend_smoothness: float = 0.7,
                    strategy_mode: str = "auto",
                    focal_detection: bool = True,
                    use_gpu: bool = False) -> 'HybridMultiConfig':
        """Create config from flat parameter list (for CLI/UI integration)."""
        config = cls()
        config.segmentation.num_segments = num_segments
        config.segmentation.min_region_area = min_region_area
        config.transition.transition_width = transition_width
        config.transition.blend_smoothness = blend_smoothness
        config.classification.focal_detection = focal_detection
        config.use_gpu = use_gpu
        
        # Strategy mode affects available strategies
        if strategy_mode == "gradient_only":
            config.assignment.available_strategies = ["gradient"]
        elif strategy_mode == "brush_only":
            config.assignment.available_strategies = ["brush"]
        elif strategy_mode == "full":
            config.assignment.available_strategies = ["gradient", "brush", "zone", "pixel"]
        # "auto" keeps defaults
        
        return config
