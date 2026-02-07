"""
Graphite Accumulator
=====================
Manages graphite buildup on the canvas with saturation behavior.
Multiple layers of graphite accumulate but eventually saturate,
just like real pencil strokes layered on paper.
"""

import numpy as np
from ..config import AccumulatorConfig


class GraphiteAccumulator:
    """Tracks and applies graphite accumulation with saturation curve."""
    
    def __init__(self, config: AccumulatorConfig):
        self.config = config
        self.max_density = config.max_density
        self.saturation_curve = config.saturation_curve
        self.layer_blending = config.layer_blending
        self._accumulation_map = None  # Tracks total graphite deposited
        
    def initialize(self, height: int, width: int):
        """Initialize accumulation map for given canvas dimensions."""
        self._accumulation_map = np.zeros((height, width), dtype=np.float32)
        
    def apply_deposit(self, deposit: np.ndarray, y_slice: slice, x_slice: slice):
        """
        Apply a graphite deposit to the accumulation map with saturation.
        
        Args:
            deposit: 2D deposit intensity array
            y_slice: Row slice for placement
            x_slice: Column slice for placement
        """
        if self._accumulation_map is None:
            return
            
        region = self._accumulation_map[y_slice, x_slice]
        
        # Ensure sizes match
        rh, rw = region.shape
        dh, dw = deposit.shape
        min_h = min(rh, dh)
        min_w = min(rw, dw)
        
        region = region[:min_h, :min_w]
        deposit = deposit[:min_h, :min_w]
        
        # Saturation curve: new_deposit is reduced when existing graphite is high
        # Uses an exponential saturation model
        headroom = self.max_density - region
        headroom = np.clip(headroom, 0, self.max_density)
        
        # Effective deposit follows: deposit * (headroom / max_density)^saturation_curve
        saturation_factor = (headroom / (self.max_density + 1e-8)) ** self.saturation_curve
        effective_deposit = deposit * saturation_factor * self.layer_blending
        
        # Apply
        new_region = region + effective_deposit
        new_region = np.clip(new_region, 0.0, self.max_density)
        
        self._accumulation_map[y_slice, x_slice][:min_h, :min_w] = new_region
        
    def apply_deposits_batch(self, deposits: list):
        """
        Apply multiple deposits in sequence.
        
        Args:
            deposits: List of (deposit_array, y_slice, x_slice) tuples
        """
        for deposit, ys, xs in deposits:
            self.apply_deposit(deposit, ys, xs)
            
    def get_canvas_darkness(self) -> np.ndarray:
        """
        Get the current canvas darkness map.
        
        Returns:
            (H, W) array where 0=white, max_density=fully dark
        """
        if self._accumulation_map is None:
            return None
        return self._accumulation_map.copy()
    
    def get_visible_mask(self, threshold: float = 0.01) -> np.ndarray:
        """
        Get binary mask of pixels with visible graphite.
        
        Returns:
            Boolean mask (H, W) of revealed pixels
        """
        if self._accumulation_map is None:
            return None
        return self._accumulation_map > threshold
    
    def get_progress(self, target_mask: np.ndarray = None) -> float:
        """
        Calculate overall drawing progress.
        
        Args:
            target_mask: Boolean mask of pixels that should be drawn.
                        If None, uses the whole canvas.
        Returns:
            Progress ratio [0, 1]
        """
        if self._accumulation_map is None:
            return 0.0
            
        if target_mask is not None:
            if target_mask.sum() == 0:
                return 1.0
            drawn = (self._accumulation_map[target_mask] > 0.01).sum()
            return float(drawn / target_mask.sum())
        else:
            total = self._accumulation_map.size
            drawn = (self._accumulation_map > 0.01).sum()
            return float(drawn / total) if total > 0 else 0.0

    @property
    def accumulation_map(self) -> np.ndarray:
        """Direct reference to accumulation map."""
        return self._accumulation_map
