"""
Tremor Noise Generator
========================
Simulates natural hand tremor that creates subtle irregularities
in stroke paths, making the drawing look more organic and hand-drawn.
"""

import numpy as np
from ..config import PressureConfig


class TremorNoise:
    """Generates natural hand tremor for stroke perturbation."""
    
    def __init__(self, config: PressureConfig):
        self.frequency = config.tremor_frequency
        self.amplitude = config.tremor_amplitude
        self._phase = 0.0  # Persistent phase for continuity
        
    def generate_offset(self, num_points: int, seed: int = None) -> np.ndarray:
        """
        Generate 2D position offsets simulating hand tremor.
        
        Args:
            num_points: Number of stroke points
            seed: Random seed
            
        Returns:
            (N, 2) array of (dy, dx) offsets in pixels
        """
        if num_points <= 0:
            return np.zeros((0, 2), dtype=np.float32)
            
        rng = np.random.RandomState(seed)
        
        # Time parameter
        t = np.linspace(0, num_points / max(self.frequency, 1.0),
                        num_points, dtype=np.float32)
        
        # Primary oscillation (main tremor frequency)
        tremor_y = np.sin(2.0 * np.pi * self.frequency * t + self._phase)
        tremor_x = np.cos(2.0 * np.pi * self.frequency * 0.7 * t + self._phase * 1.3)
        
        # Secondary high-frequency jitter
        jitter_y = rng.normal(0, 0.3, num_points).astype(np.float32)
        jitter_x = rng.normal(0, 0.3, num_points).astype(np.float32)
        
        # Combine
        offset_y = (tremor_y * 0.7 + jitter_y * 0.3) * self.amplitude * 10.0
        offset_x = (tremor_x * 0.7 + jitter_x * 0.3) * self.amplitude * 10.0
        
        # Update phase for continuity across strokes
        if num_points > 0:
            self._phase += t[-1] * 2.0 * np.pi * self.frequency
            self._phase %= (2.0 * np.pi)
        
        offsets = np.stack([offset_y, offset_x], axis=1)
        return offsets.astype(np.float32)
    
    def apply_to_points(self, points: np.ndarray, seed: int = None) -> np.ndarray:
        """
        Apply tremor offsets to stroke points.
        
        Args:
            points: (N, 2) original (y, x) positions
            seed: Random seed
            
        Returns:
            (N, 2) perturbed positions (clamped to positive)
        """
        offsets = self.generate_offset(len(points), seed)
        perturbed = points.astype(np.float32) + offsets
        perturbed = np.maximum(perturbed, 0)  # Keep in valid range
        return perturbed
    
    def generate_pressure_tremor(self, num_points: int,
                                 seed: int = None) -> np.ndarray:
        """
        Generate subtle pressure variations from hand tremor.
        
        Returns:
            (N,) multiplicative pressure modifier around 1.0
        """
        if num_points <= 0:
            return np.array([], dtype=np.float32)
            
        rng = np.random.RandomState(seed)
        t = np.linspace(0, num_points / max(self.frequency, 1.0),
                        num_points, dtype=np.float32)
        
        # Low-frequency pressure oscillation
        pressure_tremor = np.sin(2.0 * np.pi * self.frequency * 0.5 * t)
        pressure_tremor *= self.amplitude * 0.5
        
        # Add noise
        noise = rng.normal(0, self.amplitude * 0.2, num_points)
        
        modifier = 1.0 + pressure_tremor + noise
        return np.clip(modifier, 0.5, 1.5).astype(np.float32)
