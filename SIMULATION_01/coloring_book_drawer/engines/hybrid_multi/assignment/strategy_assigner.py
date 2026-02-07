"""
Strategy Assigner
===================
Assigns the optimal rendering strategy to each classified region,
considering strategy availability and preference rules.
"""

from typing import List, Set
from ..config import RegionType, StrategyType, AssignmentConfig
from ..classification.classifier import RegionInfo
from .preference_rules import PreferenceRules


class StrategyAssigner:
    """Assigns rendering strategies to classified image regions."""
    
    def __init__(self, config: AssignmentConfig):
        self.config = config
        
        # Parse available strategies from config strings
        strategy_map = {
            "gradient": StrategyType.GRADIENT_REVEAL,
            "brush": StrategyType.BRUSH_SIMULATION,
            "zone": StrategyType.ZONE_PROGRESSIVE,
            "pixel": StrategyType.PIXEL_REVEAL,
        }
        self.available: Set[StrategyType] = set()
        for name in config.available_strategies:
            if name in strategy_map:
                self.available.add(strategy_map[name])
        
        # Ensure at least one strategy
        if not self.available:
            self.available.add(StrategyType.GRADIENT_REVEAL)
        
        # Default fallback
        self.default = strategy_map.get(config.default_strategy, StrategyType.GRADIENT_REVEAL)
    
    def assign_strategies(self, regions: List[RegionInfo]) -> List[RegionInfo]:
        """
        Assign optimal strategy to each region.
        
        Modifies RegionInfo.assigned_strategy in-place.
        
        Args:
            regions: List of classified regions
            
        Returns:
            Same list with assigned_strategy set
        """
        for region in regions:
            preferences = PreferenceRules.get_preferences(region.region_type)
            
            # Select first available preferred strategy
            assigned = False
            for strategy in preferences:
                if strategy in self.available:
                    region.assigned_strategy = strategy
                    assigned = True
                    break
            
            # Fallback
            if not assigned:
                region.assigned_strategy = self.default
        
        return regions
    
    def get_strategy_summary(self, regions: List[RegionInfo]) -> dict:
        """Get a summary of how many regions use each strategy."""
        summary = {}
        for region in regions:
            strategy_name = region.assigned_strategy.value if region.assigned_strategy else "unassigned"
            summary[strategy_name] = summary.get(strategy_name, 0) + 1
        return summary
