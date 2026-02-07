"""
Frame Exporter
================
Handles frame generation and export for the simulation display.
Manages reveal mask generation and pen position estimation.
"""

import numpy as np
from ..physics.accumulator import GraphiteAccumulator


class FrameExporter:
    """Generates output frames and tracking data for the simulation."""
    
    def __init__(self, height: int, width: int):
        self.height = height
        self.width = width
        self._last_pen_position = (width // 2, height // 2)
        self._current_stroke_idx = 0
        self._current_point_idx = 0
        
    def generate_reveal_mask(self, accumulator: GraphiteAccumulator,
                             threshold: float = 0.01) -> np.ndarray:
        """
        Generate a binary reveal mask from accumulator state.
        
        Returns:
            Boolean mask (H, W) - True where graphite has been deposited
        """
        mask = accumulator.get_visible_mask(threshold)
        if mask is None:
            return np.zeros((self.height, self.width), dtype=bool)
        return mask
    
    def update_pen_position(self, y: int, x: int):
        """Update the current pen position."""
        # Clamp to canvas bounds
        x = max(0, min(self.width - 1, int(x)))
        y = max(0, min(self.height - 1, int(y)))
        self._last_pen_position = (x, y)
        
    def get_pen_position(self) -> tuple:
        """Get current pen position as (x, y)."""
        return self._last_pen_position
    
    def update_stroke_progress(self, stroke_idx: int, point_idx: int):
        """Track which stroke and point we're currently rendering."""
        self._current_stroke_idx = stroke_idx
        self._current_point_idx = point_idx
    
    def get_reveal_count(self, accumulator: GraphiteAccumulator) -> int:
        """Get total number of revealed (non-zero) pixels."""
        darkness = accumulator.get_canvas_darkness()
        if darkness is None:
            return 0
        return int((darkness > 0.01).sum())
    
    def estimate_pen_from_recent(self, stroke_points: np.ndarray,
                                  current_idx: int) -> tuple:
        """
        Estimate pen position from stroke points.
        
        Args:
            stroke_points: (N, 2) array of (y, x) positions
            current_idx: Current index in the stroke
            
        Returns:
            (x, y) pen position
        """
        if stroke_points is None or len(stroke_points) == 0:
            return self._last_pen_position
            
        idx = min(current_idx, len(stroke_points) - 1)
        y, x = int(stroke_points[idx, 0]), int(stroke_points[idx, 1])
        self.update_pen_position(y, x)
        return (x, y)
