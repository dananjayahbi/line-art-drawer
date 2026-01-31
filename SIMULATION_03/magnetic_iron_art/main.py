#!/usr/bin/env python3
"""
Magnetic Iron Filings Art - Main Simulation
=============================================
Creates mesmerizing portraits using simulated magnetic iron filings.
Particles are attracted to dark areas of a portrait image, forming
artistic renditions through physics-based animation.

Features:
- GPU acceleration using CuPy (NVIDIA) or NumPy fallback
- Inverse-square law magnetic physics
- Realistic iron filing particle rendering with shadows and glints
- Decorative animated border frame
- Configurable particle count, friction, inertia, and magnetic strength
- Auto-recording for video generation
- Interactive magnet cursor control
"""

import pygame
import pygame.gfxdraw
import math
import random
import argparse
import sys
import numpy as np
from pathlib import Path

# Add parent directory to path to access shared module
SIMULATION_DIR = Path(__file__).resolve().parent
BASE_DIR = SIMULATION_DIR.parent
sys.path.insert(0, str(BASE_DIR))

# Import modularized components
from magnetic_field_engine import MagneticFieldEngine
from particle_renderer import ParticleRenderer, MagnetRenderer
from frame_animator import FrameAnimator

# Try to import BaseSimulation from shared module
try:
    from base_simulation import BaseSimulation
except ImportError:
    # Fallback base class if shared module not available
    class BaseSimulation:
        """Fallback base simulation class if shared module not available."""
        
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
            """Save current frame to disk if recording."""
            if self.recording and self.frames_folder:
                frame_path = self.frames_folder / f"frame_{self.frame_count:06d}.png"
                pygame.image.save(self.screen, str(frame_path))
                self.frame_count += 1
        
        def run(self):
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
        
        def handle_events(self):
            """Handle pygame events. Override in subclass."""
            pass
        
        def update(self):
            """Update simulation state. Override in subclass."""
            pass
        
        def draw(self):
            """Draw simulation. Override in subclass."""
            pass


# ═══════════════════════════════════════════════════════════════════════════════
# SIMULATION STATES
# ═══════════════════════════════════════════════════════════════════════════════

class SimulationState:
    """Enumeration of simulation states."""
    PARTICLES_ACTIVE = "particles_active"      # Particles moving toward portrait
    FORMING_PORTRAIT = "forming_portrait"      # Particles settling into portrait shape
    FRAME_DRAWING = "frame_drawing"            # Drawing decorative border
    COMPLETE = "complete"                       # Simulation finished


# ═══════════════════════════════════════════════════════════════════════════════
# BACKGROUND GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════

def generate_parchment_background(width, height, base_color=(245, 240, 230)):
    """
    Generate a textured ivory/parchment background.
    
    Args:
        width: Background width
        height: Background height
        base_color: Base ivory color as RGB tuple
        
    Returns:
        pygame.Surface: Textured background surface
    """
    surface = pygame.Surface((width, height))
    
    # Fill with base color
    surface.fill(base_color)
    
    # Add subtle noise texture for parchment effect
    pixels = pygame.surfarray.pixels3d(surface)
    
    # Generate noise
    noise = np.random.randint(-8, 9, (width, height, 3), dtype=np.int16)
    
    # Apply noise to pixels
    result = np.clip(pixels.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    pixels[:] = result
    
    del pixels  # Release surface lock
    
    # Add subtle vignette effect
    vignette_surface = pygame.Surface((width, height), pygame.SRCALPHA)
    
    for i in range(50, 0, -5):
        alpha = int((50 - i) * 0.8)
        margin = i * 3
        rect = pygame.Rect(margin, margin, width - 2 * margin, height - 2 * margin)
        pygame.draw.rect(vignette_surface, (0, 0, 0, alpha), rect, 2)
    
    surface.blit(vignette_surface, (0, 0))
    
    return surface


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN SIMULATION
# ═══════════════════════════════════════════════════════════════════════════════

class MagneticIronArtSimulation(BaseSimulation):
    """
    Main simulation for magnetic iron filings portrait art.
    
    Simulates thousands of iron filing particles being attracted to 
    form a portrait image through magnetic field physics.
    
    NOTE: FPS is locked at 60 for smooth rendering and recording.
    The magnetic physics runs at this fixed timestep for consistency.
    """
    
    def __init__(self, width=540, height=960, image_path=None,
                 target_duration=None, particle_count=10000, particle_size=2.0,
                 magnetic_strength=1.0, friction=0.98, inertia=0.95,
                 shadow_enabled=True, glints_enabled=True, blur_enabled=True,
                 show_magnet=True, show_field_lines=False,
                 auto_record=True, use_gpu=True,
                 frame_thickness=6, frame_speed=1.0, frame_margin=20):
        """
        Initialize the magnetic iron art simulation.
        
        Args:
            width: Canvas width (default 540 for 9:16 aspect)
            height: Canvas height (default 960 for 9:16 aspect)
            image_path: Path to portrait image
            target_duration: Target animation duration in seconds
            particle_count: Number of iron filing particles
            particle_size: Base particle size multiplier
            magnetic_strength: Strength of magnetic attraction
            friction: Velocity damping factor (0-1)
            inertia: Velocity retention factor (0-1)
            shadow_enabled: Enable drop shadows on particles
            glints_enabled: Enable metallic glints on particles
            blur_enabled: Enable motion blur effect
            show_magnet: Show magnet cursor
            show_field_lines: Show magnetic field lines visualization
            auto_record: Auto-start recording frames
            use_gpu: Use GPU acceleration if available
            frame_thickness: Border frame line thickness
            frame_speed: Border frame drawing speed
            frame_margin: Border frame margin from edge
        """
        # FPS locked at 60 for consistent physics and smooth recording
        super().__init__(width, height, fps=60, title="Magnetic Iron Art")
        
        self.image_path = image_path
        self.target_duration = target_duration
        self.particle_count = particle_count
        self.particle_size = particle_size
        self.magnetic_strength = magnetic_strength
        self.friction = friction
        self.inertia = inertia
        self.auto_record = auto_record
        self.use_gpu = use_gpu
        self.show_field_lines = show_field_lines
        
        # Simulation state machine
        self.state = SimulationState.PARTICLES_ACTIVE
        
        # Physics engine
        self.field_engine = None
        
        # Renderers
        self.particle_renderer = ParticleRenderer(
            shadow_enabled=shadow_enabled,
            glints_enabled=glints_enabled,
            motion_blur_enabled=blur_enabled
        )
        self.magnet_renderer = MagnetRenderer()
        
        # Frame animator for border
        self.frame_animator = FrameAnimator(
            width=width,
            height=height,
            thickness=frame_thickness,
            speed=frame_speed,
            margin=frame_margin,
            color=(50, 45, 40)  # Dark brown/sepia for vintage look
        )
        
        # Cursor/magnet state
        self.magnet_x = width // 2
        self.magnet_y = height // 2
        self.magnet_active = False
        self.show_magnet_cursor = show_magnet
        
        # Previous particle positions for motion blur
        self.prev_particle_data = None
        
        # Background
        self.background_surface = None
        
        # Post-complete hold frames
        self.post_complete_frames = 0
        self.max_post_complete_frames = 180  # 3 seconds at 60fps
        
        # Initialize simulation
        self._setup()
    
    def _setup(self):
        """Initialize the simulation components."""
        # Setup recording folder
        frames_folder = SIMULATION_DIR / "frames"
        self.setup_frames_folder(frames_folder)
        
        if self.auto_record:
            self.start_recording()
        
        # Generate textured parchment background
        self.background_surface = generate_parchment_background(
            self.width, self.height
        )
        
        # Initialize physics engine if image provided
        if self.image_path:
            try:
                self.field_engine = MagneticFieldEngine(
                    image_path=self.image_path,
                    canvas_width=self.width,
                    canvas_height=self.height,
                    particle_count=self.particle_count,
                    padding=40,
                    use_gpu=self.use_gpu
                )
                
                # Apply physics parameters
                self.field_engine.magnetic_constant = 5000.0 * self.magnetic_strength
                self.field_engine.friction = self.friction
                self.field_engine.inertia = self.inertia
                self.field_engine.particle_base_size = self.particle_size
                
                # Process the portrait image
                self.field_engine.process_image()
                
                print(f"Simulation initialized with {self.particle_count} particles")
                print(f"Magnetic strength: {self.magnetic_strength}")
                print(f"Friction: {self.friction}, Inertia: {self.inertia}")
                
            except Exception as e:
                print(f"Error initializing physics engine: {e}")
                import traceback
                traceback.print_exc()
    
    def handle_events(self):
        """Handle pygame events including mouse and keyboard input."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                    
                elif event.key == pygame.K_SPACE:
                    self.paused = not self.paused
                    print("Paused" if self.paused else "Resumed")
                    
                elif event.key == pygame.K_r:
                    # Reset simulation
                    self._reset_simulation()
                    
                elif event.key == pygame.K_m:
                    # Toggle magnet cursor visibility
                    self.show_magnet_cursor = not self.show_magnet_cursor
                    
            elif event.type == pygame.MOUSEMOTION:
                # Update magnet position from mouse
                self.magnet_x, self.magnet_y = event.pos
                
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    self.magnet_active = True
                    
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:  # Left release
                    self.magnet_active = False
    
    def _reset_simulation(self):
        """Reset the simulation to initial state."""
        print("Resetting simulation...")
        
        self.state = SimulationState.PARTICLES_ACTIVE
        self.post_complete_frames = 0
        self.frame_animator.reset()
        self.prev_particle_data = None
        
        # Reinitialize particles
        if self.field_engine:
            self.field_engine._initialize_particles()
            self.field_engine.simulation_complete = False
            self.field_engine.particles_settled = 0
    
    def update(self):
        """Update simulation state for current frame."""
        if not self.field_engine:
            return
        
        if self.state == SimulationState.PARTICLES_ACTIVE:
            self._update_particles()
            
        elif self.state == SimulationState.FORMING_PORTRAIT:
            self._update_particles()
            
        elif self.state == SimulationState.FRAME_DRAWING:
            self._update_frame_drawing()
            
        elif self.state == SimulationState.COMPLETE:
            self._update_complete()
    
    def _update_particles(self):
        """Update particle physics."""
        # Store previous positions for motion blur
        self.prev_particle_data = self.field_engine.get_particles_data()
        
        # Update magnet position in physics engine
        self.field_engine.set_magnet_position(
            self.magnet_x, self.magnet_y, self.magnet_active
        )
        
        # Run physics update
        still_active = self.field_engine.update()
        
        # Check progress
        progress = self.field_engine.get_progress()
        
        if progress > 50 and self.state == SimulationState.PARTICLES_ACTIVE:
            self.state = SimulationState.FORMING_PORTRAIT
            print(f"Forming portrait... {progress:.1f}% settled")
        
        if not still_active or self.field_engine.simulation_complete:
            print("Portrait formation complete! Starting frame animation...")
            self.state = SimulationState.FRAME_DRAWING
    
    def _update_frame_drawing(self):
        """Update border frame drawing animation."""
        pen_pos = self.frame_animator.update()
        
        if self.frame_animator.complete:
            print("Frame complete! Holding final image...")
            self.state = SimulationState.COMPLETE
    
    def _update_complete(self):
        """Update complete state (hold final frame)."""
        self.post_complete_frames += 1
        
        if self.post_complete_frames >= self.max_post_complete_frames:
            print(f"Simulation complete. Total frames: {self.frame_count}")
            self.running = False
    
    def draw(self):
        """Render the current frame to screen."""
        # Draw background
        self.screen.blit(self.background_surface, (0, 0))
        
        if self.field_engine:
            # Get particle data for rendering
            particles_data = self.field_engine.get_particles_data()
            
            # Render particles with motion blur if enabled
            if self.prev_particle_data:
                self.particle_renderer.render_particles_with_motion_blur(
                    self.screen, particles_data, self.prev_particle_data
                )
            else:
                self.particle_renderer.render_particles(self.screen, particles_data)
            
            # Draw magnet cursor if active or visible
            if self.show_magnet_cursor and (
                self.state in [SimulationState.PARTICLES_ACTIVE, 
                               SimulationState.FORMING_PORTRAIT]
            ):
                self.magnet_renderer.draw_magnet(
                    self.screen, self.magnet_x, self.magnet_y, self.magnet_active
                )
        
        # Draw border frame if in frame drawing or complete state
        if self.state in [SimulationState.FRAME_DRAWING, SimulationState.COMPLETE]:
            frame_surface = self.frame_animator.get_surface()
            if frame_surface:
                self.screen.blit(frame_surface, (0, 0))
        
        # Draw progress/status overlay (optional, can be toggled)
        self._draw_status_overlay()
    
    def _draw_status_overlay(self):
        """Draw optional status information overlay."""
        if not self.field_engine:
            return
        
        # Only show during development/debug
        # Comment out for production renders
        
        # progress = self.field_engine.get_progress()
        # font = pygame.font.Font(None, 24)
        # text = font.render(f"Progress: {progress:.1f}%", True, (100, 100, 100))
        # self.screen.blit(text, (10, 10))


def main():
    """Main entry point with CLI argument parsing."""
    parser = argparse.ArgumentParser(
        description="Magnetic Iron Filings Art Simulation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --image portrait.jpg
  python main.py --image portrait.jpg --particles 15000 --strength 1.5
  python main.py --width 1080 --height 1920 --image portrait.jpg --duration 60
        """
    )
    
    # Canvas settings
    parser.add_argument("--width", type=int, default=540,
                        help="Canvas width (default: 540 for 9:16)")
    parser.add_argument("--height", type=int, default=960,
                        help="Canvas height (default: 960 for 9:16)")
    
    # Image input
    parser.add_argument("--image", type=str, required=False,
                        help="Path to portrait image")
    
    # Animation settings
    parser.add_argument("--duration", "--target-duration", type=float,
                        dest="duration",
                        help="Target duration in seconds")
    
    # Particle settings
    parser.add_argument("--particles", "--particle-count", type=int, default=10000,
                        dest="particles",
                        help="Number of particles (default: 10000)")
    
    # Physics settings
    parser.add_argument("--strength", "--magnetic-strength", type=float, default=1.0,
                        dest="strength",
                        help="Magnetic strength multiplier (default: 1.0)")
    
    # Particle size
    parser.add_argument("--particle-size", type=float, default=2.0,
                        help="Particle size multiplier (default: 2.0)")
    parser.add_argument("--friction", type=float, default=0.98,
                        help="Velocity damping factor 0-1 (default: 0.98)")
    parser.add_argument("--inertia", type=float, default=0.95,
                        help="Velocity retention factor 0-1 (default: 0.95)")
    
    # Visual effect toggles (effects are ON by default, use --no-* to disable)
    parser.add_argument("--no-shadows", action="store_true",
                        help="Disable drop shadows")
    parser.add_argument("--no-glints", action="store_true",
                        help="Disable metallic glints")
    parser.add_argument("--no-blur", action="store_true",
                        help="Disable motion blur")
    
    # Legacy flags for compatibility (effects enabled when present)
    parser.add_argument("--motion-blur", action="store_true",
                        help="Enable motion blur (enabled by default)")
    parser.add_argument("--drop-shadows", action="store_true",
                        help="Enable drop shadows (enabled by default)")
    parser.add_argument("--metallic-glints", action="store_true",
                        help="Enable metallic glints (enabled by default)")
    
    # Magnet visibility
    parser.add_argument("--no-magnet", action="store_true",
                        help="Hide magnet cursor")
    parser.add_argument("--show-field-lines", action="store_true",
                        help="Show magnetic field lines visualization")
    
    # Recording and GPU
    parser.add_argument("--no-record", action="store_true",
                        help="Disable auto-recording frames")
    parser.add_argument("--no-gpu", action="store_true",
                        help="Disable GPU acceleration")
    
    # Border frame settings
    parser.add_argument("--frame-thickness", type=int, default=6,
                        help="Border frame thickness (default: 6)")
    parser.add_argument("--frame-speed", type=float, default=1.0,
                        help="Border frame draw speed (default: 1.0)")
    parser.add_argument("--frame-margin", type=int, default=20,
                        help="Border frame margin from edge (default: 20)")
    
    args = parser.parse_args()
    
    # Validate image path if provided
    if args.image and not Path(args.image).exists():
        print(f"Error: Image file not found: {args.image}")
        sys.exit(1)
    
    # Warn if no image provided
    if not args.image:
        print("Warning: No image provided. Use --image <path> to specify a portrait.")
        print("Running in demo mode with centered attraction point.")
    
    # Handle effect flags - legacy positive flags override negative flags
    shadows_enabled = (not args.no_shadows) or args.drop_shadows
    glints_enabled = (not args.no_glints) or args.metallic_glints
    blur_enabled = (not args.no_blur) or args.motion_blur
    
    # Print configuration
    print("=" * 60)
    print("Magnetic Iron Filings Art Simulation")
    print("=" * 60)
    print(f"Canvas: {args.width}x{args.height}")
    print(f"Particles: {args.particles}")
    print(f"Particle Size: {args.particle_size}")
    print(f"Magnetic Strength: {args.strength}")
    print(f"Physics: friction={args.friction}, inertia={args.inertia}")
    print(f"Effects: shadows={shadows_enabled}, glints={glints_enabled}, blur={blur_enabled}")
    print(f"Recording: {not args.no_record}")
    print(f"GPU: {not args.no_gpu}")
    print("=" * 60)
    
    # Create and run simulation
    sim = MagneticIronArtSimulation(
        width=args.width,
        height=args.height,
        image_path=args.image,
        target_duration=args.duration,
        particle_count=args.particles,
        particle_size=args.particle_size,
        magnetic_strength=args.strength,
        friction=args.friction,
        inertia=args.inertia,
        shadow_enabled=shadows_enabled,
        glints_enabled=glints_enabled,
        blur_enabled=blur_enabled,
        show_magnet=not args.no_magnet,
        show_field_lines=args.show_field_lines,
        auto_record=not args.no_record,
        use_gpu=not args.no_gpu,
        frame_thickness=args.frame_thickness,
        frame_speed=args.frame_speed,
        frame_margin=args.frame_margin
    )
    
    sim.run()


if __name__ == "__main__":
    main()
