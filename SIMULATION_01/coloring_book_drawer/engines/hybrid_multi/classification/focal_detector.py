"""
Focal Point Detector
======================
Detects visually important focal areas in the image using
saliency analysis and optional face detection.
"""

import numpy as np
from ..config import ClassificationConfig

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False


class FocalDetector:
    """Detects focal/important regions in an image."""
    
    def __init__(self, config: ClassificationConfig):
        self.config = config
        self.enabled = config.focal_detection
        
    def detect_focal_mask(self, gray: np.ndarray,
                           image_rgb: np.ndarray = None) -> np.ndarray:
        """
        Create a binary mask of focal/important areas.
        
        Combines:
        1. Spectral residual saliency
        2. Face detection (if available)
        3. Center-weighted prior
        
        Args:
            gray: (H, W) grayscale image
            image_rgb: (H, W, 3) RGB image (optional, for face detection)
            
        Returns:
            (H, W) boolean mask of focal areas
        """
        h, w = gray.shape
        
        if not self.enabled:
            return np.zeros((h, w), dtype=bool)
        
        focal_score = np.zeros((h, w), dtype=np.float32)
        
        # 1. Saliency-based detection
        saliency = self._compute_saliency(gray)
        focal_score += saliency * 0.6
        
        # 2. Face detection (if available and image_rgb provided)
        if image_rgb is not None:
            face_mask = self._detect_faces(gray)
            focal_score += face_mask.astype(np.float32) * 0.3
        
        # 3. Center-weighted prior (central regions are often focal)
        center_weight = self._center_prior(h, w)
        focal_score += center_weight * 0.1
        
        # Threshold to get focal mask
        threshold = np.percentile(focal_score[focal_score > 0], 75) if np.any(focal_score > 0) else 0.5
        focal_mask = focal_score > threshold
        
        return focal_mask
    
    def _compute_saliency(self, gray: np.ndarray) -> np.ndarray:
        """Compute spectral residual saliency map."""
        h, w = gray.shape
        
        # Resize for efficiency
        small_size = 64
        if HAS_CV2:
            small = cv2.resize(gray.astype(np.uint8), (small_size, small_size),
                              interpolation=cv2.INTER_AREA)
        else:
            # Simple downscale
            row_idx = np.linspace(0, h - 1, small_size).astype(int)
            col_idx = np.linspace(0, w - 1, small_size).astype(int)
            small = gray[np.ix_(row_idx, col_idx)]
        
        small = small.astype(np.float32) / 255.0
        
        # FFT-based spectral residual
        f = np.fft.fft2(small)
        log_amplitude = np.log(np.abs(f) + 1e-8)
        phase = np.angle(f)
        
        # Spectral residual = log_amplitude - smoothed(log_amplitude)
        from scipy.ndimage import uniform_filter
        try:
            smoothed = uniform_filter(log_amplitude, size=3)
        except Exception:
            # Fallback: simple mean filter
            kernel_size = 3
            padded = np.pad(log_amplitude, kernel_size // 2, mode='reflect')
            smoothed = np.zeros_like(log_amplitude)
            for i in range(log_amplitude.shape[0]):
                for j in range(log_amplitude.shape[1]):
                    patch = padded[i:i+kernel_size, j:j+kernel_size]
                    smoothed[i, j] = np.mean(patch)
        
        residual = log_amplitude - smoothed
        
        # Reconstruct saliency map
        saliency_small = np.abs(np.fft.ifft2(np.exp(residual + 1j * phase))) ** 2
        saliency_small = saliency_small.astype(np.float32)
        
        # Gaussian blur
        if HAS_CV2:
            saliency_small = cv2.GaussianBlur(saliency_small, (7, 7), 2.0)
        
        # Upscale to original size
        if HAS_CV2:
            saliency = cv2.resize(saliency_small, (w, h), interpolation=cv2.INTER_LINEAR)
        else:
            row_idx = np.linspace(0, small_size - 1, h).astype(int)
            col_idx = np.linspace(0, small_size - 1, w).astype(int)
            saliency = saliency_small[np.ix_(row_idx, col_idx)]
        
        # Normalize to [0, 1]
        if saliency.max() > saliency.min():
            saliency = (saliency - saliency.min()) / (saliency.max() - saliency.min())
        
        return saliency
    
    def _detect_faces(self, gray: np.ndarray) -> np.ndarray:
        """Detect faces using Haar cascade (if cv2 available)."""
        h, w = gray.shape
        face_mask = np.zeros((h, w), dtype=bool)
        
        if not HAS_CV2:
            return face_mask
        
        try:
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            face_cascade = cv2.CascadeClassifier(cascade_path)
            
            faces = face_cascade.detectMultiScale(
                gray.astype(np.uint8), scaleFactor=1.1,
                minNeighbors=5, minSize=(30, 30)
            )
            
            for (x, y, fw, fh) in faces:
                # Expand face region slightly
                margin = int(max(fw, fh) * 0.2)
                y0 = max(0, y - margin)
                y1 = min(h, y + fh + margin)
                x0 = max(0, x - margin)
                x1 = min(w, x + fw + margin)
                face_mask[y0:y1, x0:x1] = True
                
        except Exception:
            pass
        
        return face_mask
    
    def _center_prior(self, h: int, w: int) -> np.ndarray:
        """Create center-weighted prior (Gaussian centered on image)."""
        y = np.linspace(-1, 1, h)
        x = np.linspace(-1, 1, w)
        yy, xx = np.meshgrid(y, x, indexing='ij')
        
        # Gaussian center bias
        center_weight = np.exp(-(xx**2 + yy**2) / 0.5)
        return center_weight.astype(np.float32)
