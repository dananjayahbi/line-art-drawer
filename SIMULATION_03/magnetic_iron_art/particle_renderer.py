#!/usr/bin/env python3
"""
Particle Renderer for Magnetic Iron Filings
=============================================
Renders iron filing particles with drop shadows, metallic glints,
and motion blur effects for cinematic visual quality.
"""

import pygame
import pygame.gfxdraw
import numpy as np
import math
from pathlib import Path


class ParticleRenderer:
    """
    Renders magnetic iron filing particles with visual effects.
    
    Features:
    - Charcoal-gray metallic particles
    - Drop shadows for depth
    - Metallic glints/highlights
    - Motion blur for moving particles
    - Dipole orientation visualization
    """
    
    def __init__(self, particle_color=(61, 61, 61), 
                 shadow_enabled=True, glints_enabled=True,
                 motion_blur_enabled=True, shadow_offset=(2, 2)):
        """
        Initialize particle renderer.
        
        Args:
            particle_color: RGB tuple for base particle color
            shadow_enabled: Whether to render drop shadows
            glints_enabled: Whether to render metallic highlights
            motion_blur_enabled: Whether to render motion blur
            shadow_offset: (x, y) offset for shadows
        """
        self.particle_color = particle_color
        self.shadow_enabled = shadow_enabled
        self.glints_enabled = glints_enabled
        self.motion_blur_enabled = motion_blur_enabled
        self.shadow_offset = shadow_offset
        
        # Shadow properties
        self.shadow_color = (40, 35, 30, 80)  # Semi-transparent dark
        self.shadow_blur_radius = 3
        
        # Glint properties
        self.glint_color = (180, 175, 170)  # Light metallic
        self.glint_size_ratio = 0.3  # Size relative to particle
        
        # Motion blur
        self.blur_trail_count = 3
        self.blur_alpha_decay = 0.4
        
        # Pre-rendered particle cache for performance
        self.particle_cache = {}
        self._generate_particle_cache()
    
    def _generate_particle_cache(self):
        """Pre-render particle images for common sizes."""
        for size in range(1, 8):
            self.particle_cache[size] = self._create_particle_surface(size)
    
    def _create_particle_surface(self, size):
        """
        Create a particle surface with all effects.
        
        Args:
            size: Particle diameter in pixels
            
        Returns:
            pygame.Surface with the rendered particle
        """
        # Surface needs extra space for shadow
        surface_size = size + 10
        surface = pygame.Surface((surface_size, surface_size), pygame.SRCALPHA)
        
        center = surface_size // 2
        
        # Draw shadow
        if self.shadow_enabled:
            shadow_x = center + self.shadow_offset[0]
            shadow_y = center + self.shadow_offset[1]
            
            for i in range(self.shadow_blur_radius, 0, -1):
                alpha = int(60 * (1 - i / self.shadow_blur_radius))
                shadow_color = (40, 35, 30, alpha)
                pygame.gfxdraw.filled_circle(
                    surface, shadow_x, shadow_y, 
                    size // 2 + i, shadow_color
                )
        
        # Draw main particle body (elongated for iron filing shape)
        # Base dark color
        pygame.gfxdraw.filled_circle(
            surface, center, center, 
            size // 2, (*self.particle_color, 255)
        )
        
        # Anti-aliased edge
        pygame.gfxdraw.aacircle(
            surface, center, center,
            size // 2, (*self.particle_color, 255)
        )
        
        # Draw metallic glint
        if self.glints_enabled and size >= 2:
            glint_size = max(1, int(size * self.glint_size_ratio))
            glint_x = center - size // 4
            glint_y = center - size // 4
            
            pygame.gfxdraw.filled_circle(
                surface, glint_x, glint_y,
                glint_size, (*self.glint_color, 200)
            )
        
        return surface
    
    def render_particles(self, screen, particles_data, background_color=(245, 240, 230)):
        """
        Render all particles to the screen.
        
        Args:
            screen: Pygame surface to render to
            particles_data: List of (x, y, angle, size, attracted) tuples
            background_color: Background color for blending
        """
        # Create particle layer with alpha
        particle_layer = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        
        for x, y, angle, size, attracted in particles_data:
            # Skip particles outside screen bounds
            if x < -50 or x > screen.get_width() + 50:
                continue
            if y < -50 or y > screen.get_height() + 50:
                continue
            
            # Get cached particle or create new one
            size_key = max(1, min(7, int(size)))
            
            if size_key in self.particle_cache:
                particle_surf = self.particle_cache[size_key].copy()
            else:
                particle_surf = self._create_particle_surface(size_key)
            
            # Rotate particle based on dipole angle
            rotated_surf = pygame.transform.rotate(particle_surf, -math.degrees(angle))
            
            # Calculate blit position (centered)
            rect = rotated_surf.get_rect(center=(int(x), int(y)))
            
            # Blit to particle layer
            particle_layer.blit(rotated_surf, rect)
        
        # Blit particle layer to screen
        screen.blit(particle_layer, (0, 0))
    
    def render_particles_with_motion_blur(self, screen, particles_data, 
                                           prev_positions=None):
        """
        Render particles with motion blur trails.
        
        Args:
            screen: Pygame surface to render to
            particles_data: Current particle positions
            prev_positions: Previous frame positions for blur calculation
        """
        if not self.motion_blur_enabled or prev_positions is None:
            self.render_particles(screen, particles_data)
            return
        
        # Create layers for blur effect
        blur_layer = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        
        for i, (x, y, angle, size, attracted) in enumerate(particles_data):
            if i < len(prev_positions):
                px, py = prev_positions[i][:2]
                
                # Draw blur trail
                dx = x - px
                dy = y - py
                speed = math.sqrt(dx**2 + dy**2)
                
                if speed > 2:  # Only blur if moving fast enough
                    for t in range(self.blur_trail_count):
                        trail_alpha = int(100 * (1 - t / self.blur_trail_count) 
                                         * self.blur_alpha_decay)
                        
                        trail_x = px + dx * (t / self.blur_trail_count)
                        trail_y = py + dy * (t / self.blur_trail_count)
                        
                        # Draw faded particle
                        trail_size = max(1, int(size * 0.8))
                        pygame.gfxdraw.filled_circle(
                            blur_layer,
                            int(trail_x), int(trail_y),
                            trail_size,
                            (*self.particle_color, trail_alpha)
                        )
        
        screen.blit(blur_layer, (0, 0))
        
        # Draw main particles on top
        self.render_particles(screen, particles_data)
    
    def render_elongated_particles(self, screen, particles_data):
        """
        Render particles as elongated iron filings (capsule shapes).
        
        Args:
            screen: Pygame surface to render to
            particles_data: List of particle data
        """
        particle_layer = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        
        for x, y, angle, size, attracted in particles_data:
            # Skip off-screen particles
            if x < -50 or x > screen.get_width() + 50:
                continue
            if y < -50 or y > screen.get_height() + 50:
                continue
            
            # Calculate elongated shape endpoints
            length = size * 2.5  # Elongation factor
            half_len = length / 2
            
            # Endpoints based on angle
            dx = math.cos(angle) * half_len
            dy = math.sin(angle) * half_len
            
            x1, y1 = int(x - dx), int(y - dy)
            x2, y2 = int(x + dx), int(y + dy)
            
            # Draw shadow first
            if self.shadow_enabled:
                shadow_x1 = x1 + self.shadow_offset[0]
                shadow_y1 = y1 + self.shadow_offset[1]
                shadow_x2 = x2 + self.shadow_offset[0]
                shadow_y2 = y2 + self.shadow_offset[1]
                
                pygame.draw.line(
                    particle_layer,
                    (40, 35, 30, 60),
                    (shadow_x1, shadow_y1),
                    (shadow_x2, shadow_y2),
                    max(1, int(size * 0.8))
                )
            
            # Draw main filing shape
            thickness = max(1, int(size * 0.6))
            
            # Main body
            pygame.draw.line(
                particle_layer,
                (*self.particle_color, 255),
                (x1, y1), (x2, y2),
                thickness
            )
            
            # End caps for rounded look
            cap_radius = thickness // 2
            pygame.gfxdraw.filled_circle(
                particle_layer, x1, y1, cap_radius,
                (*self.particle_color, 255)
            )
            pygame.gfxdraw.filled_circle(
                particle_layer, x2, y2, cap_radius,
                (*self.particle_color, 255)
            )
            
            # Metallic glint
            if self.glints_enabled and size >= 2:
                glint_x = int(x - dx * 0.3)
                glint_y = int(y - dy * 0.3 - 1)
                pygame.gfxdraw.pixel(
                    particle_layer, glint_x, glint_y,
                    (*self.glint_color, 180)
                )
        
        screen.blit(particle_layer, (0, 0))
    
    def set_particle_color(self, color):
        """Update particle color and regenerate cache."""
        self.particle_color = color
        self.particle_cache.clear()
        self._generate_particle_cache()
    
    def set_effects(self, shadows=None, glints=None, motion_blur=None):
        """Update visual effect settings."""
        if shadows is not None:
            self.shadow_enabled = shadows
        if glints is not None:
            self.glints_enabled = glints
        if motion_blur is not None:
            self.motion_blur_enabled = motion_blur
        
        # Regenerate cache with new settings
        self.particle_cache.clear()
        self._generate_particle_cache()


class MagnetRenderer:
    """Renders the magnet/cursor indicator."""
    
    def __init__(self, custom_magnet_path=None, magnet_scale=0.5):
        """
        Initialize magnet renderer.
        
        Args:
            custom_magnet_path: Path to custom magnet image
            magnet_scale: Scale factor for magnet image
        """
        self.custom_magnet_path = custom_magnet_path
        self.magnet_scale = magnet_scale
        self.magnet_image = None
        
        if custom_magnet_path and Path(custom_magnet_path).exists():
            self._load_custom_magnet()
    
    def _load_custom_magnet(self):
        """Load custom magnet image."""
        try:
            img = pygame.image.load(self.custom_magnet_path)
            
            # Scale image
            new_width = int(img.get_width() * self.magnet_scale)
            new_height = int(img.get_height() * self.magnet_scale)
            
            self.magnet_image = pygame.transform.smoothscale(
                img, (new_width, new_height)
            )
        except Exception as e:
            print(f"Failed to load custom magnet: {e}")
            self.magnet_image = None
    
    def draw_magnet(self, screen, x, y, active=True):
        """
        Draw the magnet indicator at position.
        
        Args:
            screen: Pygame surface
            x, y: Position
            active: Whether magnet is active
        """
        if self.magnet_image:
            # Draw custom magnet image centered
            rect = self.magnet_image.get_rect(center=(int(x), int(y)))
            screen.blit(self.magnet_image, rect)
        else:
            # Draw default magnet indicator
            self._draw_default_magnet(screen, x, y, active)
    
    def _draw_default_magnet(self, screen, x, y, active):
        """Draw default magnet indicator."""
        x, y = int(x), int(y)
        
        # Outer glow when active
        if active:
            for r in range(25, 15, -2):
                alpha = int(50 * (1 - (r - 15) / 10))
                glow_surf = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
                pygame.gfxdraw.filled_circle(
                    glow_surf, r, r, r,
                    (100, 150, 255, alpha)
                )
                screen.blit(glow_surf, (x - r, y - r))
        
        # Magnet body (horseshoe shape simplified as two poles)
        color = (180, 50, 50) if active else (100, 100, 100)
        
        # North pole (red)
        pygame.gfxdraw.filled_circle(screen, x - 8, y, 6, (200, 60, 60))
        pygame.gfxdraw.aacircle(screen, x - 8, y, 6, (180, 40, 40))
        
        # South pole (blue)
        pygame.gfxdraw.filled_circle(screen, x + 8, y, 6, (60, 60, 200))
        pygame.gfxdraw.aacircle(screen, x + 8, y, 6, (40, 40, 180))
        
        # Connector bar
        pygame.draw.rect(screen, (80, 80, 80), (x - 8, y - 3, 16, 6))
        
        # Field lines indicator
        if active:
            for angle in range(0, 360, 45):
                rad = math.radians(angle)
                lx = x + math.cos(rad) * 20
                ly = y + math.sin(rad) * 20
                pygame.gfxdraw.pixel(screen, int(lx), int(ly), (150, 150, 200))
