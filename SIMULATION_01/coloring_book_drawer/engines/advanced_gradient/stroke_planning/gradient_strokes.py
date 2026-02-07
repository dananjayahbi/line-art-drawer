"""
Gradient Stroke Generator
==========================
Generates smooth reveal paths for gradient/tonal regions.
Uses intensity-aware reveal ordering that follows the flow field.
"""

import numpy as np
import cv2
import math
from typing import List, Dict, Optional
from .contour_strokes import StrokePoint


class GradientStrokeGenerator:
    """
    Generates gradient reveal strokes for smooth tonal regions.
    Instead of hatching, reveals original pixels progressively
    following natural drawing patterns.
    """

    def __init__(self, use_gpu: bool = False):
        self.use_gpu = use_gpu

    def generate(self, regions: Dict, intensity_map: np.ndarray,
                 orientation: np.ndarray, coherence: np.ndarray,
                 gradient_smoothness: float = 0.7) -> List[StrokePoint]:
        """
        Generate gradient reveal strokes for smooth tonal regions.

        Args:
            regions: Region dict from RegionSegmenter (type, mask, bounds, etc.)
            intensity_map: Continuous intensity map (0-1)
            orientation: Per-pixel orientation from structure tensor
            coherence: Coherence map from structure tensor
            gradient_smoothness: How smooth the gradient reveal should be

        Returns:
            List of StrokePoints for gradient regions
        """
        all_strokes = []

        # Process only gradient regions
        gradient_regions = {
            label: info for label, info in regions.items()
            if info['type'] == 'gradient'
        }

        if not gradient_regions:
            print("  [GradientStrokes] No gradient regions found")
            return all_strokes

        for label, info in gradient_regions.items():
            mask = info['mask']
            bounds = info['bounds']  # (min_row, min_col, max_row, max_col)

            strokes = self._generate_region_strokes(
                mask, bounds, intensity_map, orientation,
                coherence, gradient_smoothness
            )
            all_strokes.extend(strokes)

        # Sort by intensity (light areas first for form building)
        all_strokes.sort(key=lambda p: p.intensity)

        print(f"  [GradientStrokes] Generated {len(all_strokes)} gradient stroke points "
              f"from {len(gradient_regions)} regions")
        return all_strokes

    def _generate_region_strokes(self, mask: np.ndarray, bounds: tuple,
                                  intensity_map: np.ndarray,
                                  orientation: np.ndarray,
                                  coherence: np.ndarray,
                                  smoothness: float) -> List[StrokePoint]:
        """Generate strokes for a single gradient region."""
        min_row, min_col, max_row, max_col = bounds
        strokes = []

        # Determine scan spacing based on smoothness
        spacing = max(1, int(3 * (1.0 - smoothness) + 1))

        # Scan the bounding box (bounds are absolute coordinates)
        for y in range(min_row, max_row + 1, spacing):
            for x in range(min_col, max_col + 1, spacing):
                if y >= mask.shape[0] or x >= mask.shape[1]:
                    continue
                if not mask[y, x]:
                    continue

                intensity = float(intensity_map[y, x])
                if intensity < 0.02:  # Skip near-white
                    continue

                # Get local orientation for stroke direction
                angle = float(orientation[y, x]) if orientation is not None else 0.0
                coh = float(coherence[y, x]) if coherence is not None else 0.5

                # Pressure based on intensity
                pressure = 0.3 + 0.5 * intensity

                # Width based on smoothness and coherence
                width = 1.5 + smoothness * 2.0

                strokes.append(StrokePoint(
                    x=float(x), y=float(y),
                    pressure=pressure,
                    angle=angle,
                    width=width,
                    phase='gradient',
                    intensity=intensity
                ))

        return strokes

    def generate_highlight_strokes(self, regions: Dict,
                                    intensity_map: np.ndarray) -> List[StrokePoint]:
        """
        Generate minimal strokes for highlight regions (very light areas).
        These are revealed quickly with minimal drawing.
        """
        strokes = []
        highlight_regions = {
            label: info for label, info in regions.items()
            if info['type'] == 'highlight'
        }

        for label, info in highlight_regions.items():
            mask = info['mask']
            bounds = info['bounds']
            min_row, min_col, max_row, max_col = bounds

            # Very sparse sampling for highlights (bounds are absolute coordinates)
            for y in range(min_row, max_row + 1, 5):
                for x in range(min_col, max_col + 1, 5):
                    if y >= mask.shape[0] or x >= mask.shape[1]:
                        continue
                    if not mask[y, x]:
                        continue

                    intensity = float(intensity_map[y, x])
                    if intensity < 0.01:
                        continue

                    strokes.append(StrokePoint(
                        x=float(x), y=float(y),
                        pressure=0.2,
                        angle=0.0,
                        width=2.0,
                        phase='gradient',
                        intensity=intensity
                    ))

        print(f"  [GradientStrokes] Generated {len(strokes)} highlight stroke points")
        return strokes
