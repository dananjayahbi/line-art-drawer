#!/usr/bin/env python3
"""
Frame Animator for Pixel Sorting Art
=====================================
Handles the animated decorative border frame with vaporwave/cyberpunk styling.
Features progressive drawing with gradient and glow effects.
"""

import pygame
import pygame.gfxdraw
import math
import random
from typing import Tuple, List, Optional
from dataclasses import dataclass


@dataclass
class GradientStop:
    """Gradient color stop."""
    position: float  # 0.0 to 1.0
    color: Tuple[int, int, int]


class FrameAnimator:
    """
    Handles progressive drawing of decorative border frame.
    
    Features:
    - Vaporwave/Cyberpunk styled gradients
    - Neon glow effects
    - Animated drawing progression
    - Configurable thickness, speed, margin
    """
    
    # Style presets
    STYLES = {
        "vaporwave": {
            "gradient": [
                GradientStop(0.0, (255, 0, 255)),    # Magenta
                GradientStop(0.25, (255, 113, 206)), # Pink
                GradientStop(0.5, (0, 255, 255)),    # Cyan
                GradientStop(0.75, (185, 103, 255)), # Purple
                GradientStop(1.0, (255, 0, 255)),    # Magenta
            ],
            "glow_color": (255, 0, 255),
            "glow_intensity": 0.6,
        },
        "cyberpunk": {
            "gradient": [
                GradientStop(0.0, (0, 255, 0)),      # Neon green
                GradientStop(0.25, (57, 255, 20)),   # Electric green
                GradientStop(0.5, (255, 255, 0)),    # Yellow
                GradientStop(0.75, (255, 0, 0)),     # Red
                GradientStop(1.0, (0, 255, 0)),      # Neon green
            ],
            "glow_color": (0, 255, 0),
            "glow_intensity": 0.8,
        },
    }
    
    def __init__(
        self,
        width: int,
        height: int,
        thickness: int = 4,
        speed: float = 1.0,
        margin: int = 20,
        color: Tuple[int, int, int] = (255, 0, 255),
        style: str = "vaporwave",
        glow_enabled: bool = True
    ):
        """
        Initialize frame animator.
        
        Args:
            width: Canvas width
            height: Canvas height
            thickness: Frame line thickness
            speed: Drawing speed multiplier
            margin: Margin from edge
            color: Primary frame color (RGB tuple)
            style: Visual style ("vaporwave" or "cyberpunk")
            glow_enabled: Enable neon glow effect
        """
        self.width = width
        self.height = height
        self.thickness = thickness
        self.speed = speed
        self.margin = margin
        self.color = color
        self.style = style
        self.glow_enabled = glow_enabled
        
        # Get style preset
        self.style_preset = self.STYLES.get(style, self.STYLES["vaporwave"])
        
        # Frame path points
        self.frame_points: List[Tuple[float, float]] = []
        self.current_idx: int = 0
        self.is_complete: bool = False
        
        # Surfaces
        self.frame_surface: Optional[pygame.Surface] = None
        self.glow_surface: Optional[pygame.Surface] = None
        
        # Initialize
        self._init_frame_points()
    
    def _init_frame_points(self) -> None:
        """Initialize the frame points going clockwise from top-left."""
        margin = self.margin
        w, h = self.width, self.height
        
        self.frame_points = []
        
        # Subtle wobble for organic feel
        wobble_amount = 0.4
        
        def add_wobble(x: float, y: float, is_horizontal: bool) -> Tuple[float, float]:
            """Add natural hand-drawn wobble to a point."""
            if is_horizontal:
                return (x, y + random.uniform(-wobble_amount, wobble_amount))
            else:
                return (x + random.uniform(-wobble_amount, wobble_amount), y)
        
        # Step size for points
        step = 3
        
        # Top edge (left to right)
        for x in range(margin, w - margin + 1, step):
            self.frame_points.append(add_wobble(float(x), float(margin), True))
        
        # Right edge (top to bottom)
        for y in range(margin, h - margin + 1, step):
            self.frame_points.append(add_wobble(float(w - margin), float(y), False))
        
        # Bottom edge (right to left)
        for x in range(w - margin, margin - 1, -step):
            self.frame_points.append(add_wobble(float(x), float(h - margin), True))
        
        # Left edge (bottom to top)
        for y in range(h - margin, margin - 1, -step):
            self.frame_points.append(add_wobble(float(margin), float(y), False))
        
        self.current_idx = 0
        self.is_complete = False
        
        # Create surfaces
        self.frame_surface = pygame.Surface((w, h), pygame.SRCALPHA)
        self.frame_surface.fill((0, 0, 0, 0))
        
        if self.glow_enabled:
            self.glow_surface = pygame.Surface((w, h), pygame.SRCALPHA)
            self.glow_surface.fill((0, 0, 0, 0))
    
    def _get_gradient_color(self, progress: float) -> Tuple[int, int, int]:
        """
        Get color from gradient at given progress position.
        
        Args:
            progress: Position in gradient (0.0 to 1.0)
            
        Returns:
            RGB color tuple
        """
        gradient = self.style_preset["gradient"]
        
        # Find surrounding gradient stops
        for i in range(len(gradient) - 1):
            if gradient[i].position <= progress <= gradient[i + 1].position:
                # Interpolate between stops
                stop1 = gradient[i]
                stop2 = gradient[i + 1]
                
                # Calculate local progress
                range_size = stop2.position - stop1.position
                if range_size > 0:
                    local_progress = (progress - stop1.position) / range_size
                else:
                    local_progress = 0
                
                # Linear interpolation
                r = int(stop1.color[0] + (stop2.color[0] - stop1.color[0]) * local_progress)
                g = int(stop1.color[1] + (stop2.color[1] - stop1.color[1]) * local_progress)
                b = int(stop1.color[2] + (stop2.color[2] - stop1.color[2]) * local_progress)
                
                return (r, g, b)
        
        # Fallback to primary color
        return self.color
    
    def update(self) -> Optional[Tuple[int, int]]:
        """
        Update frame drawing animation.
        
        Returns:
            Current pen position (x, y) or None if complete
        """
        if self.is_complete or not self.frame_points:
            return None
        
        # Points per frame based on speed
        points_per_frame = max(2, int(6 * self.speed))
        
        for _ in range(points_per_frame):
            if self.current_idx >= len(self.frame_points) - 1:
                self.is_complete = True
                print("[FRAME] Border drawing complete!")
                return None
            
            # Get current and next points
            p1 = self.frame_points[self.current_idx]
            p2 = self.frame_points[self.current_idx + 1]
            
            # Convert to int
            p1_int = (int(p1[0]), int(p1[1]))
            p2_int = (int(p2[0]), int(p2[1]))
            
            # Calculate gradient progress
            progress = self.current_idx / len(self.frame_points)
            gradient_color = self._get_gradient_color(progress)
            
            # Draw line segment
            self._draw_smooth_line(p1_int, p2_int, gradient_color)
            
            # Draw glow if enabled
            if self.glow_enabled:
                self._draw_glow_line(p1_int, p2_int)
            
            self.current_idx += 1
        
        # Return current pen position
        if self.current_idx < len(self.frame_points):
            p = self.frame_points[self.current_idx]
            return (int(p[0]), int(p[1]))
        
        return None
    
    def _draw_smooth_line(
        self, 
        p1: Tuple[int, int], 
        p2: Tuple[int, int],
        color: Tuple[int, int, int]
    ) -> None:
        """Draw a smooth anti-aliased line with gradient color."""
        x1, y1 = p1
        x2, y2 = p2
        
        # Calculate distance
        dx = x2 - x1
        dy = y2 - y1
        dist = max(1, int(math.sqrt(dx * dx + dy * dy)))
        
        # Draw filled circles along the line
        radius = self.thickness // 2
        
        for i in range(dist + 1):
            t = i / max(1, dist)
            x = int(x1 + dx * t)
            y = int(y1 + dy * t)
            
            # Anti-aliased filled circle
            pygame.gfxdraw.aacircle(self.frame_surface, x, y, radius, color)
            pygame.gfxdraw.filled_circle(self.frame_surface, x, y, radius, color)
    
    def _draw_glow_line(
        self, 
        p1: Tuple[int, int], 
        p2: Tuple[int, int]
    ) -> None:
        """Draw glow effect for a line segment."""
        if not self.glow_surface:
            return
        
        x1, y1 = p1
        x2, y2 = p2
        
        glow_color = self.style_preset["glow_color"]
        glow_intensity = self.style_preset["glow_intensity"]
        
        # Calculate distance
        dx = x2 - x1
        dy = y2 - y1
        dist = max(1, int(math.sqrt(dx * dx + dy * dy)))
        
        # Draw glow circles (larger and more transparent)
        glow_radius = self.thickness * 2
        alpha = int(50 * glow_intensity)
        glow_with_alpha = (*glow_color, alpha)
        
        for i in range(0, dist + 1, 2):  # Skip some for performance
            t = i / max(1, dist)
            x = int(x1 + dx * t)
            y = int(y1 + dy * t)
            
            pygame.gfxdraw.filled_circle(
                self.glow_surface, x, y, glow_radius, glow_with_alpha
            )
    
    def get_surface(self) -> Optional[pygame.Surface]:
        """
        Get the combined frame surface (glow + frame).
        
        Returns:
            Combined pygame Surface
        """
        if not self.frame_surface:
            return None
        
        # Create combined surface
        combined = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        
        # Draw glow first (underneath)
        if self.glow_enabled and self.glow_surface:
            combined.blit(self.glow_surface, (0, 0))
        
        # Draw frame on top
        combined.blit(self.frame_surface, (0, 0))
        
        return combined
    
    def get_start_position(self) -> Optional[Tuple[int, int]]:
        """Get the starting position for the pen cursor."""
        if self.frame_points:
            p = self.frame_points[0]
            return (int(p[0]), int(p[1]))
        return None
    
    def get_current_position(self) -> Optional[Tuple[int, int]]:
        """Get the current drawing position."""
        if self.current_idx < len(self.frame_points):
            p = self.frame_points[self.current_idx]
            return (int(p[0]), int(p[1]))
        return None
    
    def get_progress(self) -> float:
        """Get the current drawing progress (0.0 to 1.0)."""
        if len(self.frame_points) == 0:
            return 0.0
        return self.current_idx / len(self.frame_points)
    
    def reset(self) -> None:
        """Reset the frame animation."""
        self.current_idx = 0
        self.is_complete = False
        
        if self.frame_surface:
            self.frame_surface.fill((0, 0, 0, 0))
        
        if self.glow_surface:
            self.glow_surface.fill((0, 0, 0, 0))


class AnimatedFrameCorner:
    """
    Animated corner decoration for the frame.
    Can be used for additional flair at frame corners.
    """
    
    def __init__(
        self,
        x: int,
        y: int,
        size: int = 20,
        corner_type: str = "top_left",
        color: Tuple[int, int, int] = (255, 0, 255),
        style: str = "vaporwave"
    ):
        """
        Initialize corner decoration.
        
        Args:
            x: X position
            y: Y position
            size: Size of corner decoration
            corner_type: "top_left", "top_right", "bottom_left", "bottom_right"
            color: Primary color
            style: Visual style
        """
        self.x = x
        self.y = y
        self.size = size
        self.corner_type = corner_type
        self.color = color
        self.style = style
        
        self.animation_progress = 0.0
        self.is_complete = False
    
    def update(self, dt: float = 1/60) -> None:
        """Update corner animation."""
        if self.is_complete:
            return
        
        self.animation_progress += dt * 2  # Animation speed
        
        if self.animation_progress >= 1.0:
            self.animation_progress = 1.0
            self.is_complete = True
    
    def draw(self, surface: pygame.Surface) -> None:
        """Draw the corner decoration."""
        if self.animation_progress <= 0:
            return
        
        # Calculate animated size
        current_size = int(self.size * self.animation_progress)
        
        # Draw corner lines based on type
        if self.corner_type == "top_left":
            # Horizontal line
            pygame.draw.line(
                surface, self.color,
                (self.x, self.y),
                (self.x + current_size, self.y),
                2
            )
            # Vertical line
            pygame.draw.line(
                surface, self.color,
                (self.x, self.y),
                (self.x, self.y + current_size),
                2
            )
        elif self.corner_type == "top_right":
            pygame.draw.line(
                surface, self.color,
                (self.x, self.y),
                (self.x - current_size, self.y),
                2
            )
            pygame.draw.line(
                surface, self.color,
                (self.x, self.y),
                (self.x, self.y + current_size),
                2
            )
        elif self.corner_type == "bottom_left":
            pygame.draw.line(
                surface, self.color,
                (self.x, self.y),
                (self.x + current_size, self.y),
                2
            )
            pygame.draw.line(
                surface, self.color,
                (self.x, self.y),
                (self.x, self.y - current_size),
                2
            )
        elif self.corner_type == "bottom_right":
            pygame.draw.line(
                surface, self.color,
                (self.x, self.y),
                (self.x - current_size, self.y),
                2
            )
            pygame.draw.line(
                surface, self.color,
                (self.x, self.y),
                (self.x, self.y - current_size),
                2
            )
