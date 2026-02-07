"""
GPU Accelerator with CPU Fallback
===================================
Provides GPU-accelerated operations when CuPy/CUDA is available,
with transparent fallback to CPU (NumPy/SciPy).
"""

import numpy as np


# Try to import CuPy for GPU acceleration
_HAS_GPU = False
_GPU_INFO = "No GPU acceleration"
_cp = None

try:
    import cupy as _cp_module
    _cp = _cp_module
    from cupyx.scipy import ndimage as _cp_ndimage

    try:
        device = _cp.cuda.Device(0)
        cuda_version = _cp.cuda.runtime.runtimeGetVersion()
        cuda_major = cuda_version // 1000
        cuda_minor = (cuda_version % 1000) // 10

        test_arr = _cp.array([1, 2, 3])
        _ = _cp.asnumpy(test_arr)

        _HAS_GPU = True
        _GPU_INFO = f"GPU: {device}, CUDA {cuda_major}.{cuda_minor}"
    except Exception:
        _HAS_GPU = False
        _cp = None
except ImportError:
    _HAS_GPU = False
    _cp = None


class GPUAccelerator:
    """
    GPU-accelerated processing with transparent CPU fallback.
    Detects available backend and uses the best option.
    """

    def __init__(self, use_gpu: bool = True):
        self.use_gpu = use_gpu and _HAS_GPU
        self.backend = 'gpu' if self.use_gpu else 'cpu'
        self.cp = _cp if self.use_gpu else None

    @property
    def is_gpu_available(self) -> bool:
        return _HAS_GPU

    @property
    def gpu_info(self) -> str:
        return _GPU_INFO if _HAS_GPU else "CPU only"

    def to_device(self, array: np.ndarray):
        """Move numpy array to GPU if available."""
        if self.use_gpu and self.cp is not None:
            return self.cp.asarray(array)
        return array

    def to_host(self, array) -> np.ndarray:
        """Move array back to CPU if on GPU."""
        if self.use_gpu and self.cp is not None and hasattr(array, 'get'):
            return self.cp.asnumpy(array)
        return np.asarray(array)

    def gaussian_filter(self, image: np.ndarray, sigma: float) -> np.ndarray:
        """GPU-accelerated Gaussian filter with CPU fallback."""
        if self.use_gpu and self.cp is not None:
            try:
                from cupyx.scipy.ndimage import gaussian_filter as gpu_gaussian
                img_gpu = self.cp.asarray(image.astype(np.float32))
                result_gpu = gpu_gaussian(img_gpu, sigma=sigma)
                return self.cp.asnumpy(result_gpu)
            except Exception:
                pass

        # CPU fallback
        try:
            from scipy.ndimage import gaussian_filter
            return gaussian_filter(image.astype(np.float32), sigma=sigma)
        except ImportError:
            import cv2
            ksize = int(6 * sigma + 1)
            if ksize % 2 == 0:
                ksize += 1
            return cv2.GaussianBlur(image.astype(np.float32), (ksize, ksize), sigma)

    def sobel(self, image: np.ndarray, axis: int) -> np.ndarray:
        """GPU-accelerated Sobel filter with CPU fallback."""
        import cv2

        if axis == 0:
            return cv2.Sobel(image, cv2.CV_64F, 0, 1, ksize=3)
        else:
            return cv2.Sobel(image, cv2.CV_64F, 1, 0, ksize=3)
