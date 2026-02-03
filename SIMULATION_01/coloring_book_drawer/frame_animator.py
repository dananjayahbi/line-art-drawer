#!/usr/bin/env python3
"""
Frame Animator for Coloring Book Drawer
========================================
Handles the animated border frame that draws around completed artwork.
Now with natural hand-drawn pencil effect.
"""

import pygame
import pygame.gfxdraw
import math
import random
import numpy as np


class FrameAnimator:
    """Handles progressive drawing of decorative border frame with hand-drawn effect."""
    
    def __init__(self, width, height, thickness=6, speed=1.0, margin=20, color=(40, 40, 50)):
        """
        Initialize frame animator.
        
        Args:
            width: Canvas width
            height: Canvas height
            thickness: Frame line thickness
            speed: Drawing speed multiplier
            margin: Margin from edge
            color: Frame color (RGB tuple)
        """
        self.width = width
        self.height = height
        self.thickness = thickness
        self.speed = speed
        self.margin = margin
        self.color = color
        
        self.frame_points = []
        self.current_idx = 0
        self.is_complete = False
        self.frame_surface = None
        
        # Hand-drawn effect settings
        self.wobble_frequency = 0.15    # How often wobbles occur
        self.wobble_amplitude = 1.2     # Maximum wobble in pixels
        self.pressure_variation = 0.3   # How much pressure/thickness varies
        self.corner_overshoot = 3       # Pixels to overshoot at corners
        
        # Generate noise pattern for pencil texture
        self._generate_pencil_texture()
        
        self._init_frame_points()
    
    def _generate_pencil_texture(self):
        """Pre-generate Perlin-like noise for pressure variation."""
        # Create a simple noise pattern for consistent pressure variation
        self.pressure_noise = []
        length = 4000  # Should be more than enough for any frame
        
        # Use smooth noise (low-frequency sine waves with variation)
        for i in range(length):
            t = i / 50.0  # Slow variation
            base_pressure = 0.85  # Base pressure (85%)
            variation = (
                0.10 * math.sin(t * 1.7) +
                0.05 * math.sin(t * 3.3 + 1.5) +
                0.05 * math.sin(t * 7.1 + 2.3)
            )
            # Add small random jitter
            jitter = random.uniform(-0.02, 0.02)
            pressure = max(0.5, min(1.0, base_pressure + variation + jitter))
            self.pressure_noise.append(pressure)
    
    def _get_pressure_at(self, idx):
        """Get pressure value for a given point index."""
        return self.pressure_noise[idx % len(self.pressure_noise)]
    
    def _init_frame_points(self):
        """Initialize the frame points with natural hand-drawn wobble."""
        margin = self.margin
        w, h = self.width, self.height
        
        self.frame_points = []
        
        # Precompute corner positions
        corners = [
            (margin, margin),           # Top-left
            (w - margin, margin),       # Top-right  
            (w - margin, h - margin),   # Bottom-right
            (margin, h - margin),       # Bottom-left
            (margin, margin)            # Back to top-left
        ]
        
        # Generate points along each edge with natural wobble
        point_idx = 0
        
        for edge_idx in range(4):
            start = corners[edge_idx]
            end = corners[edge_idx + 1]
            
            is_horizontal = abs(end[1] - start[1]) < abs(end[0] - start[0])
            
            # Calculate edge length and number of points
            edge_length = math.sqrt((end[0] - start[0])**2 + (end[1] - start[1])**2)
            num_points = max(2, int(edge_length / 3))  # One point every 3 pixels
            
            # Add slight overshoot at start of edge (except first edge)
            if edge_idx > 0:
                # Overshoot into the previous edge's direction slightly
                overshoot_x = 0
                overshoot_y = 0
                if edge_idx == 1:  # Starting top-right, came from top edge
                    overshoot_x = self.corner_overshoot
                elif edge_idx == 2:  # Starting bottom-right, came from right edge
                    overshoot_y = self.corner_overshoot
                elif edge_idx == 3:  # Starting bottom-left, came from bottom edge
                    overshoot_x = -self.corner_overshoot
            
            for i in range(num_points):
                t = i / max(1, num_points - 1)
                
                # Base position (linear interpolation)
                base_x = start[0] + (end[0] - start[0]) * t
                base_y = start[1] + (end[1] - start[1]) * t
                
                # Add natural wobble using sine waves with different frequencies
                wobble_factor = math.sin(point_idx * self.wobble_frequency * 2)
                wobble_factor += 0.5 * math.sin(point_idx * self.wobble_frequency * 5 + 1.2)
                wobble_factor *= self.wobble_amplitude
                
                # Also add small random jitter
                jitter = random.uniform(-0.3, 0.3)
                
                if is_horizontal:
                    # Wobble perpendicular to horizontal edge (vertically)
                    wobble_x = 0
                    wobble_y = wobble_factor + jitter
                else:
                    # Wobble perpendicular to vertical edge (horizontally)
                    wobble_x = wobble_factor + jitter
                    wobble_y = 0
                
                # Reduce wobble at corners for cleaner look
                corner_proximity = min(t, 1 - t) * 2  # 0 at corners, 1 in middle
                corner_dampening = 0.3 + 0.7 * corner_proximity
                wobble_x *= corner_dampening
                wobble_y *= corner_dampening
                
                self.frame_points.append((base_x + wobble_x, base_y + wobble_y))
                point_idx += 1
        
        self.current_idx = 0
        self.is_complete = False
        
        # Create a surface for the frame line
        self.frame_surface = pygame.Surface((w, h), pygame.SRCALPHA)
        self.frame_surface.fill((0, 0, 0, 0))  # Transparent
    
    def update(self):
        """
        Update frame drawing animation.
        Returns the current pen position (x, y) or None if complete.
        """
        if self.is_complete or not self.frame_points:
            return None
        
        # Frame drawing uses its own separate speed setting
        points_per_frame = max(3, int(8 * self.speed))
        
        for _ in range(points_per_frame):
            if self.current_idx >= len(self.frame_points) - 1:
                self.is_complete = True
                print("Frame complete!")
                return None
            
            # Draw line segment from current point to next
            p1 = self.frame_points[self.current_idx]
            p2 = self.frame_points[self.current_idx + 1]
            
            # Get pressure for this segment
            pressure = self._get_pressure_at(self.current_idx)
            
            # Convert to int for pygame
            p1_int = (int(p1[0]), int(p1[1]))
            p2_int = (int(p2[0]), int(p2[1]))
            
            # Draw smooth anti-aliased thick line with pressure
            self._draw_pencil_line(p1_int, p2_int, pressure)
            
            self.current_idx += 1
        
        # Return current pen position
        if self.current_idx < len(self.frame_points):
            p = self.frame_points[self.current_idx]
            return (int(p[0]), int(p[1]))
        
        return None
    
    def _draw_pencil_line(self, p1, p2, pressure):
        """Draw a pencil-like line with pressure variation and texture."""
        x1, y1 = p1
        x2, y2 = p2
        
        # Calculate line length and direction
        dx = x2 - x1
        dy = y2 - y1
        dist = max(1, int(math.sqrt(dx*dx + dy*dy)))
        
        # Base radius affected by pressure
        base_radius = self.thickness / 2
        
        # Draw filled circles along the line with varying radius
        for i in range(dist + 1):
            t = i / max(1, dist)
            x = int(x1 + dx * t)
            y = int(y1 + dy * t)
            
            # Vary radius based on pressure and add micro-variation
            micro_var = 1.0 + random.uniform(-0.08, 0.08)
            radius = int(base_radius * pressure * micro_var)
            radius = max(1, radius)
            
            # Vary opacity slightly for pencil texture effect
            opacity_var = random.uniform(0.85, 1.0)
            color_with_opacity = (
                int(self.color[0] * opacity_var),
                int(self.color[1] * opacity_var),
                int(self.color[2] * opacity_var),
                int(255 * opacity_var * pressure)
            )
            
            # Draw anti-aliased filled circle
            if radius > 0:
                pygame.gfxdraw.aacircle(self.frame_surface, x, y, radius, color_with_opacity)
                pygame.gfxdraw.filled_circle(self.frame_surface, x, y, radius, color_with_opacity)
    
    def _draw_smooth_line(self, p1, p2):
        """Legacy method - kept for compatibility."""
        self._draw_pencil_line(p1, p2, 1.0)
    
    def get_surface(self):
        """Get the frame surface to blit."""
        return self.frame_surface
    
    def get_start_position(self):
        """Get the starting position for the pen."""
        if self.frame_points:
            p = self.frame_points[0]
            return (int(p[0]), int(p[1]))
        return None
    
    def reset(self):
        """Reset the frame animation."""
        self.current_idx = 0
        self.is_complete = False
        if self.frame_surface:
            self.frame_surface.fill((0, 0, 0, 0))
