"""
Zone-Based Progressive Engine - Transition Blender
====================================================
Smooths transitions between zone boundaries to prevent
hard edges during progressive reveal.
"""

import cv2
import numpy as np
from typing import List

from ..config import AnimationConfig


class TransitionBlender:
    """
    Handles smooth blending at zone boundaries during reveal.
    Applies feathering and edge softening to prevent visible seams.
    """
    
    def __init__(self, config: AnimationConfig = None):
        self.config = config or AnimationConfig()
    
    def blend_zone_edges(self, reveal_mask: np.ndarray) -> np.ndarray:
        """
        Apply edge blending to the reveal mask.
        Smooths out hard zone boundaries.
        
        Args:
            reveal_mask: Float32 mask (H, W), 0-1
            
        Returns:
            Blended mask with smoother edges
        """
        sigma = self.config.blend_sigma
        if sigma <= 0:
            return reveal_mask
        
        # Gaussian blur for edge smoothing
        ksize = int(sigma * 4) | 1  # Ensure odd kernel size
        ksize = max(3, ksize)
        
        blended = cv2.GaussianBlur(reveal_mask, (ksize, ksize), sigma)
        
        # Preserve fully revealed and fully hidden areas
        # Only blend in the transition zone
        fully_revealed = reveal_mask > 0.99
        fully_hidden = reveal_mask < 0.01
        
        result = blended.copy()
        result[fully_revealed] = 1.0
        result[fully_hidden] = 0.0
        
        return result
    
    def create_soft_transition(self, mask_a: np.ndarray,
                                mask_b: np.ndarray,
                                blend_factor: float = 0.5) -> np.ndarray:
        """
        Create a soft transition between two zone masks.
        
        Args:
            mask_a: First zone mask (float32, 0-1)
            mask_b: Second zone mask (float32, 0-1)
            blend_factor: How much to blend (0 = all A, 1 = all B)
            
        Returns:
            Blended mask
        """
        return mask_a * (1.0 - blend_factor) + mask_b * blend_factor
    
    def feather_reveal_edge(self, reveal_mask: np.ndarray,
                             feather_radius: int = 3) -> np.ndarray:
        """
        Apply feathering to the leading edge of the reveal mask.
        Creates a soft gradient at the boundary between revealed and unrevealed.
        
        Args:
            reveal_mask: Float32 mask (H, W), 0-1
            feather_radius: Radius of the feathering effect
            
        Returns:
            Feathered mask
        """
        if feather_radius <= 0:
            return reveal_mask
        
        # Create a binary version of the mask
        binary = (reveal_mask > 0.5).astype(np.uint8)
        
        # Distance transform from the edge
        dist_inside = cv2.distanceTransform(binary, cv2.DIST_L2, 3)
        dist_outside = cv2.distanceTransform(1 - binary, cv2.DIST_L2, 3)
        
        # Create smooth falloff at the edge
        signed_dist = dist_inside - dist_outside
        feathered = np.clip(signed_dist / feather_radius * 0.5 + 0.5, 0.0, 1.0)
        
        # Blend with original (preserve fully revealed areas from zone masks)
        result = np.maximum(reveal_mask, feathered.astype(np.float32))
        
        # But don't reveal areas that are fully hidden in original
        result = np.where(reveal_mask < 0.01, feathered.astype(np.float32) * reveal_mask * 100, result)
        
        return np.clip(result, 0.0, 1.0)
