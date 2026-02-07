"""
Zone-Based Progressive Engine - Per-Zone Stroke Generator
==========================================================
Generates ordered pixel reveal sequences within each zone.
Supports multiple animation modes: single_focal, multi_focal, spiral, burst.
"""

import numpy as np
from typing import List, Tuple, Dict, Any

from ..config import AnimationConfig


class ZoneStrokeGenerator:
    """
    Generates ordered reveal sequences (stroke paths) within zones.
    Each zone's pixels are ordered to create a natural drawing-like flow.
    """
    
    def __init__(self, config: AnimationConfig = None):
        self.config = config or AnimationConfig()
    
    def generate_zone_sequence(self, zone_ids: np.ndarray,
                                priority_map: np.ndarray,
                                focal_points: List[Dict[str, Any]],
                                ink_mask: np.ndarray = None
                                ) -> List[np.ndarray]:
        """
        Generate ordered pixel reveal sequences for each zone.
        
        Args:
            zone_ids: Integer zone map (H, W)
            priority_map: Continuous priority map (H, W), float32 (0-1)
            focal_points: List of focal point dicts
            ink_mask: Optional binary mask of ink pixels (True = has content)
            
        Returns:
            List of (N_z, 2) arrays, one per zone, each containing 
            (row, col) coordinates in reveal order.
        """
        num_zones = int(zone_ids.max()) + 1
        mode = self.config.animation_mode
        
        zone_sequences = []
        
        for z in range(num_zones):
            # Get all pixels in this zone
            zone_pixels = np.argwhere(zone_ids == z)  # (N, 2) of (row, col)
            
            if len(zone_pixels) == 0:
                zone_sequences.append(np.empty((0, 2), dtype=np.int32))
                continue
            
            # If ink_mask provided, prioritize ink pixels
            if ink_mask is not None:
                ink_flags = ink_mask[zone_pixels[:, 0], zone_pixels[:, 1]]
                ink_pixels = zone_pixels[ink_flags]
                bg_pixels = zone_pixels[~ink_flags]
            else:
                ink_pixels = zone_pixels
                bg_pixels = np.empty((0, 2), dtype=np.int32)
            
            # Order pixels within zone based on animation mode
            if mode == "spiral":
                ordered_ink = self._spiral_order(ink_pixels, focal_points, zone_ids.shape)
                ordered_bg = self._spiral_order(bg_pixels, focal_points, zone_ids.shape)
            elif mode == "burst":
                ordered_ink = self._burst_order(ink_pixels, focal_points, zone_ids.shape)
                ordered_bg = self._burst_order(bg_pixels, focal_points, zone_ids.shape)
            else:
                # "single_focal" or "multi_focal" — radial order from focal points
                ordered_ink = self._radial_order(ink_pixels, focal_points)
                ordered_bg = self._radial_order(bg_pixels, focal_points)
            
            # Add jitter for natural feel
            if self.config.stroke_jitter > 0 and len(ordered_ink) > 1:
                ordered_ink = self._apply_jitter(ordered_ink, self.config.stroke_jitter)
            
            # Combine: ink first, then background
            if len(ordered_ink) > 0 and len(ordered_bg) > 0:
                combined = np.concatenate([ordered_ink, ordered_bg], axis=0)
            elif len(ordered_ink) > 0:
                combined = ordered_ink
            else:
                combined = ordered_bg
            
            zone_sequences.append(combined.astype(np.int32))
        
        return zone_sequences
    
    def _radial_order(self, pixels: np.ndarray,
                       focal_points: List[Dict[str, Any]]) -> np.ndarray:
        """Order pixels by distance to nearest focal point (closest first)."""
        if len(pixels) == 0:
            return pixels
        
        if not focal_points:
            # No focal points — random shuffle
            indices = np.arange(len(pixels))
            np.random.shuffle(indices)
            return pixels[indices]
        
        # Compute min distance to any focal point
        min_dists = np.full(len(pixels), np.inf, dtype=np.float32)
        
        for fp in focal_points:
            fx, fy = fp['point']  # (col, row)
            dists = np.sqrt(
                (pixels[:, 1].astype(np.float32) - fx) ** 2 +
                (pixels[:, 0].astype(np.float32) - fy) ** 2
            )
            min_dists = np.minimum(min_dists, dists)
        
        # Sort by distance (closest first)
        order = np.argsort(min_dists)
        return pixels[order]
    
    def _spiral_order(self, pixels: np.ndarray,
                       focal_points: List[Dict[str, Any]],
                       image_shape: tuple) -> np.ndarray:
        """Order pixels in a spiral pattern from focal points outward."""
        if len(pixels) == 0:
            return pixels
        
        h, w = image_shape[:2]
        
        # Use first focal point (or center) as spiral center
        if focal_points:
            cx, cy = focal_points[0]['point']
        else:
            cx, cy = w // 2, h // 2
        
        # Convert to polar coordinates relative to center
        dx = pixels[:, 1].astype(np.float64) - cx
        dy = pixels[:, 0].astype(np.float64) - cy
        
        radii = np.sqrt(dx ** 2 + dy ** 2)
        angles = np.arctan2(dy, dx)  # -π to π
        
        # Spiral ordering: combine radius with angle
        # Normalize radius
        max_r = radii.max() if radii.max() > 0 else 1.0
        norm_radii = radii / max_r
        
        # Create spiral parameter: radius + angle_offset
        tightness = self.config.spiral_tightness
        num_arms = self.config.spiral_arms
        
        # Spiral distance: how far along a spiral arm this pixel is
        spiral_angle = angles + 2.0 * np.pi * norm_radii * tightness * num_arms
        spiral_param = norm_radii + 0.1 * (spiral_angle % (2 * np.pi)) / (2 * np.pi)
        
        order = np.argsort(spiral_param)
        return pixels[order]
    
    def _burst_order(self, pixels: np.ndarray,
                      focal_points: List[Dict[str, Any]],
                      image_shape: tuple) -> np.ndarray:
        """Order pixels with burst pattern: focal fast, background slow."""
        if len(pixels) == 0:
            return pixels
        
        # Same as radial order but the engine will use different speeds
        return self._radial_order(pixels, focal_points)
    
    def _apply_jitter(self, pixels: np.ndarray, jitter_amount: float) -> np.ndarray:
        """
        Apply local reordering jitter for a more natural feel.
        Swaps nearby pixels in the sequence with some probability.
        """
        n = len(pixels)
        if n < 2:
            return pixels
        
        result = pixels.copy()
        
        # Block-level shuffle: divide into small blocks and shuffle within
        block_size = max(3, int(n * jitter_amount * 0.02))
        
        for start in range(0, n - block_size, block_size):
            end = min(start + block_size, n)
            block_indices = np.arange(start, end)
            np.random.shuffle(block_indices)
            result[start:end] = result[block_indices]
        
        return result
    
    def build_full_reveal_sequence(self, zone_sequences: List[np.ndarray]
                                    ) -> np.ndarray:
        """
        Flatten zone sequences into a single reveal sequence.
        
        Args:
            zone_sequences: List of per-zone pixel arrays
            
        Returns:
            Full (N, 2) reveal sequence array of (row, col) coords
        """
        non_empty = [seq for seq in zone_sequences if len(seq) > 0]
        if not non_empty:
            return np.empty((0, 2), dtype=np.int32)
        return np.concatenate(non_empty, axis=0)
