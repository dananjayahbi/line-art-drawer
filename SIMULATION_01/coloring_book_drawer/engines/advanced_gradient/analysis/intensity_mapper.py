"""
Continuous Intensity Mapper
============================
Maps image intensity to continuous reveal-priority and stroke-density
values, replacing the hard-banded thresholds from Engine 2.

The mapping pipeline:

1. **Normalize** the grayscale image to [0, 1] and **invert** so that
   dark pixels (heavy pencil) map to high intensity values.
2. Apply **perceptual gamma correction** (power 0.45) so that perceived
   mid-tones are spread more evenly across the value range.
3. Expose three query interfaces:
   - ``get_reveal_priority(y, x)`` – light areas → high priority (drawn
     first).
   - ``get_stroke_density(y, x)`` – 1 / 2 / 3 passes depending on
     darkness.
   - ``get_continuous_map()`` – the full perceptual intensity array.
"""

from __future__ import annotations

import logging
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional GPU acceleration via CuPy
# ---------------------------------------------------------------------------
try:
    import cupy as cp

    _GPU_AVAILABLE = True
    logger.debug("CuPy detected – GPU acceleration available for intensity mapping.")
except ImportError:
    _GPU_AVAILABLE = False


class ContinuousIntensityMapper:
    """Perceptual intensity mapper for progressive reveal ordering.

    Parameters
    ----------
    gamma : float
        Exponent for perceptual gamma correction.  The default (0.45)
        roughly linearises perceived brightness on most displays.
    use_gpu : bool
        If *True* **and** CuPy is available the mapping is computed on
        the GPU.  Falls back silently to NumPy otherwise.
    """

    # Stroke-density bin edges (applied to the *intensity_map*, not
    # the perceptual map).
    _DENSITY_LOW = 0.3
    _DENSITY_MID = 0.6

    def __init__(self, gamma: float = 0.45, use_gpu: bool = False) -> None:
        self.gamma = gamma
        self.use_gpu = use_gpu and _GPU_AVAILABLE

        # Internal maps (set after ``compute`` is called)
        self._intensity_map: Optional[np.ndarray] = None
        self._perceptual_map: Optional[np.ndarray] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def compute(self, gray_image: np.ndarray) -> None:
        """Build the intensity and perceptual maps from *gray_image*.

        Parameters
        ----------
        gray_image : np.ndarray
            Single-channel uint8 or float image.  Multi-channel images
            are auto-converted to grayscale.
        """
        gray = self._ensure_grayscale(gray_image)

        if self.use_gpu:
            try:
                self._compute_gpu(gray)
                return
            except Exception as exc:
                logger.warning("GPU intensity mapping failed (%s). Using CPU.", exc)

        self._compute_cpu(gray)

    # -- point queries --------------------------------------------------

    def get_reveal_priority(self, y: int, x: int) -> float:
        """Return reveal priority for pixel *(y, x)*.

        Higher values mean the pixel should be revealed **earlier**.
        Light areas (low intensity) get the highest priority so the
        drawing starts with gentle, light strokes.

        Returns
        -------
        float in [0, 1]
        """
        self._require_computed()
        return float(1.0 - self._intensity_map[y, x])

    def get_stroke_density(self, y: int, x: int) -> int:
        """Number of drawing passes required at pixel *(y, x)*.

        Returns
        -------
        int
            1 – single pass (light), 2 – double pass (mid-tone),
            3 – triple pass (deep shadow).
        """
        self._require_computed()
        intensity = float(self._intensity_map[y, x])
        if intensity < self._DENSITY_LOW:
            return 1
        if intensity < self._DENSITY_MID:
            return 2
        return 3

    # -- bulk access ----------------------------------------------------

    def get_continuous_map(self) -> np.ndarray:
        """Return the full perceptual intensity map (float64, [0, 1]).

        Raises
        ------
        RuntimeError
            If ``compute`` has not been called yet.
        """
        self._require_computed()
        return self._perceptual_map.copy()

    def get_intensity_map(self) -> np.ndarray:
        """Return the raw (non-gamma-corrected) intensity map."""
        self._require_computed()
        return self._intensity_map.copy()

    def get_reveal_priority_map(self) -> np.ndarray:
        """Return a full-image reveal-priority map (float64, [0, 1])."""
        self._require_computed()
        return 1.0 - self._intensity_map

    def get_stroke_density_map(self) -> np.ndarray:
        """Return a full-image stroke-density map (int, values 1/2/3)."""
        self._require_computed()
        density = np.ones_like(self._intensity_map, dtype=np.int32)
        density[self._intensity_map >= self._DENSITY_LOW] = 2
        density[self._intensity_map >= self._DENSITY_MID] = 3
        return density

    # ------------------------------------------------------------------
    # CPU implementation
    # ------------------------------------------------------------------

    def _compute_cpu(self, gray: np.ndarray) -> None:
        logger.debug("Computing intensity map on CPU …")
        normalized = gray.astype(np.float64) / 255.0
        # Invert: dark pencil → high intensity
        self._intensity_map = np.clip(1.0 - normalized, 0.0, 1.0)
        # Perceptual gamma correction
        self._perceptual_map = np.power(self._intensity_map, self.gamma)

    # ------------------------------------------------------------------
    # GPU implementation
    # ------------------------------------------------------------------

    def _compute_gpu(self, gray: np.ndarray) -> None:
        logger.debug("Computing intensity map on GPU …")
        g = cp.asarray(gray.astype(np.float64)) / 255.0
        intensity = cp.clip(1.0 - g, 0.0, 1.0)
        perceptual = cp.power(intensity, self.gamma)
        self._intensity_map = cp.asnumpy(intensity)
        self._perceptual_map = cp.asnumpy(perceptual)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _require_computed(self) -> None:
        """Raise if ``compute`` hasn't been called."""
        if self._intensity_map is None:
            raise RuntimeError(
                "Intensity map not computed yet.  Call compute(gray_image) first."
            )

    @staticmethod
    def _ensure_grayscale(image: np.ndarray) -> np.ndarray:
        if image is None or image.size == 0:
            raise ValueError("Input image is empty or None.")
        if image.ndim == 3:
            if image.shape[2] == 4:
                return cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
            elif image.shape[2] == 3:
                return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return image
