"""
Reveal Renderer
================
Progressive reveal compositor that blends original pixels through
a soft alpha mask with phase-specific brush behavior.
"""

import numpy as np
import math
from typing import Optional, Tuple
from ..config import BrushConfig, BRUSH_PRESETS


class RevealRenderer:
    """
    Renders the progressive reveal of original image pixels.
    Uses soft brushes with variable softness, opacity, and pressure.
    Supports phase-specific brush presets for natural variation.
    """

    def __init__(self, image_shape: Tuple[int, int],
                 bg_color: Tuple[int, int, int] = (255, 255, 255)):
        """
        Args:
            image_shape: (height, width) of the canvas
            bg_color: Background color RGB
        """
        self.h, self.w = image_shape
        self.bg_color = np.array(bg_color, dtype=np.uint8)

        # Main reveal mask (alpha channel for compositing)
        self.reveal_mask = np.zeros((self.h, self.w), dtype=np.float32)

        # Pressure accumulation map
        self.pressure_map = np.zeros((self.h, self.w), dtype=np.float32)

    def draw_stroke_point(self, x: float, y: float, pressure: float,
                          width: float, intensity: float, phase: str,
                          prev_x: Optional[float] = None,
                          prev_y: Optional[float] = None,
                          prev_pressure: Optional[float] = None,
                          prev_width: Optional[float] = None,
                          prev_intensity: Optional[float] = None):
        """
        Draw a single stroke point on the reveal mask.
        Interpolates between previous point if provided.

        Args:
            x, y: Position
            pressure: 0.0-1.0 pen pressure
            width: Brush width
            intensity: Target darkness (0-1)
            phase: Drawing phase name for brush preset selection
            prev_*: Previous point for interpolation
        """
        ix, iy = int(x), int(y)
        if not (0 <= ix < self.w and 0 <= iy < self.h):
            return

        # Get brush config for this phase
        brush = BRUSH_PRESETS.get(phase, BRUSH_PRESETS['contour'])

        # Calculate effective radius
        radius = max(1.0, width * brush.size_multiplier)

        # Calculate effective opacity
        opacity = pressure * brush.opacity_base * intensity

        # Draw the soft circle
        self._draw_soft_circle(ix, iy, radius, opacity, intensity, brush.softness)

        # Interpolate from previous point if close enough
        if prev_x is not None and prev_y is not None:
            dist = math.sqrt((x - prev_x) ** 2 + (y - prev_y) ** 2)
            pen_lift_threshold = 15.0

            if 1.5 < dist < pen_lift_threshold:
                steps = max(1, int(dist / 1.0))
                for step in range(1, steps):
                    t = step / steps
                    interp_x = prev_x + t * (x - prev_x)
                    interp_y = prev_y + t * (y - prev_y)
                    interp_p = (prev_pressure or pressure) + t * (pressure - (prev_pressure or pressure))
                    interp_w = (prev_width or width) + t * (width - (prev_width or width))
                    interp_i = (prev_intensity or intensity) + t * (intensity - (prev_intensity or intensity))

                    iix, iiy = int(interp_x), int(interp_y)
                    if 0 <= iix < self.w and 0 <= iiy < self.h:
                        ir = max(1.0, interp_w * brush.size_multiplier)
                        io = interp_p * brush.opacity_base * interp_i
                        self._draw_soft_circle(iix, iiy, ir, io, interp_i, brush.softness)

    def _draw_soft_circle(self, x: int, y: int, radius: float,
                          opacity: float, intensity: float,
                          softness: float):
        """Draw a soft-edged circle on the reveal mask."""
        r_int = int(np.ceil(radius * (1.5 + softness)))

        x1 = max(0, x - r_int)
        x2 = min(self.w, x + r_int + 1)
        y1 = max(0, y - r_int)
        y2 = min(self.h, y + r_int + 1)

        if x2 <= x1 or y2 <= y1:
            return

        yy, xx = np.mgrid[y1:y2, x1:x2]
        dist = np.sqrt((xx - x) ** 2 + (yy - y) ** 2)

        if softness > 0:
            sigma = max(0.5, radius * softness)
            falloff = np.exp(-0.5 * (dist / sigma) ** 2)
            mask_values = np.where(dist <= radius, 1.0, falloff)
            mask_values = np.clip(mask_values, 0, 1)
        else:
            mask_values = (dist <= radius).astype(np.float32)

        contribution = mask_values * opacity
        current = self.reveal_mask[y1:y2, x1:x2]
        self.reveal_mask[y1:y2, x1:x2] = np.maximum(current, contribution)

    def composite_frame(self, original_image: np.ndarray,
                        binary_mask: np.ndarray = None) -> np.ndarray:
        """
        Composite the current reveal state with original image.

        Args:
            original_image: RGB numpy array (h, w, 3)
            binary_mask: Optional binary mask of non-white pixels

        Returns:
            Composited RGB frame
        """
        reveal = np.clip(self.reveal_mask, 0, 1)

        if binary_mask is not None:
            effective_reveal = reveal * binary_mask.astype(np.float32)
        else:
            effective_reveal = reveal

        reveal_3ch = np.stack([effective_reveal] * 3, axis=-1)
        frame = self.bg_color * (1 - reveal_3ch) + original_image * reveal_3ch
        return frame.astype(np.uint8)

    def reset(self):
        """Reset the reveal mask for re-animation."""
        self.reveal_mask[:] = 0
        self.pressure_map[:] = 0
