"""
Zone-Based Progressive Engine - Configuration
===============================================
Dataclass configuration for Engine 3D parameters.
"""

from dataclasses import dataclass, field
from typing import List, Tuple


@dataclass
class FocalDetectionConfig:
    """Configuration for focal point detection."""
    # Saliency detection
    spectral_blur_ksize: int = 3          # Kernel size for spectral residual averaging
    saliency_blur_ksize: int = 9          # Gaussian blur kernel for final saliency
    saliency_blur_sigma: float = 2.5      # Sigma for saliency Gaussian blur
    saliency_threshold: float = 0.3       # Minimum saliency to be a focal point
    local_max_size: int = 50              # Neighborhood size for local maxima detection
    
    # Focal point filtering
    max_focal_points: int = 5             # Maximum number of focal points
    min_focal_distance: int = 100         # Minimum pixel distance between focal points
    
    # Portrait detection
    enable_portrait_detection: bool = True # Try face/eye detection
    eye_priority: float = 1.0             # Priority weight for eye focal points
    face_priority: float = 0.8            # Priority weight for face focal points
    saliency_priority: float = 0.6        # Priority weight for saliency-based focals


@dataclass
class ZoneConfig:
    """Configuration for zone partitioning."""
    num_zones: int = 10                   # Number of concentric reveal zones
    priority_blend: float = 0.5           # Blend factor: 0=distance only, 1=saliency only
    saliency_influence: float = 0.5       # How much saliency modifies zone assignment
    zone_smoothing_ksize: int = 5         # Kernel size for zone boundary smoothing
    zone_smoothing_sigma: float = 1.5     # Sigma for zone boundary smoothing
    merge_threshold: float = 0.15         # Threshold for merging overlapping zones


@dataclass
class AnimationConfig:
    """Configuration for reveal animation."""
    # Animation mode: "single_focal", "multi_focal", "spiral", "burst"
    animation_mode: str = "multi_focal"
    
    # Per-zone stroke generation
    stroke_density: float = 0.8           # Density of strokes within zones (0-1)
    stroke_jitter: float = 0.3            # Random jitter for stroke placement
    stroke_min_length: int = 5            # Minimum stroke length in pixels
    stroke_max_length: int = 40           # Maximum stroke length in pixels
    
    # Transition blending
    transition_width: float = 0.1         # Width of smooth transition between zones (0-1)
    blend_sigma: float = 2.0             # Gaussian sigma for zone edge blending
    
    # Spiral mode
    spiral_tightness: float = 0.5         # How tight the spiral is (0=loose, 1=tight)
    spiral_arms: int = 3                  # Number of spiral arms
    
    # Burst mode
    burst_focal_speed: float = 2.0        # Speed multiplier for focal zone reveal
    burst_bg_speed: float = 0.5           # Speed multiplier for background reveal


@dataclass
class RenderingConfig:
    """Configuration for frame composition."""
    background_color: Tuple[int, int, int] = (255, 255, 255)  # White background
    use_soft_mask: bool = True            # Use soft-edged mask transitions
    mask_feather_radius: int = 3          # Feathering radius for mask edges
    gamma_correction: float = 1.0         # Gamma correction for final output


@dataclass
class ZoneProgressiveConfig:
    """Master configuration for Zone-Based Progressive Engine."""
    focal: FocalDetectionConfig = field(default_factory=FocalDetectionConfig)
    zone: ZoneConfig = field(default_factory=ZoneConfig)
    animation: AnimationConfig = field(default_factory=AnimationConfig)
    rendering: RenderingConfig = field(default_factory=RenderingConfig)
    
    # GPU acceleration
    use_gpu: bool = False
    
    @classmethod
    def from_params(cls,
                    num_zones: int = 10,
                    saliency_threshold: float = 0.3,
                    max_focal_points: int = 5,
                    animation_mode: str = "multi_focal",
                    transition_width: float = 0.1,
                    stroke_density: float = 0.8,
                    enable_portrait: bool = True,
                    use_gpu: bool = False) -> 'ZoneProgressiveConfig':
        """Create config from flat parameter list (for CLI/UI integration)."""
        config = cls()
        config.zone.num_zones = num_zones
        config.focal.saliency_threshold = saliency_threshold
        config.focal.max_focal_points = max_focal_points
        config.animation.animation_mode = animation_mode
        config.animation.transition_width = transition_width
        config.animation.stroke_density = stroke_density
        config.focal.enable_portrait_detection = enable_portrait
        config.use_gpu = use_gpu
        return config
