"""
Structure Tensor Analyzer
=========================
Computes per-pixel gradient orientation and coherence using eigenanalysis
of the structure tensor.  This drives contour-aware stroke direction so
strokes follow the natural flow of the artwork (hair, skin contours, etc.).

Theory
------
For each pixel the structure tensor **J** is the 2×2 matrix built from
image gradients *Ix*, *Iy*:

    J = | Jxx  Jxy |     where  Jxx = G_σ(Ix²)
        | Jxy  Jyy |            Jyy = G_σ(Iy²)
                                 Jxy = G_σ(Ix·Iy)

G_σ denotes Gaussian smoothing (integration window).

The dominant orientation is:
    θ = 0.5 · arctan2(2·Jxy, Jxx − Jyy)

Coherence (anisotropy) measures how strongly oriented a region is:
    C = (λ₁ − λ₂) / (λ₁ + λ₂ + ε)

where λ₁ ≥ λ₂ are eigenvalues of **J**.
"""

from __future__ import annotations

import logging
from typing import Dict, Optional, Tuple

import cv2
import numpy as np
from scipy.ndimage import gaussian_filter

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional GPU acceleration via CuPy
# ---------------------------------------------------------------------------
try:
    import cupy as cp
    from cupyx.scipy.ndimage import gaussian_filter as gpu_gaussian_filter

    _GPU_AVAILABLE = True
    logger.debug("CuPy detected – GPU acceleration enabled for structure tensor.")
except ImportError:
    _GPU_AVAILABLE = False


class StructureTensorAnalyzer:
    """Compute the structure-tensor orientation and coherence fields.

    Parameters
    ----------
    sigma_gradient : float
        Gaussian pre-smoothing applied before computing Sobel gradients.
    sigma_tensor : float
        Gaussian integration window applied to the tensor components
        (Jxx, Jyy, Jxy).  Larger values produce smoother orientation fields.
    use_gpu : bool
        If *True* **and** CuPy is installed, computation runs on the GPU.
        Falls back to CPU (NumPy) transparently when CuPy is unavailable.
    """

    def __init__(
        self,
        sigma_gradient: float = 1.0,
        sigma_tensor: float = 3.0,
        use_gpu: bool = False,
    ) -> None:
        self.sigma_gradient = sigma_gradient
        self.sigma_tensor = sigma_tensor
        self.use_gpu = use_gpu and _GPU_AVAILABLE

        # Cached results -------------------------------------------------
        self._orientation: Optional[np.ndarray] = None
        self._coherence: Optional[np.ndarray] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(
        self, gray_image: np.ndarray
    ) -> Dict[str, np.ndarray]:
        """Run the full structure-tensor analysis.

        Parameters
        ----------
        gray_image : np.ndarray
            Single-channel uint8 or float image.  If the image has three
            channels it is automatically converted to grayscale.

        Returns
        -------
        dict
            ``orientation`` – angle map in radians (−π/2 … π/2).
            ``coherence``   – anisotropy map in [0, 1].
        """
        gray = self._ensure_grayscale(gray_image)
        gray_f = gray.astype(np.float64)

        if self.use_gpu:
            orientation, coherence = self._analyze_gpu(gray_f)
        else:
            orientation, coherence = self._analyze_cpu(gray_f)

        self._orientation = orientation
        self._coherence = coherence

        return {"orientation": orientation, "coherence": coherence}

    def get_orientation(self) -> Optional[np.ndarray]:
        """Return the cached orientation map, or *None* if not yet computed."""
        return self._orientation

    def get_coherence(self) -> Optional[np.ndarray]:
        """Return the cached coherence map, or *None* if not yet computed."""
        return self._coherence

    # ------------------------------------------------------------------
    # CPU implementation
    # ------------------------------------------------------------------

    def _analyze_cpu(
        self, gray_f: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Structure-tensor computation on CPU (NumPy / SciPy)."""
        logger.debug("Computing structure tensor on CPU …")

        # Optional pre-smoothing
        if self.sigma_gradient > 0:
            smoothed = gaussian_filter(gray_f, sigma=self.sigma_gradient)
        else:
            smoothed = gray_f

        # Sobel gradients
        Ix = cv2.Sobel(smoothed, cv2.CV_64F, 1, 0, ksize=3)
        Iy = cv2.Sobel(smoothed, cv2.CV_64F, 0, 1, ksize=3)

        # Tensor components (windowed auto-correlation)
        Jxx = gaussian_filter(Ix * Ix, sigma=self.sigma_tensor)
        Jyy = gaussian_filter(Iy * Iy, sigma=self.sigma_tensor)
        Jxy = gaussian_filter(Ix * Iy, sigma=self.sigma_tensor)

        # Orientation
        orientation = 0.5 * np.arctan2(2.0 * Jxy, Jxx - Jyy + 1e-8)

        # Coherence (anisotropy)
        coherence = self._compute_coherence(Jxx, Jyy, Jxy)

        return orientation, coherence

    # ------------------------------------------------------------------
    # GPU implementation
    # ------------------------------------------------------------------

    def _analyze_gpu(
        self, gray_f: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Structure-tensor computation on GPU (CuPy)."""
        logger.debug("Computing structure tensor on GPU …")

        try:
            gray_gpu = cp.asarray(gray_f)

            if self.sigma_gradient > 0:
                smoothed = gpu_gaussian_filter(gray_gpu, sigma=self.sigma_gradient)
            else:
                smoothed = gray_gpu

            # CuPy does not wrap cv2.Sobel – use finite-difference kernels
            sobel_x = cp.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=cp.float64)
            sobel_y = cp.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]], dtype=cp.float64)

            from cupyx.scipy.signal import fftconvolve

            Ix = fftconvolve(smoothed, sobel_x[cp.newaxis, :, :] if smoothed.ndim == 3 else sobel_x, mode="same")
            Iy = fftconvolve(smoothed, sobel_y[cp.newaxis, :, :] if smoothed.ndim == 3 else sobel_y, mode="same")

            Jxx = gpu_gaussian_filter(Ix * Ix, sigma=self.sigma_tensor)
            Jyy = gpu_gaussian_filter(Iy * Iy, sigma=self.sigma_tensor)
            Jxy = gpu_gaussian_filter(Ix * Iy, sigma=self.sigma_tensor)

            orientation = 0.5 * cp.arctan2(2.0 * Jxy, Jxx - Jyy + 1e-8)

            # Coherence
            trace = Jxx + Jyy + 1e-8
            diff = Jxx - Jyy
            discriminant = cp.sqrt(diff ** 2 + 4.0 * Jxy ** 2)
            lambda1 = 0.5 * (trace + discriminant)
            lambda2 = 0.5 * (trace - discriminant)
            coherence = (lambda1 - lambda2) / (lambda1 + lambda2 + 1e-8)

            return cp.asnumpy(orientation), cp.asnumpy(coherence)

        except Exception as exc:
            logger.warning("GPU structure-tensor failed (%s). Falling back to CPU.", exc)
            return self._analyze_cpu(gray_f)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_coherence(
        Jxx: np.ndarray, Jyy: np.ndarray, Jxy: np.ndarray
    ) -> np.ndarray:
        """Compute coherence (anisotropy) from tensor components."""
        trace = Jxx + Jyy + 1e-8
        diff = Jxx - Jyy
        discriminant = np.sqrt(diff ** 2 + 4.0 * Jxy ** 2)
        lambda1 = 0.5 * (trace + discriminant)
        lambda2 = 0.5 * (trace - discriminant)
        coherence = (lambda1 - lambda2) / (lambda1 + lambda2 + 1e-8)
        return np.clip(coherence, 0.0, 1.0)

    @staticmethod
    def _ensure_grayscale(image: np.ndarray) -> np.ndarray:
        """Convert to single-channel uint8 if necessary."""
        if image is None or image.size == 0:
            raise ValueError("Input image is empty or None.")
        if image.ndim == 3:
            if image.shape[2] == 4:
                image = cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
            elif image.shape[2] == 3:
                image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return image
