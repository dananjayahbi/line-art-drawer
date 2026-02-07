"""
Unified Renderer
==================
Composites per-region reveal masks into a final output frame.
Manages the global reveal mask and pen position tracking.
"""

import numpy as np
from typing import Tuple, Optional, List

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

from ..config import RenderingConfig
from ..classification.classifier import RegionInfo


class UnifiedRenderer:
    """
    Composites region-based reveals into a single output frame.
    Maintains the global reveal mask and pen cursor position.
    """
    
    def __init__(self, config: RenderingConfig):
        self.config = config
        self.feather_radius = config.mask_feather_radius
        
        # State
        self._reveal_mask: Optional[np.ndarray] = None  # (H, W) float 0-1
        self._original: Optional[np.ndarray] = None     # (H, W, 3) BGR
        self._pen_position: Tuple[int, int] = (0, 0)
        self._height: int = 0
        self._width: int = 0
    
    def initialize(self, original_image: np.ndarray):
        """
        Set up renderer with the original image.
        
        Args:
            original_image: (H, W, 3) BGR image
        """
        self._original = original_image.copy()
        self._height, self._width = original_image.shape[:2]
        self._reveal_mask = np.zeros((self._height, self._width), dtype=np.float32)
        self._pen_position = (self._width // 2, self._height // 2)
    
    def update_reveal(self, composite_mask: np.ndarray,
                      active_regions: List[RegionInfo] = None):
        """
        Update the global reveal mask from the composite.
        
        The reveal mask only increases — once a pixel is revealed,
        it stays revealed (monotonic increase).
        
        Args:
            composite_mask: (H, W) float [0, 1] blended mask
            active_regions: Optional list for pen position tracking
        """
        if self._reveal_mask is None:
            return
        
        # Monotonic: take the max of existing and new
        self._reveal_mask = np.maximum(self._reveal_mask, composite_mask)
        
        # Clamp to [0, 1]
        np.clip(self._reveal_mask, 0.0, 1.0, out=self._reveal_mask)
        
        # Update pen position to the region being most actively revealed
        if active_regions:
            self._update_pen_position(composite_mask, active_regions)
    
    def get_current_frame(self) -> np.ndarray:
        """
        Render the current frame by blending original with white background.
        
        Returns:
            (H, W, 3) BGR frame
        """
        if self._original is None or self._reveal_mask is None:
            return np.ones((480, 640, 3), dtype=np.uint8) * 255
        
        # Feather the mask for smoother edges
        feathered = self._feather_mask(self._reveal_mask)
        
        # White background
        white = np.ones_like(self._original, dtype=np.uint8) * 255
        
        # Blend: revealed areas show original, unrevealed show white
        mask_3ch = feathered[:, :, np.newaxis]  # (H, W, 1)
        frame = (self._original.astype(np.float32) * mask_3ch +
                 white.astype(np.float32) * (1.0 - mask_3ch))
        
        return frame.astype(np.uint8)
    
    def get_reveal_mask(self) -> np.ndarray:
        """Get the current reveal mask (H, W) float [0, 1]."""
        if self._reveal_mask is None:
            return np.zeros((1, 1), dtype=np.float32)
        return self._reveal_mask.copy()
    
    def get_pen_position(self) -> Tuple[int, int]:
        """Get current pen (x, y) position."""
        return self._pen_position
    
    def get_progress(self) -> float:
        """Get overall reveal progress [0, 1]."""
        if self._reveal_mask is None:
            return 0.0
        return float(np.mean(self._reveal_mask))
    
    def get_binary_mask(self, threshold: float = 0.5) -> np.ndarray:
        """
        Get binary reveal mask (for compatibility with other components).
        
        Args:
            threshold: Pixels above this are considered revealed
            
        Returns:
            (H, W) bool mask
        """
        if self._reveal_mask is None:
            return np.zeros((1, 1), dtype=bool)
        return self._reveal_mask >= threshold
    
    def get_reveal_count(self) -> int:
        """Get number of revealed pixels (above 0.5 threshold)."""
        if self._reveal_mask is None:
            return 0
        return int(np.sum(self._reveal_mask >= 0.5))
    
    def reset(self):
        """Reset the renderer state."""
        if self._height > 0 and self._width > 0:
            self._reveal_mask = np.zeros(
                (self._height, self._width), dtype=np.float32
            )
        self._pen_position = (0, 0)
    
    def _feather_mask(self, mask: np.ndarray) -> np.ndarray:
        """Apply Gaussian feathering to the reveal mask."""
        if self.feather_radius <= 0:
            return mask
        
        if HAS_CV2:
            ksize = self.feather_radius * 2 + 1
            return cv2.GaussianBlur(
                mask, (ksize, ksize), 0
            )
        else:
            # Simple box blur fallback
            from scipy.ndimage import uniform_filter
            try:
                return uniform_filter(mask, size=self.feather_radius * 2 + 1)
            except ImportError:
                return mask
    
    def _update_pen_position(self, composite_mask: np.ndarray,
                              regions: List[RegionInfo]):
        """
        Update pen position to track the most recently active area.
        Picks the region with the highest reveal delta near its frontier.
        """
        if self._reveal_mask is None:
            return
        
        best_region = None
        best_activity = 0.0
        
        for region in regions:
            # Check how much new reveal happened in this region
            region_mask = region.mask
            if region_mask is None:
                continue
            
            new_reveal = composite_mask[region_mask]
            old_reveal = self._reveal_mask[region_mask]
            
            # Activity = average increase
            delta = np.mean(np.maximum(new_reveal - old_reveal, 0.0))
            if delta > best_activity:
                best_activity = delta
                best_region = region
        
        if best_region is not None:
            # Pen position = centroid of the most active region
            cy, cx = best_region.centroid
            self._pen_position = (
                int(np.clip(cx, 0, self._width - 1)),
                int(np.clip(cy, 0, self._height - 1))
            )
