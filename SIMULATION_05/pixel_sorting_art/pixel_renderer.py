#!/usr/bin/env python3
"""
Pixel Renderer for Pixel Sorting Art
=====================================
Manim-based renderer for cinematic pixel sorting visualization
with vaporwave/cyberpunk aesthetics.
"""

import numpy as np
from typing import List, Tuple, Optional, Dict, Any, Literal
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

try:
    from manim import (
        Scene, VGroup, Square, Rectangle, ImageMobject,
        FadeIn, FadeOut, Transform, Create, Write,
        LaggedStart, AnimationGroup, Succession,
        config, LEFT, RIGHT, UP, DOWN, ORIGIN,
        linear, smooth, rush_into, rush_from,
        interpolate_color, ManimColor,
        RED, GREEN, BLUE, WHITE, BLACK, PINK, PURPLE, YELLOW
    )
    from manim.mobject.types.vectorized_mobject import VMobject
    HAS_MANIM = True
except ImportError:
    HAS_MANIM = False
    print("Manim not found. Install with: pip install manim")


class ColorStyle(Enum):
    """Available color grading styles."""
    VAPORWAVE = "vaporwave"
    CYBERPUNK = "cyberpunk"


@dataclass
class PixelMobject:
    """Represents a pixel as a Manim mobject."""
    row: int
    col: int
    mobject: Any  # Square mobject
    color: np.ndarray
    target_pos: Tuple[float, float, float]
    is_sorted: bool = False
    glow_intensity: float = 0.0


class PixelRenderer:
    """
    Manim-based renderer for pixel sorting visualization.
    
    Features:
    - Creates pixel Mobjects (tiny borderless squares)
    - Handles LaggedStart cascading wave effects
    - Manages neon glow effects on unsorted pixels
    - Applies vaporwave/cyberpunk color grading
    - Supports motion blur simulation
    - Handles dynamic camera zoom
    - Creates smooth sliding animations
    """
    
    # Color palettes
    VAPORWAVE_PALETTE = {
        "primary": "#ff00ff",      # Magenta
        "secondary": "#00ffff",    # Cyan
        "accent": "#ff71ce",       # Pink
        "background": "#1a1a2e",   # Dark purple
        "glow": "#ff00ff",         # Magenta glow
    }
    
    CYBERPUNK_PALETTE = {
        "primary": "#00ff00",      # Neon green
        "secondary": "#ff0000",    # Red
        "accent": "#ffff00",       # Yellow
        "background": "#0a0a0a",   # Near black
        "glow": "#00ff00",         # Green glow
    }
    
    def __init__(
        self,
        width: int = 1080,
        height: int = 1920,
        color_style: str = "vaporwave",
        neon_glow_intensity: float = 0.8,
        zoom_intensity: float = 0.1,
        motion_blur_strength: float = 0.3,
        pixel_scale: float = 1.0
    ):
        """
        Initialize the pixel renderer.
        
        Args:
            width: Canvas width in pixels
            height: Canvas height in pixels
            color_style: Color grading style ("vaporwave" or "cyberpunk")
            neon_glow_intensity: Intensity of neon glow effects (0-1)
            zoom_intensity: Intensity of dynamic camera zoom (0-1)
            motion_blur_strength: Strength of motion blur effect (0-1)
            pixel_scale: Scale factor for pixel size
        """
        self.width = width
        self.height = height
        self.color_style = ColorStyle(color_style)
        self.neon_glow_intensity = neon_glow_intensity
        self.zoom_intensity = zoom_intensity
        self.motion_blur_strength = motion_blur_strength
        self.pixel_scale = pixel_scale
        
        # Get color palette
        self.palette = (
            self.VAPORWAVE_PALETTE if self.color_style == ColorStyle.VAPORWAVE
            else self.CYBERPUNK_PALETTE
        )
        
        # Pixel mobjects storage
        self.pixel_mobjects: Dict[Tuple[int, int], PixelMobject] = {}
        self.pixel_group: Optional[VGroup] = None
        self.glow_group: Optional[VGroup] = None
        
        # Animation state
        self.current_zoom: float = 1.0
        self.target_zoom: float = 1.0
        
        # Calculate pixel size based on canvas
        self.pixel_size = self._calculate_pixel_size()
    
    def _calculate_pixel_size(self) -> float:
        """Calculate the size of each pixel mobject."""
        # In Manim, the default frame width is about 14 units
        # We need to map our pixel grid to Manim coordinates
        base_size = 14.0 / max(self.width, self.height) * self.pixel_scale
        return base_size
    
    def _rgb_to_manim_color(self, rgb: np.ndarray) -> str:
        """
        Convert RGB numpy array to Manim hex color.
        
        Args:
            rgb: RGB values as numpy array (0-255)
            
        Returns:
            Hex color string
        """
        r, g, b = int(rgb[0]), int(rgb[1]), int(rgb[2])
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def _pixel_to_manim_coords(self, row: int, col: int) -> Tuple[float, float, float]:
        """
        Convert pixel coordinates to Manim scene coordinates.
        
        Args:
            row: Row index
            col: Column index
            
        Returns:
            (x, y, z) Manim coordinates
        """
        # Center the image in the scene
        x = (col - self.width / 2) * self.pixel_size
        y = (self.height / 2 - row) * self.pixel_size  # Flip Y axis
        return (x, y, 0)
    
    def create_pixel_mobjects(self, image: np.ndarray) -> VGroup:
        """
        Create Manim mobjects for each pixel in the image.
        
        Args:
            image: RGB image as numpy array (H, W, 3)
            
        Returns:
            VGroup containing all pixel squares
        """
        if not HAS_MANIM:
            raise RuntimeError("Manim is required for pixel rendering")
        
        h, w = image.shape[:2]
        self.pixel_mobjects = {}
        pixels = []
        
        print(f"Creating {h * w} pixel mobjects...")
        
        for row in range(h):
            for col in range(w):
                # Get pixel color
                color = image[row, col]
                hex_color = self._rgb_to_manim_color(color)
                
                # Create square mobject
                square = Square(
                    side_length=self.pixel_size,
                    fill_color=hex_color,
                    fill_opacity=1.0,
                    stroke_width=0  # Borderless
                )
                
                # Position the square
                pos = self._pixel_to_manim_coords(row, col)
                square.move_to(pos)
                
                # Store pixel mobject
                pixel_mob = PixelMobject(
                    row=row,
                    col=col,
                    mobject=square,
                    color=color,
                    target_pos=pos
                )
                self.pixel_mobjects[(row, col)] = pixel_mob
                pixels.append(square)
        
        self.pixel_group = VGroup(*pixels)
        print(f"Created {len(pixels)} pixel mobjects")
        
        return self.pixel_group
    
    def create_cascading_wave_animation(
        self,
        pixel_positions: List[Tuple[int, int]],
        target_positions: Dict[Tuple[int, int], Tuple[int, int]],
        wave_direction: str = "horizontal",
        wave_speed: float = 0.5
    ) -> Any:
        """
        Create a LaggedStart cascading wave animation.
        
        Args:
            pixel_positions: List of (row, col) positions to animate
            target_positions: Dict mapping (row, col) to target (row, col)
            wave_direction: Direction of the wave ("horizontal" or "vertical")
            wave_speed: Speed of the wave effect (lag ratio)
            
        Returns:
            Manim Animation object
        """
        if not HAS_MANIM:
            raise RuntimeError("Manim is required for animations")
        
        animations = []
        
        # Sort pixels by wave direction for cascading effect
        if wave_direction == "horizontal":
            sorted_positions = sorted(pixel_positions, key=lambda p: (p[0], p[1]))
        else:
            sorted_positions = sorted(pixel_positions, key=lambda p: (p[1], p[0]))
        
        for pos in sorted_positions:
            if pos in self.pixel_mobjects and pos in target_positions:
                pixel_mob = self.pixel_mobjects[pos]
                target_pos = target_positions[pos]
                target_coords = self._pixel_to_manim_coords(target_pos[0], target_pos[1])
                
                # Create sliding animation
                anim = pixel_mob.mobject.animate.move_to(target_coords)
                animations.append(anim)
        
        if animations:
            return LaggedStart(*animations, lag_ratio=wave_speed)
        return None
    
    def create_glow_effect(
        self,
        pixel_positions: List[Tuple[int, int]],
        intensity: float = 1.0
    ) -> VGroup:
        """
        Create neon glow effects for specified pixels.
        
        Args:
            pixel_positions: List of (row, col) positions to add glow
            intensity: Glow intensity multiplier
            
        Returns:
            VGroup containing glow mobjects
        """
        if not HAS_MANIM:
            raise RuntimeError("Manim is required for glow effects")
        
        glow_color = self.palette["glow"]
        glow_mobjects = []
        
        for pos in pixel_positions:
            if pos in self.pixel_mobjects:
                pixel_mob = self.pixel_mobjects[pos]
                
                # Create glow squares (larger, semi-transparent)
                for scale, opacity in [(2.0, 0.1), (1.5, 0.2), (1.2, 0.3)]:
                    glow_square = Square(
                        side_length=self.pixel_size * scale,
                        fill_color=glow_color,
                        fill_opacity=opacity * intensity * self.neon_glow_intensity,
                        stroke_width=0
                    )
                    glow_square.move_to(pixel_mob.mobject.get_center())
                    glow_mobjects.append(glow_square)
                
                # Update glow intensity in pixel mobject
                pixel_mob.glow_intensity = intensity
        
        self.glow_group = VGroup(*glow_mobjects)
        return self.glow_group
    
    def apply_color_grading(self, image: np.ndarray) -> np.ndarray:
        """
        Apply vaporwave or cyberpunk color grading to an image.
        
        Args:
            image: RGB image as numpy array
            
        Returns:
            Color-graded image
        """
        graded = image.astype(np.float32)
        
        if self.color_style == ColorStyle.VAPORWAVE:
            # Boost magenta and cyan
            graded[:, :, 0] = np.clip(graded[:, :, 0] * 1.1 + 20, 0, 255)  # Red boost
            graded[:, :, 2] = np.clip(graded[:, :, 2] * 1.2 + 30, 0, 255)  # Blue boost
            
            # Add slight purple tint
            purple_tint = np.array([20, -10, 30], dtype=np.float32)
            graded = graded + purple_tint
            
        elif self.color_style == ColorStyle.CYBERPUNK:
            # Boost contrast and add green/red tints
            graded = (graded - 128) * 1.3 + 128  # Increase contrast
            
            # Add green tint to highlights
            highlights = graded.mean(axis=2) > 150
            graded[highlights, 1] = np.clip(graded[highlights, 1] + 30, 0, 255)
            
            # Add red tint to shadows
            shadows = graded.mean(axis=2) < 100
            graded[shadows, 0] = np.clip(graded[shadows, 0] + 20, 0, 255)
        
        return np.clip(graded, 0, 255).astype(np.uint8)
    
    def create_motion_blur_effect(
        self,
        pixel_positions: List[Tuple[int, int]],
        direction: Tuple[float, float],
        strength: float = 0.5
    ) -> VGroup:
        """
        Create motion blur effect for moving pixels.
        
        Args:
            pixel_positions: List of (row, col) positions
            direction: (dx, dy) direction of motion
            strength: Blur strength
            
        Returns:
            VGroup containing blur trail mobjects
        """
        if not HAS_MANIM:
            raise RuntimeError("Manim is required for motion blur")
        
        blur_mobjects = []
        blur_strength = strength * self.motion_blur_strength
        
        dx, dy = direction
        norm = np.sqrt(dx * dx + dy * dy)
        if norm > 0:
            dx, dy = dx / norm, dy / norm
        
        for pos in pixel_positions:
            if pos in self.pixel_mobjects:
                pixel_mob = self.pixel_mobjects[pos]
                center = pixel_mob.mobject.get_center()
                
                # Create trail of fading squares
                num_trails = 5
                for i in range(1, num_trails + 1):
                    trail_pos = (
                        center[0] - dx * self.pixel_size * i * blur_strength,
                        center[1] + dy * self.pixel_size * i * blur_strength,
                        0
                    )
                    
                    trail_square = Square(
                        side_length=self.pixel_size,
                        fill_color=self._rgb_to_manim_color(pixel_mob.color),
                        fill_opacity=0.6 - (i * 0.1),
                        stroke_width=0
                    )
                    trail_square.move_to(trail_pos)
                    blur_mobjects.append(trail_square)
        
        return VGroup(*blur_mobjects)
    
    def get_camera_zoom_factor(self, progress: float) -> float:
        """
        Calculate dynamic camera zoom based on progress.
        
        Args:
            progress: Sorting progress (0-1)
            
        Returns:
            Zoom factor
        """
        # Create subtle zoom pulses during sorting
        base_zoom = 1.0
        pulse = np.sin(progress * np.pi * 4) * self.zoom_intensity
        
        # Zoom in slightly at the end
        if progress > 0.8:
            end_zoom = 1.0 + (progress - 0.8) * 0.5 * self.zoom_intensity
            return end_zoom + pulse
        
        return base_zoom + pulse
    
    def create_sliding_animation(
        self,
        from_pos: Tuple[int, int],
        to_pos: Tuple[int, int],
        duration: float = 0.3
    ) -> Any:
        """
        Create smooth sliding animation for a single pixel.
        
        Args:
            from_pos: Starting (row, col) position
            to_pos: Target (row, col) position
            duration: Animation duration in seconds
            
        Returns:
            Manim Animation object
        """
        if not HAS_MANIM:
            raise RuntimeError("Manim is required for animations")
        
        if from_pos not in self.pixel_mobjects:
            return None
        
        pixel_mob = self.pixel_mobjects[from_pos]
        target_coords = self._pixel_to_manim_coords(to_pos[0], to_pos[1])
        
        return pixel_mob.mobject.animate(run_time=duration).move_to(target_coords)
    
    def create_swap_animation(
        self,
        pos1: Tuple[int, int],
        pos2: Tuple[int, int],
        duration: float = 0.3
    ) -> Any:
        """
        Create animation for swapping two pixels.
        
        Args:
            pos1: First pixel (row, col)
            pos2: Second pixel (row, col)
            duration: Animation duration
            
        Returns:
            AnimationGroup for the swap
        """
        if not HAS_MANIM:
            raise RuntimeError("Manim is required for animations")
        
        if pos1 not in self.pixel_mobjects or pos2 not in self.pixel_mobjects:
            return None
        
        pixel1 = self.pixel_mobjects[pos1]
        pixel2 = self.pixel_mobjects[pos2]
        
        target1 = self._pixel_to_manim_coords(pos2[0], pos2[1])
        target2 = self._pixel_to_manim_coords(pos1[0], pos1[1])
        
        anim1 = pixel1.mobject.animate(run_time=duration).move_to(target1)
        anim2 = pixel2.mobject.animate(run_time=duration).move_to(target2)
        
        # Swap the mobject references
        self.pixel_mobjects[pos1], self.pixel_mobjects[pos2] = \
            self.pixel_mobjects[pos2], self.pixel_mobjects[pos1]
        
        return AnimationGroup(anim1, anim2)
    
    def update_pixel_colors(self, image: np.ndarray) -> None:
        """
        Update all pixel mobject colors from an image.
        
        Args:
            image: RGB image as numpy array
        """
        if not HAS_MANIM:
            return
        
        h, w = image.shape[:2]
        
        for row in range(min(h, self.height)):
            for col in range(min(w, self.width)):
                if (row, col) in self.pixel_mobjects:
                    color = image[row, col]
                    hex_color = self._rgb_to_manim_color(color)
                    self.pixel_mobjects[(row, col)].mobject.set_fill(color=hex_color)
                    self.pixel_mobjects[(row, col)].color = color
    
    def create_beat_drop_flash(self) -> Any:
        """
        Create a flash effect for beat drop moments.
        
        Returns:
            Animation for the flash effect
        """
        if not HAS_MANIM:
            raise RuntimeError("Manim is required for animations")
        
        glow_color = self.palette["glow"]
        
        # Create full-screen flash rectangle
        flash = Rectangle(
            width=20,  # Cover whole screen
            height=20,
            fill_color=glow_color,
            fill_opacity=0.3,
            stroke_width=0
        )
        
        # Fade out animation
        return Succession(
            FadeIn(flash, run_time=0.1),
            FadeOut(flash, run_time=0.3)
        )
    
    def get_background_color(self) -> str:
        """Get the background color for the current style."""
        return self.palette["background"]
    
    def cleanup(self) -> None:
        """Clean up all mobjects and reset state."""
        self.pixel_mobjects = {}
        self.pixel_group = None
        self.glow_group = None
        self.current_zoom = 1.0
        self.target_zoom = 1.0
