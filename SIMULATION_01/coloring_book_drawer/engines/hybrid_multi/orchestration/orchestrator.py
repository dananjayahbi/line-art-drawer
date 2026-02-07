"""
Multi-Strategy Orchestrator
===============================
Core orchestrator for Engine 3F.  Dispatches lightweight *internal*
strategy renderers for each classified region — no external sub-engine
imports are used, avoiding circular dependencies.

Four strategies are implemented inline:
    * GRADIENT_REVEAL  – radial/directional gradient from centroid
    * ZONE_PROGRESSIVE – distance-band reveal (inner → outer)
    * BRUSH_SIMULATION – directional scan-line brush strokes
    * PIXEL_REVEAL     – random/ordered pixel-by-pixel reveal
"""

from __future__ import annotations

import logging
from typing import Dict, List

import numpy as np

from ..config import HybridMultiConfig, StrategyType
from ..classification.classifier import RegionInfo

logger = logging.getLogger(__name__)


class MultiStrategyOrchestrator:
    """Generates per-region reveal masks using lightweight strategy renderers.

    Parameters
    ----------
    image : np.ndarray
        Grayscale source image, shape ``(H, W)``, dtype ``uint8`` or
        ``float64``.
    regions : List[RegionInfo]
        Classified image regions with assigned strategies.
    config : HybridMultiConfig
        Master configuration for the hybrid engine.
    """

    def __init__(
        self,
        image: np.ndarray,
        regions: List[RegionInfo],
        config: HybridMultiConfig,
    ) -> None:
        if image.ndim != 2:
            raise ValueError(
                f"Expected 2-D grayscale image, got shape {image.shape}"
            )
        self.image = image.astype(np.float64) / 255.0 if image.dtype == np.uint8 else image.astype(np.float64)
        self.height, self.width = image.shape[:2]
        self.regions = regions
        self.config = config

        # Map strategy enum → internal renderer
        self._strategy_dispatch: Dict[StrategyType, callable] = {
            StrategyType.GRADIENT_REVEAL: self._gradient_reveal_for_region,
            StrategyType.ZONE_PROGRESSIVE: self._zone_progressive_for_region,
            StrategyType.BRUSH_SIMULATION: self._brush_simulation_for_region,
            StrategyType.PIXEL_REVEAL: self._pixel_reveal_for_region,
        }

        # Pre-compute coordinate grids (shared by several strategies)
        self._yy, self._xx = np.mgrid[0:self.height, 0:self.width]

        # Stable RNG for reproducible reveals
        self._rng = np.random.RandomState(42)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_region_reveals(
        self, progress: float
    ) -> Dict[int, np.ndarray]:
        """Generate reveal masks for every region at *progress* ∈ [0, 1].

        Parameters
        ----------
        progress : float
            Global animation progress, clamped to ``[0.0, 1.0]``.

        Returns
        -------
        dict
            Mapping ``region_id → reveal_mask`` where each mask is a
            float array of shape ``(H, W)`` with values in ``[0, 1]``.
        """
        progress = float(np.clip(progress, 0.0, 1.0))
        reveals: Dict[int, np.ndarray] = {}

        for region in self.regions:
            strategy = region.assigned_strategy
            if strategy is None:
                strategy = StrategyType.GRADIENT_REVEAL
                logger.debug(
                    "Region %d has no assigned strategy; defaulting to "
                    "GRADIENT_REVEAL.",
                    region.region_id,
                )

            renderer = self._strategy_dispatch.get(strategy)
            if renderer is None:
                logger.warning(
                    "Unknown strategy '%s' for region %d; falling back to "
                    "GRADIENT_REVEAL.",
                    strategy,
                    region.region_id,
                )
                renderer = self._gradient_reveal_for_region

            try:
                mask = renderer(region, progress)
                # Ensure valid output shape and range
                mask = np.clip(mask, 0.0, 1.0)
                reveals[region.region_id] = mask
            except Exception:
                logger.exception(
                    "Strategy '%s' failed for region %d; returning empty "
                    "reveal.",
                    strategy,
                    region.region_id,
                )
                reveals[region.region_id] = np.zeros(
                    (self.height, self.width), dtype=np.float64
                )

        return reveals

    # ------------------------------------------------------------------
    # Internal lightweight strategy renderers
    # ------------------------------------------------------------------

    def _gradient_reveal_for_region(
        self, region: RegionInfo, progress: float
    ) -> np.ndarray:
        """Radial gradient reveal from centroid outward.

        Pixels closer to the centroid are revealed first.  The reveal
        front expands as *progress* increases from 0 → 1.

        Returns
        -------
        np.ndarray
            Float mask ``(H, W)`` in ``[0, 1]``.
        """
        cy, cx = region.centroid

        # Distance from centroid for every pixel
        dist = np.sqrt(
            (self._yy - cy).astype(np.float64) ** 2
            + (self._xx - cx).astype(np.float64) ** 2
        )

        # Normalise distance within the region's mask to [0, 1]
        region_pixels = dist[region.mask]
        if region_pixels.size == 0:
            return np.zeros((self.height, self.width), dtype=np.float64)

        max_dist = region_pixels.max()
        if max_dist < 1e-6:
            max_dist = 1.0
        norm_dist = dist / max_dist

        # Threshold: pixels with normalised distance ≤ progress are revealed
        reveal = np.where(norm_dist <= progress, 1.0, 0.0)

        # Confine to region
        reveal[~region.mask] = 0.0
        return reveal

    def _zone_progressive_for_region(
        self, region: RegionInfo, progress: float
    ) -> np.ndarray:
        """Zone-by-zone progressive reveal using distance bands.

        The region is split into concentric bands around the centroid.
        Inner zones are revealed first (focal → edges → body → details).

        Returns
        -------
        np.ndarray
            Float mask ``(H, W)`` in ``[0, 1]``.
        """
        num_zones = 5
        cy, cx = region.centroid

        dist = np.sqrt(
            (self._yy - cy).astype(np.float64) ** 2
            + (self._xx - cx).astype(np.float64) ** 2
        )

        region_pixels = dist[region.mask]
        if region_pixels.size == 0:
            return np.zeros((self.height, self.width), dtype=np.float64)

        max_dist = region_pixels.max()
        if max_dist < 1e-6:
            max_dist = 1.0

        norm_dist = dist / max_dist

        # Determine which zones are fully / partially revealed
        # progress maps linearly across zones
        reveal = np.zeros((self.height, self.width), dtype=np.float64)

        for zone_idx in range(num_zones):
            zone_lo = zone_idx / num_zones
            zone_hi = (zone_idx + 1) / num_zones

            # Map global progress to per-zone visibility
            zone_progress = np.clip(
                (progress - zone_lo) / (1.0 / num_zones), 0.0, 1.0
            )
            if zone_progress <= 0.0:
                continue

            band = (norm_dist >= zone_lo) & (norm_dist < zone_hi)
            reveal[band] = zone_progress

        # Confine to region
        reveal[~region.mask] = 0.0
        return reveal

    def _brush_simulation_for_region(
        self, region: RegionInfo, progress: float
    ) -> np.ndarray:
        """Directional scan-line brush stroke simulation.

        Horizontal scan lines sweep across the region bounding box.  As
        *progress* advances, more scan lines (and more of each line) are
        filled in, mimicking a pencil stroke pass.

        Returns
        -------
        np.ndarray
            Float mask ``(H, W)`` in ``[0, 1]``.
        """
        reveal = np.zeros((self.height, self.width), dtype=np.float64)

        # Bounding box of the region mask
        rows, cols = np.where(region.mask)
        if rows.size == 0:
            return reveal

        y_min, y_max = int(rows.min()), int(rows.max())
        x_min, x_max = int(cols.min()), int(cols.max())

        total_rows = y_max - y_min + 1
        total_cols = x_max - x_min + 1

        if total_rows == 0 or total_cols == 0:
            return reveal

        # Number of scan-line rows revealed so far
        rows_revealed = int(np.ceil(progress * total_rows))

        for i in range(rows_revealed):
            y = y_min + i
            if y > y_max:
                break

            # Within this row, reveal columns left → right proportional
            # to progress.  For the *last* partially-revealed row, use
            # fractional column coverage.
            if i < rows_revealed - 1:
                col_frac = 1.0
            else:
                # Fractional leftover for the last row
                exact_rows = progress * total_rows
                col_frac = exact_rows - int(exact_rows)
                if col_frac < 1e-9:
                    col_frac = 1.0  # row fully revealed

            cols_revealed = int(np.ceil(col_frac * total_cols))
            x_end = min(x_min + cols_revealed, x_max + 1)

            reveal[y, x_min:x_end] = 1.0

        # Confine to region
        reveal[~region.mask] = 0.0
        return reveal

    def _pixel_reveal_for_region(
        self, region: RegionInfo, progress: float
    ) -> np.ndarray:
        """Simple random pixel-by-pixel reveal.

        A pre-shuffled order of region pixels is used so the reveal is
        deterministic for a given region.  *progress* controls what
        fraction of pixels are visible.

        Returns
        -------
        np.ndarray
            Float mask ``(H, W)`` in ``[0, 1]``.
        """
        reveal = np.zeros((self.height, self.width), dtype=np.float64)

        ys, xs = np.where(region.mask)
        if ys.size == 0:
            return reveal

        total_pixels = ys.size
        num_reveal = int(np.ceil(progress * total_pixels))
        num_reveal = min(num_reveal, total_pixels)

        # Deterministic shuffle per region (seed based on region_id)
        rng = np.random.RandomState(region.region_id)
        order = rng.permutation(total_pixels)

        selected = order[:num_reveal]
        reveal[ys[selected], xs[selected]] = 1.0

        return reveal
