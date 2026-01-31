#!/usr/bin/env python3
"""
Frame Animator for Magnetic Iron Art
=====================================
Handles the animated decorative border frame that draws around the canvas
after the portrait formation is complete.
"""

import pygame
import pygame.gfxdraw
import math
import random


class FrameAnimator:
    """
    Handles progressive drawing of decorative border frame.
    
    Draws an animated rectangle border around the edge of the canvas,
    supporting customizable thickness, speed, and margin settings.
    """
    
    def __init__(self, width, height, thickness=6, speed=1.0, margin=20, 
                 color=(40, 40, 50)):
        """
        Initialize frame animator.
        
        Args:
            width: Canvas width in pixels
            height: Canvas height in pixels
            thickness: Frame line thickness in pixels
            speed: Drawing speed multiplier (1.0 = normal)
            margin: Margin from canvas edge in pixels
            color: Frame color as RGB tuple
        """
        self.width = width
        self.height = height
        self.thickness = thickness
        self.speed = speed
        self.margin = margin
        self.color = color
        
        # Animation state
        self.frame_points = []
        self.current_idx = 0
        self.is_complete = False
        self.frame_surface = None
        
        # Current pen position for external access
        self.current_pen_pos = None
        
        # Initialize frame points
        self._init_frame_points()
    
    def _init_frame_points(self):
        """
        Initialize the frame points going clockwise from top-left.
        Adds subtle natural wobble for a hand-drawn aesthetic.
        """
        margin = self.margin
        w, h = self.width, self.height
        
        # Create frame points with subtle natural wobble
        self.frame_points = []
        
        # Very subtle wobble for natural, organic look
        wobble_amount = 0.5
        
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
        
        # Reset animation state
        self.current_idx = 0
        self.is_complete = False
        
        # Create a transparent surface for the frame line
        self.frame_surface = pygame.Surface((w, h), pygame.SRCALPHA)
        self.frame_surface.fill((0, 0, 0, 0))  # Fully transparent
        
        # Set initial pen position
        if self.frame_points:
            p = self.frame_points[0]
            self.current_pen_pos = (int(p[0]), int(p[1]))
    
    def update(self):
        """
        Update frame drawing animation for one frame.
        
        Progresses the border drawing animation by drawing multiple
        line segments per call, controlled by the speed setting.
        
        Returns:
            tuple: Current pen position (x, y) or None if animation is complete
        """
        if self.is_complete or not self.frame_points:
            return None
        
        # Calculate points to draw per frame based on speed
        # Base speed of 8 points per frame, scaled by speed multiplier
        points_per_frame = max(3, int(8 * self.speed))
        
        for _ in range(points_per_frame):
            if self.current_idx >= len(self.frame_points) - 1:
                # Frame animation complete
                self.is_complete = True
                self.current_pen_pos = None
                print("Border frame complete!")
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
        
        # Update and return current pen position
        if self.current_idx < len(self.frame_points):
            p = self.frame_points[self.current_idx]
            self.current_pen_pos = (int(p[0]), int(p[1]))
            return self.current_pen_pos
        
        return None
    
    def _draw_smooth_line(self, p1, p2):
        """
        Draw a smooth anti-aliased line with proper thickness.
        
        Uses filled circles along the line for a smooth, brush-like effect.
        
        Args:
            p1: Start point (x, y)
            p2: End point (x, y)
        """
        x1, y1 = p1
        x2, y2 = p2
        
        # Calculate line length and direction
        dx = x2 - x1
        dy = y2 - y1
        dist = max(1, int(math.sqrt(dx * dx + dy * dy)))
        
        # Draw filled circles along the line for smooth thick effect
        radius = max(1, self.thickness // 2)
        
        for i in range(dist + 1):
            t = i / max(1, dist)
            x = int(x1 + dx * t)
            y = int(y1 + dy * t)
            
            # Ensure we're within bounds
            if 0 <= x < self.width and 0 <= y < self.height:
                # Draw anti-aliased filled circle
                pygame.gfxdraw.aacircle(self.frame_surface, x, y, radius, self.color)
                pygame.gfxdraw.filled_circle(self.frame_surface, x, y, radius, self.color)
    
    def get_surface(self):
        """
        Get the frame surface to blit onto the main screen.
        
        Returns:
            pygame.Surface: The transparent surface containing the drawn frame
        """
        return self.frame_surface
    
    def get_start_position(self):
        """
        Get the starting position for the pen cursor.
        
        Returns:
            tuple: Starting position (x, y) or None if no points defined
        """
        if self.frame_points:
            p = self.frame_points[0]
            return (int(p[0]), int(p[1]))
        return None
    
    def get_current_position(self):
        """
        Get the current pen position during animation.
        
        Returns:
            tuple: Current position (x, y) or None if animation is complete
        """
        return self.current_pen_pos
    
    def reset(self):
        """
        Reset the frame animation to the beginning.
        
        Clears the drawn frame and resets all animation state.
        """
        self.current_idx = 0
        self.is_complete = False
        
        if self.frame_surface:
            self.frame_surface.fill((0, 0, 0, 0))
        
        if self.frame_points:
            p = self.frame_points[0]
            self.current_pen_pos = (int(p[0]), int(p[1]))
        else:
            self.current_pen_pos = None
    
    def set_color(self, color):
        """
        Update the frame color.
        
        Args:
            color: New RGB tuple for frame color
        """
        self.color = color
    
    def set_thickness(self, thickness):
        """
        Update the frame thickness.
        
        Args:
            thickness: New thickness in pixels
        """
        self.thickness = thickness
    
    def set_speed(self, speed):
        """
        Update the animation speed.
        
        Args:
            speed: New speed multiplier (1.0 = normal)
        """
        self.speed = speed
    
    def get_progress(self):
        """
        Get the animation progress as a percentage.
        
        Returns:
            float: Progress from 0.0 to 100.0
        """
        if not self.frame_points or len(self.frame_points) <= 1:
            return 100.0
        
        progress = (self.current_idx / (len(self.frame_points) - 1)) * 100.0
        return min(100.0, progress)
    
    @property
    def complete(self):
        """Check if frame animation is complete."""
        return self.is_complete
