#!/usr/bin/env python3
"""
Physics Engine - Pymunk-based physics simulation
=================================================
Handles all physics calculations for sand particles including:
- Particle creation and management
- Collision detection
- Gravity and forces
- Spatial optimization
"""

import pymunk
import pymunk.pygame_util
import random
import math
from typing import List, Tuple, Optional


class SandParticle:
    """Represents a single sand particle with physics properties."""
    
    def __init__(self, body: pymunk.Body, shape: pymunk.Circle, color: Tuple[int, int, int], target_pos: Optional[Tuple[int, int]] = None):
        self.body = body
        self.shape = shape
        self.color = color
        self.target_pos = target_pos  # Position in target image
        self.settled = False
        self.settle_timer = 0
        
    def check_settled(self):
        """Check if particle has settled (velocity near zero)."""
        velocity = self.body.velocity
        speed = math.sqrt(velocity.x ** 2 + velocity.y ** 2)
        
        if speed < 1.0:  # Velocity threshold
            self.settle_timer += 1
            if self.settle_timer > 30:  # Settled for 30 frames
                self.settled = True
        else:
            self.settle_timer = 0


class PhysicsEngine:
    """Physics simulation engine using Pymunk."""
    
    def __init__(self, width: int, height: int, gravity: float = 980.0):
        """
        Initialize physics engine.
        
        Args:
            width: Simulation width
            height: Simulation height
            gravity: Gravity strength (pixels/s^2)
        """
        self.width = width
        self.height = height
        self.gravity_strength = gravity
        
        # Create Pymunk space
        self.space = pymunk.Space()
        self.space.gravity = (0, gravity)
        
        # Collision optimization
        self.space.collision_slop = 0.5
        self.space.collision_bias = math.pow(1.0 - 0.1, 60.0)  # For 60 FPS
        
        # Particles list
        self.particles: List[SandParticle] = []
        
        # Setup boundaries
        self._setup_boundaries()
        
        # Performance tracking
        self.max_particles = 50000  # Safety limit
        
    def _setup_boundaries(self):
        """Create static boundary walls to contain the sand."""
        static_body = self.space.static_body
        
        # Wall thickness
        wall_thickness = 10
        
        # Bottom wall (ground) - across full width
        ground = pymunk.Segment(static_body, (0, self.height), (self.width, self.height), wall_thickness)
        ground.friction = 0.8
        ground.elasticity = 0.1
        
        # Left wall - full height
        left_wall = pymunk.Segment(static_body, (0, 0), (0, self.height), wall_thickness)
        left_wall.friction = 0.8
        left_wall.elasticity = 0.1
        
        # Right wall - full height
        right_wall = pymunk.Segment(static_body, (self.width, 0), (self.width, self.height), wall_thickness)
        right_wall.friction = 0.8
        right_wall.elasticity = 0.1
        
        # Add a container frame at the bottom to hold sand
        # Create a U-shaped container
        container_height = int(self.height * 0.8)  # Container takes bottom 80% of screen
        container_y = int(self.height * 0.2)  # Start at 20% from top
        
        # Bottom of container
        container_bottom = pymunk.Segment(
            static_body, 
            (wall_thickness, self.height - wall_thickness), 
            (self.width - wall_thickness, self.height - wall_thickness), 
            wall_thickness
        )
        container_bottom.friction = 0.9
        container_bottom.elasticity = 0.05
        
        # Left side of container
        container_left = pymunk.Segment(
            static_body,
            (wall_thickness, container_y),
            (wall_thickness, self.height - wall_thickness),
            wall_thickness
        )
        container_left.friction = 0.9
        container_left.elasticity = 0.05
        
        # Right side of container
        container_right = pymunk.Segment(
            static_body,
            (self.width - wall_thickness, container_y),
            (self.width - wall_thickness, self.height - wall_thickness),
            wall_thickness
        )
        container_right.friction = 0.9
        container_right.elasticity = 0.05
        
        self.space.add(ground, left_wall, right_wall, container_bottom, container_left, container_right)
        
        # Store container bounds for reference
        self.container_bounds = {
            'left': wall_thickness,
            'right': self.width - wall_thickness,
            'top': container_y,
            'bottom': self.height - wall_thickness
        }
    
    def create_sand_particle(self, x: float, y: float, radius: float, color: Tuple[int, int, int], 
                            target_pos: Optional[Tuple[int, int]] = None, 
                            mass: float = 1.0) -> Optional[SandParticle]:
        """
        Create a new sand particle.
        
        Args:
            x: X position
            y: Y position
            radius: Particle radius
            color: RGB color tuple
            target_pos: Target position in image (x, y)
            mass: Particle mass
            
        Returns:
            Created SandParticle or None if limit reached
        """
        if len(self.particles) >= self.max_particles:
            return None
        
        # Create physics body
        moment = pymunk.moment_for_circle(mass, 0, radius)
        body = pymunk.Body(mass, moment)
        body.position = (x, y)
        
        # Add slight random velocity for natural variation
        body.velocity = (random.uniform(-10, 10), random.uniform(0, 20))
        
        # Create shape
        shape = pymunk.Circle(body, radius)
        shape.friction = 0.7
        shape.elasticity = 0.1  # Low bounce
        
        # Add to space
        self.space.add(body, shape)
        
        # Create particle object
        particle = SandParticle(body, shape, color, target_pos)
        self.particles.append(particle)
        
        return particle
    
    def step(self, dt: float = 1/60.0):
        """
        Step the physics simulation.
        
        Args:
            dt: Time delta (default: 1/60 for 60 FPS)
        """
        # Update physics
        self.space.step(dt)
        
        # Check settled particles
        for particle in self.particles:
            if not particle.settled:
                particle.check_settled()
    
    def get_active_particles(self) -> List[SandParticle]:
        """Get all non-settled particles."""
        return [p for p in self.particles if not p.settled]
    
    def get_settled_particles(self) -> List[SandParticle]:
        """Get all settled particles."""
        return [p for p in self.particles if p.settled]
    
    def remove_particle(self, particle: SandParticle):
        """Remove a particle from simulation."""
        if particle in self.particles:
            self.space.remove(particle.body, particle.shape)
            self.particles.remove(particle)
    
    def clear_all_particles(self):
        """Remove all particles from simulation."""
        for particle in self.particles[:]:
            self.space.remove(particle.body, particle.shape)
        self.particles.clear()
    
    def set_gravity(self, gravity: float):
        """Update gravity strength."""
        self.gravity_strength = gravity
        self.space.gravity = (0, gravity)
    
    def get_particle_count(self) -> int:
        """Get total particle count."""
        return len(self.particles)
    
    def get_stats(self) -> dict:
        """Get physics statistics."""
        return {
            'total_particles': len(self.particles),
            'active_particles': len(self.get_active_particles()),
            'settled_particles': len(self.get_settled_particles()),
            'max_particles': self.max_particles,
            'gravity': self.gravity_strength
        }
