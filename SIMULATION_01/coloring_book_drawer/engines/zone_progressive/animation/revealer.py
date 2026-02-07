"""
Zone-Based Progressive Engine - Zone-Ordered Revealer
======================================================
Core reveal logic: tracks progress through zones and generates
the current reveal mask based on zone completion.
"""

import cv2
import numpy as np
from typing import List, Tuple

from ..config import AnimationConfig


class ZoneOrderedRevealer:
    """
    Manages the zone-by-zone progressive reveal.
    Tracks which zones are complete, which is active,
    and provides the current reveal mask.
    """
    
    def __init__(self, zone_masks: List[np.ndarray],
                 zone_pixel_counts: List[int],
                 config: AnimationConfig = None):
        """
        Args:
            zone_masks: List of smooth float masks (one per zone)
            zone_pixel_counts: Number of pixels in each zone
            config: Animation configuration
        """
        self.config = config or AnimationConfig()
        self.zone_masks = zone_masks
        self.zone_pixel_counts = zone_pixel_counts
        self.num_zones = len(zone_masks)
        
        # State tracking
        self.current_zone = 0
        self.zone_progress = 0.0  # 0.0 to 1.0 within current zone
        self.total_revealed = 0
        self.total_pixels = sum(zone_pixel_counts)
        
        # Pre-compute cumulative pixel counts for progress tracking
        self._cum_counts = np.cumsum([0] + zone_pixel_counts)
    
    def reveal_next_batch(self, points_per_update: int) -> bool:
        """
        Advance the reveal by a batch of points.
        
        Args:
            points_per_update: Number of pixels to reveal in this update
            
        Returns:
            True if there's still more to reveal, False if complete
        """
        if self.current_zone >= self.num_zones:
            return False
        
        # How many pixels in the current zone
        current_zone_pixels = self.zone_pixel_counts[self.current_zone]
        if current_zone_pixels == 0:
            self.current_zone += 1
            self.zone_progress = 0.0
            return self.current_zone < self.num_zones
        
        # Apply mode-specific speed modifiers
        effective_points = points_per_update
        if self.config.animation_mode == "burst":
            if self.current_zone < self.num_zones // 3:
                # First third of zones = focal area, reveal faster
                effective_points = int(points_per_update * self.config.burst_focal_speed)
            else:
                # Background zones, reveal slower
                effective_points = int(points_per_update * self.config.burst_bg_speed)
        
        # Progress within zone
        self.zone_progress += effective_points / max(1, current_zone_pixels)
        self.total_revealed += effective_points
        
        if self.zone_progress >= 1.0:
            self.current_zone += 1
            self.zone_progress = 0.0
        
        return self.current_zone < self.num_zones
    
    def get_reveal_mask(self) -> np.ndarray:
        """
        Get the current reveal mask based on zone progress.
        
        Returns:
            Float32 mask (H, W), values 0-1. 
            1.0 = fully revealed, 0.0 = hidden.
        """
        if self.num_zones == 0:
            return np.zeros((1, 1), dtype=np.float32)
        
        h, w = self.zone_masks[0].shape
        reveal_mask = np.zeros((h, w), dtype=np.float32)
        
        # Fully revealed zones
        for z in range(min(self.current_zone, self.num_zones)):
            reveal_mask = np.maximum(reveal_mask, self.zone_masks[z])
        
        # Partially revealed current zone
        if self.current_zone < self.num_zones:
            partial = self.zone_masks[self.current_zone] * self.zone_progress
            reveal_mask = np.maximum(reveal_mask, partial)
        
        # Clamp to [0, 1]
        reveal_mask = np.clip(reveal_mask, 0.0, 1.0)
        
        return reveal_mask
    
    def get_progress(self) -> float:
        """Get overall reveal progress (0.0 to 1.0)."""
        if self.total_pixels == 0:
            return 1.0
        
        # Cumulative progress
        completed_pixels = self._cum_counts[min(self.current_zone, self.num_zones)]
        if self.current_zone < self.num_zones:
            completed_pixels += int(self.zone_progress * self.zone_pixel_counts[self.current_zone])
        
        return min(1.0, completed_pixels / self.total_pixels)
    
    def is_complete(self) -> bool:
        """Whether all zones have been fully revealed."""
        return self.current_zone >= self.num_zones
    
    def reset(self):
        """Reset reveal state to beginning."""
        self.current_zone = 0
        self.zone_progress = 0.0
        self.total_revealed = 0
