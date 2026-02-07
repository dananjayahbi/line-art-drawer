"""
Velocity Model
================
Computes stroke velocity and its effect on pressure and deposit.
Faster strokes create lighter marks; slower strokes are darker.
"""

import numpy as np
from ..config import PressureConfig


class VelocityModel:
    """Models velocity-based pressure modification along strokes."""
    
    def __init__(self, config: PressureConfig):
        self.velocity_influence = config.velocity_influence
        
    def compute_velocities(self, points: np.ndarray) -> np.ndarray:
        """
        Compute velocity at each point along a stroke path.
        
        Args:
            points: (N, 2) array of (y, x) positions
            
        Returns:
            (N,) array of velocities (pixel distance between consecutive points)
        """
        if len(points) <= 1:
            return np.ones(len(points), dtype=np.float32)
            
        # Distance between consecutive points
        diffs = np.diff(points, axis=0)
        distances = np.sqrt((diffs ** 2).sum(axis=1))
        
        # First point gets same velocity as second
        velocities = np.zeros(len(points), dtype=np.float32)
        velocities[1:] = distances
        velocities[0] = distances[0] if len(distances) > 0 else 1.0
        
        return velocities
    
    def compute_angles(self, points: np.ndarray) -> np.ndarray:
        """
        Compute stroke direction angle at each point.
        
        Args:
            points: (N, 2) array of (y, x) positions
            
        Returns:
            (N,) array of angles in radians
        """
        if len(points) <= 1:
            return np.zeros(len(points), dtype=np.float32)
            
        diffs = np.diff(points, axis=0)
        angles_tail = np.arctan2(diffs[:, 0], diffs[:, 1])  # atan2(dy, dx)
        
        angles = np.zeros(len(points), dtype=np.float32)
        angles[1:] = angles_tail
        angles[0] = angles_tail[0] if len(angles_tail) > 0 else 0.0
        
        return angles
    
    def velocity_pressure_modifier(self, velocities: np.ndarray) -> np.ndarray:
        """
        Convert velocity to a pressure modifier.
        
        Higher velocity → lower pressure (lighter marks)
        Lower velocity → higher pressure (darker marks)
        
        Args:
            velocities: (N,) array of velocities
            
        Returns:
            (N,) pressure modifier in [0.3, 1.0]
        """
        if len(velocities) == 0:
            return np.array([], dtype=np.float32)
            
        # Normalize velocity to [0, 1]
        v_max = velocities.max()
        if v_max > 0:
            v_norm = velocities / v_max
        else:
            v_norm = np.zeros_like(velocities)
        
        # Inverse relationship: fast = light, slow = heavy
        # modifier = 1.0 - velocity_influence * v_norm
        modifier = 1.0 - self.velocity_influence * v_norm
        modifier = np.clip(modifier, 0.3, 1.0)
        
        return modifier.astype(np.float32)
