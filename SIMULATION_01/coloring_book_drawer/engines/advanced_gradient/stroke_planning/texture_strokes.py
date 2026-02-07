"""
Texture Stroke Generator
==========================
Generates direction-following hatching strokes for textured regions.
Uses the structure tensor orientation to follow natural flow (hair, fabric, etc.).
"""

import numpy as np
import math
from typing import List, Dict
from .contour_strokes import StrokePoint


class TextureStrokeGenerator:
    """
    Generates direction-aware hatching strokes for textured regions.
    Strokes follow the local orientation from structure tensor analysis.
    """

    def __init__(self, use_gpu: bool = False):
        self.use_gpu = use_gpu
        self._cp = None
        if use_gpu:
            try:
                import cupy
                self._cp = cupy
            except ImportError:
                pass

    def generate(self, regions: Dict, intensity_map: np.ndarray,
                 orientation: np.ndarray, coherence: np.ndarray,
                 stroke_spacing: int = 3,
                 texture_strength: float = 0.6) -> List[StrokePoint]:
        """
        Generate texture-following strokes for textured regions.

        Args:
            regions: Region dict from RegionSegmenter
            intensity_map: Continuous intensity map (0-1)
            orientation: Per-pixel orientation from structure tensor
            coherence: Coherence map from structure tensor
            stroke_spacing: Spacing between hatching lines
            texture_strength: How strongly to follow detected texture

        Returns:
            List of StrokePoints for textured regions
        """
        all_strokes = []

        textured_regions = {
            label: info for label, info in regions.items()
            if info['type'] == 'textured'
        }

        if not textured_regions:
            print("  [TextureStrokes] No textured regions found")
            return all_strokes

        for label, info in textured_regions.items():
            mask = info['mask']
            bounds = info['bounds']

            strokes = self._generate_direction_hatching(
                mask, bounds, intensity_map, orientation,
                coherence, stroke_spacing, texture_strength
            )
            all_strokes.extend(strokes)

        print(f"  [TextureStrokes] Generated {len(all_strokes)} texture stroke points "
              f"from {len(textured_regions)} regions")
        return all_strokes

    def _generate_direction_hatching(self, mask: np.ndarray, bounds: tuple,
                                      intensity_map: np.ndarray,
                                      orientation: np.ndarray,
                                      coherence: np.ndarray,
                                      spacing: int,
                                      strength: float) -> List[StrokePoint]:
        """Generate direction-following hatching for a single textured region."""
        min_row, min_col, max_row, max_col = bounds
        h, w = mask.shape
        strokes = []

        # Get the dominant orientation in this region
        region_orientations = orientation[mask]
        if len(region_orientations) == 0:
            return strokes

        # Use coherence-weighted mean orientation
        region_coherence = coherence[mask]
        if np.sum(region_coherence) > 0:
            # Circular mean weighted by coherence
            sin_sum = np.sum(np.sin(2 * region_orientations) * region_coherence)
            cos_sum = np.sum(np.cos(2 * region_orientations) * region_coherence)
            dominant_angle = 0.5 * math.atan2(sin_sum, cos_sum)
        else:
            dominant_angle = np.mean(region_orientations)

        # Generate hatching lines following the dominant direction
        # Perpendicular to the dominant angle for hatching effect
        hatch_angle = dominant_angle + math.pi / 2

        dx = math.cos(hatch_angle)
        dy = math.sin(hatch_angle)
        perp_dx = -dy
        perp_dy = dx

        # Calculate diagonal of bounding region (bounds are absolute coordinates)
        region_h = max_row - min_row
        region_w = max_col - min_col
        diagonal = math.sqrt(region_w ** 2 + region_h ** 2)

        if spacing <= 0:
            spacing = 3

        num_lines = int(diagonal / spacing) + 1
        start_offset = -diagonal / 2

        cx_base = min_col + region_w / 2
        cy_base = min_row + region_h / 2

        for line_idx in range(num_lines):
            offset = start_offset + line_idx * spacing
            cx = cx_base + perp_dx * offset
            cy = cy_base + perp_dy * offset

            stroke = []
            step_size = 1.5

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
                if intensity < 0.08:
                    if stroke and len(stroke) > 2:
                        strokes.extend(stroke)
                        stroke = []
                    continue

                # Blend between fixed hatch angle and local orientation
                local_angle = float(orientation[iy, ix])
                local_coh = float(coherence[iy, ix])
                blended_angle = (hatch_angle * (1 - local_coh * strength) +
                                 (local_angle + math.pi / 2) * local_coh * strength)

                pressure = min(1.0, intensity * 1.1)
                point_width = 1.0 + intensity * 1.5

                stroke.append(StrokePoint(
                    x=x, y=y,
                    pressure=pressure,
                    angle=blended_angle,
                    width=point_width,
                    phase='texture',
                    intensity=intensity
                ))

            if stroke and len(stroke) > 2:
                strokes.extend(stroke)

        return strokes
