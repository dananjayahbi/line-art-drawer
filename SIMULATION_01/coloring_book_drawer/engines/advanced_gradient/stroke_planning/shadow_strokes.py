"""
Shadow Stroke Generator
========================
Generates multi-pass dense strokes for deep shadow regions.
Each pass adds more density to approach target darkness.
"""

import numpy as np
import math
from typing import List, Dict
from .contour_strokes import StrokePoint


class ShadowStrokeGenerator:
    """
    Handles deep shadow areas that need multiple overlapping passes.
    Each pass uses a slightly different angle and diminishing opacity.
    """

    def __init__(self, use_gpu: bool = False):
        self.use_gpu = use_gpu

    def generate(self, regions: Dict, intensity_map: np.ndarray,
                 orientation: np.ndarray, coherence: np.ndarray,
                 shadow_passes: int = 3,
                 angle_variation: float = 30.0,
                 stroke_spacing: int = 3) -> List[StrokePoint]:
        """
        Generate multi-pass shadow strokes.

        Args:
            regions: Region dict from RegionSegmenter
            intensity_map: Continuous intensity map (0-1)
            orientation: Per-pixel orientation from structure tensor
            coherence: Coherence map from structure tensor
            shadow_passes: Number of overlapping passes (1-5)
            angle_variation: Degrees between passes
            stroke_spacing: Spacing between hatching lines

        Returns:
            List of StrokePoints for shadow regions
        """
        all_strokes = []

        shadow_regions = {
            label: info for label, info in regions.items()
            if info['type'] == 'shadow'
        }

        if not shadow_regions:
            print("  [ShadowStrokes] No shadow regions found")
            return all_strokes

        # Build combined shadow mask
        h, w = intensity_map.shape
        shadow_mask = np.zeros((h, w), dtype=bool)
        for label, info in shadow_regions.items():
            shadow_mask |= info['mask']

        # Plan multiple passes
        passes = self._plan_shadow_passes(
            shadow_mask, intensity_map,
            shadow_passes, angle_variation, stroke_spacing,
            orientation, coherence
        )

        for pass_info in passes:
            all_strokes.extend(pass_info['strokes'])

        print(f"  [ShadowStrokes] Generated {len(all_strokes)} shadow stroke points "
              f"({shadow_passes} passes, {len(shadow_regions)} regions)")
        return all_strokes

    def _plan_shadow_passes(self, shadow_mask: np.ndarray,
                             intensity_map: np.ndarray,
                             num_passes: int,
                             angle_variation: float,
                             spacing: int,
                             orientation: np.ndarray,
                             coherence: np.ndarray) -> List[Dict]:
        """
        Generate multiple passes for deep shadows.
        Each pass adds more density with a different angle.
        """
        passes = []
        h, w = intensity_map.shape

        # Calculate how many passes each pixel needs
        pass_count = np.ceil(intensity_map * num_passes).astype(int)

        base_angle = math.radians(45)

        for pass_num in range(1, num_passes + 1):
            # Pixels that need this pass
            needs_pass = (pass_count >= pass_num) & shadow_mask

            if not np.any(needs_pass):
                continue

            # Different angle for each pass
            angle_offset = math.radians((pass_num - 1) * angle_variation)
            pass_angle = base_angle + angle_offset

            # Diminishing opacity per pass
            opacity_factor = 0.8 / pass_num

            strokes = self._generate_shadow_pass_strokes(
                needs_pass, intensity_map, pass_angle,
                spacing, opacity_factor, pass_num,
                orientation, coherence
            )

            passes.append({
                'pass_num': pass_num,
                'strokes': strokes,
                'description': f'Shadow Pass {pass_num}'
            })

        return passes

    def _generate_shadow_pass_strokes(self, mask: np.ndarray,
                                       intensity_map: np.ndarray,
                                       angle: float, spacing: int,
                                       opacity_factor: float,
                                       pass_num: int,
                                       orientation: np.ndarray,
                                       coherence: np.ndarray) -> List[StrokePoint]:
        """Generate strokes for a single shadow pass."""
        h, w = mask.shape
        strokes = []

        dx = math.cos(angle)
        dy = math.sin(angle)
        perp_dx = -dy
        perp_dy = dx

        diagonal = math.sqrt(w ** 2 + h ** 2)
        if spacing <= 0:
            spacing = 3

        num_lines = int(diagonal / spacing) + 1
        start_offset = -diagonal / 2

        step_size = 1.5

        for line_idx in range(num_lines):
            offset = start_offset + line_idx * spacing
            cx = w / 2 + perp_dx * offset
            cy = h / 2 + perp_dy * offset

            stroke = []
            for t_idx in range(int(diagonal / step_size)):
                t = -diagonal / 2 + t_idx * step_size
                x = cx + dx * t
                y = cy + dy * t

                ix, iy = int(x), int(y)
                if not (0 <= ix < w and 0 <= iy < h):
                    continue
                if not mask[iy, ix]:
                    if stroke and len(stroke) > 2:
                        strokes.extend(stroke)
                        stroke = []
                    continue

                intensity = float(intensity_map[iy, ix])
                if intensity < 0.3:  # Shadow threshold
                    if stroke and len(stroke) > 2:
                        strokes.extend(stroke)
                        stroke = []
                    continue

                pressure = min(1.0, intensity * opacity_factor * 1.5)
                point_width = 1.2 + intensity * 1.8

                stroke.append(StrokePoint(
                    x=x, y=y,
                    pressure=pressure,
                    angle=angle,
                    width=point_width,
                    phase='shadow',
                    intensity=intensity
                ))

            if stroke and len(stroke) > 2:
                strokes.extend(stroke)

        return strokes
