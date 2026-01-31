#!/usr/bin/env python3
"""
Sand Renderer - Rendering system for sand particles
===================================================
Handles rendering of sand particles, effects, and visual feedback.
"""

import pygame
import pygame.gfxdraw
import math
from typing import List, Tuple
from physics_engine import SandParticle


class SandRenderer:
    """Renderer for sand particles and visual effects."""
    
    def __init__(self, width: int, height: int):
        """
        Initialize sand renderer.
        
        Args:
            width: Screen width
            height: Screen height
        """
        self.width = width
        self.height = height
        
        # Rendering options
        self.show_physics_debug = False
        self.particle_glow = True
        self.show_target_outline = False
        self.show_container = True  # Show container frame
        
        # Container bounds (will be updated by physics engine)
        self.container_bounds = None
        
    def render_particles(self, screen: pygame.Surface, particles: List[SandParticle], 
                        antialiasing: bool = True):
        """
        Render all sand particles.
        
        Args:
            screen: Pygame surface to render on
            particles: List of particles to render
            antialiasing: Use anti-aliased circles
        """
        for particle in particles:
            x = int(particle.body.position.x)
            y = int(particle.body.position.y)
            radius = int(particle.shape.radius)
            
            # Ensure color is tuple of ints (not numpy types)
            color = (int(particle.color[0]), int(particle.color[1]), int(particle.color[2]))
            
            # Validate coordinates are within screen bounds
            if x < 0 or x >= self.width or y < 0 or y >= self.height:
                continue
            
            # Draw particle
            if antialiasing and radius > 0:
                # Anti-aliased filled circle
                try:
                    pygame.gfxdraw.aacircle(screen, x, y, radius, color)
                    pygame.gfxdraw.filled_circle(screen, x, y, radius, color)
                except (OverflowError, ValueError):
                    # Fallback to regular circle if antialiasing fails
                    pygame.draw.circle(screen, color, (x, y), radius)
            else:
                # Regular circle (faster)
                pygame.draw.circle(screen, color, (x, y), radius)
            
            # Subtle glow for active particles
            if self.particle_glow and not particle.settled:
                glow_color = (
                    min(255, int(color[0]) + 30),
                    min(255, int(color[1]) + 30),
                    min(255, int(color[2]) + 30)
                )
                glow_radius = radius + 1
                if glow_radius > 0 and x >= 0 and y >= 0:
                    try:
                        pygame.gfxdraw.aacircle(screen, x, y, glow_radius, glow_color)
                    except (OverflowError, ValueError):
                        pass  # Skip glow if it fails
    
    def render_spawn_area(self, screen: pygame.Surface, spawn_y: int, spawn_width: int,
                         color: Tuple[int, int, int] = (255, 255, 0), alpha: int = 50):
        """
        Render the spawn area indicator.
        
        Args:
            screen: Pygame surface
            spawn_y: Y position of spawn line
            spawn_width: Width of spawn area
            color: Indicator color
            alpha: Transparency (0-255)
        """
        # Create semi-transparent surface
        indicator = pygame.Surface((spawn_width, 3), pygame.SRCALPHA)
        indicator.fill((*color, alpha))
        
        x_start = (self.width - spawn_width) // 2
        screen.blit(indicator, (x_start, spawn_y))
    
    def render_target_outline(self, screen: pygame.Surface, target_surface: pygame.Surface,
                             offset_x: int = 0, offset_y: int = 0, color: Tuple[int, int, int] = (100, 100, 255)):
        """
        Render outline of target image.
        
        Args:
            screen: Pygame surface
            target_surface: Target image surface
            offset_x: X offset for target
            offset_y: Y offset for target
            color: Outline color
        """
        if not self.show_target_outline:
            return
        
        # Draw semi-transparent overlay
        overlay = target_surface.copy()
        overlay.set_alpha(30)
        screen.blit(overlay, (offset_x, offset_y))
        
        # Draw border
        rect = pygame.Rect(offset_x, offset_y, target_surface.get_width(), target_surface.get_height())
        pygame.draw.rect(screen, color, rect, 2)
    
    def render_stats(self, screen: pygame.Surface, stats: dict, x: int = 10, y: int = 10):
        """
        Render statistics overlay.
        
        Args:
            screen: Pygame surface
            stats: Statistics dictionary
            x: X position
            y: Y position
        """
        font = pygame.font.SysFont('Consolas', 16)
        line_height = 20
        
        # Background
        stats_height = len(stats) * line_height + 20
        bg_surface = pygame.Surface((250, stats_height), pygame.SRCALPHA)
        bg_surface.fill((0, 0, 0, 180))
        screen.blit(bg_surface, (x - 5, y - 5))
        
        # Render each stat
        current_y = y
        for key, value in stats.items():
            # Format key
            display_key = key.replace('_', ' ').title()
            text = f"{display_key}: {value}"
            
            # Render text
            text_surface = font.render(text, True, (255, 255, 255))
            screen.blit(text_surface, (x, current_y))
            current_y += line_height
    
    def render_progress_bar(self, screen: pygame.Surface, progress: float, 
                           x: int, y: int, width: int = 300, height: int = 20):
        """
        Render progress bar.
        
        Args:
            screen: Pygame surface
            progress: Progress value (0.0 to 1.0)
            x: X position
            y: Y position
            width: Bar width
            height: Bar height
        """
        # Clamp progress
        progress = max(0.0, min(1.0, progress))
        
        # Background
        bg_rect = pygame.Rect(x, y, width, height)
        pygame.draw.rect(screen, (50, 50, 50), bg_rect)
        pygame.draw.rect(screen, (100, 100, 100), bg_rect, 2)
        
        # Progress fill
        fill_width = int(width * progress)
        if fill_width > 0:
            fill_rect = pygame.Rect(x, y, fill_width, height)
            
            # Gradient effect
            for i in range(fill_width):
                ratio = i / fill_width
                color = (
                    int(100 + 155 * ratio),
                    int(200 - 100 * ratio),
                    int(50)
                )
                pygame.draw.line(screen, color, (x + i, y), (x + i, y + height))
        
        # Progress text
        font = pygame.font.SysFont('Arial', 14, bold=True)
        progress_text = f"{int(progress * 100)}%"
        text_surface = font.render(progress_text, True, (255, 255, 255))
        text_rect = text_surface.get_rect(center=(x + width // 2, y + height // 2))
        screen.blit(text_surface, text_rect)
    
    def render_pause_overlay(self, screen: pygame.Surface):
        """Render pause overlay."""
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 100))
        screen.blit(overlay, (0, 0))
        
        # Pause text
        font = pygame.font.SysFont('Arial', 72, bold=True)
        text = font.render("PAUSED", True, (255, 255, 255))
        text_rect = text.get_rect(center=(self.width // 2, self.height // 2))
        
        # Shadow
        shadow = font.render("PAUSED", True, (0, 0, 0))
        screen.blit(shadow, (text_rect.x + 3, text_rect.y + 3))
        screen.blit(text, text_rect)
    
    def render_container_frame(self, screen: pygame.Surface, container_bounds: dict,
                               color: Tuple[int, int, int] = (80, 80, 100), thickness: int = 10):
        """
        Render the container frame that holds the sand.
        
        Args:
            screen: Pygame surface
            container_bounds: Dictionary with 'left', 'right', 'top', 'bottom' keys
            color: Frame color
            thickness: Frame thickness
        """
        if not container_bounds:
            return
        
        left = container_bounds['left']
        right = container_bounds['right']
        top = container_bounds['top']
        bottom = container_bounds['bottom']
        
        # Draw frame borders with rounded corners
        # Left wall
        pygame.draw.line(screen, color, (left, top), (left, bottom), thickness)
        
        # Right wall
        pygame.draw.line(screen, color, (right, top), (right, bottom), thickness)
        
        # Bottom
        pygame.draw.line(screen, color, (left, bottom), (right, bottom), thickness)
        
        # Add decorative corners
        corner_size = 20
        corner_color = (120, 120, 140)
        
        # Bottom-left corner
        pygame.draw.circle(screen, corner_color, (left, bottom), corner_size // 2)
        
        # Bottom-right corner
        pygame.draw.circle(screen, corner_color, (right, bottom), corner_size // 2)

