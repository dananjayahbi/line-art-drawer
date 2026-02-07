"""
Region Segmenter
================
Superpixel-based region segmentation using the SLIC algorithm.  Each
resulting region is classified into one of five types that determine
the stroke strategy used by the rendering pipeline.

Region Types
------------
=============  =============================================  ==================
Type           Heuristic                                      Stroke Strategy
=============  =============================================  ==================
highlight      mean > 240 **and** std < threshold             Minimal, quick
gradient       smooth tone, low std                           Soft reveal paths
textured       high std (patterns)                            Direction-following
shadow         mean < 80                                      Dense multi-pass
edge_border    high mean gradient magnitude                   Skeleton-based
=============  =============================================  ==================
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional scikit-image (preferred for SLIC + regionprops)
# ---------------------------------------------------------------------------
try:
    from skimage.segmentation import slic as skimage_slic
    from skimage.measure import regionprops, label as skimage_label

    _SKIMAGE_AVAILABLE = True
    logger.debug("scikit-image detected – using skimage SLIC segmentation.")
except ImportError:
    _SKIMAGE_AVAILABLE = False
    logger.debug("scikit-image not available – falling back to OpenCV superpixels.")

# ---------------------------------------------------------------------------
# Optional GPU acceleration via CuPy (used for gradient magnitude only)
# ---------------------------------------------------------------------------
try:
    import cupy as cp

    _GPU_AVAILABLE = True
except ImportError:
    _GPU_AVAILABLE = False


# ---------------------------------------------------------------------------
# Classification thresholds (tuned for pencil-art scans)
# ---------------------------------------------------------------------------
_HIGHLIGHT_MEAN_MIN = 240
_HIGHLIGHT_STD_MAX = 15.0
_SHADOW_MEAN_MAX = 80
_TEXTURED_STD_MIN = 30.0
_EDGE_GRADIENT_MIN = 40.0  # mean gradient magnitude threshold


class RegionSegmenter:
    """Segment an image into classified superpixel regions.

    Parameters
    ----------
    n_segments : int or None
        Target number of SLIC superpixels.  When *None* the count is
        estimated automatically from the image area.
    compactness : float
        SLIC compactness (higher → more square-shaped superpixels).
    sigma : float
        Gaussian smoothing applied before segmentation.
    use_gpu : bool
        Use CuPy for gradient computation when available.
    """

    def __init__(
        self,
        n_segments: Optional[int] = None,
        compactness: float = 10.0,
        sigma: float = 1.0,
        use_gpu: bool = False,
    ) -> None:
        self.n_segments = n_segments
        self.compactness = compactness
        self.sigma = sigma
        self.use_gpu = use_gpu and _GPU_AVAILABLE

        # Cached results
        self._labels: Optional[np.ndarray] = None
        self._regions: Optional[Dict[int, Dict[str, Any]]] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def segment(self, gray_image: np.ndarray) -> Dict[int, Dict[str, Any]]:
        """Run SLIC segmentation and classify every region.

        Parameters
        ----------
        gray_image : np.ndarray
            Single-channel image (uint8).  Multi-channel input is auto-converted.

        Returns
        -------
        dict
            Mapping *label → region_info* where each *region_info* contains:
            ``type`` (str), ``mask`` (ndarray bool), ``bounds`` (tuple),
            ``centroid`` (tuple), ``mean_intensity`` (float),
            ``std_intensity`` (float).
        """
        gray = self._ensure_grayscale(gray_image)
        n_seg = self.n_segments or self._estimate_segment_count(gray)

        labels = self._slic_segment(gray, n_seg)
        self._labels = labels

        gradient_mag = self._gradient_magnitude(gray)

        regions = self._classify_regions(gray, labels, gradient_mag)
        self._regions = regions
        return regions

    def get_labels(self) -> Optional[np.ndarray]:
        """Return the cached label map (H×W int array), or *None*."""
        return self._labels

    def get_regions(self) -> Optional[Dict[int, Dict[str, Any]]]:
        """Return the cached region dict, or *None*."""
        return self._regions

    # ------------------------------------------------------------------
    # SLIC segmentation
    # ------------------------------------------------------------------

    def _slic_segment(self, gray: np.ndarray, n_segments: int) -> np.ndarray:
        """Produce a label map using SLIC superpixels."""
        if _SKIMAGE_AVAILABLE:
            return self._slic_skimage(gray, n_segments)
        return self._slic_opencv(gray, n_segments)

    def _slic_skimage(self, gray: np.ndarray, n_segments: int) -> np.ndarray:
        """SLIC via scikit-image."""
        try:
            # skimage SLIC expects float [0,1] or uint8 multichannel
            img = gray.astype(np.float64) / 255.0 if gray.dtype == np.uint8 else gray
            labels = skimage_slic(
                img,
                n_segments=n_segments,
                compactness=self.compactness,
                sigma=self.sigma,
                channel_axis=None,  # single-channel
                start_label=0,
            )
            return labels.astype(np.int32)
        except Exception as exc:
            logger.warning("skimage SLIC failed (%s). Falling back to OpenCV.", exc)
            return self._slic_opencv(gray, n_segments)

    def _slic_opencv(self, gray: np.ndarray, n_segments: int) -> np.ndarray:
        """Fallback SLIC using OpenCV's ``ximgproc`` (if available) or a
        simple grid-based approximation."""
        try:
            slic = cv2.ximgproc.createSuperpixelSLIC(
                gray, cv2.ximgproc.SLIC, region_size=max(4, int(np.sqrt(gray.size / n_segments))),
                ruler=self.compactness,
            )
            slic.iterate(10)
            return slic.getLabels().astype(np.int32)
        except AttributeError:
            logger.info("cv2.ximgproc unavailable – using grid-based segmentation.")
            return self._grid_segment(gray, n_segments)

    @staticmethod
    def _grid_segment(gray: np.ndarray, n_segments: int) -> np.ndarray:
        """Naïve grid-based segmentation (last-resort fallback)."""
        h, w = gray.shape[:2]
        cols = max(1, int(np.sqrt(n_segments * w / h)))
        rows = max(1, n_segments // cols)
        labels = np.zeros((h, w), dtype=np.int32)
        row_step = max(1, h // rows)
        col_step = max(1, w // cols)
        label_id = 0
        for r in range(0, h, row_step):
            for c in range(0, w, col_step):
                labels[r: r + row_step, c: c + col_step] = label_id
                label_id += 1
        return labels

    # ------------------------------------------------------------------
    # Region classification
    # ------------------------------------------------------------------

    def _classify_regions(
        self,
        gray: np.ndarray,
        labels: np.ndarray,
        gradient_mag: np.ndarray,
    ) -> Dict[int, Dict[str, Any]]:
        """Classify each superpixel region."""
        unique_labels = np.unique(labels)
        regions: Dict[int, Dict[str, Any]] = {}

        for lbl in unique_labels:
            mask = labels == lbl
            pixels = gray[mask].astype(np.float64)

            if pixels.size == 0:
                continue

            mean_val = float(np.mean(pixels))
            std_val = float(np.std(pixels))
            grad_vals = gradient_mag[mask].astype(np.float64)
            mean_grad = float(np.mean(grad_vals))

            region_type = self._classify_single(mean_val, std_val, mean_grad)

            # Bounding box & centroid
            ys, xs = np.where(mask)
            bounds = (int(ys.min()), int(xs.min()), int(ys.max()), int(xs.max()))
            centroid = (float(np.mean(ys)), float(np.mean(xs)))

            regions[int(lbl)] = {
                "type": region_type,
                "mask": mask,
                "bounds": bounds,
                "centroid": centroid,
                "mean_intensity": mean_val,
                "std_intensity": std_val,
                "mean_gradient": mean_grad,
            }

        return regions

    @staticmethod
    def _classify_single(
        mean_val: float, std_val: float, mean_grad: float
    ) -> str:
        """Return the region type string for one superpixel."""
        if mean_grad >= _EDGE_GRADIENT_MIN:
            return "edge_border"
        if mean_val > _HIGHLIGHT_MEAN_MIN and std_val < _HIGHLIGHT_STD_MAX:
            return "highlight"
        if mean_val < _SHADOW_MEAN_MAX:
            return "shadow"
        if std_val >= _TEXTURED_STD_MIN:
            return "textured"
        return "gradient"

    # ------------------------------------------------------------------
    # Gradient magnitude
    # ------------------------------------------------------------------

    def _gradient_magnitude(self, gray: np.ndarray) -> np.ndarray:
        """Compute per-pixel gradient magnitude (Sobel)."""
        if self.use_gpu:
            try:
                return self._gradient_magnitude_gpu(gray)
            except Exception as exc:
                logger.warning("GPU gradient failed (%s). Using CPU.", exc)

        gray_f = gray.astype(np.float64)
        gx = cv2.Sobel(gray_f, cv2.CV_64F, 1, 0, ksize=3)
        gy = cv2.Sobel(gray_f, cv2.CV_64F, 0, 1, ksize=3)
        return np.sqrt(gx ** 2 + gy ** 2)

    @staticmethod
    def _gradient_magnitude_gpu(gray: np.ndarray) -> np.ndarray:
        """GPU gradient magnitude via CuPy."""
        from cupyx.scipy.signal import fftconvolve

        g = cp.asarray(gray.astype(np.float64))
        sx = cp.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=cp.float64)
        sy = cp.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]], dtype=cp.float64)
        gx = fftconvolve(g, sx, mode="same")
        gy = fftconvolve(g, sy, mode="same")
        mag = cp.sqrt(gx ** 2 + gy ** 2)
        return cp.asnumpy(mag)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _estimate_segment_count(gray: np.ndarray) -> int:
        """Heuristic: ~1 superpixel per 30×30 block."""
        h, w = gray.shape[:2]
        count = max(50, (h * w) // (30 * 30))
        return min(count, 4000)

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
