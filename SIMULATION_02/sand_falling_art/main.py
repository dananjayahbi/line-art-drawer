#!/usr/bin/env python3
"""
Sand Falling Art - Main Simulation
===================================
Physics-based sand art simulation where colored sand grains fall and pile up
to form a target image using realistic collision physics.

Features:
- Pymunk physics engine for realistic sand behavior
- Colored sand particles matching target image
- Progressive image formation through particle accumulation
- Video recording support
"""

import pygame
import sys
import argparse
import json
import time
from pathlib import Path
from typing import Optional
import random
import math

# Add parent directory to path
SIMULATION_DIR = Path(__file__).resolve().parent
BASE_DIR = SIMULATION_DIR.parent
sys.path.insert(0, str(BASE_DIR))

# Import modularized components
from physics_engine import PhysicsEngine, SandParticle
from sand_renderer import SandRenderer
from image_target import ImageTarget

# Import base simulation
try:
    sys.path.insert(0, str(BASE_DIR / "shared"))
    from base_simulation import BaseSimulation
except ImportError:
    # Fallback base class
    class BaseSimulation:
        def __init__(self, width=1200, height=700, fps=60, title="Simulation"):
            pygame.init()
            self.width = width
            self.height = height
            self.fps = fps
            self.title = title
            self.screen = pygame.display.set_mode((width, height))
            pygame.display.set_caption(title)
            self.clock = pygame.time.Clock()
            self.font = pygame.font.SysFont('Arial', 24)
            self.recording = False
            self.frame_count = 0
            self.frames_folder = "frames"
            self.running = True
            self.paused = False
        
        def setup_frames_folder(self, folder_path=None):
            if folder_path:
                self.frames_folder = folder_path
            Path(self.frames_folder).mkdir(parents=True, exist_ok=True)
        
        def save_frame(self):
            if self.recording:
                filename = Path(self.frames_folder) / f"frame_{self.frame_count:06d}.png"
                pygame.image.save(self.screen, str(filename))
                self.frame_count += 1
        
        def start_recording(self):
            self.recording = True
            self.frame_count = 0
            self.setup_frames_folder()
        
        def stop_recording(self):
            self.recording = False
        
        def quit(self):
            self.running = False
        
        def run(self):
            """Main simulation loop."""
            while self.running:
                self.handle_events()
                if not self.paused:
                    self.update()
                self.draw()
                if self.recording:
                    self.save_frame()
                pygame.display.flip()
                self.clock.tick(self.fps)
            pygame.quit()


class SandFallingArtSimulation(BaseSimulation):
    """Main sand falling art simulation."""
    
    def __init__(self, image_path: str, width: int = 1600, height: int = 1200, 
                 fps: int = 60, particle_size: float = 2.0, spawn_rate: int = 10,
                 gravity: float = 980.0, auto_record: bool = False, use_gpu: bool = True):
        """
        Initialize simulation.
        
        Args:
            image_path: Path to target image
            width: Screen width (4:3 aspect ratio recommended)
            height: Screen height
            fps: Frames per second
            particle_size: Sand particle radius
            spawn_rate: Particles spawned per frame
            gravity: Gravity strength
            auto_record: Start recording automatically
            use_gpu: Use GPU acceleration if available
        """
        super().__init__(width, height, fps, "Sand Falling Art")
        
        # Configuration
        self.image_path = image_path
        self.particle_size = particle_size
        self.spawn_rate = spawn_rate
        self.gravity = gravity
        self.use_gpu = use_gpu
        
        # Initialize physics engine
        self.physics = PhysicsEngine(width, height, gravity)
        
        # Initialize renderer
        self.renderer = SandRenderer(width, height)
        
        # Initialize image target
        target_width = int(width * 0.6)  # 60% of screen width
        target_height = int(height * 0.7)  # 70% of screen height
        self.target = ImageTarget(image_path, target_width, target_height)
        
        # Calculate spawn area
        self.spawn_y = 50  # Spawn from top
        img_width, img_height = self.target.get_image_dimensions()
        self.spawn_width = img_width
        self.spawn_x_offset = (width - img_width) // 2
        
        # Calculate target position offset
        self.target_offset_x, self.target_offset_y = self.target.get_image_offset(width, height)
        
        # Simulation state
        self.particle_index = 0
        self.spawn_timer = 0
        self.spawn_delay = max(1, 60 // spawn_rate)  # Frames between spawns
        self.simulation_complete = False
        
        # Statistics
        self.start_time = time.time()
        self.total_particles_to_spawn = self.target.get_total_pixels()
        
        # Setup recording
        if auto_record:
            frames_dir = SIMULATION_DIR / "frames"
            self.setup_frames_folder(str(frames_dir))
            self.start_recording()
        
        print(f"Simulation initialized:")
        print(f"  Target: {self.total_particles_to_spawn} particles")
        print(f"  Image size: {self.target.get_image_dimensions()}")
        print(f"  Spawn area: {self.spawn_width}px wide")
    
    def handle_events(self):
        """Handle pygame events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE or event.key == pygame.K_q:
                    self.running = False
                
                elif event.key == pygame.K_SPACE:
                    self.paused = not self.paused
                
                elif event.key == pygame.K_r:
                    # Toggle recording
                    if self.recording:
                        self.stop_recording()
                        print("Recording stopped")
                    else:
                        self.start_recording()
                        print("Recording started")
                
                elif event.key == pygame.K_d:
                    # Toggle physics debug
                    self.renderer.show_physics_debug = not self.renderer.show_physics_debug
                
                elif event.key == pygame.K_t:
                    # Toggle target outline
                    self.renderer.show_target_outline = not self.renderer.show_target_outline
                
                elif event.key == pygame.K_g:
                    # Toggle particle glow
                    self.renderer.particle_glow = not self.renderer.particle_glow
    
    def update(self):
        """Update simulation state."""
        if self.simulation_complete:
            # Keep physics running for settling
            self.physics.step()
            return
        
        # Spawn new particles
        self.spawn_timer += 1
        if self.spawn_timer >= self.spawn_delay:
            self.spawn_timer = 0
            self._spawn_particles()
        
        # Update physics
        self.physics.step()
        
        # Check completion
        if self.particle_index >= self.total_particles_to_spawn:
            if len(self.physics.get_active_particles()) == 0:
                self.simulation_complete = True
                print("Simulation complete! All particles settled.")
    
    def _spawn_particles(self):
        """Spawn sand particles."""
        for _ in range(self.spawn_rate):
            if self.particle_index >= self.total_particles_to_spawn:
                break
            
            # Get particle info from target
            particle_info = self.target.get_next_particle_info(self.particle_index)
            if particle_info is None:
                break
            
            target_pos, color = particle_info
            
            # Calculate spawn position
            # Spawn above the target pixel position with some randomness
            spawn_x = self.target_offset_x + target_pos[0] + random.uniform(-5, 5)
            spawn_y = self.spawn_y + random.uniform(-10, 10)
            
            # Clamp to spawn area
            spawn_x = max(self.spawn_x_offset, min(self.spawn_x_offset + self.spawn_width, spawn_x))
            
            # Create particle
            particle = self.physics.create_sand_particle(
                spawn_x, spawn_y,
                self.particle_size,
                color,
                target_pos
            )
            
            if particle:
                self.particle_index += 1
    
    def draw(self):
        """Draw simulation."""
        # Clear screen
        self.screen.fill((30, 30, 40))  # Dark blue-gray background
        
        # Draw container frame
        if hasattr(self.physics, 'container_bounds'):
            self.renderer.render_container_frame(self.screen, self.physics.container_bounds)
        
        # Draw spawn indicator
        self.renderer.render_spawn_area(self.screen, self.spawn_y, self.spawn_width)
        
        # Draw particles
        particles = self.physics.particles
        self.renderer.render_particles(self.screen, particles, antialiasing=True)
        
        # Draw statistics
        stats = self._get_stats()
        self.renderer.render_stats(self.screen, stats, 10, 10)
        
        # Draw progress bar
        progress = self.particle_index / max(1, self.total_particles_to_spawn)
        self.renderer.render_progress_bar(
            self.screen, progress,
            self.width - 320, 10, 300, 25
        )
        
        # Draw pause overlay
        if self.paused:
            self.renderer.render_pause_overlay(self.screen)
        
        # Draw controls hint
        self._draw_controls()
    
    def _get_stats(self) -> dict:
        """Get current statistics."""
        physics_stats = self.physics.get_stats()
        elapsed_time = time.time() - self.start_time
        
        return {
            'Spawned': f"{self.particle_index}/{self.total_particles_to_spawn}",
            'Active': physics_stats['active_particles'],
            'Settled': physics_stats['settled_particles'],
            'FPS': int(self.clock.get_fps()),
            'Time': f"{elapsed_time:.1f}s",
            'Recording': 'ON' if self.recording else 'OFF'
        }
    
    def _draw_controls(self):
        """Draw control hints."""
        font = pygame.font.SysFont('Consolas', 14)
        controls = [
            "SPACE: Pause",
            "R: Record",
            "T: Target Outline",
            "G: Glow",
            "ESC: Quit"
        ]
        
        y_offset = self.height - 120
        for i, text in enumerate(controls):
            surface = font.render(text, True, (180, 180, 180))
            self.screen.blit(surface, (10, y_offset + i * 20))


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Sand Falling Art Simulation")
    parser.add_argument("--image", type=str, help="Path to target image")
    parser.add_argument("--width", type=int, default=1600, help="Window width (4:3 ratio)")
    parser.add_argument("--height", type=int, default=1200, help="Window height (4:3 ratio)")
    parser.add_argument("--fps", type=int, default=60, help="Frames per second")
    parser.add_argument("--particle-size", type=float, default=2.0, help="Particle radius")
    parser.add_argument("--spawn-rate", type=int, default=10, help="Particles per frame")
    parser.add_argument("--gravity", type=float, default=980.0, help="Gravity strength")
    parser.add_argument("--record", action="store_true", help="Auto-start recording")
    parser.add_argument("--use-gpu", action="store_true", default=True, help="Use GPU acceleration")
    
    args = parser.parse_args()
    
    # Get image path
    image_path = args.image
    if not image_path:
        # Try to find an image in uploads folder
        uploads_folder = SIMULATION_DIR / "uploads"
        if uploads_folder.exists():
            images = list(uploads_folder.glob("*.png")) + list(uploads_folder.glob("*.jpg"))
            if images:
                image_path = str(images[0])
    
    if not image_path or not Path(image_path).exists():
        print("Error: No image specified or found!")
        print("Usage: python main.py --image path/to/image.png")
        sys.exit(1)
    
    # Create and run simulation
    sim = SandFallingArtSimulation(
        image_path=image_path,
        width=args.width,
        height=args.height,
        fps=args.fps,
        particle_size=args.particle_size,
        spawn_rate=args.spawn_rate,
        gravity=args.gravity,
        auto_record=args.record,
        use_gpu=args.use_gpu
    )
    
    sim.run()


if __name__ == "__main__":
    main()
