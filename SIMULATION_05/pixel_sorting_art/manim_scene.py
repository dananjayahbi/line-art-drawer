#!/usr/bin/env python3
"""
Pixel Sorting Art - Manim Scene
================================
High-quality Manim Scene class for cinematic pixel sorting video export.

Features:
- Pixel grid rendered as Manim Mobjects
- LaggedStart wave effects for sorting animation
- Vaporwave/Cyberpunk color grading
- Neon glow effects on unsorted pixels
- Beat drop acceleration sequence
- Dynamic camera zoom reveal
- 9:16 vertical format for viral platforms
"""

import numpy as np
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any
import cv2
from dataclasses import dataclass

try:
    from manim import (
        Scene, VGroup, Square, Rectangle, ImageMobject,
        FadeIn, FadeOut, Transform, Create, Write,
        LaggedStart, LaggedStartMap, AnimationGroup, Succession,
        config, LEFT, RIGHT, UP, DOWN, ORIGIN,
        linear, smooth, rush_into, rush_from, rate_functions,
        interpolate_color, ManimColor, Text,
        RED, GREEN, BLUE, WHITE, BLACK, PINK, PURPLE, YELLOW, GREY,
        MovingCameraScene, GrowFromCenter, ShrinkToCenter,
        ApplyMethod, Animation
    )
    from manim.mobject.types.vectorized_mobject import VMobject
    HAS_MANIM = True
except ImportError:
    HAS_MANIM = False
    print("[WARNING] Manim not installed. Install with: pip install manim")
    # Stub class to prevent import errors
    class Scene:
        pass
    class MovingCameraScene:
        pass


# ═══════════════════════════════════════════════════════════════════════════════
# COLOR PALETTES
# ═══════════════════════════════════════════════════════════════════════════════

VAPORWAVE_PALETTE = {
    "primary": "#ff00ff",       # Magenta
    "secondary": "#00ffff",     # Cyan
    "accent": "#ff71ce",        # Pink
    "background": "#1a1a2e",    # Dark purple
    "glow": "#ff00ff",          # Magenta glow
    "highlight": "#b967ff",     # Light purple
}

CYBERPUNK_PALETTE = {
    "primary": "#00ff00",       # Neon green
    "secondary": "#ff0000",     # Red
    "accent": "#ffff00",        # Yellow
    "background": "#0a0a0a",    # Near black
    "glow": "#00ff00",          # Green glow
    "highlight": "#39ff14",     # Electric green
}


@dataclass
class PixelData:
    """Data structure for pixel animation tracking."""
    row: int
    col: int
    color: np.ndarray
    sort_value: float
    original_pos: Tuple[float, float, float]
    target_pos: Tuple[float, float, float]
    mobject: Optional[Any] = None
    is_sorted: bool = False


class PixelSortScene(Scene if HAS_MANIM else object):
    """
    Manim Scene for high-quality pixel sorting video export.
    
    Creates stunning pixel sorting animations with:
    - Scrambled to sorted pixel transitions
    - Cascading wave effects
    - Neon glow on unsorted pixels
    - Beat drop acceleration
    - Dynamic camera zoom
    - Vaporwave/Cyberpunk aesthetics
    """
    
    def __init__(
        self,
        image_path: str,
        color_style: str = "vaporwave",
        sort_direction: str = "horizontal",
        sort_criteria: str = "brightness",
        threshold: float = 0.3,
        wave_speed: float = 0.1,
        neon_glow: bool = True,
        beat_drop_timing: float = 0.7,
        beat_drop_multiplier: float = 5.0,
        zoom_reveal: bool = True,
        pixel_size: float = 0.05,
        **kwargs
    ):
        """
        Initialize the pixel sort scene.
        
        Args:
            image_path: Path to source image
            color_style: "vaporwave" or "cyberpunk"
            sort_direction: "horizontal", "vertical", or "both"
            sort_criteria: "brightness" or "hue"
            threshold: Scramble intensity (0-1)
            wave_speed: LaggedStart lag ratio
            neon_glow: Enable neon glow effects
            beat_drop_timing: When beat drop occurs (0-1)
            beat_drop_multiplier: Speed multiplier at beat drop
            zoom_reveal: Enable zoom reveal at end
            pixel_size: Size of each pixel mobject
        """
        if HAS_MANIM:
            super().__init__(**kwargs)
        
        self.image_path = Path(image_path)
        self.color_style = color_style
        self.sort_direction = sort_direction
        self.sort_criteria = sort_criteria
        self.threshold = threshold
        self.wave_speed = wave_speed
        self.neon_glow = neon_glow
        self.beat_drop_timing = beat_drop_timing
        self.beat_drop_multiplier = beat_drop_multiplier
        self.zoom_reveal = zoom_reveal
        self.pixel_size = pixel_size
        
        # Get color palette
        self.palette = (
            VAPORWAVE_PALETTE if color_style == "vaporwave" 
            else CYBERPUNK_PALETTE
        )
        
        # Pixel data storage
        self.pixels: List[List[PixelData]] = []
        self.pixel_group: Optional[VGroup] = None
        self.glow_group: Optional[VGroup] = None
        
        # Image data
        self.original_image: Optional[np.ndarray] = None
        self.scrambled_order: List[List[int]] = []
    
    def construct(self) -> None:
        """
        Main construct method for Manim scene.
        Builds and animates the pixel sorting visualization.
        """
        if not HAS_MANIM:
            print("[ERROR] Manim is required for this scene")
            return
        
        # Set background color
        self.camera.background_color = self.palette["background"]
        
        # Load and process image
        print(f"Loading image: {self.image_path}")
        self._load_image()
        
        # Create pixel mobjects in scrambled positions
        print("Creating pixel grid...")
        self._create_scrambled_pixel_grid()
        
        # Add pixel group to scene
        self.add(self.pixel_group)
        
        # Wait a moment before starting
        self.wait(0.5)
        
        # Animate sorting with wave effect
        print("Animating sorting...")
        self._animate_sorting()
        
        # Zoom reveal at end
        if self.zoom_reveal:
            print("Zoom reveal...")
            self._animate_zoom_reveal()
        
        # Final hold
        self.wait(2)
    
    def _load_image(self) -> None:
        """Load and preprocess the source image."""
        # Read image
        img = cv2.imread(str(self.image_path))
        if img is None:
            raise ValueError(f"Could not load image: {self.image_path}")
        
        # Convert BGR to RGB
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # Resize for performance (limit to reasonable resolution)
        max_dim = 100  # Max dimension for pixel grid
        h, w = img.shape[:2]
        scale = min(max_dim / max(h, w), 1.0)
        
        if scale < 1.0:
            new_w = int(w * scale)
            new_h = int(h * scale)
            img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        
        self.original_image = img
        print(f"Image size: {img.shape[1]}x{img.shape[0]} pixels")
    
    def _rgb_to_hex(self, rgb: np.ndarray) -> str:
        """Convert RGB array to hex color string."""
        r, g, b = int(rgb[0]), int(rgb[1]), int(rgb[2])
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def _get_sort_value(self, rgb: np.ndarray) -> float:
        """Calculate sort value for a pixel."""
        if self.sort_criteria == "brightness":
            # ITU-R BT.601 brightness formula
            return 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]
        else:
            # Hue value (simplified)
            import colorsys
            r, g, b = rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0
            h, _, _ = colorsys.rgb_to_hsv(r, g, b)
            return h * 360.0
    
    def _pixel_to_manim_coords(self, row: int, col: int) -> Tuple[float, float, float]:
        """Convert pixel grid coords to Manim scene coords."""
        h, w = self.original_image.shape[:2]
        
        # Center the grid in the scene
        x = (col - w / 2) * self.pixel_size
        y = (h / 2 - row) * self.pixel_size  # Flip Y axis
        
        return (x, y, 0)
    
    def _create_scrambled_pixel_grid(self) -> None:
        """Create pixel mobjects in scrambled positions."""
        h, w = self.original_image.shape[:2]
        self.pixels = []
        pixel_mobjects = []
        
        # Create scrambled order for each row
        self.scrambled_order = []
        for row in range(h):
            indices = list(range(w))
            np.random.shuffle(indices)
            
            # Partial shuffle based on threshold
            n_scrambled = int(w * self.threshold)
            indices[:n_scrambled] = sorted(
                indices[:n_scrambled], 
                key=lambda x: np.random.random()
            )
            self.scrambled_order.append(indices)
        
        # Create pixels
        for row in range(h):
            row_pixels = []
            scrambled = self.scrambled_order[row]
            
            for col in range(w):
                # Get pixel at scrambled position
                scrambled_col = scrambled[col]
                color = self.original_image[row, scrambled_col]
                sort_value = self._get_sort_value(color)
                
                # Create pixel data
                original_pos = self._pixel_to_manim_coords(row, col)
                target_pos = self._pixel_to_manim_coords(row, col)
                
                # Calculate scrambled starting position
                scrambled_pos = self._pixel_to_manim_coords(row, scrambled_col)
                
                pixel_data = PixelData(
                    row=row,
                    col=col,
                    color=color,
                    sort_value=sort_value,
                    original_pos=scrambled_pos,  # Start at scrambled position
                    target_pos=target_pos,       # End at sorted position
                    is_sorted=False
                )
                
                # Create square mobject
                hex_color = self._rgb_to_hex(color)
                square = Square(
                    side_length=self.pixel_size,
                    fill_color=hex_color,
                    fill_opacity=1.0,
                    stroke_width=0
                )
                square.move_to(scrambled_pos)
                
                pixel_data.mobject = square
                row_pixels.append(pixel_data)
                pixel_mobjects.append(square)
            
            self.pixels.append(row_pixels)
        
        self.pixel_group = VGroup(*pixel_mobjects)
    
    def _animate_sorting(self) -> None:
        """Animate the sorting process with wave effects."""
        h = len(self.pixels)
        w = len(self.pixels[0]) if h > 0 else 0
        
        # Calculate total animation time
        base_time = 3.0  # Base animation duration
        
        # Create animations for each row (horizontal wave)
        row_animations = []
        
        for row in range(h):
            row_pixels = self.pixels[row]
            
            # Sort pixels in this row by sort value
            sorted_indices = sorted(
                range(len(row_pixels)),
                key=lambda i: row_pixels[i].sort_value
            )
            
            # Create movement animations
            anims = []
            for new_col, old_col in enumerate(sorted_indices):
                pixel = row_pixels[old_col]
                target_pos = self._pixel_to_manim_coords(row, new_col)
                
                anim = pixel.mobject.animate.move_to(target_pos)
                anims.append(anim)
            
            if anims:
                # Use LaggedStart for wave effect within row
                row_anim = LaggedStart(
                    *anims,
                    lag_ratio=self.wave_speed,
                    run_time=base_time / h * 2
                )
                row_animations.append(row_anim)
        
        # Play all row animations with vertical wave
        if row_animations:
            # First part: normal speed
            pre_beat_count = int(len(row_animations) * self.beat_drop_timing)
            post_beat_count = len(row_animations) - pre_beat_count
            
            if pre_beat_count > 0:
                self.play(
                    LaggedStart(
                        *row_animations[:pre_beat_count],
                        lag_ratio=0.8
                    )
                )
            
            # Beat drop: accelerated
            if post_beat_count > 0:
                # Flash effect for beat drop
                flash = Rectangle(
                    width=14,
                    height=8,
                    fill_color=self.palette["glow"],
                    fill_opacity=0.3,
                    stroke_width=0
                )
                self.play(
                    FadeIn(flash, run_time=0.1),
                    FadeOut(flash, run_time=0.2)
                )
                
                # Accelerated sorting
                self.play(
                    LaggedStart(
                        *row_animations[pre_beat_count:],
                        lag_ratio=0.2  # Much faster
                    ),
                    run_time=base_time / self.beat_drop_multiplier
                )
    
    def _animate_zoom_reveal(self) -> None:
        """Animate camera zoom for final reveal."""
        # Scale down pixel group (simulates zoom out)
        self.play(
            self.pixel_group.animate.scale(0.9),
            run_time=0.5,
            rate_func=smooth
        )
        
        # Slight pause
        self.wait(0.3)
        
        # Scale back up
        self.play(
            self.pixel_group.animate.scale(1.0 / 0.9),
            run_time=0.3,
            rate_func=rush_from
        )
    
    def _add_neon_glow(self, pixels: List[PixelData]) -> VGroup:
        """Create neon glow effect for specified pixels."""
        glow_mobjects = []
        glow_color = self.palette["glow"]
        
        for pixel in pixels:
            if not pixel.is_sorted:
                center = pixel.mobject.get_center()
                
                # Create layered glow
                for scale, opacity in [(2.0, 0.1), (1.5, 0.2), (1.2, 0.3)]:
                    glow = Square(
                        side_length=self.pixel_size * scale,
                        fill_color=glow_color,
                        fill_opacity=opacity,
                        stroke_width=0
                    )
                    glow.move_to(center)
                    glow_mobjects.append(glow)
        
        return VGroup(*glow_mobjects)


class PixelSortSceneVertical(PixelSortScene if HAS_MANIM else object):
    """
    Pixel Sort Scene optimized for 9:16 vertical format.
    Perfect for TikTok, Instagram Reels, YouTube Shorts.
    """
    
    def __init__(self, *args, **kwargs):
        if HAS_MANIM:
            # Configure for vertical format
            config.pixel_height = 1920
            config.pixel_width = 1080
            config.frame_height = 16
            config.frame_width = 9
        
        super().__init__(*args, **kwargs)


def render_video(
    image_path: str,
    output_path: Optional[str] = None,
    color_style: str = "vaporwave",
    quality: str = "high_quality",
    format_vertical: bool = True,
    **kwargs
) -> Optional[str]:
    """
    Render pixel sorting video using Manim.
    
    Args:
        image_path: Path to source image
        output_path: Output video path (optional)
        color_style: "vaporwave" or "cyberpunk"
        quality: Manim quality setting
        format_vertical: Use 9:16 vertical format
        **kwargs: Additional scene parameters
        
    Returns:
        Path to rendered video file, or None if failed
    """
    if not HAS_MANIM:
        print("[ERROR] Manim is required for video rendering")
        print("Install with: pip install manim")
        return None
    
    try:
        # Configure Manim
        config.quality = quality
        
        if format_vertical:
            config.pixel_height = 1920
            config.pixel_width = 1080
            config.frame_height = 16
            config.frame_width = 9
        
        if output_path:
            config.output_file = output_path
        
        # Create and render scene
        scene_class = PixelSortSceneVertical if format_vertical else PixelSortScene
        scene = scene_class(
            image_path=image_path,
            color_style=color_style,
            **kwargs
        )
        scene.render()
        
        print(f"[OK] Video rendered successfully")
        return config.output_file
        
    except Exception as e:
        print(f"[ERROR] Rendering failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Command-line interface for rendering pixel sort videos."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Render pixel sorting video with Manim"
    )
    parser.add_argument(
        "--image", type=str, required=True,
        help="Path to source image"
    )
    parser.add_argument(
        "--output", type=str,
        help="Output video path"
    )
    parser.add_argument(
        "--style", type=str, default="vaporwave",
        choices=["vaporwave", "cyberpunk"],
        help="Color style (default: vaporwave)"
    )
    parser.add_argument(
        "--direction", type=str, default="horizontal",
        choices=["horizontal", "vertical", "both"],
        help="Sort direction (default: horizontal)"
    )
    parser.add_argument(
        "--quality", type=str, default="production_quality",
        choices=["low_quality", "medium_quality", "high_quality", "production_quality"],
        help="Render quality (default: production_quality)"
    )
    parser.add_argument(
        "--horizontal", action="store_true",
        help="Use 16:9 horizontal format instead of 9:16 vertical"
    )
    
    args = parser.parse_args()
    
    # Validate image path
    if not Path(args.image).exists():
        print(f"[ERROR] Image not found: {args.image}")
        return 1
    
    print("=" * 60)
    print("PIXEL SORTING ART - Manim Renderer")
    print("=" * 60)
    
    result = render_video(
        image_path=args.image,
        output_path=args.output,
        color_style=args.style,
        sort_direction=args.direction,
        quality=args.quality,
        format_vertical=not args.horizontal
    )
    
    if result:
        print(f"\n[DONE] Video saved to: {result}")
        return 0
    else:
        return 1


if __name__ == "__main__":
    exit(main())
