#!/usr/bin/env python3
"""
Paint Renderer for Pendulum Paint Art
=======================================
Renders thick, glossy paint drops with bevel effects and specular highlights.
Creates a wet acrylic paint look with trails on a dark matte studio floor.

Features:
- Glossy paint rendering with specular highlights
- Bevel effect for 3D appearance
- Trail rendering with fade
- Pendulum arm and bob visualization
"""

import pygame
import pygame.gfxdraw
import math
import numpy as np


class PaintRenderer:
    """
    Renders paint drops with glossy, wet acrylic appearance.
    Also handles pendulum visualization and floor rendering.
    """
    
    def __init__(self, canvas_width, canvas_height, 
                 paint_color=(44, 24, 16),
                 floor_color=(30, 28, 26),
                 show_pendulum=True,
                 show_trails=True):
        """
        Initialize paint renderer.
        
        Args:
            canvas_width: Width of the canvas
            canvas_height: Height of the canvas
            paint_color: RGB tuple for paint color
            floor_color: RGB tuple for floor/background color
            show_pendulum: Whether to render pendulum arm and bob
            show_trails: Whether to render paint trails
        """
        self.canvas_width = canvas_width
        self.canvas_height = canvas_height
        self.paint_color = paint_color
        self.floor_color = floor_color
        self.show_pendulum = show_pendulum
        self.show_trails = show_trails
        
        # Pre-compute lighting parameters
        self.light_angle = math.radians(-45)  # Light from top-left
        self.highlight_offset = 0.3  # Offset for specular highlight
        
        # Paint layer surface (accumulated paint)
        self.paint_surface = pygame.Surface((canvas_width, canvas_height), pygame.SRCALPHA)
        
        # Trail surface (for pendulum path)
        self.trail_surface = pygame.Surface((canvas_width, canvas_height), pygame.SRCALPHA)
        
        # Pendulum rendering colors
        self.arm_color = (80, 80, 85)
        self.bob_color = (120, 115, 110)
        self.bob_highlight = (180, 175, 170)
    
    def render_floor(self, screen):
        """
        Render the dark matte studio floor background.
        
        Args:
            screen: Pygame surface to draw on
        """
        screen.fill(self.floor_color)
        
        # Add subtle texture/grain
        for i in range(0, self.canvas_height, 20):
            for j in range(0, self.canvas_width, 20):
                # Subtle color variation
                variation = np.random.randint(-3, 4)
                color = tuple(max(0, min(255, c + variation)) for c in self.floor_color)
                rect = pygame.Rect(j, i, 20, 20)
                pygame.draw.rect(screen, color, rect)
        
        # Add very subtle vignette effect at edges
        self._render_vignette(screen)
    
    def _render_vignette(self, screen):
        """Add subtle vignette darkening at edges."""
        vignette = pygame.Surface((self.canvas_width, self.canvas_height), pygame.SRCALPHA)
        
        # Create radial gradient from center
        center_x = self.canvas_width // 2
        center_y = self.canvas_height // 2
        max_dist = math.sqrt(center_x**2 + center_y**2)
        
        # Draw concentric rectangles with increasing darkness
        for i in range(10):
            alpha = int(i * 2)  # Very subtle
            margin = int((10 - i) * max_dist / 15)
            
            rect = pygame.Rect(margin, margin, 
                             self.canvas_width - 2*margin, 
                             self.canvas_height - 2*margin)
            pygame.draw.rect(vignette, (0, 0, 0, alpha), rect, 1)
        
        screen.blit(vignette, (0, 0))
    
    def render_paint_drop(self, surface, x, y, radius, opacity=1.0):
        """
        Render a single glossy paint drop with bevel and specular highlight.
        
        Args:
            surface: Pygame surface to draw on
            x: X position
            y: Y position
            radius: Drop radius
            opacity: Opacity (0.0-1.0)
        """
        if radius < 1:
            return
        
        x, y = int(x), int(y)
        radius = int(radius)
        
        # Base paint color with opacity
        base_r, base_g, base_b = self.paint_color
        alpha = int(255 * opacity)
        
        # Outer shadow (darker ring)
        shadow_radius = radius + 2
        shadow_color = (
            max(0, base_r - 20),
            max(0, base_g - 20),
            max(0, base_b - 20),
            int(alpha * 0.5)
        )
        pygame.gfxdraw.filled_circle(surface, x + 1, y + 1, shadow_radius, shadow_color)
        
        # Main paint body
        body_color = (base_r, base_g, base_b, alpha)
        pygame.gfxdraw.filled_circle(surface, x, y, radius, body_color)
        pygame.gfxdraw.aacircle(surface, x, y, radius, body_color)
        
        # Inner bevel (darker bottom edge for 3D effect)
        bevel_radius = int(radius * 0.85)
        if bevel_radius > 2:
            bevel_color = (
                max(0, base_r - 15),
                max(0, base_g - 15),
                max(0, base_b - 15),
                int(alpha * 0.6)
            )
            bevel_y = y + int(radius * 0.15)
            pygame.gfxdraw.filled_circle(surface, x, bevel_y, bevel_radius, bevel_color)
        
        # Specular highlight (glossy wet look)
        if radius > 4:
            highlight_radius = max(2, int(radius * 0.3))
            highlight_x = x - int(radius * self.highlight_offset)
            highlight_y = y - int(radius * self.highlight_offset)
            
            # Primary highlight
            highlight_color = (
                min(255, base_r + 80),
                min(255, base_g + 80),
                min(255, base_b + 80),
                int(alpha * 0.7)
            )
            pygame.gfxdraw.filled_circle(surface, highlight_x, highlight_y, 
                                         highlight_radius, highlight_color)
            
            # Secondary smaller highlight
            if radius > 8:
                small_highlight_radius = max(1, int(radius * 0.15))
                small_x = highlight_x - int(radius * 0.1)
                small_y = highlight_y - int(radius * 0.1)
                bright_highlight = (
                    min(255, base_r + 120),
                    min(255, base_g + 120),
                    min(255, base_b + 120),
                    int(alpha * 0.9)
                )
                pygame.gfxdraw.filled_circle(surface, small_x, small_y,
                                            small_highlight_radius, bright_highlight)
    
    def render_all_drips(self, drips):
        """
        Render all paint drips to the paint surface.
        
        Args:
            drips: List of drip dictionaries from DripEngine
        """
        for drip in drips:
            # Calculate opacity based on age
            age_factor = 1.0 - (drip['age'] / 120) * 0.3  # Slight fade
            opacity = drip['opacity'] * age_factor
            
            self.render_paint_drop(
                self.paint_surface,
                drip['x'],
                drip['y'],
                drip['radius'],
                opacity
            )
    
    def render_paint_accumulation(self, accumulation_map):
        """
        Render accumulated paint based on density map.
        
        Args:
            accumulation_map: 2D numpy array of paint density (0-1)
        """
        # This is called less frequently for performance
        # Convert accumulation to paint visualization
        h, w = accumulation_map.shape
        
        # Find areas with significant paint
        threshold = 0.2
        paint_mask = accumulation_map > threshold
        
        # Get coordinates of painted areas
        ys, xs = np.where(paint_mask)
        
        # Sample points to render (for performance)
        sample_rate = 10
        for i in range(0, len(xs), sample_rate):
            x, y = xs[i], ys[i]
            intensity = accumulation_map[y, x]
            radius = int(3 + intensity * 5)
            self.render_paint_drop(self.paint_surface, x, y, radius, intensity * 0.5)
    
    def render_trail(self, positions, max_age=100):
        """
        Render pendulum movement trail.
        
        Args:
            positions: List of (x, y, time) tuples
            max_age: Maximum trail age to display
        """
        if not self.show_trails or len(positions) < 2:
            return
        
        # Clear trail surface with fade
        fade_surface = pygame.Surface((self.canvas_width, self.canvas_height), pygame.SRCALPHA)
        fade_surface.fill((0, 0, 0, 5))  # Very subtle fade
        self.trail_surface.blit(fade_surface, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)
        
        # Draw recent trail points
        for i in range(max(0, len(positions) - max_age), len(positions) - 1):
            x1, y1, t1 = positions[i]
            x2, y2, t2 = positions[i + 1]
            
            # Age-based alpha
            age = len(positions) - i
            alpha = int(255 * (1 - age / max_age) * 0.3)
            
            if alpha > 0:
                trail_color = (*self.paint_color[:3], alpha)
                pygame.draw.line(self.trail_surface, trail_color,
                               (int(x1), int(y1)), (int(x2), int(y2)), 2)
    
    def render_pendulum(self, screen, pivot_pos, bob_pos):
        """
        Render the pendulum arm and bob.
        
        Args:
            screen: Pygame surface to draw on
            pivot_pos: (x, y) position of pivot point
            bob_pos: (x, y) position of bob
        """
        if not self.show_pendulum:
            return
        
        px, py = int(pivot_pos[0]), int(pivot_pos[1])
        bx, by = int(bob_pos[0]), int(bob_pos[1])
        
        # Draw arm shadow
        shadow_offset = 3
        pygame.draw.line(screen, (20, 20, 20),
                        (px + shadow_offset, py + shadow_offset),
                        (bx + shadow_offset, by + shadow_offset), 4)
        
        # Draw arm (metallic look)
        pygame.draw.line(screen, self.arm_color, (px, py), (bx, by), 3)
        pygame.draw.line(screen, (100, 100, 105), (px, py), (bx, by), 1)
        
        # Draw pivot point
        pygame.gfxdraw.filled_circle(screen, px, py, 8, (60, 60, 65))
        pygame.gfxdraw.aacircle(screen, px, py, 8, (80, 80, 85))
        pygame.gfxdraw.filled_circle(screen, px - 2, py - 2, 3, (100, 100, 105))
        
        # Draw bob (paint container)
        bob_radius = 15
        
        # Shadow
        pygame.gfxdraw.filled_circle(screen, bx + 2, by + 2, bob_radius + 2, (20, 20, 20))
        
        # Main bob body
        pygame.gfxdraw.filled_circle(screen, bx, by, bob_radius, self.bob_color)
        pygame.gfxdraw.aacircle(screen, bx, by, bob_radius, self.arm_color)
        
        # Highlight
        pygame.gfxdraw.filled_circle(screen, bx - 4, by - 4, 5, self.bob_highlight)
        
        # Paint drip indicator at bottom of bob
        drip_y = by + bob_radius
        pygame.gfxdraw.filled_circle(screen, bx, drip_y, 4, self.paint_color)
        pygame.gfxdraw.aacircle(screen, bx, drip_y, 4, self.paint_color)
    
    def get_paint_surface(self):
        """Get the accumulated paint surface."""
        return self.paint_surface
    
    def get_trail_surface(self):
        """Get the trail surface."""
        return self.trail_surface
    
    def clear_paint(self):
        """Clear all accumulated paint."""
        self.paint_surface.fill((0, 0, 0, 0))
    
    def clear_trails(self):
        """Clear trails."""
        self.trail_surface.fill((0, 0, 0, 0))
    
    def reset(self):
        """Reset all rendering surfaces."""
        self.clear_paint()
        self.clear_trails()
    
    def set_paint_color(self, color):
        """Set paint color (RGB tuple)."""
        self.paint_color = color
    
    def set_show_pendulum(self, show):
        """Set whether to show pendulum."""
        self.show_pendulum = show
    
    def set_show_trails(self, show):
        """Set whether to show trails."""
        self.show_trails = show
