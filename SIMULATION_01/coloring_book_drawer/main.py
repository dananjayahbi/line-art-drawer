#!/usr/bin/env python3
"""
Coloring Book Drawer - Main Simulation (Pixel-Reveal Approach)
================================================================
Uses a revolutionary PIXEL-REVEAL approach instead of vector tracing.
The final result is PIXEL-IDENTICAL to the original uploaded image.

How it works:
1. Extract skeleton (centerline) of the ink regions
2. Use distance transform to get line thickness at each skeleton point
3. Progressively REVEAL original image pixels along skeleton paths
4. Variable brush sizes match the local line thickness exactly

Features:
- GPU acceleration using CuPy (NVIDIA) or NumPy fallback
- 100% accurate reproduction of original artwork
- Smooth handwriting-like reveal animations
- Natural stroke ordering for realistic drawing flow
"""

import pygame
import pygame.gfxdraw
import math
import random
import argparse
import sys
import json
import numpy as np
from pathlib import Path
from collections import deque

# OpenCV for image processing
import cv2
from PIL import Image

# Scikit-image for skeleton extraction
try:
    from skimage.morphology import skeletonize, medial_axis
    from skimage import img_as_ubyte
    HAS_SKIMAGE = True
except ImportError:
    HAS_SKIMAGE = False
    print("scikit-image not found. Using OpenCV fallback for skeletonization.")

# Add parent directory to path to access shared module
SIMULATION_DIR = Path(__file__).resolve().parent
BASE_DIR = SIMULATION_DIR.parent
sys.path.insert(0, str(BASE_DIR))

# Import modularized components
from pixel_reveal_engine import PixelRevealEngine
from pencil_shading_engine import PencilShadingEngine, DrawingPhase
from pen_renderer import PenRenderer
from frame_animator import FrameAnimator

# GPU acceleration - try to import CuPy for CUDA support
HAS_GPU = False
GPU_INFO = "No GPU acceleration"

try:
    import cupy as cp
    from cupyx.scipy import ndimage as cp_ndimage
    
    # Test GPU availability and get info
    try:
        device = cp.cuda.Device(0)
        cuda_version = cp.cuda.runtime.runtimeGetVersion()
        cuda_major = cuda_version // 1000
        cuda_minor = (cuda_version % 1000) // 10
        
        # Quick test
        test_arr = cp.array([1, 2, 3])
        _ = cp.asnumpy(test_arr)
        
        HAS_GPU = True
        GPU_INFO = f"GPU: {device}, CUDA {cuda_major}.{cuda_minor}"
        print(f"[OK] GPU acceleration enabled: {GPU_INFO}")
    except Exception as e:
        print(f"CuPy available but GPU init failed: {e}")
        HAS_GPU = False
except ImportError:
    print("CuPy not installed. For GPU acceleration:")
    print("  NVIDIA: pip install cupy-cuda12x")

# Scipy for CPU fallback
try:
    from scipy import ndimage
    from scipy.ndimage import distance_transform_edt
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

try:
    from base_simulation import BaseSimulation
except ImportError:
    # Fallback base class if shared module not available
    class BaseSimulation:
        def __init__(self, width=800, height=1000, fps=60, title="Simulation"):
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
            self.frames_folder = None
        
        def setup_frames_folder(self, folder):
            self.frames_folder = Path(folder)
            self.frames_folder.mkdir(parents=True, exist_ok=True)
        
        def start_recording(self):
            self.recording = True
        
        def stop_recording(self):
            self.recording = False
        
        def save_frame(self):
            if self.recording and self.frames_folder:
                frame_path = self.frames_folder / f"frame_{self.frame_count:06d}.png"
                pygame.image.save(self.screen, str(frame_path))
                self.frame_count += 1
        
        def run(self):
            while self.running:
                self.handle_events()
                if not self.paused:
                    self.update()
                self.draw()
                self.save_frame()
                pygame.display.flip()
                self.clock.tick(self.fps)
            pygame.quit()
        
        def handle_events(self):
            pass
        
        def update(self):
            pass
        
        def draw(self):
            pass


# ═══════════════════════════════════════════════════════════════════════════════
# VISUAL THEME - Classic mode for exact reproduction
# ═══════════════════════════════════════════════════════════════════════════════

THEMES = {
    "classic": {
        "bg_color": (255, 255, 255),
        "paper_texture": False,
        "pen_style": "fountain",
        "pen_color": (40, 40, 50),
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN SIMULATION
# ═══════════════════════════════════════════════════════════════════════════════

class ColoringBookDrawerSimulation(BaseSimulation):
    """
    Main simulation using pixel-reveal approach.
    Progressively reveals the original image pixels for perfect reproduction.
    
    ENHANCED: Now supports two rendering engines:
    - PixelRevealEngine: For simple line drawings (fast, skeleton-based)
    - PencilShadingEngine: For complex shaded artwork with textures/shadows
    
    The engine is auto-selected based on image complexity analysis.
    
    NOTE: FPS is now locked at 60 for smooth rendering and recording.
    The 'speed' parameter controls animation speed independently.
    In target_duration mode, speed is auto-calculated to match the desired duration.
    """
    
    def __init__(self, width=800, height=1000, image_path=None,
                 speed=5.0, target_duration=None, thickness_scale=1.0, theme="classic", 
                 show_pen=True, auto_record=True, use_gpu=True,
                 frame_thickness=6, frame_speed=1.0, frame_margin=20,
                 custom_pen_path=None, pen_tip_x=0, pen_tip_y=0, 
                 pen_scale=1.0, pen_rotation=True,
                 force_shading_engine=False, shading_sensitivity=0.5,
                 hatching_angle=45.0, stroke_spacing=3):
        # FPS is now LOCKED at 60 for all simulations
        super().__init__(width, height, fps=60, title="Coloring Book Drawer")
        
        self.image_path = image_path
        self.target_duration = target_duration  # If set, speed will be auto-calculated
        self.speed = speed  # Will be overridden if target_duration is set
        self.thickness_scale = thickness_scale
        self.theme_name = theme
        self.theme = THEMES.get(theme, THEMES["classic"])
        self.show_pen = show_pen
        self.auto_record = auto_record
        self.use_gpu = use_gpu
        
        # Engine selection settings
        self.force_shading_engine = force_shading_engine
        self.shading_sensitivity = shading_sensitivity
        self.hatching_angle = hatching_angle
        self.stroke_spacing = stroke_spacing
        self.using_shading_engine = False  # Will be set during setup
        
        # Pixel reveal engine (one of two engines will be used)
        self.reveal_engine = None
        
        # Pen renderer
        self.pen_renderer = PenRenderer(
            custom_pen_path=custom_pen_path,
            pen_tip_x=pen_tip_x,
            pen_tip_y=pen_tip_y,
            pen_scale=pen_scale,
            pen_rotation=pen_rotation
        )
        
        # Frame animator
        self.frame_animator = FrameAnimator(
            width=width,
            height=height,
            thickness=frame_thickness,
            speed=frame_speed,
            margin=frame_margin,
            color=(40, 40, 50)
        )
        
        # Points to reveal per frame (controls animation speed)
        # Increased for smoother animation - reveals more points per frame
        # Lower value = slower minimum speed at speed=1
        self.base_reveal_rate = 15
        
        # Pen cursor
        self.pen_pos = (width // 2, height // 2)
        self.pen_visible = False
        
        # Rendering surfaces
        self.main_surface = None
        
        # State
        self.drawing_complete = False
        self.frame_drawing = False   # Whether we're drawing the frame
        self.frame_complete = False  # Whether frame is fully drawn
        self.post_complete_frames = 0
        self.max_post_complete_frames = 120  # 2 seconds at 60fps
        
        # Setup
        self._setup()
    
    def _setup(self):
        """Initialize the simulation."""
        # Setup recording folder
        frames_folder = SIMULATION_DIR / "frames"
        self.setup_frames_folder(frames_folder)
        
        if self.auto_record:
            self.start_recording()
        
        # Create main rendering surface
        self.main_surface = pygame.Surface((self.width, self.height))
        self.main_surface.fill(self.theme["bg_color"])
        
        # Process image if provided
        if self.image_path:
            try:
                # First, analyze image to determine which engine to use
                engine_choice = self._analyze_and_select_engine()
                
                if engine_choice == "shading" or self.force_shading_engine:
                    print("\n🎨 Using PENCIL SHADING ENGINE (for complex artwork)")
                    self.using_shading_engine = True
                    self.reveal_engine = PencilShadingEngine(
                        self.image_path,
                        self.width,
                        self.height,
                        padding=40,
                        use_gpu=self.use_gpu,
                        shade_sensitivity=self.shading_sensitivity,
                        hatching_angle=self.hatching_angle,
                        stroke_spacing=self.stroke_spacing
                    )
                else:
                    print("\n✏️ Using PIXEL REVEAL ENGINE (for line art)")
                    self.using_shading_engine = False
                    self.reveal_engine = PixelRevealEngine(
                        self.image_path, 
                        self.width, 
                        self.height,
                        padding=40,
                        use_gpu=self.use_gpu
                    )
                
                self.reveal_engine.process_image()
                
                # Adjust brush scale based on thickness setting (for PixelRevealEngine)
                if not self.using_shading_engine:
                    self.reveal_engine.brush_scale = 1.1 + (self.thickness_scale * 0.3)
                
                # Auto-calculate speed if target_duration is set
                if self.target_duration:
                    self._calculate_speed_for_duration()
                
            except Exception as e:
                print(f"Error processing image: {e}")
                import traceback
                traceback.print_exc()
    
    def _analyze_and_select_engine(self):
        """
        Analyze the image to determine which rendering engine to use.
        
        Returns:
            "simple" for line art (use PixelRevealEngine)
            "shading" for complex artwork (use PencilShadingEngine)
        """
        # Quick analysis using OpenCV
        img = cv2.imread(str(self.image_path))
        if img is None:
            return "simple"
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Detect edges
        edges = cv2.Canny(gray, 50, 150)
        edge_coverage = np.mean(edges > 0)
        
        # Detect shading (non-white, non-edge pixels with gradient values)
        # White is 255, so anything significantly darker is potential shading
        dark_pixels = gray < 240
        very_dark_pixels = gray < 200
        
        # Calculate local variance to detect gradients
        kernel_size = 11
        local_mean = cv2.blur(gray.astype(np.float32), (kernel_size, kernel_size))
        local_sq_mean = cv2.blur((gray.astype(np.float32))**2, (kernel_size, kernel_size))
        local_variance = local_sq_mean - local_mean**2
        gradient_coverage = np.mean(local_variance > 50)
        
        # Calculate shading coverage (dark areas that aren't edges)
        edge_dilated = cv2.dilate(edges, np.ones((5, 5), np.uint8), iterations=1)
        shade_mask = dark_pixels & (edge_dilated == 0)
        shade_coverage = np.mean(shade_mask)
        
        print(f"\n📊 Image Analysis:")
        print(f"   Edge coverage: {100*edge_coverage:.1f}%")
        print(f"   Shade coverage: {100*shade_coverage:.1f}%")
        print(f"   Gradient regions: {100*gradient_coverage:.1f}%")
        print(f"   Dark pixel coverage: {100*np.mean(very_dark_pixels):.1f}%")
        
        # Decision logic:
        # - If shade coverage > 10% OR gradient coverage > 5%, use shading engine
        # - Otherwise, use simple engine
        if shade_coverage > 0.10 or gradient_coverage > 0.05:
            print("   → Detected complex shading/textures")
            return "shading"
        else:
            print("   → Detected simple line art")
            return "simple"
    
    def _calculate_speed_for_duration(self):
        """Calculate the speed needed to complete animation in target_duration seconds."""
        if not self.reveal_engine or not self.target_duration:
            return
        
        # Total reveal points to process
        total_points = len(self.reveal_engine.reveal_sequence)
        
        # At 60 FPS, total frames for target duration
        target_frames = int(self.target_duration * 60)
        
        # Calculate points per frame needed
        points_per_frame = total_points / target_frames
        
        # base_reveal_rate is 15, so speed = points_per_frame / 15
        calculated_speed = points_per_frame / self.base_reveal_rate
        
        # Clamp to reasonable range
        calculated_speed = max(0.5, min(15.0, calculated_speed))
        
        self.speed = calculated_speed
        print(f"Auto-calculated speed: {self.speed:.2f} (for {self.target_duration}s duration at 60 FPS)")
        print(f"Total points: {total_points}, Target frames: {target_frames}, Points/frame: {points_per_frame:.1f}")
    
    def handle_events(self):
        """Handle pygame events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_SPACE:
                    self.paused = not self.paused
                elif event.key == pygame.K_r:
                    # Reset animation
                    if self.reveal_engine:
                        h, w = self.reveal_engine.original_image.shape[:2]
                        self.reveal_engine.reveal_mask = np.zeros((h, w), dtype=np.float32)
                        self.reveal_engine.current_reveal_idx = 0
                        self.drawing_complete = False
                        self.frame_drawing = False
                        self.frame_complete = False
                        self.post_complete_frames = 0
                        self.frame_animator.reset()
    
    def update(self):
        """Update animation state."""
        if not self.reveal_engine:
            return
        
        if self.drawing_complete:
            # After image drawing complete, start frame drawing
            if not self.frame_drawing and not self.frame_complete:
                self.frame_drawing = True
                # Get start position
                start_pos = self.frame_animator.get_start_position()
                if start_pos:
                    self.pen_pos = start_pos
                    self.pen_visible = True
            
            if self.frame_drawing and not self.frame_complete:
                # Update frame drawing
                pen_pos = self.frame_animator.update()
                if pen_pos:
                    self.pen_pos = pen_pos
                    self.pen_visible = True
                else:
                    self.frame_complete = True
                    self.pen_visible = False
            elif self.frame_complete:
                # Hold after everything is done
                self.pen_visible = False
                self.post_complete_frames += 1
                if self.post_complete_frames >= self.max_post_complete_frames:
                    self.running = False
            return
        
        # Calculate points to reveal this frame based on speed
        if self.using_shading_engine:
            # PencilShadingEngine uses phase-based speed
            base_points = self.reveal_engine.get_points_per_update()
            points_per_frame = int(base_points * self.speed)
        else:
            # PixelRevealEngine uses fixed base rate
            points_per_frame = int(self.base_reveal_rate * self.speed)
        
        # Reveal next batch of pixels
        has_more = self.reveal_engine.reveal_next_batch(points_per_frame)
        
        if not has_more:
            self.drawing_complete = True
            print("Drawing complete! Starting frame...")
        
        # Update pen position (for visual feedback)
        if has_more and self.show_pen:
            if self.using_shading_engine:
                # PencilShadingEngine provides pen position directly
                self.pen_pos = self.reveal_engine.get_current_pen_position()
                self.pen_visible = True
            else:
                # PixelRevealEngine uses reveal sequence
                idx = min(self.reveal_engine.current_reveal_idx - 1, 
                         len(self.reveal_engine.reveal_sequence) - 1)
                if idx >= 0:
                    y, x, _ = self.reveal_engine.reveal_sequence[idx]
                    self.pen_pos = (int(x), int(y))
                    self.pen_visible = True
        else:
            self.pen_visible = False
    
    def draw(self):
        """Render the current frame."""
        # Clear screen
        self.screen.fill(self.theme["bg_color"])
        
        if self.reveal_engine:
            # Get current revealed frame
            frame_rgb = self.reveal_engine.get_current_frame()
            
            # Convert numpy array to pygame surface
            # Pygame expects (width, height, 3) but numpy is (height, width, 3)
            frame_surface = pygame.surfarray.make_surface(
                np.transpose(frame_rgb, (1, 0, 2))
            )
            
            self.screen.blit(frame_surface, (0, 0))
            
            # Draw animated frame if it's being drawn or complete
            if self.frame_drawing or self.frame_complete:
                frame_surf = self.frame_animator.get_surface()
                if frame_surf:
                    self.screen.blit(frame_surf, (0, 0))
            
            # Draw pen cursor if visible
            if self.pen_visible and self.show_pen:
                x, y = self.pen_pos
                self.pen_renderer.draw_pen(self.screen, x, y, self.reveal_engine)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Coloring Book Drawer Simulation")
    parser.add_argument("--width", type=int, default=800, help="Canvas width")
    parser.add_argument("--height", type=int, default=1000, help="Canvas height")
    # NOTE: FPS is now locked at 60 - removed --fps argument
    parser.add_argument("--image", type=str, help="Path to line art image")
    parser.add_argument("--speed", type=float, default=5.0, help="Drawing/animation speed (1-10)")
    parser.add_argument("--target-duration", type=float, help="Target duration in seconds (overrides --speed)")
    parser.add_argument("--thickness", type=float, default=1.0, help="Thickness multiplier")
    parser.add_argument("--no-pen", action="store_true", help="Hide pen cursor")
    parser.add_argument("--no-record", action="store_true", help="Disable auto-recording")
    parser.add_argument("--no-gpu", action="store_true", help="Disable GPU acceleration")
    parser.add_argument("--frame-thickness", type=int, default=6, help="Border frame thickness")
    parser.add_argument("--frame-speed", type=float, default=1.0, help="Border frame draw speed")
    parser.add_argument("--frame-margin", type=int, default=20, help="Border frame margin from edge")
    parser.add_argument("--custom-pen", type=str, help="Path to custom pen PNG image")
    parser.add_argument("--pen-tip-x", type=int, default=0, help="Custom pen tip X offset")
    parser.add_argument("--pen-tip-y", type=int, default=0, help="Custom pen tip Y offset")
    parser.add_argument("--pen-scale", type=float, default=1.0, help="Custom pen scale")
    parser.add_argument("--pen-rotation", action="store_true", help="Enable pen rotation")
    
    # New shading engine options
    parser.add_argument("--force-shading", action="store_true", 
                        help="Force use of pencil shading engine (for complex artwork)")
    parser.add_argument("--shading-sensitivity", type=float, default=0.5,
                        help="Shading detection sensitivity (0.0-1.0)")
    parser.add_argument("--hatching-angle", type=float, default=45.0,
                        help="Primary hatching angle in degrees")
    parser.add_argument("--stroke-spacing", type=int, default=3,
                        help="Spacing between hatching strokes in pixels")
    
    args = parser.parse_args()
    
    # Handle target duration mode
    if args.target_duration:
        # Note: Speed will be auto-calculated based on image complexity
        # For now, we'll use a reasonable default and let the simulation adjust
        # This is a placeholder - proper implementation would analyze the image first
        print(f"Target duration mode: {args.target_duration} seconds")
        print("Speed will be auto-adjusted to match duration...")
        # We'll pass this to the simulation constructor
    
    # Validate image path
    if args.image and not Path(args.image).exists():
        print(f"Error: Image file not found: {args.image}")
        sys.exit(1)
    
    # Create and run simulation (FPS is locked at 60)
    sim = ColoringBookDrawerSimulation(
        width=args.width,
        height=args.height,
        # FPS removed - always 60
        image_path=args.image,
        speed=args.speed,
        target_duration=args.target_duration,  # Auto-calculate speed if set
        thickness_scale=args.thickness,
        theme="classic",  # Only classic mode for exact reproduction
        show_pen=not args.no_pen,
        auto_record=not args.no_record,
        use_gpu=not args.no_gpu,
        frame_thickness=args.frame_thickness,
        frame_speed=args.frame_speed,
        frame_margin=args.frame_margin,
        custom_pen_path=args.custom_pen,
        pen_tip_x=args.pen_tip_x,
        pen_tip_y=args.pen_tip_y,
        pen_scale=args.pen_scale,
        pen_rotation=args.pen_rotation,
        # New shading engine options
        force_shading_engine=args.force_shading,
        shading_sensitivity=args.shading_sensitivity,
        hatching_angle=args.hatching_angle,
        stroke_spacing=args.stroke_spacing
    )
    
    sim.run()


if __name__ == "__main__":
    main()
