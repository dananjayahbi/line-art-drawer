"""
Transition Blender
=====================
Creates feathered boundary transition zones between adjacent regions
and composites per-region reveal masks into a single blended output.

Uses ``cv2.distanceTransform`` and ``cv2.GaussianBlur`` when OpenCV is
available, with a pure-NumPy fallback otherwise.
"""

from __future__ import annotations

import logging
from typing import Dict, List

import numpy as np

from ..config import TransitionConfig
from ..classification.classifier import RegionInfo

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

logger = logging.getLogger(__name__)


def _gaussian_blur_fallback(
    image: np.ndarray, kernel_size: int
) -> np.ndarray:
    """Simple box-blur fallback when OpenCV is unavailable.

    This is an approximate replacement for ``cv2.GaussianBlur`` — good
    enough for transition feathering but not a true Gaussian kernel.

    Parameters
    ----------
    image : np.ndarray
        2-D float array to blur.
    kernel_size : int
        Side length of the blur kernel (will be forced to odd).

    Returns
    -------
    np.ndarray
        Blurred image of the same shape.
    """
    if kernel_size < 3:
        return image
    # Ensure odd kernel
    kernel_size = kernel_size | 1
    pad = kernel_size // 2

    padded = np.pad(image, pad, mode="reflect")
    # Cumulative sum box blur (fast approximation)
    cs = np.cumsum(np.cumsum(padded, axis=0), axis=1)
    h, w = image.shape
    blurred = (
        cs[kernel_size:h + kernel_size, kernel_size:w + kernel_size]
        - cs[:h, kernel_size:w + kernel_size]
        - cs[kernel_size:h + kernel_size, :w]
        + cs[:h, :w]
    ) / (kernel_size * kernel_size)
    return blurred


def _distance_transform_fallback(binary_mask: np.ndarray) -> np.ndarray:
    """Approximate Euclidean distance transform without OpenCV.

    Iteratively dilates the boundary inward, incrementing a counter at
    each step.  The result is a coarse but usable distance field.

    Parameters
    ----------
    binary_mask : np.ndarray
        2-D boolean or uint8 mask (non-zero = foreground).

    Returns
    -------
    np.ndarray
        Float distance array of the same shape.
    """
    mask = (binary_mask > 0).astype(np.float64)
    dist = np.zeros_like(mask, dtype=np.float64)

    remaining = mask.copy()
    step = 0
    while remaining.any():
        step += 1
        # Erode by checking 4-connected neighbours
        padded = np.pad(remaining, 1, mode="constant", constant_values=0)
        eroded = (
            padded[1:-1, 1:-1]
            * padded[:-2, 1:-1]
            * padded[2:, 1:-1]
            * padded[1:-1, :-2]
            * padded[1:-1, 2:]
        )
        boundary = remaining - eroded
        dist[boundary > 0] = step
        remaining = eroded
        # Safety cap to avoid runaway loops on large masks
        if step > 500:
            dist[remaining > 0] = step + 1
            break

    return dist


class TransitionBlender:
    """Creates transition zones and blends region reveals.

    Parameters
    ----------
    config : TransitionConfig
        Transition / feathering parameters.
    """

    def __init__(self, config: TransitionConfig) -> None:
        self.config = config
        self.transition_width = max(config.transition_width, 1)
        self.blend_smoothness = config.blend_smoothness
        self.feather_edges = config.feather_edges
        self._cached_blend_maps: Dict[int, np.ndarray] = {}
        self._blend_maps_computed: bool = False

        if not HAS_CV2:
            logger.info(
                "OpenCV not available – using NumPy fallback for distance "
                "transforms and blurring.  Quality may be reduced."
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_transition_zones(
        self, regions: List[RegionInfo]
    ) -> Dict[int, np.ndarray]:
        """Compute per-region boundary blend maps.

        For each region, the blend map is ``1.0`` in the interior and
        fades to ``0.0`` at the boundary over ``transition_width``
        pixels, producing a feathered edge.

        Parameters
        ----------
        regions : List[RegionInfo]
            Classified image regions.

        Returns
        -------
        dict
            Mapping ``region_id → blend_map`` (float ``(H, W)``).
        """
        blend_maps: Dict[int, np.ndarray] = {}

        for region in regions:
            try:
                blend_map = self._compute_blend_map(region)
                blend_maps[region.region_id] = blend_map
            except Exception:
                logger.exception(
                    "Failed to create transition zone for region %d; "
                    "using hard mask.",
                    region.region_id,
                )
                blend_maps[region.region_id] = region.mask.astype(np.float64)

        return blend_maps

    def blend_region_reveals(
        self,
        region_reveals: Dict[int, np.ndarray],
        regions: List[RegionInfo],
    ) -> np.ndarray:
        """Composite per-region reveals into a single blended mask.

        Overlapping region boundaries are feathered and weighted so that
        the composite has smooth, artifact-free transitions.

        Parameters
        ----------
        region_reveals : dict
            Mapping ``region_id → reveal_mask`` (float ``(H, W)``).
        regions : List[RegionInfo]
            Full list of classified regions.

        Returns
        -------
        np.ndarray
            Blended composite reveal mask, shape ``(H, W)``, float in
            ``[0, 1]``.
        """
        if not regions:
            logger.warning("No regions provided; returning empty composite.")
            return np.zeros((1, 1), dtype=np.float64)

        # Infer canvas size from the first region mask
        h, w = regions[0].mask.shape[:2]
        composite = np.zeros((h, w), dtype=np.float64)
        weight_sum = np.zeros((h, w), dtype=np.float64)

        # Use cached blend maps (computed once, reused every frame)
        if not self._blend_maps_computed:
            self._cached_blend_maps = self.create_transition_zones(regions)
            self._blend_maps_computed = True
        blend_maps = self._cached_blend_maps

        for region in regions:
            rid = region.region_id
            reveal = region_reveals.get(rid)
            if reveal is None:
                continue

            blend_weight = blend_maps.get(rid)
            if blend_weight is None:
                blend_weight = region.mask.astype(np.float64)

            # Weighted accumulation
            weighted_reveal = reveal * blend_weight
            composite += weighted_reveal
            weight_sum += blend_weight

        # Normalise where weights overlap
        nonzero = weight_sum > 1e-8
        composite[nonzero] /= weight_sum[nonzero]

        # Final smoothing pass for overall consistency
        composite = self._smooth_composite(composite)

        return np.clip(composite, 0.0, 1.0)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _compute_blend_map(self, region: RegionInfo) -> np.ndarray:
        """Build a feathered blend map for a single region.

        Parameters
        ----------
        region : RegionInfo
            Region whose mask defines the domain.

        Returns
        -------
        np.ndarray
            Float ``(H, W)`` blend map in ``[0, 1]``.
        """
        mask_uint8 = region.mask.astype(np.uint8) * 255

        # Distance from interior pixels to the nearest boundary
        if HAS_CV2:
            dist = cv2.distanceTransform(
                mask_uint8, cv2.DIST_L2, cv2.DIST_MASK_PRECISE
            ).astype(np.float64)
        else:
            dist = _distance_transform_fallback(mask_uint8)

        if not self.feather_edges:
            # Hard mask – no feathering
            return (dist > 0).astype(np.float64)

        # Normalise distance to [0, 1] over the transition width
        blend = np.clip(dist / max(self.transition_width, 1), 0.0, 1.0)

        # Apply smoothness curve (power mapping)
        if self.blend_smoothness > 0:
            blend = np.power(blend, 1.0 / max(self.blend_smoothness, 0.01))

        # Optional Gaussian smoothing of the blend map itself
        kernel_size = self.transition_width * 2 + 1
        if HAS_CV2:
            blend = cv2.GaussianBlur(
                blend, (kernel_size, kernel_size), 0
            ).astype(np.float64)
        else:
            blend = _gaussian_blur_fallback(blend, kernel_size)

        # Re-mask to ensure no bleed outside the region
        blend[~region.mask] = 0.0
        return np.clip(blend, 0.0, 1.0)

    def _smooth_composite(self, composite: np.ndarray) -> np.ndarray:
        """Apply a light global smoothing pass to the composite mask.

        Parameters
        ----------
        composite : np.ndarray
            Raw blended composite ``(H, W)``.

        Returns
        -------
        np.ndarray
            Smoothed composite of the same shape.
        """
        kernel_size = max(3, int(self.blend_smoothness * 5)) | 1  # odd

        if HAS_CV2:
            return cv2.GaussianBlur(
                composite, (kernel_size, kernel_size), 0
            ).astype(np.float64)

        return _gaussian_blur_fallback(composite, kernel_size)
