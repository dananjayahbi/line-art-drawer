#!/usr/bin/env python3
"""
Drip Engine for Pendulum Paint Art
====================================
Handles paint dripping with attraction-weighted probability based on target image.
Drip frequency increases over dark pixels and decreases over white areas.

Features:
- Attraction probability map from target image
- Velocity-based drip probability
- Paint accumulation tracking
- Thickness variation based on position
"""

import numpy as np
import cv2
from pathlib import Path
import random


class DripEngine:
    """
    Paint dripping system with attraction-weighted probability mapping.
    
    The engine creates a probability map from the target image where
    dark pixels have higher probability of triggering paint drips.
    """
    
    def __init__(self, canvas_width, canvas_height, 
                 base_drip_rate=0.15,
                 paint_thickness=8,
                 viscosity=0.7,
                 paint_color=(44, 24, 16)):
        """
        Initialize drip engine.
        
        Args:
            canvas_width: Width of the canvas
            canvas_height: Height of the canvas
            base_drip_rate: Base probability of dripping per frame (0.0-1.0)
            paint_thickness: Base radius of paint drops
            viscosity: How much paint spreads (0.0-1.0)
            paint_color: RGB tuple for paint color
        """
        self.canvas_width = canvas_width
        self.canvas_height = canvas_height
        self.base_drip_rate = base_drip_rate
        self.paint_thickness = paint_thickness
        self.viscosity = viscosity
        self.paint_color = paint_color
        
        # Attraction probability map (normalized 0-1)
        self.attraction_map = None
        
        # Paint accumulation map
        self.paint_accumulation = np.zeros((canvas_height, canvas_width), dtype=np.float32)
        
        # List of active drips/splats
        self.drips = []
        
        # Statistics
        self.total_drips = 0
        self.coverage = 0.0
        
        # Target image reference
        self.target_image = None
    
    def load_target_image(self, image_path, padding=40):
        """
        Load target image and create attraction probability map.
        
        Dark pixels in the image create high probability zones for dripping.
        
        Args:
            image_path: Path to target image file
            padding: Padding around image
        """
        if image_path is None:
            # No target image - uniform probability
            self.attraction_map = np.ones((self.canvas_height, self.canvas_width), dtype=np.float32) * 0.5
            return
        
        # Load image
        img = cv2.imread(str(image_path))
        if img is None:
            print(f"Warning: Could not load image {image_path}")
            self.attraction_map = np.ones((self.canvas_height, self.canvas_width), dtype=np.float32) * 0.5
            return
        
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Resize to canvas size with padding
        target_w = self.canvas_width - 2 * padding
        target_h = self.canvas_height - 2 * padding
        
        # Maintain aspect ratio
        h, w = gray.shape[:2]
        scale = min(target_w / w, target_h / h)
        new_w = int(w * scale)
        new_h = int(h * scale)
        
        resized = cv2.resize(gray, (new_w, new_h), interpolation=cv2.INTER_AREA)
        
        # Create full canvas with white background
        full_canvas = np.ones((self.canvas_height, self.canvas_width), dtype=np.uint8) * 255
        
        # Center the image
        x_offset = (self.canvas_width - new_w) // 2
        y_offset = (self.canvas_height - new_h) // 2
        full_canvas[y_offset:y_offset+new_h, x_offset:x_offset+new_w] = resized
        
        # Store target for reference
        self.target_image = full_canvas.copy()
        
        # Invert and normalize: dark pixels -> high probability
        # 255 (white) -> 0.0, 0 (black) -> 1.0
        self.attraction_map = (255 - full_canvas.astype(np.float32)) / 255.0
        
        # Apply Gaussian blur for smoother probability transitions
        self.attraction_map = cv2.GaussianBlur(self.attraction_map, (21, 21), 0)
        
        # Normalize to 0-1 range
        min_val = self.attraction_map.min()
        max_val = self.attraction_map.max()
        if max_val > min_val:
            self.attraction_map = (self.attraction_map - min_val) / (max_val - min_val)
        
        print(f"Loaded target image: {image_path}")
        print(f"Attraction map range: {self.attraction_map.min():.3f} - {self.attraction_map.max():.3f}")
    
    def should_drip(self, x, y, velocity_factor=1.0):
        """
        Determine if paint should drip at the given position.
        
        Probability is based on:
        1. Base drip rate
        2. Attraction map value at position
        3. Velocity factor (slower = more drip)
        4. Current paint accumulation (less if already painted)
        
        Args:
            x: X position on canvas
            y: Y position on canvas
            velocity_factor: Speed factor (0=stopped, 1=normal, >1=fast)
            
        Returns:
            bool: True if should drip
        """
        # Clamp position to canvas bounds
        x = int(max(0, min(self.canvas_width - 1, x)))
        y = int(max(0, min(self.canvas_height - 1, y)))
        
        # Get attraction value at position
        if self.attraction_map is not None:
            attraction = self.attraction_map[y, x]
        else:
            attraction = 0.5
        
        # Get current accumulation (reduce probability if already painted)
        current_paint = self.paint_accumulation[y, x]
        accumulation_factor = max(0.1, 1.0 - current_paint * 0.5)
        
        # Velocity factor: slower movement = more drips
        # Invert: low velocity -> high factor
        vel_factor = 1.0 / (1.0 + velocity_factor * 0.5)
        
        # Calculate final probability
        probability = self.base_drip_rate * attraction * accumulation_factor * vel_factor
        
        # Add some randomness
        probability *= random.uniform(0.8, 1.2)
        
        # Random check
        return random.random() < probability
    
    def create_drip(self, x, y, velocity=(0, 0)):
        """
        Create a new paint drip at the specified position.
        
        Args:
            x: X position
            y: Y position
            velocity: Current pendulum velocity for drip trajectory
            
        Returns:
            dict: Drip data
        """
        # Clamp position
        x = max(0, min(self.canvas_width - 1, x))
        y = max(0, min(self.canvas_height - 1, y))
        
        # Thickness varies based on attraction (thicker over dark areas)
        if self.attraction_map is not None:
            ix, iy = int(x), int(y)
            attraction = self.attraction_map[iy, ix]
        else:
            attraction = 0.5
        
        thickness = self.paint_thickness * (0.5 + attraction * 0.5)
        thickness *= random.uniform(0.8, 1.2)
        
        drip = {
            'x': x,
            'y': y,
            'vx': velocity[0] * 0.1,  # Inherit some velocity
            'vy': velocity[1] * 0.1 + random.uniform(0.5, 2.0),  # Gravity
            'radius': thickness,
            'initial_radius': thickness,
            'opacity': 1.0,
            'spreading': True,
            'age': 0
        }
        
        self.drips.append(drip)
        self.total_drips += 1
        
        return drip
    
    def update_drips(self):
        """
        Update all active drips (spreading, fading).
        
        Returns:
            list: Active drips for rendering
        """
        active_drips = []
        
        for drip in self.drips:
            drip['age'] += 1
            
            # Spreading phase
            if drip['spreading']:
                # Paint spreads based on viscosity
                spread_rate = 0.1 * self.viscosity
                drip['radius'] += spread_rate
                
                # Stop spreading after reaching max size
                max_radius = drip['initial_radius'] * (1 + self.viscosity)
                if drip['radius'] >= max_radius:
                    drip['spreading'] = False
                    drip['radius'] = max_radius
            
            # Update position (gravity and initial velocity)
            if drip['age'] < 10:  # Brief falling phase
                drip['x'] += drip['vx']
                drip['y'] += drip['vy']
                drip['vy'] += 0.5  # Gravity acceleration
            
            # Clamp to canvas
            drip['x'] = max(0, min(self.canvas_width - 1, drip['x']))
            drip['y'] = max(0, min(self.canvas_height - 1, drip['y']))
            
            # Update paint accumulation
            ix, iy = int(drip['x']), int(drip['y'])
            radius = int(drip['radius'])
            
            # Add paint to accumulation map
            y_start = max(0, iy - radius)
            y_end = min(self.canvas_height, iy + radius + 1)
            x_start = max(0, ix - radius)
            x_end = min(self.canvas_width, ix + radius + 1)
            
            for py in range(y_start, y_end):
                for px in range(x_start, x_end):
                    dist = np.sqrt((px - ix)**2 + (py - iy)**2)
                    if dist <= radius:
                        # Falloff from center
                        intensity = 1.0 - (dist / radius) * 0.5
                        self.paint_accumulation[py, px] = min(1.0, 
                            self.paint_accumulation[py, px] + intensity * 0.1)
            
            # Keep drip if still active
            if drip['age'] < 120:  # Keep for 2 seconds at 60fps
                active_drips.append(drip)
        
        self.drips = active_drips
        
        # Update coverage statistic
        self.coverage = np.mean(self.paint_accumulation > 0.1)
        
        return active_drips
    
    def get_drips(self):
        """Get list of current drips for rendering."""
        return self.drips
    
    def get_paint_accumulation(self):
        """Get paint accumulation map."""
        return self.paint_accumulation
    
    def get_coverage(self):
        """Get canvas coverage percentage."""
        return self.coverage
    
    def get_attraction_at(self, x, y):
        """Get attraction value at position."""
        if self.attraction_map is None:
            return 0.5
        
        x = int(max(0, min(self.canvas_width - 1, x)))
        y = int(max(0, min(self.canvas_height - 1, y)))
        return self.attraction_map[y, x]
    
    def reset(self):
        """Reset drip engine state."""
        self.drips.clear()
        self.paint_accumulation.fill(0)
        self.total_drips = 0
        self.coverage = 0.0
    
    def set_paint_color(self, color):
        """Set paint color (RGB tuple)."""
        self.paint_color = color
    
    def set_drip_rate(self, rate):
        """Set base drip rate."""
        self.base_drip_rate = max(0.0, min(1.0, rate))
    
    def set_thickness(self, thickness):
        """Set base paint thickness."""
        self.paint_thickness = max(1, thickness)
    
    def set_viscosity(self, viscosity):
        """Set paint viscosity."""
        self.viscosity = max(0.0, min(1.0, viscosity))
