"""
Pencil Tip Simulation
======================
Models the physical pencil tip shape, wear, and deposit pattern.
The tip shape determines how graphite is laid down at each stroke point.
"""

import numpy as np
from ..config import TipShape, PencilTipConfig


class PencilTip:
    """Simulates a physical pencil tip with shape and wear properties."""
    
    def __init__(self, config: PencilTipConfig):
        self.config = config
        self.shape = config.shape
        self.hardness = config.hardness
        self.sharpness = config.sharpness
        self.graphite_load = config.graphite_load
        self.base_size = config.base_size
        
        # Build the tip kernel
        self._kernel = self._build_kernel()
        
    def _build_kernel(self) -> np.ndarray:
        """Build the deposit pattern kernel based on tip shape and sharpness."""
        # Effective tip size depends on sharpness (sharp=smaller, dull=larger)
        effective_size = max(3, int(self.base_size * (2.0 - self.sharpness)))
        if effective_size % 2 == 0:
            effective_size += 1  # Ensure odd size
            
        center = effective_size // 2
        y, x = np.ogrid[-center:center+1, -center:center+1]
        
        if self.shape == TipShape.ROUND:
            kernel = self._round_kernel(x, y, center)
        elif self.shape == TipShape.CHISEL:
            kernel = self._chisel_kernel(x, y, center, effective_size)
        elif self.shape == TipShape.BLUNT:
            kernel = self._blunt_kernel(x, y, center)
        else:
            kernel = self._round_kernel(x, y, center)
            
        # Normalize to [0, 1]
        if kernel.max() > 0:
            kernel = kernel / kernel.max()
            
        # Apply hardness: hard pencils deposit less per point
        # softness factor: soft=more deposit, hard=less
        softness = 1.0 - self.hardness
        deposit_factor = 0.3 + 0.7 * softness  # Range [0.3, 1.0]
        kernel *= deposit_factor
        
        return kernel.astype(np.float32)
        
    def _round_kernel(self, x: np.ndarray, y: np.ndarray, center: int) -> np.ndarray:
        """Standard round pencil tip - Gaussian falloff from center."""
        radius = center * 0.8
        dist_sq = x**2 + y**2
        sigma = radius * (0.5 + 0.5 * (1.0 - self.sharpness))
        kernel = np.exp(-dist_sq / (2.0 * sigma**2 + 1e-8))
        # Mask outside circle
        mask = dist_sq <= (center * 1.0)**2
        return kernel * mask
        
    def _chisel_kernel(self, x: np.ndarray, y: np.ndarray, center: int,
                       size: int) -> np.ndarray:
        """Chisel tip - elongated, flat contact pattern."""
        # Wider along x, narrow along y
        aspect = 2.5
        sigma_x = center * 0.7
        sigma_y = center * 0.3
        kernel = np.exp(-((x / aspect)**2 / (2 * sigma_x**2 + 1e-8) +
                          y**2 / (2 * sigma_y**2 + 1e-8)))
        return kernel
    
    def _blunt_kernel(self, x: np.ndarray, y: np.ndarray, center: int) -> np.ndarray:
        """Blunt tip - broad, relatively uniform contact area."""
        radius = center * 1.0
        dist_sq = x**2 + y**2
        # Flatter profile - less Gaussian, more uniform
        sigma = radius * 1.2
        kernel = np.exp(-dist_sq / (2.0 * sigma**2 + 1e-8))
        # Clip to make more uniform
        kernel = np.clip(kernel, 0, 1)
        kernel = np.where(kernel > 0.2, kernel * 0.8 + 0.2, kernel)
        mask = dist_sq <= (center * 1.2)**2
        return kernel * mask
    
    def get_deposit_pattern(self, pressure: float = 1.0, angle: float = 0.0) -> np.ndarray:
        """
        Get the graphite deposit pattern for a single contact point.
        
        Args:
            pressure: Normalized pressure (0-1) 
            angle: Stroke direction in radians (for chisel tip rotation)
            
        Returns:
            2D array representing deposit intensity at this point
        """
        pattern = self._kernel.copy()
        
        # Scale by pressure and graphite load
        effective_deposit = pressure * self.graphite_load
        pattern *= effective_deposit
        
        # Rotate chisel tip with stroke angle
        if self.shape == TipShape.CHISEL and abs(angle) > 0.01:
            pattern = self._rotate_kernel(pattern, angle)
            
        return pattern
    
    def _rotate_kernel(self, kernel: np.ndarray, angle: float) -> np.ndarray:
        """Rotate the kernel by given angle (radians)."""
        try:
            from scipy.ndimage import rotate as scipy_rotate
            angle_deg = np.degrees(angle)
            rotated = scipy_rotate(kernel, angle_deg, reshape=False, order=1, mode='constant', cval=0)
            return np.clip(rotated, 0, 1).astype(np.float32)
        except ImportError:
            return kernel
    
    def wear(self, amount: float = 0.001):
        """Simulate tip wear - reduces sharpness slightly over time."""
        self.sharpness = max(0.1, self.sharpness - amount)
        self.graphite_load = max(0.1, self.graphite_load - amount * 0.5)
        # Rebuild kernel if significant wear
        if amount > 0.01:
            self._kernel = self._build_kernel()
    
    @property
    def kernel_size(self) -> int:
        """Current kernel size."""
        return self._kernel.shape[0]
