"""
Zone-Based Progressive Engine - Zone Partitioner
==================================================
Discretizes the continuous priority map into numbered zones.
Each zone represents a group of pixels revealed together.
"""

import cv2
import numpy as np
from typing import List, Dict, Any

from ..config import ZoneConfig


class ZonePartitioner:
    """
    Partitions the image into discrete reveal zones based on the priority map.
    Zone 0 = revealed first, zone N-1 = revealed last.
    """
    
    def __init__(self, config: ZoneConfig = None):
        self.config = config or ZoneConfig()
    
    def create_zones(self, priority_map: np.ndarray) -> np.ndarray:
        """
        Discretize the continuous priority map into zone IDs.
        
        Args:
            priority_map: 2D float array (0-1), lower = higher priority (reveal first)
            
        Returns:
            Zone ID map (int32), values 0 to num_zones-1.
            Zone 0 = first revealed, zone (num_zones-1) = last.
        """
        num_zones = self.config.num_zones
        
        # Create zone boundaries using linspace
        # np.digitize assigns each pixel to a zone bin
        boundaries = np.linspace(0.0, 1.0, num_zones + 1)[1:-1]  # inner boundaries
        
        zone_ids = np.digitize(priority_map, boundaries).astype(np.int32)
        
        # Clamp to valid range [0, num_zones - 1]
        zone_ids = np.clip(zone_ids, 0, num_zones - 1)
        
        return zone_ids
    
    def create_zone_masks(self, zone_ids: np.ndarray) -> List[np.ndarray]:
        """
        Create smooth masks for each zone.
        Each mask is a float32 array (0-1) with smoothed boundaries.
        
        Args:
            zone_ids: Integer zone map from create_zones()
            
        Returns:
            List of zone masks (one per zone), each shape (H, W), float32
        """
        num_zones = int(zone_ids.max()) + 1
        ksize = self.config.zone_smoothing_ksize
        sigma = self.config.zone_smoothing_sigma
        
        # Ensure ksize is odd
        if ksize % 2 == 0:
            ksize += 1
        
        masks = []
        for z in range(num_zones):
            # Binary mask for this zone
            mask = (zone_ids == z).astype(np.float32)
            
            # Smooth edges for natural transitions
            if ksize >= 3:
                mask = cv2.GaussianBlur(mask, (ksize, ksize), sigma)
            
            masks.append(mask)
        
        return masks
    
    def get_zone_pixel_counts(self, zone_ids: np.ndarray) -> List[int]:
        """
        Count pixels in each zone.
        
        Args:
            zone_ids: Integer zone map
            
        Returns:
            List of pixel counts per zone
        """
        num_zones = int(zone_ids.max()) + 1
        counts = []
        for z in range(num_zones):
            counts.append(int(np.sum(zone_ids == z)))
        return counts
    
    def get_zone_pixels(self, zone_ids: np.ndarray, zone_id: int) -> np.ndarray:
        """
        Get pixel coordinates belonging to a specific zone.
        
        Args:
            zone_ids: Integer zone map
            zone_id: Which zone to extract
            
        Returns:
            (N, 2) array of (row, col) coordinates
        """
        return np.argwhere(zone_ids == zone_id)
