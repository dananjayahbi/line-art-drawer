"""
Pressure Dynamics Controller
==============================
Implements an attack-sustain-release envelope for stroke pressure,
creating natural pressure variation along each stroke.
"""

import numpy as np
from ..config import PressureConfig


class PressureDynamicsController:
    """
    Controls pressure along a stroke using an ASR (Attack-Sustain-Release) envelope.
    
    Attack: Pressure ramps up from 0 as pencil contacts paper
    Sustain: Pressure remains relatively constant with subtle noise
    Release: Pressure ramps down as stroke ends / pencil lifts
    """
    
    def __init__(self, config: PressureConfig):
        self.config = config
        self.attack_ratio = config.attack_ratio
        self.release_ratio = config.release_ratio
        self.sustain_noise = config.sustain_noise
        
    def generate_pressure_envelope(self, num_points: int,
                                   base_pressure: float = 0.8,
                                   seed: int = None) -> np.ndarray:
        """
        Generate pressure values for a stroke of given length.
        
        Args:
            num_points: Number of points in the stroke
            base_pressure: Target sustain pressure [0, 1]
            seed: Random seed for reproducibility
            
        Returns:
            (num_points,) array of pressure values [0, 1]
        """
        if num_points <= 0:
            return np.array([], dtype=np.float32)
        if num_points == 1:
            return np.array([base_pressure], dtype=np.float32)
            
        rng = np.random.RandomState(seed)
        envelope = np.ones(num_points, dtype=np.float32) * base_pressure
        
        # Attack phase
        attack_len = max(1, int(num_points * self.attack_ratio))
        if attack_len > 0 and attack_len < num_points:
            # Smooth ease-in (quadratic)
            t = np.linspace(0, 1, attack_len, dtype=np.float32)
            attack_curve = t ** 2  # Quadratic ease-in
            envelope[:attack_len] = attack_curve * base_pressure
        
        # Release phase
        release_len = max(1, int(num_points * self.release_ratio))
        release_start = num_points - release_len
        if release_len > 0 and release_start > 0:
            # Smooth ease-out (inverse quadratic)
            t = np.linspace(1, 0, release_len, dtype=np.float32)
            release_curve = t ** 2  # Quadratic ease-out
            envelope[release_start:] = release_curve * base_pressure
        
        # Sustain noise
        if self.sustain_noise > 0:
            noise = rng.normal(0, self.sustain_noise, num_points).astype(np.float32)
            # Only add noise to sustain region (between attack and release)
            sustain_start = attack_len
            sustain_end = release_start if release_start > attack_len else num_points
            envelope[sustain_start:sustain_end] += noise[sustain_start:sustain_end]
        
        return np.clip(envelope, 0.0, 1.0)
    
    def modulate_with_darkness(self, pressure_envelope: np.ndarray,
                               target_darkness: np.ndarray) -> np.ndarray:
        """
        Modulate pressure based on target pixel darkness.
        Darker targets get higher pressure for more graphite.
        
        Args:
            pressure_envelope: Base pressure values (N,)
            target_darkness: Target darkness at each point (N,) in [0, 1]
            
        Returns:
            Modulated pressure (N,)
        """
        # Scale pressure by how dark the target should be
        modulated = pressure_envelope * (0.3 + 0.7 * target_darkness)
        return np.clip(modulated, 0.0, 1.0).astype(np.float32)
