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
from loading_screen import LoadingScreen, BackgroundProcessor

# Import Engine 3 - Advanced Gradient Shading
try:
    from engines.advanced_gradient import AdvancedGradientEngine
    HAS_ADVANCED_GRADIENT = True
except ImportError as e:
    HAS_ADVANCED_GRADIENT = False
    print(f"Advanced Gradient Engine not available: {e}")

# Import Engine 3D - Zone Progressive Reveal
try:
    from engines.zone_progressive import ZoneProgressiveEngine
    HAS_ZONE_PROGRESSIVE = True
except ImportError as e:
    HAS_ZONE_PROGRESSIVE = False
    print(f"Zone Progressive Engine not available: {e}")

# Import Engine 3E - Adaptive Brush Simulation
try:
    from engines.adaptive_brush import AdaptiveBrushEngine
    HAS_ADAPTIVE_BRUSH = True
except ImportError as e:
    HAS_ADAPTIVE_BRUSH = False
    print(f"Adaptive Brush Engine not available: {e}")

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
    
    ENHANCED: Now supports five rendering engines:
    - PixelRevealEngine (Engine 1): For simple line drawings (fast, skeleton-based)
    - PencilShadingEngine (Engine 2): For complex shaded artwork with textures/shadows
    - AdvancedGradientEngine (Engine 3): For high-contrast pencil art with rich gradients
    - ZoneProgressiveEngine (Engine 3D): Focal-point-first dramatic reveal animation
    - AdaptiveBrushEngine (Engine 3E): Physics-based pencil simulation
    
    The engine is auto-selected based on image complexity analysis,
    or can be manually selected via the control panel.
    
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
                 hatching_angle=45.0, stroke_spacing=3,
                 edge_phases_first=1, shading_order="top_to_bottom",
                 engine_type="auto",
                 contour_sensitivity=0.5, gradient_smoothness=0.7,
                 texture_detection_strength=0.6, shadow_passes=3,
                 shadow_angle_variation=30.0, brush_softness_contour=0.3,
                 brush_softness_shading=0.7, pressure_variation=0.5,
                 zp_num_zones=10, zp_saliency_threshold=0.3,
                 zp_max_focal_points=5, zp_animation_mode="multi_focal",
                 zp_transition_width=0.1, zp_stroke_density=0.8,
                 zp_enable_portrait=True,
                 ab_tip_shape="round", ab_pencil_hardness=0.5,
                 ab_pencil_sharpness=0.7, ab_paper_type="cold_press",
                 ab_paper_texture_strength=0.5, ab_pressure_variation=0.5,
                 ab_graphite_buildup=0.7):
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
        self.edge_phases_first = edge_phases_first
        self.shading_order = shading_order
        self.using_shading_engine = False  # Will be set during setup
        self.using_advanced_gradient = False  # Will be set during setup
        self.using_zone_progressive = False  # Will be set during setup
        self.using_adaptive_brush = False  # Will be set during setup
        
        # Engine type: "auto", "pixel_reveal", "pencil_shading", "advanced_gradient", "zone_progressive", "adaptive_brush"
        self.engine_type = engine_type
        
        # Advanced Gradient Engine (Engine 3) settings
        self.contour_sensitivity = contour_sensitivity
        self.gradient_smoothness = gradient_smoothness
        self.texture_detection_strength = texture_detection_strength
        self.shadow_passes = shadow_passes
        self.shadow_angle_variation = shadow_angle_variation
        self.brush_softness_contour = brush_softness_contour
        self.brush_softness_shading = brush_softness_shading
        self.pressure_variation = pressure_variation
        
        # Zone Progressive Engine (Engine 3D) settings
        self.zp_num_zones = zp_num_zones
        self.zp_saliency_threshold = zp_saliency_threshold
        self.zp_max_focal_points = zp_max_focal_points
        self.zp_animation_mode = zp_animation_mode
        self.zp_transition_width = zp_transition_width
        self.zp_stroke_density = zp_stroke_density
        self.zp_enable_portrait = zp_enable_portrait
        
        # Adaptive Brush Engine (Engine 3E) settings
        self.ab_tip_shape = ab_tip_shape
        self.ab_pencil_hardness = ab_pencil_hardness
        self.ab_pencil_sharpness = ab_pencil_sharpness
        self.ab_paper_type = ab_paper_type
        self.ab_paper_texture_strength = ab_paper_texture_strength
        self.ab_pressure_variation = ab_pressure_variation
        self.ab_graphite_buildup = ab_graphite_buildup
        
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
                # Determine which engine to use
                if self.engine_type == "auto":
                    engine_choice = self._analyze_and_select_engine()
                    # Check if force_shading overrides
                    if self.force_shading_engine and engine_choice == "simple":
                        engine_choice = "shading"
                elif self.engine_type == "pixel_reveal":
                    engine_choice = "simple"
                elif self.engine_type == "pencil_shading":
                    engine_choice = "shading"
                elif self.engine_type == "advanced_gradient":
                    engine_choice = "advanced_gradient"
                elif self.engine_type == "zone_progressive":
                    engine_choice = "zone_progressive"
                elif self.engine_type == "adaptive_brush":
                    engine_choice = "adaptive_brush"
                else:
                    engine_choice = self._analyze_and_select_engine()
                
                if engine_choice == "advanced_gradient":
                    if not HAS_ADVANCED_GRADIENT:
                        print("\n⚠️  Advanced Gradient Engine not available, falling back to Pencil Shading")
                        engine_choice = "shading"
                    else:
                        print("\n🌈 Using ADVANCED GRADIENT ENGINE (Engine 3)")
                        self.using_advanced_gradient = True
                        self.using_shading_engine = False
                        
                        self.reveal_engine = AdvancedGradientEngine(
                            self.image_path,
                            self.width,
                            self.height,
                            padding=40,
                            use_gpu=self.use_gpu,
                            contour_sensitivity=self.contour_sensitivity,
                            gradient_smoothness=self.gradient_smoothness,
                            texture_detection_strength=self.texture_detection_strength,
                            shadow_passes=self.shadow_passes,
                            shadow_angle_variation=self.shadow_angle_variation,
                            brush_softness_contour=self.brush_softness_contour,
                            brush_softness_shading=self.brush_softness_shading,
                            pressure_variation=self.pressure_variation,
                        )
                        
                        # Process with loading screen (Engine 3 is slow like Engine 2)
                        self._process_with_loading_screen()
                
                if engine_choice == "zone_progressive":
                    if not HAS_ZONE_PROGRESSIVE:
                        print("\n⚠️  Zone Progressive Engine not available, falling back to Pencil Shading")
                        engine_choice = "shading"
                    else:
                        print("\n🎯 Using ZONE PROGRESSIVE ENGINE (Engine 3D)")
                        self.using_zone_progressive = True
                        self.using_advanced_gradient = False
                        self.using_shading_engine = False
                        
                        self.reveal_engine = ZoneProgressiveEngine(
                            self.image_path,
                            self.width,
                            self.height,
                            padding=40,
                            use_gpu=self.use_gpu,
                            num_zones=self.zp_num_zones,
                            saliency_threshold=self.zp_saliency_threshold,
                            max_focal_points=self.zp_max_focal_points,
                            animation_mode=self.zp_animation_mode,
                            transition_width=self.zp_transition_width,
                            stroke_density=self.zp_stroke_density,
                            enable_portrait=self.zp_enable_portrait,
                        )
                        
                        # Process with loading screen (saliency + zone computation)
                        self._process_with_loading_screen()
                
                if engine_choice == "adaptive_brush":
                    if not HAS_ADAPTIVE_BRUSH:
                        print("\n⚠️  Adaptive Brush Engine not available, falling back to Pencil Shading")
                        engine_choice = "shading"
                    else:
                        print("\n🖊️ Using ADAPTIVE BRUSH ENGINE (Engine 3E)")
                        self.using_adaptive_brush = True
                        self.using_zone_progressive = False
                        self.using_advanced_gradient = False
                        self.using_shading_engine = False
                        
                        self.reveal_engine = AdaptiveBrushEngine(
                            self.image_path,
                            self.width,
                            self.height,
                            padding=40,
                            use_gpu=self.use_gpu,
                            tip_shape=self.ab_tip_shape,
                            pencil_hardness=self.ab_pencil_hardness,
                            pencil_sharpness=self.ab_pencil_sharpness,
                            paper_type=self.ab_paper_type,
                            paper_texture_strength=self.ab_paper_texture_strength,
                            pressure_variation=self.ab_pressure_variation,
                            graphite_buildup=self.ab_graphite_buildup,
                        )
                        
                        # Process with loading screen (stroke extraction + physics)
                        self._process_with_loading_screen()
                
                if engine_choice == "shading":
                    print("\n🎨 Using PENCIL SHADING ENGINE (for complex artwork)")
                    self.using_shading_engine = True
                    self.using_advanced_gradient = False
                    
                    # Create engine instance
                    self.reveal_engine = PencilShadingEngine(
                        self.image_path,
                        self.width,
                        self.height,
                        padding=40,
                        use_gpu=self.use_gpu,
                        shade_sensitivity=self.shading_sensitivity,
                        hatching_angle=self.hatching_angle,
                        stroke_spacing=self.stroke_spacing,
                        edge_phases_first=self.edge_phases_first,
                        shading_order=self.shading_order
                    )
                    
                    # Process with loading screen (for shading engine which is slow)
                    self._process_with_loading_screen()
                    
                elif engine_choice == "simple":
                    print("\n✏️ Using PIXEL REVEAL ENGINE (for line art)")
                    self.using_shading_engine = False
                    self.using_advanced_gradient = False
                    self.reveal_engine = PixelRevealEngine(
                        self.image_path, 
                        self.width, 
                        self.height,
                        padding=40,
                        use_gpu=self.use_gpu
                    )
                    # PixelRevealEngine is fast, no loading screen needed
                    self.reveal_engine.process_image()
                
                # Adjust brush scale based on thickness setting (for PixelRevealEngine)
                if not self.using_shading_engine and not self.using_advanced_gradient and not self.using_zone_progressive and not self.using_adaptive_brush:
                    self.reveal_engine.brush_scale = 1.1 + (self.thickness_scale * 0.3)
                
                # Auto-calculate speed if target_duration is set
                if self.target_duration:
                    self._calculate_speed_for_duration()
                
            except Exception as e:
                print(f"Error processing image: {e}")
                import traceback
                traceback.print_exc()
    
    def _process_with_loading_screen(self):
        """Process the image with a loading screen to prevent UI freeze."""
        import threading
        import time
        
        # Create loading screen
        loading_screen = LoadingScreen(self.screen, self.width, self.height)
        
        # Flag for thread completion
        processing_complete = False
        processing_error = None
        
        # Define the processing function
        def do_processing():
            nonlocal processing_complete, processing_error
            try:
                # The progress callback will update the loading screen
                def progress_callback(step, name):
                    loading_screen.update_progress(step, name)
                
                self.reveal_engine.process_image(progress_callback)
                processing_complete = True
            except Exception as e:
                processing_error = str(e)
                import traceback
                traceback.print_exc()
        
        # Start processing in background thread
        processing_thread = threading.Thread(target=do_processing, daemon=True)
        processing_thread.start()
        
        # Run loading screen loop
        clock = pygame.time.Clock()
        while not processing_complete and processing_error is None:
            # Handle events to keep window responsive
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        sys.exit()
            
            # Draw loading screen
            loading_screen.draw()
            
            # Limit frame rate
            clock.tick(30)
        
        # Wait for thread to finish
        processing_thread.join(timeout=1.0)
        
        # Check for errors
        if processing_error:
            raise RuntimeError(f"Image processing failed: {processing_error}")
    
    def _analyze_and_select_engine(self):
        """
        Analyze the image to determine which rendering engine to use.
        
        Returns:
            "simple" for line art (use PixelRevealEngine)
            "shading" for complex artwork (use PencilShadingEngine)
            "advanced_gradient" for high-contrast pencil art (use AdvancedGradientEngine)
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
        
        # Calculate gradient complexity (for Engine 3 detection)
        # High gradient coverage + high shade coverage = advanced gradient territory
        high_gradient_coverage = np.mean(local_variance > 100)
        deep_dark_coverage = np.mean(gray < 150)
        
        print(f"\n📊 Image Analysis:")
        print(f"   Edge coverage: {100*edge_coverage:.1f}%")
        print(f"   Shade coverage: {100*shade_coverage:.1f}%")
        print(f"   Gradient regions: {100*gradient_coverage:.1f}%")
        print(f"   High gradient regions: {100*high_gradient_coverage:.1f}%")
        print(f"   Dark pixel coverage: {100*np.mean(very_dark_pixels):.1f}%")
        print(f"   Deep dark coverage: {100*deep_dark_coverage:.1f}%")
        
        # Decision logic:
        # Engine 3: Very complex - high gradient coverage AND deep dark areas
        # Requires both rich tonal range and significant dark regions
        if HAS_ADVANCED_GRADIENT and (
            (high_gradient_coverage > 0.08 and deep_dark_coverage > 0.10) or
            (shade_coverage > 0.20 and gradient_coverage > 0.10)
        ):
            print("   → Detected high-contrast artwork with rich gradients")
            return "advanced_gradient"
        # Engine 2: Moderate shading/textures
        elif shade_coverage > 0.10 or gradient_coverage > 0.05:
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
        if self.using_shading_engine or self.using_advanced_gradient or self.using_zone_progressive or self.using_adaptive_brush:
            # Phase/zone-based engines provide their own base speed
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
            if self.using_shading_engine or self.using_advanced_gradient or self.using_zone_progressive or self.using_adaptive_brush:
                # These engines provide pen position directly
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
    parser.add_argument("--edge-phases-first", type=int, default=1,
                        help="Number of edge layers to complete before shading (1-3)")
    parser.add_argument("--shading-order", type=str, default="top_to_bottom",
                        choices=["top_to_bottom", "natural", "random"],
                        help="Order for shading strokes after edges")
    
    # Engine selection
    parser.add_argument("--engine-type", type=str, default="auto",
                        choices=["auto", "pixel_reveal", "pencil_shading", "advanced_gradient", "zone_progressive", "adaptive_brush"],
                        help="Rendering engine to use (auto = auto-detect)")
    
    # Advanced Gradient Engine (Engine 3) options
    parser.add_argument("--contour-sensitivity", type=float, default=0.5,
                        help="Engine 3: Contour detection sensitivity (0.0-1.0)")
    parser.add_argument("--gradient-smoothness", type=float, default=0.7,
                        help="Engine 3: Gradient transition smoothness (0.0-1.0)")
    parser.add_argument("--texture-detection-strength", type=float, default=0.6,
                        help="Engine 3: Texture pattern detection strength (0.0-1.0)")
    parser.add_argument("--shadow-passes", type=int, default=3,
                        help="Engine 3: Number of shadow accumulation passes (1-6)")
    parser.add_argument("--shadow-angle-variation", type=float, default=30.0,
                        help="Engine 3: Angle variation between shadow passes (degrees)")
    parser.add_argument("--brush-softness-contour", type=float, default=0.3,
                        help="Engine 3: Brush softness for contour strokes (0.0-1.0)")
    parser.add_argument("--brush-softness-shading", type=float, default=0.7,
                        help="Engine 3: Brush softness for shading strokes (0.0-1.0)")
    parser.add_argument("--pressure-variation", type=float, default=0.5,
                        help="Engine 3: Stroke pressure variation (0.0-1.0)")
    
    # Zone Progressive Engine (Engine 3D) options
    parser.add_argument("--zp-num-zones", type=int, default=10,
                        help="Engine 3D: Number of reveal zones (3-25)")
    parser.add_argument("--zp-saliency-threshold", type=float, default=0.3,
                        help="Engine 3D: Minimum saliency for focal point detection (0.0-1.0)")
    parser.add_argument("--zp-max-focal-points", type=int, default=5,
                        help="Engine 3D: Maximum number of focal points (1-10)")
    parser.add_argument("--zp-animation-mode", type=str, default="multi_focal",
                        choices=["single_focal", "multi_focal", "spiral", "burst"],
                        help="Engine 3D: Animation mode for reveal")
    parser.add_argument("--zp-transition-width", type=float, default=0.1,
                        help="Engine 3D: Zone transition width (0.0-1.0)")
    parser.add_argument("--zp-stroke-density", type=float, default=0.8,
                        help="Engine 3D: Stroke density within zones (0.0-1.0)")
    parser.add_argument("--zp-enable-portrait", type=str, default="True",
                        help="Engine 3D: Enable portrait face/eye detection (True/False)")
    
    # Adaptive Brush Engine (Engine 3E) options
    parser.add_argument("--ab-tip-shape", type=str, default="round",
                        choices=["round", "chisel", "blunt"],
                        help="Engine 3E: Pencil tip shape")
    parser.add_argument("--ab-pencil-hardness", type=float, default=0.5,
                        help="Engine 3E: Pencil hardness 0=soft(6B), 1=hard(4H)")
    parser.add_argument("--ab-pencil-sharpness", type=float, default=0.7,
                        help="Engine 3E: Pencil sharpness (0.0-1.0)")
    parser.add_argument("--ab-paper-type", type=str, default="cold_press",
                        choices=["smooth", "cold_press", "rough"],
                        help="Engine 3E: Paper texture type")
    parser.add_argument("--ab-paper-texture-strength", type=float, default=0.5,
                        help="Engine 3E: Paper texture effect strength (0.0-1.0)")
    parser.add_argument("--ab-pressure-variation", type=float, default=0.5,
                        help="Engine 3E: Pressure variation amount (0.0-1.0)")
    parser.add_argument("--ab-graphite-buildup", type=float, default=0.7,
                        help="Engine 3E: Graphite saturation buildup speed (0.0-1.0)")
    
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
        stroke_spacing=args.stroke_spacing,
        edge_phases_first=args.edge_phases_first,
        shading_order=args.shading_order,
        # Engine selection
        engine_type=args.engine_type,
        # Advanced Gradient Engine (Engine 3) options
        contour_sensitivity=args.contour_sensitivity,
        gradient_smoothness=args.gradient_smoothness,
        texture_detection_strength=args.texture_detection_strength,
        shadow_passes=args.shadow_passes,
        shadow_angle_variation=args.shadow_angle_variation,
        brush_softness_contour=args.brush_softness_contour,
        brush_softness_shading=args.brush_softness_shading,
        pressure_variation=args.pressure_variation,
        # Zone Progressive Engine (Engine 3D) options
        zp_num_zones=args.zp_num_zones,
        zp_saliency_threshold=args.zp_saliency_threshold,
        zp_max_focal_points=args.zp_max_focal_points,
        zp_animation_mode=args.zp_animation_mode,
        zp_transition_width=args.zp_transition_width,
        zp_stroke_density=args.zp_stroke_density,
        zp_enable_portrait=str(args.zp_enable_portrait).lower() == "true",
        # Adaptive Brush Engine (Engine 3E) options
        ab_tip_shape=args.ab_tip_shape,
        ab_pencil_hardness=args.ab_pencil_hardness,
        ab_pencil_sharpness=args.ab_pencil_sharpness,
        ab_paper_type=args.ab_paper_type,
        ab_paper_texture_strength=args.ab_paper_texture_strength,
        ab_pressure_variation=args.ab_pressure_variation,
        ab_graphite_buildup=args.ab_graphite_buildup,
    )
    
    sim.run()


if __name__ == "__main__":
    main()
