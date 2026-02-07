"""
Paper Texture Simulation
==========================
Generates procedural paper textures that influence graphite deposit.
Three texture types: smooth, cold-press, and rough.
"""

import numpy as np
from ..config import PaperType, PaperConfig


class PaperTexture:
    """Procedural paper texture generator and applicator."""
    
    def __init__(self, config: PaperConfig):
        self.config = config
        self.paper_type = config.paper_type
        self.texture_strength = config.texture_strength
        self.grain_scale = config.grain_scale
        self._texture_map = None
        self._height = 0
        self._width = 0
        
    def generate(self, height: int, width: int) -> np.ndarray:
        """
        Generate paper texture map for the given dimensions.
        
        Returns:
            Texture map (H, W) with values in [0, 1] where 1 = full receptivity.
        """
        self._height = height
        self._width = width
        
        if self.paper_type == PaperType.SMOOTH:
            texture = self._generate_smooth(height, width)
        elif self.paper_type == PaperType.COLD_PRESS:
            texture = self._generate_cold_press(height, width)
        elif self.paper_type == PaperType.ROUGH:
            texture = self._generate_rough(height, width)
        else:
            texture = np.ones((height, width), dtype=np.float32)
            
        # Blend with flat texture based on texture_strength
        flat = np.ones((height, width), dtype=np.float32)
        self._texture_map = flat * (1.0 - self.texture_strength) + texture * self.texture_strength
        self._texture_map = np.clip(self._texture_map, 0.0, 1.0).astype(np.float32)
        
        return self._texture_map
    
    def _generate_smooth(self, h: int, w: int) -> np.ndarray:
        """Smooth paper - very little texture variation."""
        # Very subtle noise
        base = np.ones((h, w), dtype=np.float32) * 0.95
        noise = np.random.RandomState(42).uniform(-0.05, 0.05, (h, w)).astype(np.float32)
        return np.clip(base + noise, 0.0, 1.0)
        
    def _generate_cold_press(self, h: int, w: int) -> np.ndarray:
        """Cold-press paper - medium grain with visible texture pattern."""
        rng = np.random.RandomState(42)
        
        # Multi-scale Perlin-like noise using octave summation
        texture = np.zeros((h, w), dtype=np.float32)
        
        scales = [
            int(max(4, 8 * self.grain_scale)),
            int(max(8, 16 * self.grain_scale)),
            int(max(16, 32 * self.grain_scale))
        ]
        weights = [0.5, 0.3, 0.2]
        
        for scale, weight in zip(scales, weights):
            # Generate low-res noise and upsample
            small_h = max(2, h // scale)
            small_w = max(2, w // scale)
            noise_small = rng.uniform(0, 1, (small_h, small_w)).astype(np.float32)
            
            # Bilinear upscale
            try:
                import cv2
                noise_upscaled = cv2.resize(noise_small, (w, h), interpolation=cv2.INTER_LINEAR)
            except ImportError:
                # Fallback: nearest neighbor via numpy
                row_idx = np.linspace(0, small_h - 1, h).astype(int)
                col_idx = np.linspace(0, small_w - 1, w).astype(int)
                noise_upscaled = noise_small[np.ix_(row_idx, col_idx)]
            
            texture += weight * noise_upscaled
        
        # Normalize to [0.3, 1.0] range - paper is never fully blocking
        texture = 0.3 + 0.7 * (texture - texture.min()) / (texture.max() - texture.min() + 1e-8)
        return texture.astype(np.float32)
    
    def _generate_rough(self, h: int, w: int) -> np.ndarray:
        """Rough paper - heavy grain with peaks and valleys."""
        rng = np.random.RandomState(42)
        
        # Start with cold-press as base
        texture = self._generate_cold_press(h, w)
        
        # Add stronger high-frequency detail
        fine_noise = rng.uniform(0, 1, (h, w)).astype(np.float32)
        texture = 0.6 * texture + 0.4 * fine_noise
        
        # Add "fiber" pattern
        fiber_h = np.zeros((h, w), dtype=np.float32)
        for i in range(0, h, max(1, int(3 * self.grain_scale))):
            fiber_h[i, :] = rng.uniform(0.0, 0.15)
        
        fiber_v = np.zeros((h, w), dtype=np.float32)
        for j in range(0, w, max(1, int(5 * self.grain_scale))):
            fiber_v[:, j] = rng.uniform(0.0, 0.1)
        
        texture = texture - fiber_h - fiber_v
        
        # Normalize to [0.15, 1.0] - rough paper has deeper valleys
        texture = np.clip(texture, 0, 1)
        texture = 0.15 + 0.85 * (texture - texture.min()) / (texture.max() - texture.min() + 1e-8)
        return texture.astype(np.float32)
    
    def get_receptivity(self, y: int, x: int, radius: int = 1) -> np.ndarray:
        """
        Get paper receptivity for a region around (y, x).
        
        Args:
            y, x: Center position
            radius: Half-size of the region to sample
            
        Returns:
            Receptivity patch (2*radius+1, 2*radius+1)
        """
        if self._texture_map is None:
            return np.ones((2*radius+1, 2*radius+1), dtype=np.float32)
            
        h, w = self._texture_map.shape
        y0 = max(0, y - radius)
        y1 = min(h, y + radius + 1)
        x0 = max(0, x - radius)
        x1 = min(w, x + radius + 1)
        
        patch = self._texture_map[y0:y1, x0:x1]
        return patch
    
    @property
    def texture_map(self) -> np.ndarray:
        """Full texture map, or None if not generated."""
        return self._texture_map
