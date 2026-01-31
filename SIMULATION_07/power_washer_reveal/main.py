#!/usr/bin/env python3
"""
Power Washer Reveal - Main Simulation
======================================
Simulates a power washer cleaning effect to reveal an image underneath dirt/grime.
Uses realistic water particle physics and spray patterns.

How it works:
1. Load target image and cover with dirt/grime layer
2. User controls nozzle position with mouse or uses cinematic path mode
3. Water particles spray and erode the dirt layer
4. Progressive reveal with drip effects and water splatter
5. Realistic pressure-based wash radius

Features:
- Interactive mouse control for nozzle
- Pre-programmed cinematic wash paths
- Adjustable pressure/spray radius
- Realistic water particle physics
- Drip and splatter effects
- Auto-record frames for video generation
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

# Add parent directory to path to access shared module
SIMULATION_DIR = Path(__file__).resolve().parent
BASE_DIR = SIMULATION_DIR.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR.parent))

# Import modularized components
from power_washer_engine import PowerWasherEngine
from water_particle_system import WaterParticleSystem
from nozzle_renderer import NozzleRenderer

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
    from shared.base_simulation import BaseSimulation
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
# VISUAL THEMES
# ═══════════════════════════════════════════════════════════════════════════════

THEMES = {
    "classic": {
        "dirt_color": (89, 71, 51),        # Brown dirt
        "dirt_variation": 20,               # Color variation in dirt
        "water_color": (150, 200, 255, 180),  # Light blue water
        "splash_color": (200, 230, 255, 150),  # Splash droplets
        "bg_color": (40, 40, 40),           # Dark background
    },
    "mud": {
        "dirt_color": (60, 45, 30),         # Dark mud
        "dirt_variation": 15,
        "water_color": (120, 180, 255, 200),
        "splash_color": (180, 220, 255, 160),
        "bg_color": (30, 30, 30),
    },
    "dust": {
        "dirt_color": (150, 140, 120),      # Light dust
        "dirt_variation": 25,
        "water_color": (100, 180, 255, 150),
        "splash_color": (150, 200, 255, 120),
        "bg_color": (50, 50, 50),
    },
    "grime": {
        "dirt_color": (50, 55, 45),         # Dark grime/oil
        "dirt_variation": 10,
        "water_color": (140, 190, 255, 190),
        "splash_color": (190, 220, 255, 160),
        "bg_color": (35, 35, 35),
    },
}

# ═══════════════════════════════════════════════════════════════════════════════
# CINEMATIC WASH PATHS
# ═══════════════════════════════════════════════════════════════════════════════

class CinematicPath:
    """Pre-programmed wash paths for auto-mode."""
    
    @staticmethod
    def horizontal_sweep(width, height, passes=8, margin=50):
        """Horizontal sweep pattern from top to bottom."""
        path = []
        row_height = (height - 2 * margin) / passes
        
        for i in range(passes):
            y = margin + i * row_height + row_height / 2
            if i % 2 == 0:
                # Left to right
                path.append((margin, y))
                path.append((width - margin, y))
            else:
                # Right to left
                path.append((width - margin, y))
                path.append((margin, y))
        
        return path
    
    @staticmethod
    def vertical_sweep(width, height, passes=6, margin=50):
        """Vertical sweep pattern from left to right."""
        path = []
        col_width = (width - 2 * margin) / passes
        
        for i in range(passes):
            x = margin + i * col_width + col_width / 2
            if i % 2 == 0:
                # Top to bottom
                path.append((x, margin))
                path.append((x, height - margin))
            else:
                # Bottom to top
                path.append((x, height - margin))
                path.append((x, margin))
        
        return path
    
    @staticmethod
    def spiral_inward(width, height, turns=4, margin=50):
        """Spiral from outside to center."""
        path = []
        cx, cy = width / 2, height / 2
        max_radius = min(width, height) / 2 - margin
        points_per_turn = 60
        total_points = turns * points_per_turn
        
        for i in range(total_points):
            t = i / total_points
            radius = max_radius * (1 - t)
            angle = t * turns * 2 * math.pi
            x = cx + radius * math.cos(angle)
            y = cy + radius * math.sin(angle)
            path.append((x, y))
        
        return path
    
    @staticmethod
    def zigzag(width, height, rows=10, margin=50):
        """Zigzag pattern for thorough coverage."""
        path = []
        row_height = (height - 2 * margin) / rows
        
        for i in range(rows):
            y = margin + i * row_height
            if i % 2 == 0:
                for x in range(int(margin), int(width - margin), 30):
                    path.append((x, y))
            else:
                for x in range(int(width - margin), int(margin), -30):
                    path.append((x, y))
        
        return path
    
    @staticmethod
    def random_spots(width, height, num_spots=50, margin=50):
        """Random spot cleaning pattern."""
        path = []
        for _ in range(num_spots):
            x = random.randint(margin, width - margin)
            y = random.randint(margin, height - margin)
            # Add small circular motion around each spot
            for angle in range(0, 360, 30):
                rad = math.radians(angle)
                px = x + 20 * math.cos(rad)
                py = y + 20 * math.sin(rad)
                path.append((px, py))
        return path


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN SIMULATION
# ═══════════════════════════════════════════════════════════════════════════════

class PowerWasherRevealSimulation(BaseSimulation):
    """
    Main simulation for power washer reveal effect.
    Progressively reveals an image by washing away a dirt layer.
    
    NOTE: FPS is locked at 60 for smooth rendering and recording.
    The 'speed' parameter controls wash speed independently.
    In target_duration mode, speed is auto-calculated to match the desired duration.
    """
    
    def __init__(self, width=800, height=1000, image_path=None,
                 speed=5.0, target_duration=None, pressure=1.0, theme="classic",
                 show_nozzle=True, auto_record=True, use_gpu=True,
                 cinematic_mode=False, cinematic_path="horizontal",
                 particle_density=1.0, drip_enabled=True,
                 splash_enabled=True, wash_radius=40):
        # FPS is locked at 60 for all simulations
        super().__init__(width, height, fps=60, title="Power Washer Reveal")
        
        self.image_path = image_path
        self.target_duration = target_duration  # If set, speed will be auto-calculated
        self.speed = speed  # Will be overridden if target_duration is set
        self.pressure = pressure
        self.theme_name = theme
        self.theme = THEMES.get(theme, THEMES["classic"])
        self.show_nozzle = show_nozzle
        self.auto_record = auto_record
        self.use_gpu = use_gpu and HAS_GPU
        
        # Cinematic mode settings
        self.cinematic_mode = cinematic_mode
        self.cinematic_path_name = cinematic_path
        self.cinematic_path = []
        self.cinematic_index = 0
        self.cinematic_progress = 0.0
        
        # Effect settings
        self.particle_density = particle_density
        self.drip_enabled = drip_enabled
        self.splash_enabled = splash_enabled
        self.base_wash_radius = wash_radius
        
        # Engine and renderers
        self.wash_engine = None
        self.particle_system = None
        self.nozzle_renderer = None
        
        # Mouse/nozzle state
        self.nozzle_pos = (width // 2, height // 2)
        self.prev_nozzle_pos = self.nozzle_pos
        self.nozzle_active = False  # Whether washing is active
        self.mouse_pressed = False
        
        # Pressure control
        self.current_pressure = pressure
        self.min_pressure = 0.3
        self.max_pressure = 2.0
        
        # Rendering surfaces
        self.main_surface = None
        self.particle_surface = None
        
        # State
        self.wash_complete = False
        self.post_complete_frames = 0
        self.max_post_complete_frames = 120  # 2 seconds at 60fps
        self.completion_percentage = 0.0
        
        # Base wash rate (pixels revealed per frame at speed=1)
        self.base_wash_rate = 20
        
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
        
        # Create particle surface with alpha
        self.particle_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        
        # Initialize nozzle renderer
        self.nozzle_renderer = NozzleRenderer(
            width=self.width,
            height=self.height,
            theme=self.theme
        )
        
        # Initialize particle system
        self.particle_system = WaterParticleSystem(
            width=self.width,
            height=self.height,
            water_color=self.theme["water_color"],
            splash_color=self.theme["splash_color"],
            particle_density=self.particle_density,
            drip_enabled=self.drip_enabled,
            splash_enabled=self.splash_enabled
        )
        
        # Process image if provided
        if self.image_path:
            try:
                self.wash_engine = PowerWasherEngine(
                    self.image_path,
                    self.width,
                    self.height,
                    dirt_color=self.theme["dirt_color"],
                    dirt_variation=self.theme["dirt_variation"],
                    use_gpu=self.use_gpu
                )
                self.wash_engine.process_image()
                
                # Setup cinematic path if in cinematic mode
                if self.cinematic_mode:
                    self._setup_cinematic_path()
                
                # Auto-calculate speed if target_duration is set
                if self.target_duration:
                    self._calculate_speed_for_duration()
                
            except Exception as e:
                print(f"Error processing image: {e}")
                import traceback
                traceback.print_exc()
    
    def _setup_cinematic_path(self):
        """Setup the cinematic wash path."""
        path_generators = {
            "horizontal": lambda: CinematicPath.horizontal_sweep(self.width, self.height),
            "vertical": lambda: CinematicPath.vertical_sweep(self.width, self.height),
            "spiral": lambda: CinematicPath.spiral_inward(self.width, self.height),
            "zigzag": lambda: CinematicPath.zigzag(self.width, self.height),
            "random": lambda: CinematicPath.random_spots(self.width, self.height),
        }
        
        generator = path_generators.get(self.cinematic_path_name, 
                                         path_generators["horizontal"])
        self.cinematic_path = generator()
        self.cinematic_index = 0
        self.cinematic_progress = 0.0
        
        if self.cinematic_path:
            self.nozzle_pos = self.cinematic_path[0]
            self.prev_nozzle_pos = self.nozzle_pos
        
        print(f"Cinematic path '{self.cinematic_path_name}' initialized with {len(self.cinematic_path)} waypoints")
    
    def _calculate_speed_for_duration(self):
        """Calculate the speed needed to complete wash in target_duration seconds."""
        if not self.wash_engine or not self.target_duration:
            return
        
        # Estimate total pixels to wash (dirt coverage)
        total_dirt_pixels = self.wash_engine.get_total_dirt_pixels()
        
        # At 60 FPS, total frames for target duration
        target_frames = int(self.target_duration * 60)
        
        # Calculate wash area per frame needed
        # Wash radius affects area, so we need to account for that
        wash_area = math.pi * (self.base_wash_radius ** 2) * self.pressure
        pixels_per_wash = wash_area * 0.7  # Overlap factor
        
        washes_needed = total_dirt_pixels / pixels_per_wash
        washes_per_frame = washes_needed / target_frames
        
        # Calculate speed multiplier
        calculated_speed = washes_per_frame / self.base_wash_rate * 10
        
        # Clamp to reasonable range
        calculated_speed = max(0.5, min(15.0, calculated_speed))
        
        self.speed = calculated_speed
        print(f"Auto-calculated speed: {self.speed:.2f} (for {self.target_duration}s duration at 60 FPS)")
        print(f"Total dirt pixels: {total_dirt_pixels}, Target frames: {target_frames}")
    
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
                    # Reset simulation
                    self._reset()
                elif event.key == pygame.K_c:
                    # Toggle cinematic mode
                    self.cinematic_mode = not self.cinematic_mode
                    if self.cinematic_mode:
                        self._setup_cinematic_path()
                    print(f"Cinematic mode: {'ON' if self.cinematic_mode else 'OFF'}")
                elif event.key == pygame.K_UP:
                    # Increase pressure
                    self.current_pressure = min(self.max_pressure, 
                                                 self.current_pressure + 0.1)
                    print(f"Pressure: {self.current_pressure:.1f}")
                elif event.key == pygame.K_DOWN:
                    # Decrease pressure
                    self.current_pressure = max(self.min_pressure,
                                                 self.current_pressure - 0.1)
                    print(f"Pressure: {self.current_pressure:.1f}")
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    self.mouse_pressed = True
                    self.nozzle_active = True
                elif event.button == 4:  # Scroll up
                    self.current_pressure = min(self.max_pressure,
                                                 self.current_pressure + 0.1)
                elif event.button == 5:  # Scroll down
                    self.current_pressure = max(self.min_pressure,
                                                 self.current_pressure - 0.1)
            
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:  # Left click release
                    self.mouse_pressed = False
                    if not self.cinematic_mode:
                        self.nozzle_active = False
            
            elif event.type == pygame.MOUSEMOTION:
                if not self.cinematic_mode:
                    self.prev_nozzle_pos = self.nozzle_pos
                    self.nozzle_pos = event.pos
    
    def _reset(self):
        """Reset the simulation to initial state."""
        if self.wash_engine:
            self.wash_engine.reset()
        
        if self.particle_system:
            self.particle_system.clear()
        
        self.nozzle_pos = (self.width // 2, self.height // 2)
        self.prev_nozzle_pos = self.nozzle_pos
        self.nozzle_active = False
        self.wash_complete = False
        self.post_complete_frames = 0
        self.completion_percentage = 0.0
        self.current_pressure = self.pressure
        
        if self.cinematic_mode:
            self._setup_cinematic_path()
        
        print("Simulation reset")
    
    def _update_cinematic_position(self):
        """Update nozzle position along cinematic path."""
        if not self.cinematic_path or self.cinematic_index >= len(self.cinematic_path) - 1:
            return False
        
        # Calculate movement speed based on simulation speed
        move_speed = self.speed * 3  # Pixels per frame
        
        # Get current and next waypoint
        current_wp = self.cinematic_path[self.cinematic_index]
        next_wp = self.cinematic_path[self.cinematic_index + 1]
        
        # Calculate direction and distance
        dx = next_wp[0] - current_wp[0]
        dy = next_wp[1] - current_wp[1]
        dist = math.sqrt(dx * dx + dy * dy)
        
        if dist < 1:
            # At waypoint, move to next
            self.cinematic_index += 1
            return self.cinematic_index < len(self.cinematic_path) - 1
        
        # Normalize and apply speed
        self.cinematic_progress += move_speed / dist
        
        if self.cinematic_progress >= 1.0:
            # Reached next waypoint
            self.cinematic_index += 1
            self.cinematic_progress = 0.0
            if self.cinematic_index < len(self.cinematic_path):
                self.prev_nozzle_pos = self.nozzle_pos
                self.nozzle_pos = self.cinematic_path[self.cinematic_index]
        else:
            # Interpolate position
            self.prev_nozzle_pos = self.nozzle_pos
            x = current_wp[0] + dx * self.cinematic_progress
            y = current_wp[1] + dy * self.cinematic_progress
            self.nozzle_pos = (x, y)
        
        return True
    
    def update(self):
        """Update simulation state."""
        if not self.wash_engine:
            return
        
        if self.wash_complete:
            # Hold after completion
            self.post_complete_frames += 1
            if self.post_complete_frames >= self.max_post_complete_frames:
                self.running = False
            
            # Still update particles for visual effect
            self.particle_system.update()
            return
        
        # Update cinematic position if in cinematic mode
        if self.cinematic_mode:
            self.nozzle_active = True
            if not self._update_cinematic_position():
                # Path complete
                print("Cinematic path complete!")
                self.wash_complete = True
                return
        
        # Apply wash if active
        if self.nozzle_active:
            # Calculate wash radius based on pressure
            wash_radius = int(self.base_wash_radius * self.current_pressure)
            
            # Calculate wash points along movement path for smooth coverage
            x1, y1 = self.prev_nozzle_pos
            x2, y2 = self.nozzle_pos
            dx = x2 - x1
            dy = y2 - y1
            dist = math.sqrt(dx * dx + dy * dy)
            
            # Apply wash along path
            steps = max(1, int(dist / (wash_radius * 0.3)))
            for i in range(steps + 1):
                t = i / max(1, steps)
                x = x1 + dx * t
                y = y1 + dy * t
                
                # Apply wash at this position
                self.wash_engine.wash_at(
                    int(x), int(y),
                    radius=wash_radius,
                    intensity=self.current_pressure * self.speed * 0.1
                )
            
            # Spawn water particles
            self.particle_system.spawn_spray(
                self.nozzle_pos[0], self.nozzle_pos[1],
                pressure=self.current_pressure,
                radius=wash_radius
            )
            
            # Add drips
            if self.drip_enabled and random.random() < 0.3 * self.current_pressure:
                self.particle_system.spawn_drip(
                    self.nozzle_pos[0] + random.randint(-wash_radius, wash_radius),
                    self.nozzle_pos[1] + random.randint(-wash_radius, wash_radius)
                )
        
        # Update particles
        self.particle_system.update()
        
        # Check completion
        self.completion_percentage = self.wash_engine.get_completion_percentage()
        if self.completion_percentage >= 99.5:
            self.wash_complete = True
            print("Wash complete!")
    
    def draw(self):
        """Render the current frame."""
        # Clear screen
        self.screen.fill(self.theme["bg_color"])
        
        if self.wash_engine:
            # Get current washed frame
            frame_rgb = self.wash_engine.get_current_frame()
            
            # Convert numpy array to pygame surface
            frame_surface = pygame.surfarray.make_surface(
                np.transpose(frame_rgb, (1, 0, 2))
            )
            
            self.screen.blit(frame_surface, (0, 0))
            
            # Draw water particles
            self.particle_surface.fill((0, 0, 0, 0))
            self.particle_system.draw(self.particle_surface)
            self.screen.blit(self.particle_surface, (0, 0))
            
            # Draw nozzle/cursor if visible and active
            if self.show_nozzle:
                self.nozzle_renderer.draw(
                    self.screen,
                    self.nozzle_pos[0], self.nozzle_pos[1],
                    active=self.nozzle_active,
                    pressure=self.current_pressure,
                    radius=int(self.base_wash_radius * self.current_pressure)
                )
            
            # Draw completion percentage (optional HUD)
            if not self.wash_complete:
                self._draw_hud()
    
    def _draw_hud(self):
        """Draw heads-up display with stats."""
        font = pygame.font.SysFont('Arial', 16)
        
        # Completion percentage
        text = f"Cleaned: {self.completion_percentage:.1f}%"
        text_surface = font.render(text, True, (255, 255, 255))
        self.screen.blit(text_surface, (10, 10))
        
        # Pressure indicator
        pressure_text = f"Pressure: {self.current_pressure:.1f}x"
        pressure_surface = font.render(pressure_text, True, (255, 255, 255))
        self.screen.blit(pressure_surface, (10, 30))
        
        # Mode indicator
        mode_text = "Mode: Cinematic" if self.cinematic_mode else "Mode: Interactive"
        mode_surface = font.render(mode_text, True, (255, 255, 255))
        self.screen.blit(mode_surface, (10, 50))


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Power Washer Reveal Simulation")
    parser.add_argument("--width", type=int, default=800, help="Canvas width")
    parser.add_argument("--height", type=int, default=1000, help="Canvas height")
    parser.add_argument("--image", type=str, help="Path to target image to reveal")
    parser.add_argument("--speed", type=float, default=5.0, help="Wash speed (1-10)")
    parser.add_argument("--target-duration", type=float, help="Target duration in seconds (overrides --speed)")
    parser.add_argument("--pressure", type=float, default=1.0, help="Initial pressure (0.3-2.0)")
    parser.add_argument("--theme", type=str, default="classic", 
                        choices=["classic", "mud", "dust", "grime"],
                        help="Visual theme for dirt layer")
    parser.add_argument("--wash-radius", type=int, default=40, help="Base wash radius in pixels")
    parser.add_argument("--no-nozzle", action="store_true", help="Hide nozzle cursor")
    parser.add_argument("--no-record", action="store_true", help="Disable auto-recording")
    parser.add_argument("--no-gpu", action="store_true", help="Disable GPU acceleration")
    parser.add_argument("--cinematic", action="store_true", help="Enable cinematic auto-wash mode")
    parser.add_argument("--cinematic-path", type=str, default="horizontal",
                        choices=["horizontal", "vertical", "spiral", "zigzag", "random"],
                        help="Cinematic wash path pattern")
    parser.add_argument("--particle-density", type=float, default=1.0, 
                        help="Water particle density multiplier")
    parser.add_argument("--no-drips", action="store_true", help="Disable water drip effects")
    parser.add_argument("--no-splash", action="store_true", help="Disable splash effects")
    
    args = parser.parse_args()
    
    # Handle target duration mode
    if args.target_duration:
        print(f"Target duration mode: {args.target_duration} seconds")
        print("Speed will be auto-adjusted to match duration...")
    
    # Validate image path
    if args.image and not Path(args.image).exists():
        print(f"Error: Image file not found: {args.image}")
        sys.exit(1)
    
    # Create and run simulation
    sim = PowerWasherRevealSimulation(
        width=args.width,
        height=args.height,
        image_path=args.image,
        speed=args.speed,
        target_duration=args.target_duration,
        pressure=args.pressure,
        theme=args.theme,
        show_nozzle=not args.no_nozzle,
        auto_record=not args.no_record,
        use_gpu=not args.no_gpu,
        cinematic_mode=args.cinematic,
        cinematic_path=args.cinematic_path,
        particle_density=args.particle_density,
        drip_enabled=not args.no_drips,
        splash_enabled=not args.no_splash,
        wash_radius=args.wash_radius
    )
    
    print("\n=== Power Washer Reveal Controls ===")
    print("Mouse: Move nozzle")
    print("Left Click: Wash (reveal image)")
    print("Mouse Wheel: Adjust pressure")
    print("Up/Down Arrows: Adjust pressure")
    print("C: Toggle cinematic mode")
    print("Space: Pause/Resume")
    print("R: Reset")
    print("ESC: Quit")
    print("====================================\n")
    
    sim.run()


if __name__ == "__main__":
    main()
