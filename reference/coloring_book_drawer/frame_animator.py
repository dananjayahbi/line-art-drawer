#!/usr/bin/env python3
"""
Frame Animator for Coloring Book Drawer
========================================
Handles the animated border frame that draws around completed artwork.
"""

import pygame
import pygame.gfxdraw
import math
import random


class FrameAnimator:
    """Handles progressive drawing of decorative border frame."""
    
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
        
        self._init_frame_points()
    
    def _init_frame_points(self):
        """Initialize the frame points going clockwise from top-left."""
        margin = self.margin
        w, h = self.width, self.height
        
        # Create frame points with subtle natural wobble
        self.frame_points = []
        
        wobble_amount = 0.6  # Very subtle wobble for natural look
        
        def add_wobble(x, y, is_horizontal_edge):
            """Add natural hand-drawn wobble to a point."""
            if is_horizontal_edge:
                # Wobble vertically on horizontal edges
                return (x, y + random.uniform(-wobble_amount, wobble_amount))
            else:
                # Wobble horizontally on vertical edges
                return (x + random.uniform(-wobble_amount, wobble_amount), y)
        
        # Top edge (left to right) - horizontal edge
        for x in range(margin, w - margin + 1, 4):
            self.frame_points.append(add_wobble(x, margin, True))
        
        # Right edge (top to bottom) - vertical edge
        for y in range(margin, h - margin + 1, 4):
            self.frame_points.append(add_wobble(w - margin, y, False))
        
        # Bottom edge (right to left) - horizontal edge
        for x in range(w - margin, margin - 1, -4):
            self.frame_points.append(add_wobble(x, h - margin, True))
        
        # Left edge (bottom to top) - vertical edge
        for y in range(h - margin, margin - 1, -4):
            self.frame_points.append(add_wobble(margin, y, False))
        
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
        # Base speed of 8 points per frame, scaled by speed
        points_per_frame = max(3, int(8 * self.speed))
        
        for _ in range(points_per_frame):
            if self.current_idx >= len(self.frame_points) - 1:
                # Frame complete
                self.is_complete = True
                print("Frame complete!")
                return None
            
            # Draw line segment from current point to next
            p1 = self.frame_points[self.current_idx]
            p2 = self.frame_points[self.current_idx + 1]
            
            # Convert to int for pygame
            p1_int = (int(p1[0]), int(p1[1]))
            p2_int = (int(p2[0]), int(p2[1]))
            
            # Draw smooth anti-aliased thick line
            self._draw_smooth_line(p1_int, p2_int)
            
            self.current_idx += 1
        
        # Return current pen position
        if self.current_idx < len(self.frame_points):
            p = self.frame_points[self.current_idx]
            return (int(p[0]), int(p[1]))
        
        return None
    
    def _draw_smooth_line(self, p1, p2):
        """Draw a smooth anti-aliased line with proper thickness using filled circles."""
        x1, y1 = p1
        x2, y2 = p2
        
        # Calculate line length and direction
        dx = x2 - x1
        dy = y2 - y1
        dist = max(1, int(math.sqrt(dx*dx + dy*dy)))
        
        # Draw filled circles along the line for smooth thick effect
        radius = self.thickness // 2
        for i in range(dist + 1):
            t = i / max(1, dist)
            x = int(x1 + dx * t)
            y = int(y1 + dy * t)
            
            # Draw anti-aliased filled circle
            pygame.gfxdraw.aacircle(self.frame_surface, x, y, radius, self.color)
            pygame.gfxdraw.filled_circle(self.frame_surface, x, y, radius, self.color)
    
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
