"""
Zone-Based Progressive Engine - Zone Merger
=============================================
Handles merging of small or overlapping zones to create
a cleaner zone map with smoother transitions.
"""

import cv2
import numpy as np
from typing import List, Tuple

from ..config import ZoneConfig


class ZoneMerger:
    """
    Merges adjacent zones that are too small or too similar,
    producing a cleaner reveal sequence with fewer abrupt boundaries.
    """
    
    def __init__(self, config: ZoneConfig = None):
        self.config = config or ZoneConfig()
    
    def merge_small_zones(self, zone_ids: np.ndarray,
                          min_fraction: float = 0.01) -> np.ndarray:
        """
        Merge zones that are too small into their nearest neighbor.
        
        Args:
            zone_ids: Integer zone map
            min_fraction: Minimum fraction of total pixels for a zone to survive
            
        Returns:
            Updated zone map with small zones merged
        """
        total_pixels = zone_ids.size
        min_pixels = int(total_pixels * min_fraction)
        num_zones = int(zone_ids.max()) + 1
        
        result = zone_ids.copy()
        
        for z in range(num_zones):
            zone_mask = (result == z)
            count = int(np.sum(zone_mask))
            
            if count > 0 and count < min_pixels:
                # Find nearest valid neighbor zone for each pixel in this zone
                # Simple approach: dilate neighboring zones and take majority
                neighbor_zone = self._find_nearest_neighbor_zone(result, z, num_zones)
                if neighbor_zone is not None and neighbor_zone != z:
                    result[zone_mask] = neighbor_zone
        
        # Re-index to remove gaps
        result = self._reindex_zones(result)
        
        return result
    
    def _find_nearest_neighbor_zone(self, zone_ids: np.ndarray,
                                     target_zone: int, num_zones: int) -> int:
        """Find the most common adjacent zone to target_zone."""
        target_mask = (zone_ids == target_zone).astype(np.uint8)
        
        # Dilate the target zone mask
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        dilated = cv2.dilate(target_mask, kernel, iterations=3)
        
        # Border region = dilated minus original
        border = (dilated > 0) & (target_mask == 0)
        
        if not np.any(border):
            # Try with bigger dilation
            dilated = cv2.dilate(target_mask, kernel, iterations=10)
            border = (dilated > 0) & (target_mask == 0)
        
        if not np.any(border):
            return None
        
        # Find most common zone in border region
        border_zones = zone_ids[border]
        if len(border_zones) == 0:
            return None
        
        # Count occurrences (exclude the target zone itself)
        counts = np.bincount(border_zones, minlength=num_zones)
        counts[target_zone] = 0
        
        if counts.max() == 0:
            return None
        
        return int(np.argmax(counts))
    
    def _reindex_zones(self, zone_ids: np.ndarray) -> np.ndarray:
        """Re-index zones to be consecutive starting from 0."""
        unique_zones = np.unique(zone_ids)
        
        if len(unique_zones) == 0:
            return zone_ids
        
        # Create mapping: old zone ID → new zone ID
        mapping = np.zeros(int(unique_zones.max()) + 1, dtype=np.int32)
        for new_id, old_id in enumerate(unique_zones):
            mapping[old_id] = new_id
        
        return mapping[zone_ids]
    
    def smooth_zone_boundaries(self, zone_ids: np.ndarray,
                                iterations: int = 2) -> np.ndarray:
        """
        Smooth zone boundaries using morphological operations.
        This reduces jagged edges between zones.
        
        Args:
            zone_ids: Integer zone map
            iterations: Number of smoothing passes
            
        Returns:
            Zone map with smoother boundaries
        """
        result = zone_ids.copy()
        num_zones = int(zone_ids.max()) + 1
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        
        for _ in range(iterations):
            # For each zone, do morphological close then open
            for z in range(num_zones):
                mask = (result == z).astype(np.uint8)
                mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
                mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
                result[mask > 0] = z
        
        return result
