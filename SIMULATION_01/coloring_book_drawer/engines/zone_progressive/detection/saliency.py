"""
Zone-Based Progressive Engine - Saliency Detection
====================================================
Computes visual saliency maps using spectral residual method.
Identifies the most visually important regions in the image.
"""

import cv2
import numpy as np

from ..config import FocalDetectionConfig


class SaliencyDetector:
    """
    Detects visually salient (important) regions in the image
    using the spectral residual method from the frequency domain.
    
    The approach:
    1. FFT → log magnitude spectrum + phase
    2. Spectral residual = log_magnitude - smoothed_log_magnitude
    3. Inverse FFT of (spectral_residual + original_phase)
    4. Squared magnitude = saliency
    """
    
    def __init__(self, config: FocalDetectionConfig = None):
        self.config = config or FocalDetectionConfig()
    
    def compute_saliency(self, image: np.ndarray) -> np.ndarray:
        """
        Compute saliency map using spectral residual method.
        
        Args:
            image: Input image (RGB or grayscale, uint8)
            
        Returns:
            Saliency map (float32, 0.0-1.0) where 1.0 = most salient
        """
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY).astype(np.float64)
        else:
            gray = image.astype(np.float64)
        
        # Resize to manageable size for FFT (preserving aspect ratio)
        h, w = gray.shape
        scale = min(1.0, 256.0 / max(h, w))
        if scale < 1.0:
            small = cv2.resize(gray, (int(w * scale), int(h * scale)),
                               interpolation=cv2.INTER_AREA)
        else:
            small = gray
        
        # FFT for spectral analysis
        f = np.fft.fft2(small)
        fshift = np.fft.fftshift(f)
        
        # Log magnitude and phase
        magnitude = np.log(np.abs(fshift) + 1e-10)
        phase = np.angle(fshift)
        
        # Spectral residual: original log-magnitude minus locally averaged
        ksize = self.config.spectral_blur_ksize
        avg_magnitude = cv2.blur(magnitude, (ksize, ksize))
        spectral_residual = magnitude - avg_magnitude
        
        # Reconstruct with spectral residual + original phase
        saliency_complex = np.exp(spectral_residual) * np.exp(1j * phase)
        saliency_shift = np.fft.ifftshift(saliency_complex)
        saliency = np.fft.ifft2(saliency_shift)
        saliency = np.abs(saliency) ** 2
        
        # Resize back to original dimensions
        if scale < 1.0:
            saliency = cv2.resize(saliency.astype(np.float32), (w, h),
                                  interpolation=cv2.INTER_LINEAR)
        
        saliency = saliency.astype(np.float32)
        
        # Normalize to 0-1
        s_min, s_max = saliency.min(), saliency.max()
        if s_max - s_min > 1e-8:
            saliency = (saliency - s_min) / (s_max - s_min)
        else:
            saliency = np.zeros_like(saliency)
        
        # Smooth for more stable focal regions
        blur_ksize = self.config.saliency_blur_ksize
        blur_sigma = self.config.saliency_blur_sigma
        saliency = cv2.GaussianBlur(saliency, (blur_ksize, blur_ksize), blur_sigma)
        
        # Re-normalize after blur
        s_min, s_max = saliency.min(), saliency.max()
        if s_max - s_min > 1e-8:
            saliency = (saliency - s_min) / (s_max - s_min)
        
        return saliency
    
    def compute_edge_saliency(self, image: np.ndarray) -> np.ndarray:
        """
        Compute additional edge-based saliency for line art.
        For pencil art, strong edges/strokes are also salient.
        
        Args:
            image: Input image (RGB or grayscale, uint8)
            
        Returns:
            Edge saliency map (float32, 0.0-1.0)
        """
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image.copy()
        
        # Multi-scale edge detection
        edges_fine = cv2.Canny(gray, 50, 150)
        edges_coarse = cv2.Canny(gray, 30, 100)
        
        # Combine scales
        combined = np.maximum(edges_fine, edges_coarse).astype(np.float32) / 255.0
        
        # Dilate to create saliency regions around edges
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        dilated = cv2.dilate(combined, kernel, iterations=2)
        
        # Smooth
        edge_saliency = cv2.GaussianBlur(dilated, (15, 15), 4.0)
        
        # Normalize
        e_max = edge_saliency.max()
        if e_max > 1e-8:
            edge_saliency = edge_saliency / e_max
        
        return edge_saliency
    
    def compute_combined_saliency(self, image: np.ndarray,
                                   spectral_weight: float = 0.6,
                                   edge_weight: float = 0.4) -> np.ndarray:
        """
        Compute a combined saliency map from spectral and edge cues.
        
        Args:
            image: Input image (RGB or grayscale, uint8)
            spectral_weight: Weight for spectral saliency
            edge_weight: Weight for edge saliency
            
        Returns:
            Combined saliency map (float32, 0.0-1.0)
        """
        spectral = self.compute_saliency(image)
        edge = self.compute_edge_saliency(image)
        
        combined = spectral * spectral_weight + edge * edge_weight
        
        # Normalize
        c_max = combined.max()
        if c_max > 1e-8:
            combined = combined / c_max
        
        return combined
