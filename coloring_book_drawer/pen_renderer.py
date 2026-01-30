#!/usr/bin/env python3
"""
Pen Renderer for Coloring Book Drawer
======================================
Handles rendering of pen cursor (custom image or default drawn pen).
"""

import pygame
import math
from pathlib import Path


class PenRenderer:
    """Handles rendering of pen cursor at drawing position."""
    
    def __init__(self, custom_pen_path=None, pen_tip_x=0, pen_tip_y=0, 
                 pen_scale=1.0, pen_rotation=True):
        """
        Initialize pen renderer.
        
        Args:
            custom_pen_path: Path to custom pen image (PNG)
            pen_tip_x: X offset to pen tip in custom image
            pen_tip_y: Y offset to pen tip in custom image
            pen_scale: Scale factor for custom pen
            pen_rotation: Whether to rotate pen with drawing direction
        """
        self.custom_pen_path = custom_pen_path
        self.pen_tip_x = pen_tip_x
        self.pen_tip_y = pen_tip_y
        self.pen_scale = pen_scale
        self.pen_rotation = pen_rotation
        self.custom_pen_image = None
        self.prev_pen_angle = -math.pi / 4  # Track for smooth rotation
        
        self._load_custom_pen()
    
    def _load_custom_pen(self):
        """Load custom pen image if provided."""
        if self.custom_pen_path and Path(self.custom_pen_path).exists():
            try:
                self.custom_pen_image = pygame.image.load(self.custom_pen_path).convert_alpha()
                
                # Scale image if needed
                if self.pen_scale != 1.0:
                    w, h = self.custom_pen_image.get_size()
                    new_w = int(w * self.pen_scale)
                    new_h = int(h * self.pen_scale)
                    self.custom_pen_image = pygame.transform.scale(
                        self.custom_pen_image, 
                        (new_w, new_h)
                    )
                    # Scale tip offset too
                    self.pen_tip_x = int(self.pen_tip_x * self.pen_scale)
                    self.pen_tip_y = int(self.pen_tip_y * self.pen_scale)
                
                print(f"Loaded custom pen: {self.custom_pen_path}")
                print(f"Pen tip offset: ({self.pen_tip_x}, {self.pen_tip_y})")
            except Exception as e:
                print(f"Failed to load custom pen: {e}")
                self.custom_pen_image = None
    
    def draw_pen(self, screen, x, y, reveal_engine=None):
        """
        Draw pen cursor at position.
        
        Args:
            screen: Pygame surface to draw on
            x: X position
            y: Y position
            reveal_engine: Optional PixelRevealEngine for rotation calculation
        """
        if self.custom_pen_image:
            self._draw_custom_pen(screen, x, y, reveal_engine)
        else:
            self._draw_default_pen(screen, x, y)
    
    def _draw_custom_pen(self, screen, x, y, reveal_engine):
        """Draw custom pen image at position with optional rotation."""
        if not self.custom_pen_image:
            return
        
        pen_image = self.custom_pen_image
        
        # Calculate rotation angle if enabled
        if self.pen_rotation and reveal_engine:
            # Get drawing direction from recent movement
            idx = reveal_engine.current_reveal_idx
            if idx > 10 and idx < len(reveal_engine.reveal_sequence):
                # Look back a few points to get direction
                curr_y, curr_x, _ = reveal_engine.reveal_sequence[min(idx - 1, len(reveal_engine.reveal_sequence) - 1)]
                prev_y, prev_x, _ = reveal_engine.reveal_sequence[max(0, idx - 10)]
                
                dx = curr_x - prev_x
                dy = curr_y - prev_y
                
                if abs(dx) > 1 or abs(dy) > 1:
                    # Calculate angle in degrees
                    target_angle = math.atan2(dy, dx)
                    
                    # Smooth angle transition
                    angle_diff = target_angle - self.prev_pen_angle
                    # Normalize to [-pi, pi]
                    while angle_diff > math.pi:
                        angle_diff -= 2 * math.pi
                    while angle_diff < -math.pi:
                        angle_diff += 2 * math.pi
                    
                    # Smooth interpolation (0.3 = smoothing factor)
                    self.prev_pen_angle += angle_diff * 0.3
                    
                    # Convert to degrees for pygame
                    angle_deg = -math.degrees(self.prev_pen_angle)
                    
                    # Rotate image
                    pen_image = pygame.transform.rotate(self.custom_pen_image, angle_deg)
        
        # Draw pen image with tip at cursor position
        pen_rect = pen_image.get_rect()
        pen_rect.topleft = (x - self.pen_tip_x, y - self.pen_tip_y)
        screen.blit(pen_image, pen_rect)
    
    def _draw_default_pen(self, screen, x, y):
        """Draw the default programmatic fountain pen cursor."""
        # Pen angle (tilted naturally as if held by right hand)
        angle = -math.pi / 4  # 45 degrees
        
        # Pen dimensions
        nib_length = 12
        body_length = 50
        grip_length = 20
        cap_length = 15
        
        # Calculate points along the pen
        def point_at_dist(dist):
            return (
                x + int(math.cos(angle) * dist),
                y + int(math.sin(angle) * dist)
            )
        
        nib_end = (x, y)
        nib_base = point_at_dist(nib_length)
        grip_end = point_at_dist(nib_length + grip_length)
        body_end = point_at_dist(nib_length + grip_length + body_length)
        cap_end = point_at_dist(nib_length + grip_length + body_length + cap_length)
        
        # Colors
        gold = (200, 165, 80)
        dark_gold = (160, 130, 60)
        black_body = (30, 30, 35)
        dark_body = (20, 20, 25)
        grip_color = (50, 50, 55)
        
        # Draw shadow
        shadow_offset = 3
        for i, (p1, p2, width) in enumerate([
            (nib_end, nib_base, 4),
            (nib_base, grip_end, 7),
            (grip_end, body_end, 8),
            (body_end, cap_end, 6),
        ]):
            sp1 = (p1[0] + shadow_offset, p1[1] + shadow_offset)
            sp2 = (p2[0] + shadow_offset, p2[1] + shadow_offset)
            pygame.draw.line(screen, (180, 180, 180), sp1, sp2, width)
        
        # Draw pen nib (gold/metal color)
        pygame.draw.line(screen, dark_gold, nib_end, nib_base, 4)
        pygame.draw.line(screen, gold, nib_end, nib_base, 2)
        
        # Nib tip (ink point)
        pygame.draw.circle(screen, (20, 20, 30), nib_end, 3)
        pygame.draw.circle(screen, (10, 10, 20), nib_end, 2)
        
        # Draw grip section (textured look)
        pygame.draw.line(screen, grip_color, nib_base, grip_end, 8)
        pygame.draw.line(screen, (60, 60, 65), nib_base, grip_end, 6)
        # Add grip rings
        for i in range(3):
            ring_pos = (
                nib_base[0] + int((grip_end[0] - nib_base[0]) * (0.25 + i * 0.25)),
                nib_base[1] + int((grip_end[1] - nib_base[1]) * (0.25 + i * 0.25))
            )
            pygame.draw.circle(screen, (70, 70, 75), ring_pos, 4)
        
        # Draw main body (elegant black)
        pygame.draw.line(screen, dark_body, grip_end, body_end, 9)
        pygame.draw.line(screen, black_body, grip_end, body_end, 7)
        # Highlight
        mid_body = (
            (grip_end[0] + body_end[0]) // 2 - 1,
            (grip_end[1] + body_end[1]) // 2 - 1
        )
        pygame.draw.line(screen, (45, 45, 50), grip_end, mid_body, 3)
        
        # Draw cap
        pygame.draw.line(screen, (25, 25, 30), body_end, cap_end, 7)
        pygame.draw.line(screen, (35, 35, 40), body_end, cap_end, 5)
        
        # Gold ring at cap junction
        pygame.draw.circle(screen, gold, body_end, 5)
        pygame.draw.circle(screen, dark_gold, body_end, 4)
        
        # Cap top (rounded)
        pygame.draw.circle(screen, (30, 30, 35), cap_end, 4)
        pygame.draw.circle(screen, (40, 40, 45), cap_end, 2)
