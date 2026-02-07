"""
Multi-Scale Edge Detector
=========================
Two-tier edge detection that separates **fine** and **coarse** edges so
the engine can reveal major contours first and fill in details later.

Tiers
-----
* **Fine edges** (σ = 1.0, thresholds 0.05/0.15) – eyelashes, textures,
  fine detail lines.
* **Coarse edges** (σ = 2.0, thresholds 0.08/0.2) – silhouettes, major
  boundaries, structural contours.

The detector returns a dict:
    primary   – coarse edges (drawn in Phase 1)
    secondary – fine-only edges not already in *primary* (Phase 4+)
    combined  – union of both tiers
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import cv2
import numpy as np
from scipy.ndimage import gaussian_filter

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional scikit-image Canny (preferred for sub-pixel accuracy)
# ---------------------------------------------------------------------------
try:
    from skimage.feature import canny as skimage_canny

    _SKIMAGE_AVAILABLE = True
    logger.debug("scikit-image detected – using skimage.feature.canny.")
except ImportError:
    _SKIMAGE_AVAILABLE = False
    logger.debug("scikit-image not available – falling back to OpenCV Canny.")

# ---------------------------------------------------------------------------
# Optional GPU acceleration via CuPy
# ---------------------------------------------------------------------------
try:
    import cupy as cp

    _GPU_AVAILABLE = True
except ImportError:
    _GPU_AVAILABLE = False


class MultiScaleEdgeDetector:
    """Detect edges at two scales and classify them.

    Parameters
    ----------
    fine_sigma : float
        Gaussian sigma for the *fine* edge detection pass.
    fine_low : float
        Hysteresis low threshold for fine edges (fraction of max gradient).
    fine_high : float
        Hysteresis high threshold for fine edges.
    coarse_sigma : float
        Gaussian sigma for pre-blurring before *coarse* detection.
    coarse_low : float
        Hysteresis low threshold for coarse edges.
    coarse_high : float
        Hysteresis high threshold for coarse edges.
    use_gpu : bool
        Attempt GPU acceleration via CuPy for the Gaussian pre-blur.
    """

    # Default values taken directly from the design document
    DEFAULT_FINE_SIGMA = 1.0
    DEFAULT_FINE_LOW = 0.05
    DEFAULT_FINE_HIGH = 0.15
    DEFAULT_COARSE_SIGMA = 2.0
    DEFAULT_COARSE_LOW = 0.08
    DEFAULT_COARSE_HIGH = 0.2

    def __init__(
        self,
        fine_sigma: float = DEFAULT_FINE_SIGMA,
        fine_low: float = DEFAULT_FINE_LOW,
        fine_high: float = DEFAULT_FINE_HIGH,
        coarse_sigma: float = DEFAULT_COARSE_SIGMA,
        coarse_low: float = DEFAULT_COARSE_LOW,
        coarse_high: float = DEFAULT_COARSE_HIGH,
        use_gpu: bool = False,
    ) -> None:
        self.fine_sigma = fine_sigma
        self.fine_low = fine_low
        self.fine_high = fine_high
        self.coarse_sigma = coarse_sigma
        self.coarse_low = coarse_low
        self.coarse_high = coarse_high
        self.use_gpu = use_gpu and _GPU_AVAILABLE

        # Cached results
        self._result: Optional[Dict[str, np.ndarray]] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect(self, gray_image: np.ndarray) -> Dict[str, np.ndarray]:
        """Run multi-scale edge detection.

        Parameters
        ----------
        gray_image : np.ndarray
            Single-channel image (uint8 or float).  Multi-channel images
            are converted automatically.

        Returns
        -------
        dict
            ``primary``   – boolean mask of coarse edges.
            ``secondary`` – boolean mask of fine-only edges (fine ∧ ¬coarse).
            ``combined``  – boolean mask of all edges (fine ∨ coarse).
        """
        gray = self._ensure_grayscale(gray_image)

        # ---- fine edges -----------------------------------------------
        edges_fine = self._canny(
            gray,
            sigma=self.fine_sigma,
            low_threshold=self.fine_low,
            high_threshold=self.fine_high,
        )

        # ---- coarse edges (pre-blur then detect) ----------------------
        blurred = self._gaussian_blur(gray, sigma=self.coarse_sigma)
        edges_coarse = self._canny(
            blurred,
            sigma=self.coarse_sigma,
            low_threshold=self.coarse_low,
            high_threshold=self.coarse_high,
        )

        # ---- classify -------------------------------------------------
        primary = edges_coarse.astype(bool)
        secondary = edges_fine.astype(bool) & ~primary
        combined = edges_fine.astype(bool) | primary

        self._result = {
            "primary": primary,
            "secondary": secondary,
            "combined": combined,
        }
        return self._result

    def get_result(self) -> Optional[Dict[str, np.ndarray]]:
        """Return cached detection result, or *None*."""
        return self._result

    # ------------------------------------------------------------------
    # Canny wrappers
    # ------------------------------------------------------------------

    def _canny(
        self,
        gray: np.ndarray,
        sigma: float,
        low_threshold: float,
        high_threshold: float,
    ) -> np.ndarray:
        """Apply Canny edge detection, preferring scikit-image."""
        if _SKIMAGE_AVAILABLE:
            return self._canny_skimage(gray, sigma, low_threshold, high_threshold)
        return self._canny_opencv(gray, sigma, low_threshold, high_threshold)

    @staticmethod
    def _canny_skimage(
        gray: np.ndarray,
        sigma: float,
        low_threshold: float,
        high_threshold: float,
    ) -> np.ndarray:
        """scikit-image Canny (works with normalized thresholds)."""
        try:
            img = gray.astype(np.float64)
            if img.max() > 1.0:
                img = img / 255.0
            edges = skimage_canny(
                img,
                sigma=sigma,
                low_threshold=low_threshold,
                high_threshold=high_threshold,
            )
            return edges.astype(np.uint8) * 255
        except Exception as exc:
            logger.warning("skimage Canny failed (%s). Falling back to OpenCV.", exc)
            return MultiScaleEdgeDetector._canny_opencv(
                gray, sigma, low_threshold, high_threshold
            )

    @staticmethod
    def _canny_opencv(
        gray: np.ndarray,
        sigma: float,
        low_threshold: float,
        high_threshold: float,
    ) -> np.ndarray:
        """OpenCV Canny fallback (thresholds mapped to 0-255 range)."""
        if gray.dtype != np.uint8:
            gray_u8 = np.clip(gray, 0, 255).astype(np.uint8)
        else:
            gray_u8 = gray

        # Pre-smooth
        ksize = max(3, int(2 * round(sigma * 3) + 1))
        blurred = cv2.GaussianBlur(gray_u8, (ksize, ksize), sigma)

        # OpenCV Canny uses absolute thresholds on gradient magnitude
        lo = int(low_threshold * 255)
        hi = int(high_threshold * 255)
        edges = cv2.Canny(blurred, lo, hi)
        return edges

    # ------------------------------------------------------------------
    # Gaussian blur (GPU-aware)
    # ------------------------------------------------------------------

    def _gaussian_blur(self, image: np.ndarray, sigma: float) -> np.ndarray:
        """Gaussian blur with optional GPU acceleration."""
        if self.use_gpu:
            try:
                from cupyx.scipy.ndimage import gaussian_filter as gpu_gauss

                gpu_img = cp.asarray(image.astype(np.float64))
                blurred = gpu_gauss(gpu_img, sigma=sigma)
                result = cp.asnumpy(blurred)
                if image.dtype == np.uint8:
                    return np.clip(result, 0, 255).astype(np.uint8)
                return result
            except Exception as exc:
                logger.warning("GPU blur failed (%s). Using CPU.", exc)

        blurred = gaussian_filter(image.astype(np.float64), sigma=sigma)
        if image.dtype == np.uint8:
            return np.clip(blurred, 0, 255).astype(np.uint8)
        return blurred

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _ensure_grayscale(image: np.ndarray) -> np.ndarray:
        """Convert to single-channel if necessary."""
        if image is None or image.size == 0:
            raise ValueError("Input image is empty or None.")
        if image.ndim == 3:
            if image.shape[2] == 4:
                return cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
            elif image.shape[2] == 3:
                return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return image
