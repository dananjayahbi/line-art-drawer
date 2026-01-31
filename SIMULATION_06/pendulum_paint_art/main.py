#!/usr/bin/env python3
"""
Pendulum Paint Art - Main Simulation
======================================
Main simulation engine combining pendulum physics, drip system, and paint rendering.

Features:
- Dual-axis pendulum with damped harmonic oscillation
- Attraction-weighted paint dripping
- Glossy acrylic paint rendering
- Video recording support
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

# OpenCV for image processing
import cv2
from PIL import Image

# Add parent directory to path
SIMULATION_DIR = Path(__file__).resolve().parent
BASE_DIR = SIMULATION_DIR.parent
sys.path.insert(0, str(BASE_DIR))

# Import modularized components
from pendulum_physics_engine import PendulumPhysicsEngine
from drip_engine import DripEngine
from paint_renderer import PaintRenderer
from frame_animator import FrameAnimator


# ═══════════════════════════════════════════════════════════════════════════════
# BASE SIMULATION CLASS
# ═══════════════════════════════════════════════════════════════════════════════

class BaseSimulation:
    """Base simulation class with common functionality."""
    
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
# MAIN SIMULATION
# ═══════════════════════════════════════════════════════════════════════════════

class PendulumPaintSimulation(BaseSimulation):
    """
    Main pendulum paint simulation.
    
    Combines physics, dripping, and rendering into a cohesive simulation.
    """
    
    def __init__(self, width=800, height=1000, image_path=None,
                 target_duration=30.0,
                 pendulum_length=300,
                 initial_angle_x=45.0,
                 initial_angle_y=30.0,
                 damping_x=0.02,
                 damping_y=0.02,
                 gravity=9.8,
                 drip_rate=0.15,
                 paint_thickness=8,
                 viscosity=0.7,
                 paint_color=(44, 24, 16),
                 show_pendulum=True,
                 show_trails=True,
                 auto_record=True):
        """
        Initialize pendulum paint simulation.
        
        Args:
            width: Canvas width
            height: Canvas height
            image_path: Path to target image
            target_duration: Animation duration in seconds
            pendulum_length: Length of pendulum arm
            initial_angle_x: Starting X angle (degrees)
            initial_angle_y: Starting Y angle (degrees)
            damping_x: X-axis damping coefficient
            damping_y: Y-axis damping coefficient
            gravity: Gravitational acceleration
            drip_rate: Base drip probability per frame
            paint_thickness: Base paint drop radius
            viscosity: Paint spread factor
            paint_color: RGB tuple for paint
            show_pendulum: Whether to render pendulum
            show_trails: Whether to render movement trails
            auto_record: Whether to auto-start recording
        """
        super().__init__(width, height, fps=60, title="Pendulum Paint Art")
        
        self.image_path = image_path
        self.target_duration = target_duration
        self.auto_record = auto_record
        
        # Initialize physics engine
        self.physics_engine = PendulumPhysicsEngine(
            canvas_width=width,
            canvas_height=height,
            length=pendulum_length,
            initial_angle_x=initial_angle_x,
            initial_angle_y=initial_angle_y,
            damping_x=damping_x,
            damping_y=damping_y,
            gravity=gravity
        )
        
        # Initialize drip engine
        self.drip_engine = DripEngine(
            canvas_width=width,
            canvas_height=height,
            base_drip_rate=drip_rate,
            paint_thickness=paint_thickness,
            viscosity=viscosity,
            paint_color=paint_color
        )
        
        # Initialize paint renderer
        self.paint_renderer = PaintRenderer(
            canvas_width=width,
            canvas_height=height,
            paint_color=paint_color,
            show_pendulum=show_pendulum,
            show_trails=show_trails
        )
        
        # Initialize frame animator
        self.frame_animator = FrameAnimator(
            width=width,
            height=height,
            fps=60,
            target_duration=target_duration
        )
        
        # Load target image if provided
        if image_path:
            self.drip_engine.load_target_image(image_path)
        
        # Animation state
        self.is_initialized = False
        self.completion_message_shown = False
        
        # Setup frames folder
        self.setup_frames_folder(SIMULATION_DIR / "frames")
        
        # Font for status display
        pygame.font.init()
        self.font = pygame.font.SysFont('Arial', 16)
    
    def initialize(self):
        """Initialize the simulation."""
        if self.is_initialized:
            return
        
        print("=" * 60)
        print("PENDULUM PAINT ART SIMULATION")
        print("=" * 60)
        print(f"Canvas: {self.width}x{self.height}")
        print(f"Duration: {self.target_duration}s")
        print(f"Image: {self.image_path}")
        print("-" * 60)
        
        # Start animation
        self.frame_animator.start()
        
        # Start recording if auto-record enabled
        if self.auto_record:
            self.start_recording()
            print("Recording started...")
        
        self.is_initialized = True
    
    def handle_events(self):
        """Handle pygame events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                
                elif event.key == pygame.K_SPACE:
                    self.paused = self.frame_animator.toggle_pause()
                    print("Paused" if self.paused else "Resumed")
                
                elif event.key == pygame.K_r:
                    self.reset()
                    print("Simulation reset")
                
                elif event.key == pygame.K_s:
                    # Take screenshot
                    screenshot_path = SIMULATION_DIR / "output" / f"screenshot_{self.frame_count:06d}.png"
                    screenshot_path.parent.mkdir(parents=True, exist_ok=True)
                    pygame.image.save(self.screen, str(screenshot_path))
                    print(f"Screenshot saved: {screenshot_path}")
    
    def update(self):
        """Update simulation state."""
        if not self.is_initialized:
            self.initialize()
        
        # Update animation frame
        if not self.frame_animator.update():
            # Animation complete
            if not self.completion_message_shown:
                self.on_complete()
                self.completion_message_shown = True
            return
        
        # Update physics
        bob_pos = self.physics_engine.update()
        velocity = self.physics_engine.get_velocity()
        speed = self.physics_engine.get_speed()
        
        # Normalize speed for drip calculation
        velocity_factor = min(5.0, speed / 50.0)
        
        # Check for drip
        if self.drip_engine.should_drip(bob_pos[0], bob_pos[1], velocity_factor):
            self.drip_engine.create_drip(bob_pos[0], bob_pos[1], velocity)
        
        # Update active drips
        self.drip_engine.update_drips()
        
        # Update trail
        self.paint_renderer.render_trail(self.physics_engine.get_position_history())
    
    def draw(self):
        """Draw the current frame."""
        # Render floor background
        self.paint_renderer.render_floor(self.screen)
        
        # Render trail
        if self.paint_renderer.show_trails:
            self.screen.blit(self.paint_renderer.get_trail_surface(), (0, 0))
        
        # Render drips to paint surface
        self.paint_renderer.render_all_drips(self.drip_engine.get_drips())
        
        # Blit paint surface
        self.screen.blit(self.paint_renderer.get_paint_surface(), (0, 0))
        
        # Render pendulum
        pivot_pos = self.physics_engine.get_pivot_position()
        bob_pos = self.physics_engine.get_position()
        self.paint_renderer.render_pendulum(self.screen, pivot_pos, bob_pos)
        
        # Render status
        self._render_status()
    
    def _render_status(self):
        """Render status text overlay."""
        status = self.frame_animator.get_status_text()
        coverage = self.drip_engine.get_coverage() * 100
        drips = self.drip_engine.total_drips
        
        lines = [
            status,
            f"Drips: {drips} | Coverage: {coverage:.1f}%",
            "Controls: SPACE=Pause, R=Reset, ESC=Exit"
        ]
        
        y = 10
        for line in lines:
            text_surface = self.font.render(line, True, (200, 200, 200))
            # Add shadow
            shadow_surface = self.font.render(line, True, (30, 30, 30))
            self.screen.blit(shadow_surface, (11, y + 1))
            self.screen.blit(text_surface, (10, y))
            y += 22
    
    def on_complete(self):
        """Called when animation completes."""
        print("=" * 60)
        print("ANIMATION COMPLETE")
        print("=" * 60)
        print(f"Total frames: {self.frame_animator.get_frame_count()}")
        print(f"Total drips: {self.drip_engine.total_drips}")
        print(f"Coverage: {self.drip_engine.get_coverage() * 100:.1f}%")
        
        if self.recording:
            self.stop_recording()
            print(f"Frames saved to: {self.frames_folder}")
    
    def reset(self):
        """Reset the simulation."""
        self.physics_engine.reset()
        self.drip_engine.reset()
        self.paint_renderer.reset()
        self.frame_animator.reset()
        self.is_initialized = False
        self.completion_message_shown = False
        self.frame_count = 0


def parse_color(color_str):
    """Parse color string (hex or RGB) to tuple."""
    if isinstance(color_str, tuple):
        return color_str
    
    if color_str.startswith('#'):
        # Hex color
        hex_color = color_str.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    # Try parsing as comma-separated RGB
    try:
        parts = color_str.split(',')
        return tuple(int(p.strip()) for p in parts)
    except:
        return (44, 24, 16)  # Default brown


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Pendulum Paint Art Simulation')
    parser.add_argument('--image', '-i', type=str, help='Path to target image')
    parser.add_argument('--width', '-W', type=int, default=800, help='Canvas width')
    parser.add_argument('--height', '-H', type=int, default=1000, help='Canvas height')
    parser.add_argument('--duration', '-d', type=float, default=30.0, help='Animation duration (seconds)')
    parser.add_argument('--length', '-l', type=int, default=300, help='Pendulum length')
    parser.add_argument('--angle-x', type=float, default=45.0, help='Initial X angle (degrees)')
    parser.add_argument('--angle-y', type=float, default=30.0, help='Initial Y angle (degrees)')
    parser.add_argument('--damping-x', type=float, default=0.02, help='X damping coefficient')
    parser.add_argument('--damping-y', type=float, default=0.02, help='Y damping coefficient')
    parser.add_argument('--gravity', '-g', type=float, default=9.8, help='Gravity multiplier')
    parser.add_argument('--drip-rate', type=float, default=0.15, help='Base drip rate')
    parser.add_argument('--thickness', '-t', type=int, default=8, help='Paint thickness')
    parser.add_argument('--viscosity', '-v', type=float, default=0.7, help='Paint viscosity')
    parser.add_argument('--color', '-c', type=str, default='#2c1810', help='Paint color (hex)')
    parser.add_argument('--no-pendulum', action='store_true', help='Hide pendulum')
    parser.add_argument('--no-trails', action='store_true', help='Hide trails')
    parser.add_argument('--no-record', action='store_true', help='Disable auto-recording')
    
    args = parser.parse_args()
    
    # Parse paint color
    paint_color = parse_color(args.color)
    
    # Create and run simulation
    sim = PendulumPaintSimulation(
        width=args.width,
        height=args.height,
        image_path=args.image,
        target_duration=args.duration,
        pendulum_length=args.length,
        initial_angle_x=args.angle_x,
        initial_angle_y=args.angle_y,
        damping_x=args.damping_x,
        damping_y=args.damping_y,
        gravity=args.gravity,
        drip_rate=args.drip_rate,
        paint_thickness=args.thickness,
        viscosity=args.viscosity,
        paint_color=paint_color,
        show_pendulum=not args.no_pendulum,
        show_trails=not args.no_trails,
        auto_record=not args.no_record
    )
    
    sim.run()


if __name__ == "__main__":
    main()
