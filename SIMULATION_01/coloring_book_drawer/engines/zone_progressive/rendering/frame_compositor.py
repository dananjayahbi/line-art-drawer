"""
Zone-Based Progressive Engine - Frame Compositor
==================================================
Composes the final output frame by applying the reveal mask
to the original image over a background.
"""

import cv2
import numpy as np
from typing import Tuple

from ..config import RenderingConfig


class FrameCompositor:
    """
    Composes the final visible frame by blending the original image
    with the background using the current reveal mask.
    
    frame = background * (1 - mask) + original * mask
    """
    
    def __init__(self, original_image: np.ndarray,
                 config: RenderingConfig = None):
        """
        Args:
            original_image: The original artwork (H, W, 3), uint8, RGB
            config: Rendering configuration
        """
        self.config = config or RenderingConfig()
        self.original = original_image.astype(np.float32)
        self.h, self.w = original_image.shape[:2]
        
        # Create background (typically white)
        self.background = np.full_like(self.original, 
                                        fill_value=self.config.background_color,
                                        dtype=np.float32)
    
    def compose_frame(self, reveal_mask: np.ndarray) -> np.ndarray:
        """
        Compose a frame by blending original with background.
        
        Args:
            reveal_mask: Float32 mask (H, W), 0-1.
                         1.0 = show original, 0.0 = show background.
                         
        Returns:
            Composed frame (H, W, 3), uint8, RGB
        """
        # Expand mask to 3 channels
        mask_3ch = np.stack([reveal_mask] * 3, axis=-1)
        
        # Apply gamma correction if configured
        if self.config.gamma_correction != 1.0:
            mask_3ch = np.power(mask_3ch, self.config.gamma_correction)
        
        # Blend: bg * (1-mask) + original * mask
        frame = self.background * (1.0 - mask_3ch) + self.original * mask_3ch
        
        return np.clip(frame, 0, 255).astype(np.uint8)
    
    def compose_frame_with_feathering(self, reveal_mask: np.ndarray,
                                       feather_radius: int = 3) -> np.ndarray:
        """
        Compose frame with additional edge feathering for softer reveal.
        
        Args:
            reveal_mask: Float32 mask (H, W), 0-1
            feather_radius: Radius for edge softening
            
        Returns:
            Composed frame (H, W, 3), uint8, RGB
        """
        if not self.config.use_soft_mask or feather_radius <= 0:
            return self.compose_frame(reveal_mask)
        
        # Apply feathering to the mask edges
        ksize = feather_radius * 2 + 1
        softened = cv2.GaussianBlur(reveal_mask, (ksize, ksize), feather_radius / 2.0)
        
        # Preserve fully revealed regions
        softened = np.maximum(softened, reveal_mask * (reveal_mask > 0.95).astype(np.float32))
        
        return self.compose_frame(softened)
    
    def get_pen_position(self, reveal_mask: np.ndarray) -> Tuple[int, int]:
        """
        Estimate pen position at the leading edge of the reveal.
        Finds the centroid of recently revealed pixels.
        
        Args:
            reveal_mask: Float32 mask (H, W), 0-1
            
        Returns:
            (x, y) pen position tuple
        """
        # Find pixels near the reveal boundary (0.3 to 0.7 range)
        boundary = ((reveal_mask > 0.3) & (reveal_mask < 0.7)).astype(np.uint8)
        
        if np.sum(boundary) < 5:
            # Fallback: find pixels near the transition edge
            edge = ((reveal_mask > 0.01) & (reveal_mask < 0.99)).astype(np.uint8)
            if np.sum(edge) < 5:
                # Default to center
                return (self.w // 2, self.h // 2)
            boundary = edge
        
        # Find centroid of boundary pixels
        coords = np.argwhere(boundary > 0)  # (row, col)
        if len(coords) == 0:
            return (self.w // 2, self.h // 2)
        
        # Use the mean position
        mean_row = int(np.mean(coords[:, 0]))
        mean_col = int(np.mean(coords[:, 1]))
        
        return (mean_col, mean_row)  # (x, y) format
