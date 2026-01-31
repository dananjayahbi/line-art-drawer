#!/usr/bin/env python3
"""
Greedy String Art Simulation - Main Entry Point
================================================
Creates stunning string art using a greedy algorithm that iteratively
selects the darkest line paths to recreate an image with a single thread.

How it works:
1. Places nails evenly around a circular canvas
2. Starts from a random nail position
3. Iteratively finds the line that crosses the darkest pixels
4. Subtracts brightness along that line (simulating thread coverage)
5. Repeats until convergence or max lines reached

Features:
- GPU acceleration using CuPy (NVIDIA) or NumPy fallback
- Smooth 60 FPS animation with customizable speed
- Semi-transparent thread rendering with glow effects
- Camera tracking for cinematic views
- Target duration mode for auto-speed calculation
- Multiple visual themes (dark_wood, classic, modern)
"""

import pygame
import numpy as np
import argparse
import sys
import json
from pathlib import Path
from typing import Optional, Tuple

# Add parent directory to path to access shared module
SIMULATION_DIR = Path(__file__).resolve().parent
BASE_DIR = SIMULATION_DIR.parent
sys.path.insert(0, str(BASE_DIR))

# Import modularized components
from string_art_engine import StringArtEngine
from thread_renderer import ThreadRenderer
from settings_manager import SettingsManager

# GPU acceleration - try to import CuPy for CUDA support
HAS_GPU = False
GPU_INFO = "No GPU acceleration"

try:
    import cupy as cp
    
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

# Try to import shared BaseSimulation
try:
    from shared.base_simulation import BaseSimulation
except ImportError:
    # Fallback base class if shared module not available
    class BaseSimulation:
        """Fallback base simulation class with core Pygame loop."""
        
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
            """Set up the folder for saving frames."""
            self.frames_folder = Path(folder)
            self.frames_folder.mkdir(parents=True, exist_ok=True)
        
        def start_recording(self):
            """Start recording frames."""
            self.recording = True
        
        def stop_recording(self):
            """Stop recording frames."""
            self.recording = False
        
        def save_frame(self):
            """Save the current frame as a PNG."""
            if self.recording and self.frames_folder:
                frame_path = self.frames_folder / f"frame_{self.frame_count:06d}.png"
                pygame.image.save(self.screen, str(frame_path))
                self.frame_count += 1
        
        def run(self):
            """Main game loop."""
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
            """Handle pygame events (override in subclass)."""
            pass
        
        def update(self):
            """Update simulation state (override in subclass)."""
            pass
        
        def draw(self):
            """Render the current frame (override in subclass)."""
            pass


# ═══════════════════════════════════════════════════════════════════════════════
# VISUAL THEMES
# ═══════════════════════════════════════════════════════════════════════════════

THEMES = {
    "dark_wood": {
        "canvas_color": (26, 20, 16),      # Dark wooden brown
        "thread_color": (255, 255, 255),   # White thread
        "nail_color": (192, 160, 128),     # Brass/gold nail heads
        "bg_color": (20, 16, 12),          # Darker background
        "text_color": (200, 180, 150),     # Warm text color
    },
    "classic": {
        "canvas_color": (240, 235, 230),   # Off-white canvas
        "thread_color": (40, 40, 50),      # Dark thread
        "nail_color": (180, 180, 190),     # Silver nails
        "bg_color": (250, 248, 245),       # Light background
        "text_color": (60, 60, 70),        # Dark text
    },
    "modern": {
        "canvas_color": (30, 30, 35),      # Dark gray canvas
        "thread_color": (0, 255, 200),     # Cyan thread
        "nail_color": (255, 100, 100),     # Red nails
        "bg_color": (15, 15, 20),          # Very dark background
        "text_color": (150, 220, 255),     # Bright cyan text
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# STATE MACHINE STATES
# ═══════════════════════════════════════════════════════════════════════════════

class SimulationState:
    """States for the string art simulation."""
    INITIALIZING = "INITIALIZING"
    GENERATING = "GENERATING"
    COMPLETE = "COMPLETE"


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN SIMULATION
# ═══════════════════════════════════════════════════════════════════════════════

class GreedyStringArtSimulation(BaseSimulation):
    """
    Main string art simulation using greedy algorithm.
    Progressively draws threads between nails to recreate an image.
    
    NOTE: FPS is locked at 60 for smooth rendering and recording.
    The 'speed' parameter controls animation speed independently.
    In target_duration mode, speed is auto-calculated to match the desired duration.
    """
    
    def __init__(
        self,
        width: int = 1080,
        height: int = 1920,
        image_path: Optional[str] = None,
        nail_count: int = 250,
        max_lines: int = 3000,
        thread_opacity: float = 0.15,
        brightness_reduction: float = 0.12,
        min_distance: int = 20,
        speed: float = 1.0,
        target_duration: Optional[float] = None,
        use_gpu: bool = True,
        use_manim: bool = False,
        camera_follow: bool = True,
        theme: str = "dark_wood",
        fullscreen: bool = False,
        auto_record: bool = True,
        debug: bool = False
    ):
        """
        Initialize the Greedy String Art Simulation.
        
        Args:
            width: Canvas width in pixels
            height: Canvas height in pixels
            image_path: Path to the input image
            nail_count: Number of nails around the circle
            max_lines: Maximum number of thread lines to draw
            thread_opacity: Opacity of each thread line (0.0-1.0)
            brightness_reduction: Amount to reduce brightness per line
            min_distance: Minimum nail distance to avoid adjacent connections
            speed: Animation speed multiplier
            target_duration: Target duration in seconds (auto-calculates speed)
            use_gpu: Enable GPU acceleration if available
            use_manim: Use Manim for high-quality rendering
            camera_follow: Enable camera tracking
            theme: Visual theme (dark_wood, classic, modern)
            fullscreen: Run in fullscreen mode
            auto_record: Automatically start recording frames
            debug: Enable debug mode
        """
        # FPS is LOCKED at 60 for all simulations
        super().__init__(width, height, fps=60, title="Greedy String Art")
        
        # Handle fullscreen
        if fullscreen:
            self.screen = pygame.display.set_mode((width, height), pygame.FULLSCREEN)
        
        # Configuration
        self.image_path = image_path
        self.nail_count = nail_count
        self.max_lines = max_lines
        self.thread_opacity = thread_opacity
        self.brightness_reduction = brightness_reduction
        self.min_distance = min_distance
        self.speed = speed
        self.target_duration = target_duration
        self.use_gpu = use_gpu and HAS_GPU
        self.use_manim = use_manim
        self.camera_follow = camera_follow
        self.theme_name = theme
        self.theme = THEMES.get(theme, THEMES["dark_wood"])
        self.debug = debug
        self.auto_record = auto_record
        
        # State machine
        self.state = SimulationState.INITIALIZING
        
        # Engine components
        self.engine: Optional[StringArtEngine] = None
        self.renderer: Optional[ThreadRenderer] = None
        
        # Animation state
        self.current_line_index = 0
        self.lines_drawn = 0
        self.iterations_per_frame = 1  # Will be calculated based on speed
        
        # Statistics
        self.total_lines = 0
        self.completion_percentage = 0.0
        
        # Font for progress display
        pygame.font.init()
        self.font_large = pygame.font.SysFont("Arial", 36)
        self.font_small = pygame.font.SysFont("Arial", 18)
        
        # Setup
        self._setup()
    
    def _setup(self):
        """Initialize the simulation components."""
        print("\n" + "="*70)
        print("GREEDY STRING ART SIMULATION")
        print("="*70)
        
        # Setup recording folder
        frames_folder = SIMULATION_DIR / "frames"
        self.setup_frames_folder(frames_folder)
        
        if self.auto_record:
            print("Recording: ENABLED (frames will be saved)")
            self.start_recording()
        else:
            print("Recording: DISABLED")
        
        # Initialize thread renderer
        print(f"\nInitializing thread renderer...")
        print(f"  Canvas size: {self.width}x{self.height}")
        print(f"  Theme: {self.theme_name}")
        print(f"  Camera follow: {self.camera_follow}")
        
        # Calculate thread alpha (0-255) from opacity (0.0-1.0)
        thread_alpha = int(self.thread_opacity * 255)
        
        self.renderer = ThreadRenderer(
            canvas_size=(self.width, self.height),
            thread_color=self.theme["thread_color"],
            thread_alpha=thread_alpha,
            thread_thickness=1,
            glow_enabled=True,
            glow_radius=3,
            glow_strength=0.5,
            nail_color=self.theme["nail_color"],
            nail_radius=3,
            canvas_color=self.theme["canvas_color"],
            use_camera=self.camera_follow,
            camera_zoom=1.2,
            camera_smooth=0.1
        )
        
        # Initialize string art engine if image provided
        if self.image_path:
            print(f"\nInitializing string art engine...")
            print(f"  Image: {self.image_path}")
            print(f"  Nail count: {self.nail_count}")
            print(f"  Max lines: {self.max_lines}")
            print(f"  Thread opacity: {self.thread_opacity}")
            print(f"  Brightness reduction: {self.brightness_reduction}")
            print(f"  GPU acceleration: {self.use_gpu}")
            
            try:
                # Determine canvas size for the engine (use smaller dimension for circle)
                canvas_size = min(self.width, self.height)
                
                self.engine = StringArtEngine(
                    nail_count=self.nail_count,
                    canvas_size=canvas_size,
                    max_lines=self.max_lines,
                    line_weight=self.brightness_reduction,
                    min_distance=self.min_distance,
                    use_gpu=self.use_gpu,
                    convergence_threshold=0.001,
                    auto_contrast=True
                )
                
                # Load and process the image
                print(f"  Processing image...")
                self.engine.initialize(self.image_path)
                
                # Get nail positions for renderer
                nail_positions = self.engine.nail_positions
                self.renderer.nail_positions = nail_positions
                
                # Calculate center and radius for proper positioning
                center_x = self.width // 2
                center_y = self.height // 2
                radius = canvas_size // 2 - 50  # Leave some margin
                
                # Scale nail positions to fit canvas
                scaled_positions = []
                for x, y in nail_positions:
                    # Engine uses center at canvas_size/2, scale to our display
                    scaled_x = center_x + (x - canvas_size/2)
                    scaled_y = center_y + (y - canvas_size/2)
                    scaled_positions.append((scaled_x, scaled_y))
                
                self.renderer.nail_positions = np.array(scaled_positions)
                
                print(f"  ✓ Engine initialized successfully")
                
                # Auto-calculate speed if target duration is set
                if self.target_duration:
                    self._calculate_speed_for_duration()
                else:
                    # Calculate iterations per frame from speed
                    self._update_iterations_per_frame()
                
                # Transition to generating state
                self.state = SimulationState.GENERATING
                
            except Exception as e:
                print(f"  ✗ Error initializing engine: {e}")
                import traceback
                traceback.print_exc()
                self.state = SimulationState.COMPLETE
        else:
            print("\nNo image provided. Waiting for input...")
            self.state = SimulationState.COMPLETE
        
        print("="*70)
        print()
    
    def _calculate_speed_for_duration(self):
        """Calculate the speed needed to complete animation in target_duration seconds."""
        if not self.engine or not self.target_duration:
            return
        
        # Total lines to draw
        total_lines = self.max_lines
        
        # At 60 FPS, total frames for target duration
        target_frames = int(self.target_duration * 60)
        
        # Calculate lines per frame needed
        lines_per_frame = total_lines / target_frames
        
        # Speed is relative to lines per frame (base is 1 line per frame)
        calculated_speed = lines_per_frame
        
        # Clamp to reasonable range
        calculated_speed = max(0.1, min(50.0, calculated_speed))
        
        self.speed = calculated_speed
        self._update_iterations_per_frame()
        
        print(f"\n  Auto-calculated speed: {self.speed:.2f}")
        print(f"  Target duration: {self.target_duration}s at 60 FPS")
        print(f"  Total lines: {total_lines}")
        print(f"  Target frames: {target_frames}")
        print(f"  Lines per frame: {lines_per_frame:.2f}")
    
    def _update_iterations_per_frame(self):
        """Update the number of iterations per frame based on speed."""
        # Base rate: 1 line per frame at speed=1.0
        self.iterations_per_frame = max(1, int(self.speed))
    
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
                    status = "PAUSED" if self.paused else "RESUMED"
                    print(f"\n{status}")
                elif event.key == pygame.K_r:
                    # Reset animation
                    print("\nResetting animation...")
                    if self.engine:
                        self.engine.reset()
                        self.renderer.clear_threads()
                        self.current_line_index = 0
                        self.lines_drawn = 0
                        self.state = SimulationState.GENERATING
                        print("Reset complete!")
                elif event.key == pygame.K_UP:
                    # Increase speed
                    self.speed = min(50.0, self.speed * 1.5)
                    self._update_iterations_per_frame()
                    print(f"\nSpeed increased to {self.speed:.2f}x")
                elif event.key == pygame.K_DOWN:
                    # Decrease speed
                    self.speed = max(0.1, self.speed / 1.5)
                    self._update_iterations_per_frame()
                    print(f"\nSpeed decreased to {self.speed:.2f}x")
    
    def update(self):
        """Update simulation state."""
        if self.state == SimulationState.INITIALIZING:
            # Nothing to update during initialization
            pass
        
        elif self.state == SimulationState.GENERATING:
            if not self.engine:
                self.state = SimulationState.COMPLETE
                return
            
            # Run algorithm iterations
            for _ in range(self.iterations_per_frame):
                if self.lines_drawn >= self.max_lines:
                    # Reached max lines
                    self.state = SimulationState.COMPLETE
                    print(f"\n✓ String art complete! ({self.lines_drawn} lines drawn)")
                    break
                
                # Get current nail before selecting next
                from_nail = self.engine.current_nail_idx
                
                # Select next nail and draw line
                result = self.engine.select_next_nail()
                
                if result["converged"]:
                    # Algorithm converged
                    self.state = SimulationState.COMPLETE
                    print(f"\n✓ Algorithm converged! ({self.lines_drawn} lines drawn)")
                    break
                
                # Get the selected next nail
                to_nail = result["next_nail"]
                
                # Add line to renderer
                nail_positions = self.renderer.nail_positions
                start_pos = tuple(nail_positions[from_nail])
                end_pos = tuple(nail_positions[to_nail])
                
                # Draw the thread line immediately (accumulates on thread_layer)
                self.renderer.draw_thread_line(start_pos, end_pos, accumulate=True)
                
                # Update camera target if enabled
                if self.camera_follow:
                    self.renderer.update_camera(end_pos)
                
                self.lines_drawn += 1
                
                # Update progress
                self.completion_percentage = (self.lines_drawn / self.max_lines) * 100
                
                # Periodic progress updates (every 100 lines)
                if self.lines_drawn % 100 == 0:
                    print(f"  Progress: {self.lines_drawn}/{self.max_lines} lines "
                          f"({self.completion_percentage:.1f}%)")
        
        elif self.state == SimulationState.COMPLETE:
            # Animation complete, hold final frame
            pass
    
    def draw(self):
        """Render the current frame."""
        # Clear screen with background color
        self.screen.fill(self.theme["bg_color"])
        
        if not self.renderer:
            return
        
        # Draw canvas background
        self.renderer.draw_canvas(self.screen)
        
        # Apply glow effect if enabled
        if self.renderer.glow_enabled:
            self.renderer.apply_glow_effect()
            self.screen.blit(self.renderer.glow_layer, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        
        # Blit the accumulated thread layer to screen with transparency
        # Create a temporary surface to control alpha
        temp_thread_surface = self.renderer.thread_layer.copy()
        temp_thread_surface.set_alpha(int(self.thread_opacity * 255 * 2))  # Double for visibility
        self.screen.blit(temp_thread_surface, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        
        # Draw nails on top
        if self.renderer.nail_positions is not None:
            for i, nail_pos in enumerate(self.renderer.nail_positions):
                # Highlight current nail if generating
                if self.state == SimulationState.GENERATING and i == self.engine.current_nail_idx:
                    highlight_color = (255, 200, 100)
                    pygame.draw.circle(
                        self.screen,
                        highlight_color,
                        (int(nail_pos[0]), int(nail_pos[1])),
                        3 + 2
                    )
                self.renderer.draw_nail(self.screen, tuple(nail_pos))
        
        # Draw progress info
        self._draw_progress_info()
    
    def _draw_progress_info(self):
        """Draw progress information overlay."""
        text_color = self.theme["text_color"]
        
        # State label
        state_text = self.font_small.render(
            f"State: {self.state}",
            True,
            text_color
        )
        self.screen.blit(state_text, (10, 10))
        
        # Progress
        if self.state == SimulationState.GENERATING:
            progress_text = self.font_large.render(
                f"{self.lines_drawn} / {self.max_lines} lines ({self.completion_percentage:.1f}%)",
                True,
                text_color
            )
            text_rect = progress_text.get_rect(center=(self.width // 2, 40))
            self.screen.blit(progress_text, text_rect)
        
        # Speed
        speed_text = self.font_small.render(
            f"Speed: {self.speed:.2f}x (↑↓ to adjust)",
            True,
            text_color
        )
        self.screen.blit(speed_text, (10, 35))
        
        # Controls
        controls = [
            "ESC: Quit",
            "SPACE: Pause/Resume",
            "R: Reset",
            "↑/↓: Speed"
        ]
        y_offset = self.height - 20 * len(controls) - 10
        for i, control in enumerate(controls):
            control_text = self.font_small.render(control, True, text_color)
            self.screen.blit(control_text, (10, y_offset + i * 20))
        
        # Debug info
        if self.debug:
            debug_lines = [
                f"FPS: {self.clock.get_fps():.1f}",
                f"Iterations/frame: {self.iterations_per_frame}",
                f"GPU: {self.use_gpu}",
                f"Recording: {self.recording}",
                f"Frames captured: {self.frame_count}",
            ]
            y_offset = self.height // 2 - len(debug_lines) * 10
            for i, line in enumerate(debug_lines):
                debug_text = self.font_small.render(line, True, (255, 255, 0))
                self.screen.blit(debug_text, (self.width - 250, y_offset + i * 20))


# ═══════════════════════════════════════════════════════════════════════════════
# COMMAND LINE INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """Main entry point with CLI argument parsing."""
    parser = argparse.ArgumentParser(
        description="Greedy String Art Simulation - Create stunning string art from images",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage with auto-calculated speed for 15-second video
  python main.py --image photo.jpg --target-duration 15

  # Custom parameters
  python main.py --image photo.jpg --nail-count 300 --max-lines 4000

  # High-quality with GPU acceleration
  python main.py --image photo.jpg --use-gpu --target-duration 20

  # Modern theme with camera tracking
  python main.py --image photo.jpg --theme modern --camera-follow
        """
    )
    
    # Image settings
    parser.add_argument("--image", type=str, help="Path to input image")
    
    # Window settings
    parser.add_argument("--width", type=int, default=1080, help="Canvas width (default: 1080)")
    parser.add_argument("--height", type=int, default=1920, help="Canvas height (default: 1920)")
    parser.add_argument("--fullscreen", action="store_true", help="Run in fullscreen mode")
    
    # Algorithm settings
    parser.add_argument("--nail-count", type=int, default=250, 
                        help="Number of nails around circle (default: 250)")
    parser.add_argument("--max-lines", type=int, default=3000,
                        help="Maximum thread lines to draw (default: 3000)")
    parser.add_argument("--thread-opacity", type=float, default=0.15,
                        help="Thread opacity 0.0-1.0 (default: 0.15)")
    parser.add_argument("--brightness-reduction", type=float, default=0.12,
                        help="Brightness reduction per line (default: 0.12)")
    parser.add_argument("--min-distance", type=int, default=20,
                        help="Minimum nail distance to avoid adjacent connections (default: 20)")
    
    # Performance settings
    parser.add_argument("--use-gpu", action="store_true",
                        help="Enable GPU acceleration (requires CuPy)")
    parser.add_argument("--use-manim", action="store_true",
                        help="Use Manim for high-quality rendering")
    
    # Animation settings
    parser.add_argument("--speed", type=float, default=1.0,
                        help="Animation speed multiplier (default: 1.0)")
    parser.add_argument("--target-duration", type=float,
                        help="Target duration in seconds (auto-calculates speed)")
    parser.add_argument("--camera-follow", action="store_true",
                        help="Enable camera tracking of thread drawing")
    
    # Visual settings
    parser.add_argument("--theme", type=str, default="dark_wood",
                        choices=["dark_wood", "classic", "modern"],
                        help="Visual theme (default: dark_wood)")
    
    # Canvas color settings
    parser.add_argument("--canvas-color", type=str, default="#1a1410",
                        help="Canvas background color (default: #1a1410)")
    parser.add_argument("--thread-color", type=str, default="#ffffff",
                        help="Thread color (default: #ffffff)")
    parser.add_argument("--nail-color", type=str, default="#c0a080",
                        help="Nail head color (default: #c0a080)")
    parser.add_argument("--nail-radius", type=int, default=3,
                        help="Nail radius in pixels (default: 3)")
    
    # Optimization settings
    parser.add_argument("--convergence", type=float, default=0.001,
                        help="Convergence threshold (default: 0.001)")
    parser.add_argument("--lookahead", type=int, default=0,
                        help="Lookahead nails (0=all, >0=nearest N) (default: 0)")
    
    # Camera settings
    parser.add_argument("--zoom", type=float, default=1.2,
                        help="Camera zoom level (default: 1.2)")
    
    # Visual effects
    parser.add_argument("--show-accumulation", action="store_true", default=True,
                        help="Show thread accumulation (default: True)")
    parser.add_argument("--glow", action="store_true", default=True,
                        help="Enable glow effect (default: True)")
    parser.add_argument("--motion-blur", action="store_true", default=True,
                        help="Enable motion blur (default: True)")
    parser.add_argument("--progress-bar", action="store_true", default=True,
                        help="Show progress bar (default: True)")
    
    # Border settings
    parser.add_argument("--show-border", action="store_true", default=True,
                        help="Show border frame (default: True)")
    parser.add_argument("--border-width", type=int, default=40,
                        help="Border width in pixels (default: 40)")
    
    # Recording settings
    parser.add_argument("--record", action="store_true", default=True,
                        help="Enable frame recording (default: True)")
    parser.add_argument("--no-record", dest="record", action="store_false",
                        help="Disable frame recording")
    parser.add_argument("--quality", type=int, default=95,
                        help="Recording quality 0-100 (default: 95)")
    
    # Debug
    parser.add_argument("--debug", action="store_true",
                        help="Enable debug mode with additional info")
    
    args = parser.parse_args()
    
    # Validate image path
    if args.image:
        image_path = Path(args.image)
        if not image_path.exists():
            print(f"Error: Image file not found: {args.image}")
            sys.exit(1)
        image_path_str = str(image_path.resolve())
    else:
        print("Warning: No image provided. Simulation will start in idle state.")
        print("Use --image <path> to specify an input image.")
        image_path_str = None
    
    # Print configuration
    print("\n" + "="*70)
    print("GREEDY STRING ART - Configuration")
    print("="*70)
    print(f"Image: {image_path_str if image_path_str else 'None'}")
    print(f"Canvas: {args.width}x{args.height}")
    print(f"Nails: {args.nail_count}")
    print(f"Max Lines: {args.max_lines}")
    print(f"Thread Opacity: {args.thread_opacity}")
    print(f"Speed: {args.speed}x" if not args.target_duration else f"Target Duration: {args.target_duration}s")
    print(f"Theme: {args.theme}")
    print(f"GPU: {'Enabled' if args.use_gpu and HAS_GPU else 'Disabled'}")
    print(f"Camera Follow: {'Enabled' if args.camera_follow else 'Disabled'}")
    print(f"Recording: {'Enabled' if args.record else 'Disabled'}")
    print("="*70 + "\n")
    
    # Create and run simulation (FPS locked at 60)
    sim = GreedyStringArtSimulation(
        width=args.width,
        height=args.height,
        image_path=image_path_str,
        nail_count=args.nail_count,
        max_lines=args.max_lines,
        thread_opacity=args.thread_opacity,
        brightness_reduction=args.brightness_reduction,
        min_distance=args.min_distance,
        speed=args.speed,
        target_duration=args.target_duration,
        use_gpu=args.use_gpu,
        use_manim=args.use_manim,
        camera_follow=args.camera_follow,
        theme=args.theme,
        fullscreen=args.fullscreen,
        auto_record=args.record,
        debug=args.debug
    )
    
    sim.run()
    
    print("\n" + "="*70)
    print("Simulation complete!")
    if sim.recording:
        print(f"Frames saved to: {sim.frames_folder}")
        print(f"Total frames: {sim.frame_count}")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
