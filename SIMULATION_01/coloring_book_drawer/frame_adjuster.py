#!/usr/bin/env python3
"""
Frame Adjuster for Coloring Book Drawer
========================================
Interactive window for adjusting the frame margin around artwork.
Uses arrow keys to increase/decrease margin in real-time.
"""

import pygame
import pygame.gfxdraw
import sys
from pathlib import Path
import cv2
import numpy as np


class FrameAdjuster:
    """
    Interactive frame margin adjuster.
    
    Opens a pygame window showing the image with a frame overlay.
    Use UP/DOWN arrow keys to adjust margin.
    Press ENTER to confirm, ESC to cancel.
    """
    
    def __init__(self, image_path: str, width: int, height: int, 
                 initial_margin: int = 20, frame_thickness: int = 6):
        """
        Initialize the frame adjuster.
        
        Args:
            image_path: Path to the image file
            width: Window width
            height: Window height
            initial_margin: Starting margin value
            frame_thickness: Frame line thickness
        """
        self.image_path = image_path
        self.width = width
        self.height = height
        self.margin = initial_margin
        self.frame_thickness = frame_thickness
        self.frame_color = (40, 40, 50)
        
        # Margin adjustment settings
        self.min_margin = 5
        self.max_margin = min(width, height) // 3  # Max 1/3 of smallest dimension
        self.margin_step = 1  # Pixels per key press
        self.fast_step = 5    # Pixels per key press when holding Shift
        
        # Result
        self.confirmed = False
        self.result_margin = initial_margin
        
        # Load and process image
        self.original_image = None
        self.display_image = None
        self._load_image()
    
    def _load_image(self):
        """Load and scale the image for display."""
        if not Path(self.image_path).exists():
            raise FileNotFoundError(f"Image not found: {self.image_path}")
        
        # Load image with OpenCV
        img = cv2.imread(self.image_path, cv2.IMREAD_UNCHANGED)
        if img is None:
            raise ValueError(f"Could not load image: {self.image_path}")
        
        # Convert to RGB
        if len(img.shape) == 2:
            # Grayscale
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
        elif img.shape[2] == 4:
            # RGBA - blend with white background
            alpha = img[:, :, 3:4] / 255.0
            rgb = img[:, :, :3]
            white_bg = np.full_like(rgb, 255)
            img = (rgb * alpha + white_bg * (1 - alpha)).astype(np.uint8)
        else:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # Calculate scaling to fit in display area with padding
        padding = 40
        max_w = self.width - padding * 2
        max_h = self.height - padding * 2
        
        h, w = img.shape[:2]
        scale = min(max_w / w, max_h / h)
        
        new_w = int(w * scale)
        new_h = int(h * scale)
        
        # Resize image
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        
        # Create centered display with white background
        display = np.full((self.height, self.width, 3), 255, dtype=np.uint8)
        
        x_offset = (self.width - new_w) // 2
        y_offset = (self.height - new_h) // 2
        
        display[y_offset:y_offset + new_h, x_offset:x_offset + new_w] = img
        
        self.original_image = display
        self.display_image = display.copy()
    
    def _draw_frame(self, surface):
        """Draw the frame overlay on the surface."""
        margin = self.margin
        w, h = self.width, self.height
        thickness = self.frame_thickness
        color = self.frame_color
        
        # Draw the four sides of the frame
        # Top edge
        pygame.draw.line(surface, color, 
                        (margin, margin), (w - margin, margin), thickness)
        # Right edge
        pygame.draw.line(surface, color, 
                        (w - margin, margin), (w - margin, h - margin), thickness)
        # Bottom edge
        pygame.draw.line(surface, color, 
                        (w - margin, h - margin), (margin, h - margin), thickness)
        # Left edge
        pygame.draw.line(surface, color, 
                        (margin, h - margin), (margin, margin), thickness)
    
    def _draw_info(self, surface, font):
        """Draw the info overlay showing current margin and instructions."""
        # Semi-transparent background for text
        info_surface = pygame.Surface((300, 100), pygame.SRCALPHA)
        info_surface.fill((0, 0, 0, 180))
        
        # Text
        title = font.render("Frame Adjustment", True, (255, 255, 255))
        margin_text = font.render(f"Margin: {self.margin}px", True, (255, 200, 100))
        controls = font.render("↑/↓: Adjust  |  Enter: Confirm  |  Esc: Cancel", True, (200, 200, 200))
        
        info_surface.blit(title, (10, 10))
        info_surface.blit(margin_text, (10, 35))
        info_surface.blit(controls, (10, 60))
        
        # Position at top-left
        surface.blit(info_surface, (10, 10))
    
    def run(self) -> int:
        """
        Run the interactive frame adjuster.
        
        Returns:
            The confirmed margin value, or the initial value if cancelled.
        """
        pygame.init()
        
        # Create window
        screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Frame Adjustment - Use ↑/↓ to adjust, Enter to confirm")
        
        # Font for info display
        try:
            font = pygame.font.SysFont('Arial', 14)
        except:
            font = pygame.font.Font(None, 18)
        
        clock = pygame.time.Clock()
        running = True
        
        # Key repeat for smooth adjustment
        pygame.key.set_repeat(100, 30)  # 100ms delay, 30ms repeat
        
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    
                elif event.type == pygame.KEYDOWN:
                    # Check for modifier keys
                    mods = pygame.key.get_mods()
                    step = self.fast_step if (mods & pygame.KMOD_SHIFT) else self.margin_step
                    
                    if event.key == pygame.K_UP:
                        self.margin = min(self.max_margin, self.margin + step)
                    elif event.key == pygame.K_DOWN:
                        self.margin = max(self.min_margin, self.margin - step)
                    elif event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
                        self.confirmed = True
                        self.result_margin = self.margin
                        running = False
                    elif event.key == pygame.K_ESCAPE:
                        self.confirmed = False
                        running = False
            
            # Draw image
            pygame_surface = pygame.surfarray.make_surface(
                self.original_image.swapaxes(0, 1)
            )
            screen.blit(pygame_surface, (0, 0))
            
            # Draw frame overlay
            self._draw_frame(screen)
            
            # Draw info
            self._draw_info(screen, font)
            
            pygame.display.flip()
            clock.tick(60)
        
        pygame.quit()
        
        return self.result_margin if self.confirmed else self.margin


def adjust_frame_margin(image_path: str, width: int, height: int, 
                        initial_margin: int = 20, frame_thickness: int = 6) -> int:
    """
    Open the frame adjuster and return the selected margin.
    
    Args:
        image_path: Path to the image file
        width: Window width  
        height: Window height
        initial_margin: Starting margin value
        frame_thickness: Frame line thickness
        
    Returns:
        The selected margin value
    """
    adjuster = FrameAdjuster(
        image_path=image_path,
        width=width,
        height=height,
        initial_margin=initial_margin,
        frame_thickness=frame_thickness
    )
    return adjuster.run()


if __name__ == "__main__":
    # Test the frame adjuster
    import argparse
    
    parser = argparse.ArgumentParser(description="Frame Adjuster Preview")
    parser.add_argument("--image", required=True, help="Path to image file")
    parser.add_argument("--width", type=int, default=800, help="Window width")
    parser.add_argument("--height", type=int, default=1000, help="Window height")
    parser.add_argument("--margin", type=int, default=20, help="Initial margin")
    parser.add_argument("--thickness", type=int, default=6, help="Frame thickness")
    
    args = parser.parse_args()
    
    result = adjust_frame_margin(
        args.image, args.width, args.height, args.margin, args.thickness
    )
    print(f"Selected margin: {result}px")
