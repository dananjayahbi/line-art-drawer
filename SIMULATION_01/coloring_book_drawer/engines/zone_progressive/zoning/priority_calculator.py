"""
Zone-Based Progressive Engine - Priority Calculator
=====================================================
Computes per-pixel priority values by combining focal distance
with saliency map weights. Lower priority = revealed first.
"""

import cv2
import numpy as np
from typing import List, Dict, Any

from ..config import ZoneConfig


class PriorityCalculator:
    """
    Calculates a per-pixel priority map from focal points and saliency.
    Priority values are continuous floats — lower means "reveal sooner."
    """
    
    def __init__(self, config: ZoneConfig = None):
        self.config = config or ZoneConfig()
    
    def compute_priority_map(self, image_shape: tuple,
                              focal_points: List[Dict[str, Any]],
                              saliency_map: np.ndarray) -> np.ndarray:
        """
        Compute a continuous priority map.
        
        Each pixel gets a priority value based on:
        - Distance to nearest focal point (further = higher priority = later reveal)
        - Saliency (more salient = lower priority = earlier reveal)
        
        Args:
            image_shape: (H, W) or (H, W, C) shape of the image
            focal_points: List of focal point dicts with 'point' and 'priority'
            saliency_map: 2D float array (0-1), higher = more salient
            
        Returns:
            Priority map (float32), normalized to 0-1. Lower = reveal first.
        """
        h, w = image_shape[:2]
        
        if not focal_points:
            # No focal points: uniform priority (center-out fallback)
            yy, xx = np.mgrid[0:h, 0:w]
            cx, cy = w // 2, h // 2
            dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2).astype(np.float32)
            max_dist = np.sqrt(h ** 2 + w ** 2)
            return dist / max_dist
        
        # Create coordinate grids
        yy, xx = np.mgrid[0:h, 0:w]
        
        # Start with maximum priority
        distance_map = np.full((h, w), np.inf, dtype=np.float32)
        
        # For each focal point, compute distance and take the minimum
        max_dist = np.sqrt(float(h ** 2 + w ** 2))
        
        for focal in focal_points:
            fx, fy = focal['point']  # (col, row) = (x, y)
            priority_weight = focal.get('priority', 0.5)
            
            # Euclidean distance from this focal point
            dist = np.sqrt((xx - fx) ** 2 + (yy - fy) ** 2).astype(np.float32)
            
            # Normalize to 0-1
            normalized_dist = dist / max_dist
            
            # Scale by inverse priority: higher focal priority → lower zone value
            # priority_weight is typically 0-1, so (2 - priority_weight) ranges 1-2
            zone_value = normalized_dist * (2.0 - priority_weight)
            
            # Take element-wise minimum (closest/highest-priority focal wins)
            distance_map = np.minimum(distance_map, zone_value)
        
        # Combine distance with saliency
        # More salient = lower priority number = revealed sooner
        saliency_influence = self.config.saliency_influence
        priority_map = distance_map * (1.0 + saliency_influence - saliency_map * saliency_influence)
        
        # Normalize to 0-1
        p_min, p_max = priority_map.min(), priority_map.max()
        if p_max - p_min > 1e-8:
            priority_map = (priority_map - p_min) / (p_max - p_min)
        else:
            priority_map = np.zeros_like(priority_map)
        
        return priority_map
