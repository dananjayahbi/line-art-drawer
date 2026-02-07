"""
Preference Rules
==================
Defines the mapping from region types to preferred rendering strategies.
"""

from typing import Dict, List
from ..config import RegionType, StrategyType


class PreferenceRules:
    """
    Defines strategy preferences for each region type.
    Lists are ordered by preference (best first).
    """
    
    # Default strategy preference mapping
    STRATEGY_PREFERENCE: Dict[RegionType, List[StrategyType]] = {
        RegionType.SMOOTH_GRADIENT: [
            StrategyType.GRADIENT_REVEAL,
            StrategyType.PIXEL_REVEAL,
        ],
        RegionType.TEXTURE: [
            StrategyType.BRUSH_SIMULATION,
            StrategyType.GRADIENT_REVEAL,
        ],
        RegionType.EDGE: [
            StrategyType.GRADIENT_REVEAL,
            StrategyType.BRUSH_SIMULATION,
        ],
        RegionType.DEEP_SHADOW: [
            StrategyType.BRUSH_SIMULATION,
            StrategyType.GRADIENT_REVEAL,
        ],
        RegionType.HIGHLIGHT: [
            StrategyType.PIXEL_REVEAL,
            StrategyType.GRADIENT_REVEAL,
        ],
        RegionType.FOCAL: [
            StrategyType.ZONE_PROGRESSIVE,
            StrategyType.GRADIENT_REVEAL,
        ],
    }
    
    # Priority ordering for global stroke sequencing
    TYPE_PRIORITY: Dict[RegionType, int] = {
        RegionType.FOCAL: 0,         # Drawn first (most important)
        RegionType.EDGE: 1,          # Outlines next
        RegionType.SMOOTH_GRADIENT: 2,  # Then fills
        RegionType.TEXTURE: 3,       # Textures after
        RegionType.DEEP_SHADOW: 4,   # Shadows later
        RegionType.HIGHLIGHT: 5,     # Highlights last
    }
    
    @classmethod
    def get_preferences(cls, region_type: RegionType) -> List[StrategyType]:
        """Get ordered strategy preferences for a region type."""
        return cls.STRATEGY_PREFERENCE.get(
            region_type,
            [StrategyType.GRADIENT_REVEAL]
        )
    
    @classmethod
    def get_priority(cls, region_type: RegionType) -> int:
        """Get priority for global ordering (lower = earlier)."""
        return cls.TYPE_PRIORITY.get(region_type, 99)
