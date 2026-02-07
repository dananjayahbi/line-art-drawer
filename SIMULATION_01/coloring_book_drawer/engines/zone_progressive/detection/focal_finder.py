"""
Zone-Based Progressive Engine - Focal Point Finder
====================================================
Extracts local maxima from saliency maps as focal points.
Filters by distance and priority to select the best candidates.
"""

import numpy as np
from scipy.ndimage import maximum_filter, label
from typing import List, Dict, Any

from ..config import FocalDetectionConfig


class FocalFinder:
    """
    Finds focal points (local maxima) in a saliency map
    and filters them by distance and importance.
    """
    
    def __init__(self, config: FocalDetectionConfig = None):
        self.config = config or FocalDetectionConfig()
    
    def find_focal_points(self, saliency_map: np.ndarray) -> List[Dict[str, Any]]:
        """
        Find focal points as local maxima in the saliency map.
        
        Args:
            saliency_map: 2D float array (0-1), higher = more salient
            
        Returns:
            List of focal point dicts with keys:
                'point': (col, row) tuple  — NOTE: (x, y) format
                'priority': float (0-1)
                'type': str ('saliency')
                'saliency': float — saliency value at that point
        """
        h, w = saliency_map.shape
        
        # Find local maxima using maximum filter
        local_max = maximum_filter(saliency_map, size=self.config.local_max_size)
        
        # Peaks: pixels that ARE the local maximum AND exceed threshold
        peaks = (saliency_map == local_max) & (saliency_map > self.config.saliency_threshold)
        
        # Extract coordinates: argwhere returns (row, col) pairs
        coords = np.argwhere(peaks)
        
        if len(coords) == 0:
            # Fallback: use image center as single focal point
            return [{
                'point': (w // 2, h // 2),
                'priority': self.config.saliency_priority,
                'type': 'center_fallback',
                'saliency': float(saliency_map[h // 2, w // 2])
            }]
        
        # Get saliency values at each peak
        saliency_values = saliency_map[coords[:, 0], coords[:, 1]]
        
        # Sort by saliency (highest first)
        sort_indices = np.argsort(-saliency_values)
        coords = coords[sort_indices]
        saliency_values = saliency_values[sort_indices]
        
        # Filter by minimum distance and max count
        focal_points = self._filter_by_distance(
            coords, saliency_values,
            self.config.max_focal_points,
            self.config.min_focal_distance
        )
        
        return focal_points
    
    def _filter_by_distance(self, coords: np.ndarray, saliency_values: np.ndarray,
                            max_points: int, min_distance: int) -> List[Dict[str, Any]]:
        """
        Filter focal point candidates by minimum distance.
        Uses greedy selection: pick highest saliency first, skip close ones.
        
        Args:
            coords: (N, 2) array of (row, col) coordinates, sorted by saliency desc
            saliency_values: (N,) saliency at each coord
            max_points: Maximum number of points to return
            min_distance: Minimum pixel distance between selected points
            
        Returns:
            Filtered list of focal point dicts
        """
        selected = []
        min_dist_sq = min_distance ** 2
        
        for i in range(len(coords)):
            row, col = int(coords[i, 0]), int(coords[i, 1])
            sal = float(saliency_values[i])
            
            # Check distance against already selected points
            too_close = False
            for s in selected:
                sr, sc = s['point'][1], s['point'][0]  # point is (col, row) = (x, y)
                dist_sq = (row - sr) ** 2 + (col - sc) ** 2
                if dist_sq < min_dist_sq:
                    too_close = True
                    break
            
            if not too_close:
                selected.append({
                    'point': (col, row),  # (x, y) format
                    'priority': self.config.saliency_priority * sal,
                    'type': 'saliency',
                    'saliency': sal
                })
            
            if len(selected) >= max_points:
                break
        
        # If no points survived filtering, pick the top one regardless
        if not selected and len(coords) > 0:
            row, col = int(coords[0, 0]), int(coords[0, 1])
            selected.append({
                'point': (col, row),
                'priority': self.config.saliency_priority * float(saliency_values[0]),
                'type': 'saliency',
                'saliency': float(saliency_values[0])
            })
        
        return selected
    
    def merge_focal_lists(self, *focal_lists: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Merge multiple focal point lists (e.g., saliency + portrait),
        removing duplicates that are too close together.
        Higher priority points take precedence.
        
        Args:
            *focal_lists: Variable number of focal point lists
            
        Returns:
            Merged list of unique focal points, sorted by priority desc
        """
        all_points = []
        for flist in focal_lists:
            all_points.extend(flist)
        
        if not all_points:
            return []
        
        # Sort by priority (highest first)
        all_points.sort(key=lambda p: p['priority'], reverse=True)
        
        # Filter by distance (greedy, highest priority first)
        min_dist_sq = self.config.min_focal_distance ** 2
        merged = []
        
        for pt in all_points:
            px, py = pt['point']
            too_close = False
            for m in merged:
                mx, my = m['point']
                if (px - mx) ** 2 + (py - my) ** 2 < min_dist_sq:
                    too_close = True
                    break
            if not too_close:
                merged.append(pt)
            if len(merged) >= self.config.max_focal_points:
                break
        
        return merged
