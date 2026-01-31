#!/usr/bin/env python3
"""
Image Target Manager - Handles target image processing
======================================================
Processes target images and provides pixel-perfect color mapping for sand particles.
"""

import cv2
import numpy as np
from PIL import Image
from pathlib import Path
from typing import Tuple, List, Optional
import random


class ImageTarget:
    """Manages target image and provides color sampling for particles."""
    
    def __init__(self, image_path: str, target_width: int, target_height: int):
        """
        Initialize image target.
        
        Args:
            image_path: Path to target image
            target_width: Desired width for simulation
            target_height: Desired height for simulation
        """
        self.image_path = image_path
        self.target_width = target_width
        self.target_height = target_height
        
        # Load and process image
        self.original_image = None
        self.processed_image = None
        self.image_array = None
        self.pixel_positions = []  # List of (x, y, color) tuples
        
        self._load_image()
        self._process_image()
        self._extract_pixel_positions()
    
    def _load_image(self):
        """Load the target image."""
        if not Path(self.image_path).exists():
            raise FileNotFoundError(f"Image not found: {self.image_path}")
        
        # Load with PIL
        self.original_image = Image.open(self.image_path)
        
        # Convert to RGB if needed
        if self.original_image.mode != 'RGB':
            self.original_image = self.original_image.convert('RGB')
    
    def _process_image(self):
        """Process image to target dimensions."""
        # Resize maintaining aspect ratio
        img_width, img_height = self.original_image.size
        aspect_ratio = img_width / img_height
        target_aspect = self.target_width / self.target_height
        
        if aspect_ratio > target_aspect:
            # Image is wider
            new_width = self.target_width
            new_height = int(self.target_width / aspect_ratio)
        else:
            # Image is taller
            new_height = self.target_height
            new_width = int(self.target_height * aspect_ratio)
        
        # Resize image
        self.processed_image = self.original_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Convert to numpy array (RGB)
        self.image_array = np.array(self.processed_image)
    
    def _extract_pixel_positions(self):
        """Extract all non-white pixel positions and colors."""
        height, width = self.image_array.shape[:2]
        
        # Find all colored pixels (non-white)
        for y in range(height):
            for x in range(width):
                color = tuple(self.image_array[y, x])
                
                # Skip near-white pixels (threshold)
                # Use int() to avoid overflow with numpy types
                if int(color[0]) + int(color[1]) + int(color[2]) < 750:  # Not pure white
                    self.pixel_positions.append((x, y, color))
        
        # Shuffle for random distribution
        random.shuffle(self.pixel_positions)
        
        print(f"Extracted {len(self.pixel_positions)} colored pixels from target image")
    
    def get_next_particle_info(self, index: int) -> Optional[Tuple[Tuple[int, int], Tuple[int, int, int]]]:
        """
        Get position and color for next particle.
        
        Args:
            index: Particle index
            
        Returns:
            ((target_x, target_y), (r, g, b)) or None if no more pixels
        """
        if index >= len(self.pixel_positions):
            return None
        
        x, y, color = self.pixel_positions[index]
        return ((x, y), color)
    
    def get_total_pixels(self) -> int:
        """Get total number of colored pixels in target."""
        return len(self.pixel_positions)
    
    def get_image_dimensions(self) -> Tuple[int, int]:
        """Get processed image dimensions."""
        if self.processed_image:
            return self.processed_image.size
        return (0, 0)
    
    def get_image_offset(self, screen_width: int, screen_height: int) -> Tuple[int, int]:
        """
        Calculate offset to center image on screen.
        
        Args:
            screen_width: Screen width
            screen_height: Screen height
            
        Returns:
            (offset_x, offset_y)
        """
        img_width, img_height = self.get_image_dimensions()
        offset_x = (screen_width - img_width) // 2
        offset_y = screen_height - img_height - 50  # Bottom with margin
        return (offset_x, offset_y)
    
    def sample_color_at_position(self, x: int, y: int) -> Tuple[int, int, int]:
        """
        Sample color at specific position.
        
        Args:
            x: X coordinate
            y: Y coordinate
            
        Returns:
            (r, g, b) color tuple
        """
        if self.image_array is None:
            return (255, 255, 255)
        
        height, width = self.image_array.shape[:2]
        
        # Clamp to bounds
        x = max(0, min(width - 1, x))
        y = max(0, min(height - 1, y))
        
        return tuple(self.image_array[y, x])
    
    def get_random_color_from_palette(self) -> Tuple[int, int, int]:
        """Get a random color from the image palette."""
        if not self.pixel_positions:
            return (0, 0, 0)
        
        _, _, color = random.choice(self.pixel_positions)
        return color
