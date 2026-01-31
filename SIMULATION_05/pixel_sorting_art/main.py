#!/usr/bin/env python3
"""
Pixel Sorting Art - Main Simulation
====================================
Interactive pixel sorting visualization with vaporwave/cyberpunk aesthetics.
Uses Manim for high-quality rendering or pygame for control panel preview.

Features:
- Progressive sorting visualization with cascading wave effect
- Beat drop moment with exponential speed acceleration
- Dynamic camera zoom to reveal final portrait
- Neon glow effects on unsorted pixels
- Vaporwave/Cyberpunk color grading
"""

import pygame
import pygame.gfxdraw
import math
import argparse
import sys
import json
import numpy as np
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any

# OpenCV for image processing
import cv2
from PIL import Image

# Add parent directory to path to access shared module
SIMULATION_DIR = Path(__file__).resolve().parent
BASE_DIR = SIMULATION_DIR.parent
sys.path.insert(0, str(BASE_DIR))

# Import modularized components
from sorting_engine import PixelSortingEngine, SortDirection, SortCriteria

# Try to import pixel renderer (handles Manim unavailability internally)
try:
    from pixel_renderer import PixelRenderer, ColorStyle
except ImportError as e:
    print(f"Warning: Could not import PixelRenderer: {e}")
    PixelRenderer = None
    from enum import Enum
    class ColorStyle(Enum):
        VAPORWAVE = "vaporwave"
        CYBERPUNK = "cyberpunk"

from frame_animator import FrameAnimator

# Try to import Manim for high-quality rendering
HAS_MANIM = False
try:
    from manim import config as manim_config
    HAS_MANIM = True
except ImportError:
    pass  # Manim not available, will use pygame fallback

# Try to import base simulation from shared folder
try:
    from shared.base_simulation import BaseSimulation
except ImportError:
    # Fallback base class if shared module not available
    class BaseSimulation:
        """Fallback base simulation class."""
        
        def __init__(
            self,
            width: int = 1080,
            height: int = 1920,
            fps: int = 60,
            title: str = "Simulation"
        ):
            pygame.init()
            self.width = width
            self.height = height
            self.fps = fps
            self.title = title
            self.screen = pygame.display.set_mode((width, height))
            pygame.display.set_caption(title)
            self.clock = pygame.time.Clock()
            self.running = True
            self.paused = False
            self.recording = False
            self.frame_count = 0
            self.frames_folder: Optional[Path] = None
        
        def setup_frames_folder(self, folder: Path) -> None:
            """Setup folder for saving frames."""
            self.frames_folder = Path(folder)
            self.frames_folder.mkdir(parents=True, exist_ok=True)
        
        def start_recording(self) -> None:
            """Start recording frames."""
            self.recording = True
        
        def stop_recording(self) -> None:
            """Stop recording frames."""
            self.recording = False
        
        def save_frame(self) -> None:
            """Save current frame to disk."""
            if self.recording and self.frames_folder:
                frame_path = self.frames_folder / f"frame_{self.frame_count:06d}.png"
                pygame.image.save(self.screen, str(frame_path))
                self.frame_count += 1
        
        def run(self) -> None:
            """Main simulation loop."""
            while self.running:
                self.handle_events()
                if not self.paused:
                    self.update()
                self.draw()
                self.save_frame()
                pygame.display.flip()
                self.clock.tick(self.fps)
            pygame.quit()
        
        def handle_events(self) -> None:
            """Handle input events."""
            pass
        
        def update(self) -> None:
            """Update simulation state."""
            pass
        
        def draw(self) -> None:
            """Draw current frame."""
            pass


# ═══════════════════════════════════════════════════════════════════════════════
# VISUAL THEMES
# ═══════════════════════════════════════════════════════════════════════════════

THEMES = {
    "vaporwave": {
        "bg_color": (26, 26, 46),      # Dark purple
        "primary": (255, 0, 255),      # Magenta
        "secondary": (0, 255, 255),    # Cyan
        "accent": (255, 113, 206),     # Pink
        "glow": (255, 0, 255),         # Magenta glow
    },
    "cyberpunk": {
        "bg_color": (10, 10, 10),      # Near black
        "primary": (0, 255, 0),        # Neon green
        "secondary": (255, 0, 0),      # Red
        "accent": (255, 255, 0),       # Yellow
        "glow": (0, 255, 0),           # Green glow
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN SIMULATION
# ═══════════════════════════════════════════════════════════════════════════════

class PixelSortingSimulation(BaseSimulation):
    """
    Main pixel sorting simulation using pygame for preview.
    
    Features:
    - Progressive sorting visualization
    - Cascading wave effect
    - Beat drop acceleration
    - Neon glow effects
    - Dynamic zoom reveal
    """
    
    def __init__(
        self,
        width: int = 1080,
        height: int = 1920,
        image_path: Optional[str] = None,
        # Sorting parameters
        algorithm: str = "quick_sort",
        sort_direction: str = "horizontal",
        sort_criteria: str = "brightness",
        threshold: float = 0.3,
        # Animation parameters
        speed: float = 1.0,
        target_duration: Optional[float] = None,
        wave_speed: float = 0.5,
        # Visual effects
        color_style: str = "vaporwave",
        neon_glow_intensity: float = 0.8,
        zoom_intensity: float = 0.1,
        motion_blur_strength: float = 0.3,
        # Beat drop settings
        beat_drop_enabled: bool = True,
        beat_drop_timing: float = 0.7,  # % of animation before beat drop
        beat_drop_multiplier: float = 5.0,  # Speed multiplier at beat drop
        # Recording settings
        auto_record: bool = True,
        # Frame animator settings
        frame_thickness: int = 4,
        frame_speed: float = 1.0,
        frame_margin: int = 20,
        frame_enabled: bool = True
    ):
        """
        Initialize the pixel sorting simulation.
        
        Args:
            width: Canvas width
            height: Canvas height
            image_path: Path to source image
            algorithm: Sorting algorithm ("quick_sort" or "shell_sort")
            sort_direction: Sort direction ("horizontal", "vertical", "both")
            sort_criteria: Sort criteria ("brightness" or "hue")
            threshold: Scramble intensity (0-1)
            speed: Base animation speed
            target_duration: Target duration in seconds (overrides speed)
            wave_speed: Cascading wave speed
            color_style: Color grading style ("vaporwave" or "cyberpunk")
            neon_glow_intensity: Intensity of neon glow (0-1)
            zoom_intensity: Dynamic zoom intensity (0-1)
            motion_blur_strength: Motion blur strength (0-1)
            beat_drop_enabled: Enable beat drop acceleration
            beat_drop_timing: When beat drop occurs (0-1)
            beat_drop_multiplier: Speed multiplier at beat drop
            auto_record: Enable auto-recording
            frame_thickness: Border frame thickness
            frame_speed: Border frame draw speed
            frame_margin: Border frame margin
            frame_enabled: Enable decorative border
        """
        super().__init__(width, height, fps=60, title="Pixel Sorting Art")
        
        self.image_path = image_path
        self.algorithm = algorithm
        self.sort_direction = sort_direction
        self.sort_criteria = sort_criteria
        self.threshold = threshold
        self.speed = speed
        self.target_duration = target_duration
        self.wave_speed = wave_speed
        self.color_style = color_style
        self.neon_glow_intensity = neon_glow_intensity
        self.zoom_intensity = zoom_intensity
        self.motion_blur_strength = motion_blur_strength
        self.beat_drop_enabled = beat_drop_enabled
        self.beat_drop_timing = beat_drop_timing
        self.beat_drop_multiplier = beat_drop_multiplier
        self.auto_record = auto_record
        self.frame_enabled = frame_enabled
        
        # Get theme colors
        self.theme = THEMES.get(color_style, THEMES["vaporwave"])
        
        # Engines
        self.sorting_engine: Optional[PixelSortingEngine] = None
        self.pixel_renderer: Optional[PixelRenderer] = None
        
        # Frame animator
        self.frame_animator: Optional[FrameAnimator] = None
        if frame_enabled:
            self.frame_animator = FrameAnimator(
                width=width,
                height=height,
                thickness=frame_thickness,
                speed=frame_speed,
                margin=frame_margin,
                color=self.theme["primary"],
                style=color_style
            )
        
        # Animation state
        self.base_steps_per_frame = 5  # Base sorting steps per frame
        self.current_step = 0
        self.total_steps = 0
        self.progress = 0.0
        self.current_speed_multiplier = 1.0
        
        # Phase tracking
        self.phase = "sorting"  # "sorting", "frame", "hold", "complete"
        self.sorting_complete = False
        self.frame_complete = False
        self.post_complete_frames = 0
        self.max_post_complete_frames = 120  # 2 seconds at 60fps
        
        # Dynamic zoom
        self.current_zoom = 1.0
        self.target_zoom = 1.0
        
        # Beat drop state
        self.beat_dropped = False
        self.beat_drop_progress = 0.0
        
        # Glow tracking
        self.glow_surface: Optional[pygame.Surface] = None
        
        # Setup
        self._setup()
    
    def _setup(self) -> None:
        """Initialize the simulation."""
        # Setup recording folder
        frames_folder = SIMULATION_DIR / "frames"
        self.setup_frames_folder(frames_folder)
        
        if self.auto_record:
            self.start_recording()
        
        # Process image if provided
        if self.image_path:
            try:
                self.sorting_engine = PixelSortingEngine(
                    image_path=self.image_path,
                    target_width=self.width,
                    target_height=self.height,
                    algorithm=self.algorithm,
                    sort_direction=self.sort_direction,
                    sort_criteria=self.sort_criteria,
                    threshold=self.threshold,
                    padding=40
                )
                
                if self.sorting_engine.load_and_process_image():
                    self.total_steps = self.sorting_engine.total_steps
                    print(f"[OK] Image loaded: {self.total_steps} sorting steps")
                    
                    # Auto-calculate speed if target_duration is set
                    if self.target_duration:
                        self._calculate_speed_for_duration()
                    
                    # Initialize pixel renderer
                    self.pixel_renderer = PixelRenderer(
                        width=self.width,
                        height=self.height,
                        color_style=self.color_style,
                        neon_glow_intensity=self.neon_glow_intensity,
                        zoom_intensity=self.zoom_intensity,
                        motion_blur_strength=self.motion_blur_strength
                    )
                else:
                    print("[ERROR] Failed to load image")
                    
            except Exception as e:
                print(f"[ERROR] Error processing image: {e}")
                import traceback
                traceback.print_exc()
    
    def _calculate_speed_for_duration(self) -> None:
        """Calculate the speed needed to complete animation in target_duration seconds."""
        if not self.sorting_engine or not self.target_duration:
            return
        
        # Total steps to process
        total_steps = self.total_steps
        
        # At 60 FPS, total frames for target duration
        target_frames = int(self.target_duration * 60)
        
        # Calculate steps per frame needed
        steps_per_frame = total_steps / target_frames
        
        # base_steps_per_frame is 5, so speed = steps_per_frame / 5
        calculated_speed = steps_per_frame / self.base_steps_per_frame
        
        # Clamp to reasonable range
        calculated_speed = max(0.5, min(20.0, calculated_speed))
        
        self.speed = calculated_speed
        print(f"[AUTO] Speed: {self.speed:.2f} for {self.target_duration}s duration")
    
    def handle_events(self) -> None:
        """Handle pygame events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_SPACE:
                    self.paused = not self.paused
                    print(f"[{'PAUSED' if self.paused else 'RESUMED'}]")
                elif event.key == pygame.K_r:
                    self._reset_animation()
                elif event.key == pygame.K_b:
                    # Force beat drop
                    if not self.beat_dropped:
                        self._trigger_beat_drop()
    
    def _reset_animation(self) -> None:
        """Reset the animation to beginning."""
        if self.sorting_engine:
            self.sorting_engine.reset()
            self.total_steps = self.sorting_engine.total_steps
            self.current_step = 0
            self.progress = 0.0
            self.current_speed_multiplier = 1.0
            self.phase = "sorting"
            self.sorting_complete = False
            self.frame_complete = False
            self.beat_dropped = False
            self.beat_drop_progress = 0.0
            self.post_complete_frames = 0
            self.current_zoom = 1.0
            if self.frame_animator:
                self.frame_animator.reset()
            print("[RESET] Animation reset")
    
    def _trigger_beat_drop(self) -> None:
        """Trigger the beat drop acceleration."""
        self.beat_dropped = True
        self.beat_drop_progress = 0.0
        print("[BEAT DROP!] Acceleration activated!")
    
    def update(self) -> None:
        """Update animation state."""
        if not self.sorting_engine:
            return
        
        if self.phase == "sorting":
            self._update_sorting()
        elif self.phase == "frame":
            self._update_frame()
        elif self.phase == "hold":
            self._update_hold()
    
    def _update_sorting(self) -> None:
        """Update sorting animation."""
        # Calculate progress from engine
        self.progress = self.sorting_engine.get_progress()
        self.current_step = self.sorting_engine.current_step
        
        # Check for beat drop timing
        if (self.beat_drop_enabled and 
            not self.beat_dropped and 
            self.progress >= self.beat_drop_timing):
            self._trigger_beat_drop()
        
        # Calculate current speed with beat drop acceleration
        if self.beat_dropped:
            # Exponential ease-in for beat drop
            self.beat_drop_progress = min(1.0, self.beat_drop_progress + 0.02)
            ease = self.beat_drop_progress ** 2
            self.current_speed_multiplier = 1.0 + (self.beat_drop_multiplier - 1.0) * ease
            
            # Activate beat drop in engine
            if not self.sorting_engine.beat_drop_active:
                self.sorting_engine.activate_beat_drop(self.current_speed_multiplier)
        
        # Calculate steps this frame
        steps_this_frame = int(
            self.base_steps_per_frame * self.speed * self.current_speed_multiplier
        )
        steps_this_frame = max(1, steps_this_frame)
        
        # Apply sorting steps using engine's step_sorting method
        is_complete = self.sorting_engine.step_sorting(steps_this_frame)
        
        # Update zoom based on progress
        if self.beat_dropped:
            # Zoom in during beat drop, then zoom out to reveal
            if self.progress < 0.95:
                self.target_zoom = 1.0 + self.zoom_intensity * self.beat_drop_progress
            else:
                self.target_zoom = 1.0
        
        # Smooth zoom transition
        self.current_zoom += (self.target_zoom - self.current_zoom) * 0.05
        
        # Check if sorting complete
        if is_complete:
            self.sorting_complete = True
            self.phase = "frame" if self.frame_enabled else "hold"
            print("[COMPLETE] Sorting complete!")
    
    def _update_frame(self) -> None:
        """Update frame drawing animation."""
        if self.frame_animator:
            self.frame_animator.update()
            if self.frame_animator.is_complete:
                self.frame_complete = True
                self.phase = "hold"
                print("[COMPLETE] Frame complete!")
    
    def _update_hold(self) -> None:
        """Update hold phase after completion."""
        self.post_complete_frames += 1
        if self.post_complete_frames >= self.max_post_complete_frames:
            self.phase = "complete"
            self.running = False
    
    def draw(self) -> None:
        """Render the current frame."""
        # Clear screen with theme background
        self.screen.fill(self.theme["bg_color"])
        
        if self.sorting_engine:
            # Get current image state using get_current_frame (includes glow)
            current_image = self.sorting_engine.get_current_frame()
            
            if current_image is not None:
                # Apply color grading
                if self.pixel_renderer:
                    current_image = self.pixel_renderer.apply_color_grading(current_image)
                
                # Apply zoom transformation
                if self.current_zoom != 1.0:
                    current_image = self._apply_zoom(current_image)
                
                # Convert to pygame surface
                frame_surface = pygame.surfarray.make_surface(
                    np.transpose(current_image, (1, 0, 2))
                )
                
                # Calculate position (centered)
                x = (self.width - frame_surface.get_width()) // 2
                y = (self.height - frame_surface.get_height()) // 2
                
                self.screen.blit(frame_surface, (x, y))
                
                # Draw neon glow overlay for unsorted pixels
                if self.neon_glow_intensity > 0 and not self.sorting_complete:
                    self._draw_glow_overlay()
            
            # Draw frame border if active
            if self.frame_animator and (self.phase == "frame" or self.frame_complete):
                frame_surf = self.frame_animator.get_surface()
                if frame_surf:
                    self.screen.blit(frame_surf, (0, 0))
            
            # Draw progress indicator
            self._draw_progress_bar()
    
    def _apply_zoom(self, image: np.ndarray) -> np.ndarray:
        """Apply zoom transformation to image."""
        h, w = image.shape[:2]
        
        # Calculate zoomed dimensions
        new_w = int(w * self.current_zoom)
        new_h = int(h * self.current_zoom)
        
        # Resize
        zoomed = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        
        # Crop to original size (center crop)
        start_x = (new_w - w) // 2
        start_y = (new_h - h) // 2
        cropped = zoomed[start_y:start_y + h, start_x:start_x + w]
        
        return cropped
    
    def _draw_glow_overlay(self) -> None:
        """Draw neon glow effect on unsorted pixels."""
        if not self.sorting_engine:
            return
        
        # Get glow mask from engine (already tracks glow intensities)
        glow_mask = self.sorting_engine.get_glow_mask()
        if glow_mask is None:
            return
        
        # Glow is already applied in get_current_frame, 
        # but we can add extra overlay if needed
        glow_color = self.theme["glow"]
        intensity = self.neon_glow_intensity * (1.0 - self.progress)
        
        if intensity > 0.1:
            glow_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            
            # Sample positions with high glow intensity
            h, w = glow_mask.shape
            for y in range(0, h, 10):  # Sample every 10 pixels for performance
                for x in range(0, w, 10):
                    if glow_mask[y, x] > 0.1:
                        alpha = int(50 * intensity * glow_mask[y, x])
                        pygame.gfxdraw.filled_circle(
                            glow_surface, x, y, 3,
                            (*glow_color, alpha)
                        )
            
            self.screen.blit(glow_surface, (0, 0), special_flags=pygame.BLEND_ADD)
    
    def _draw_progress_bar(self) -> None:
        """Draw progress bar at bottom of screen."""
        bar_height = 4
        bar_y = self.height - bar_height - 10
        bar_width = self.width - 40
        bar_x = 20
        
        # Background
        pygame.draw.rect(
            self.screen,
            (50, 50, 50),
            (bar_x, bar_y, bar_width, bar_height)
        )
        
        # Progress
        progress_width = int(bar_width * self.progress)
        if progress_width > 0:
            pygame.draw.rect(
                self.screen,
                self.theme["primary"],
                (bar_x, bar_y, progress_width, bar_height)
            )


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Pixel Sorting Art - Cinematic pixel sorting visualization"
    )
    
    # Canvas settings
    parser.add_argument(
        "--width", type=int, default=1080,
        help="Canvas width (default: 1080)"
    )
    parser.add_argument(
        "--height", type=int, default=1920,
        help="Canvas height (default: 1920)"
    )
    
    # Image input
    parser.add_argument(
        "--image", type=str, required=True,
        help="Path to source image"
    )
    
    # Sorting parameters
    parser.add_argument(
        "--algorithm", type=str, default="quick_sort",
        choices=["quick_sort", "shell_sort"],
        help="Sorting algorithm (default: quick_sort)"
    )
    parser.add_argument(
        "--direction", type=str, default="horizontal",
        choices=["horizontal", "vertical", "both"],
        help="Sort direction (default: horizontal)"
    )
    parser.add_argument(
        "--criteria", type=str, default="brightness",
        choices=["brightness", "hue"],
        help="Sort criteria (default: brightness)"
    )
    parser.add_argument(
        "--threshold", type=float, default=0.3,
        help="Scramble intensity 0-1 (default: 0.3)"
    )
    
    # Animation parameters
    parser.add_argument(
        "--speed", type=float, default=1.0,
        help="Animation speed multiplier (default: 1.0)"
    )
    parser.add_argument(
        "--target-duration", type=float,
        help="Target duration in seconds (overrides --speed)"
    )
    parser.add_argument(
        "--wave-speed", type=float, default=0.5,
        help="Cascading wave speed (default: 0.5)"
    )
    
    # Visual effects
    parser.add_argument(
        "--style", type=str, default="vaporwave",
        choices=["vaporwave", "cyberpunk"],
        help="Color grading style (default: vaporwave)"
    )
    parser.add_argument(
        "--glow", type=float, default=0.8,
        help="Neon glow intensity 0-1 (default: 0.8)"
    )
    parser.add_argument(
        "--zoom", type=float, default=0.1,
        help="Dynamic zoom intensity 0-1 (default: 0.1)"
    )
    parser.add_argument(
        "--blur", type=float, default=0.3,
        help="Motion blur strength 0-1 (default: 0.3)"
    )
    
    # Beat drop settings
    parser.add_argument(
        "--no-beat-drop", action="store_true",
        help="Disable beat drop acceleration"
    )
    parser.add_argument(
        "--beat-timing", type=float, default=0.7,
        help="Beat drop timing 0-1 (default: 0.7)"
    )
    parser.add_argument(
        "--beat-multiplier", type=float, default=5.0,
        help="Beat drop speed multiplier (default: 5.0)"
    )
    
    # Frame settings
    parser.add_argument(
        "--no-frame", action="store_true",
        help="Disable decorative border frame"
    )
    parser.add_argument(
        "--frame-thickness", type=int, default=4,
        help="Border frame thickness (default: 4)"
    )
    parser.add_argument(
        "--frame-speed", type=float, default=1.0,
        help="Border frame draw speed (default: 1.0)"
    )
    parser.add_argument(
        "--frame-margin", type=int, default=20,
        help="Border frame margin (default: 20)"
    )
    
    # Recording
    parser.add_argument(
        "--no-record", action="store_true",
        help="Disable auto-recording"
    )
    
    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    args = parse_arguments()
    
    # Validate image path
    if not Path(args.image).exists():
        print(f"[ERROR] Image file not found: {args.image}")
        sys.exit(1)
    
    print("=" * 60)
    print("PIXEL SORTING ART")
    print("=" * 60)
    print(f"Image: {args.image}")
    print(f"Canvas: {args.width}x{args.height}")
    print(f"Style: {args.style}")
    print(f"Algorithm: {args.algorithm}")
    print(f"Direction: {args.direction}")
    print("=" * 60)
    
    # Create and run simulation
    sim = PixelSortingSimulation(
        width=args.width,
        height=args.height,
        image_path=args.image,
        algorithm=args.algorithm,
        sort_direction=args.direction,
        sort_criteria=args.criteria,
        threshold=args.threshold,
        speed=args.speed,
        target_duration=args.target_duration,
        wave_speed=args.wave_speed,
        color_style=args.style,
        neon_glow_intensity=args.glow,
        zoom_intensity=args.zoom,
        motion_blur_strength=args.blur,
        beat_drop_enabled=not args.no_beat_drop,
        beat_drop_timing=args.beat_timing,
        beat_drop_multiplier=args.beat_multiplier,
        auto_record=not args.no_record,
        frame_thickness=args.frame_thickness,
        frame_speed=args.frame_speed,
        frame_margin=args.frame_margin,
        frame_enabled=not args.no_frame
    )
    
    print("\nControls:")
    print("  ESC   - Exit")
    print("  SPACE - Pause/Resume")
    print("  R     - Reset animation")
    print("  B     - Force beat drop")
    print()
    
    sim.run()
    
    print("\n[DONE] Simulation complete!")
    if sim.recording:
        print(f"Frames saved to: {sim.frames_folder}")


if __name__ == "__main__":
    main()
