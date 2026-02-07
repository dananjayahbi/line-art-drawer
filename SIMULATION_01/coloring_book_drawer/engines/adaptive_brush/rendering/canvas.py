"""
Virtual Canvas
================
Manages the drawing canvas and composites graphite accumulation
into a viewable RGB frame. Handles background, paper tint, and
the conversion from accumulation map to visible artwork.
"""

import numpy as np
from ..physics.accumulator import GraphiteAccumulator


class VirtualCanvas:
    """
    Virtual canvas for the adaptive brush simulation.
    Composites graphite darkness onto a paper-colored background.
    """
    
    def __init__(self, height: int, width: int,
                 paper_color: tuple = (255, 255, 255),
                 pencil_color: tuple = (30, 30, 30)):
        """
        Args:
            height, width: Canvas dimensions
            paper_color: RGB background color (default white)
            pencil_color: RGB graphite color (default dark gray)
        """
        self.height = height
        self.width = width
        self.paper_color = np.array(paper_color, dtype=np.float32)
        self.pencil_color = np.array(pencil_color, dtype=np.float32)
        
        # Create background
        self._background = np.zeros((height, width, 3), dtype=np.float32)
        self._background[:] = self.paper_color
        
    def composite_frame(self, accumulator: GraphiteAccumulator,
                        original_image: np.ndarray = None,
                        reveal_mode: bool = True) -> np.ndarray:
        """
        Generate a displayable RGB frame from the accumulation state.
        
        Args:
            accumulator: GraphiteAccumulator with current drawing state
            original_image: Target artwork (H, W, 3) BGR/RGB
            reveal_mode: If True, reveals original image through accumulation.
                        If False, draws graphite marks on paper.
                        
        Returns:
            (H, W, 3) uint8 RGB frame
        """
        darkness = accumulator.get_canvas_darkness()
        if darkness is None:
            return self._background.copy().astype(np.uint8)
        
        if reveal_mode and original_image is not None:
            # Reveal mode: show original artwork where graphite has been applied
            frame = self._composite_reveal(darkness, original_image)
        else:
            # Draw mode: show graphite marks on paper
            frame = self._composite_graphite(darkness)
        
        return np.clip(frame, 0, 255).astype(np.uint8)
    
    def _composite_reveal(self, darkness: np.ndarray,
                          original: np.ndarray) -> np.ndarray:
        """Reveal original artwork through graphite accumulation mask."""
        h, w = darkness.shape
        
        # Resize original if needed
        if original.shape[0] != h or original.shape[1] != w:
            try:
                import cv2
                original = cv2.resize(original, (w, h), interpolation=cv2.INTER_LINEAR)
            except ImportError:
                pass
        
        # Ensure 3-channel
        if len(original.shape) == 2:
            original = np.stack([original]*3, axis=-1)
        
        # Alpha from accumulation (0 = paper, 1 = fully revealed)
        alpha = np.clip(darkness, 0, 1)
        alpha_3ch = alpha[:, :, np.newaxis]
        
        # Blend: paper * (1 - alpha) + original * alpha
        frame = self._background * (1.0 - alpha_3ch) + original.astype(np.float32) * alpha_3ch
        
        return frame
    
    def _composite_graphite(self, darkness: np.ndarray) -> np.ndarray:
        """Draw graphite marks on paper background."""
        alpha = np.clip(darkness, 0, 1)
        alpha_3ch = alpha[:, :, np.newaxis]
        
        # Graphite darkens the paper
        pencil_layer = np.zeros_like(self._background)
        pencil_layer[:] = self.pencil_color
        
        frame = self._background * (1.0 - alpha_3ch) + pencil_layer * alpha_3ch
        return frame
    
    def get_blank_frame(self) -> np.ndarray:
        """Get a blank paper-colored frame."""
        return self._background.copy().astype(np.uint8)
