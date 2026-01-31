#!/usr/bin/env python3
"""
Pendulum Physics Engine
========================
Dual-axis spherical pendulum simulation with air resistance and gravitational damping.
Implements decaying harmonic oscillation with elliptical orbital paths.

Physics Model:
- Spherical pendulum with two angular degrees of freedom (θx, θy)
- Damping coefficients for air resistance
- Gravitational restoring force
- Elliptical Lissajous-like trajectories
"""

import numpy as np
import math


class PendulumPhysicsEngine:
    """
    Dual-axis spherical pendulum physics simulation.
    
    The pendulum swings in 3D space but we project its tip position onto
    a 2D canvas for the paint dripping simulation.
    """
    
    def __init__(self, canvas_width, canvas_height, 
                 length=300, 
                 initial_angle_x=45.0, 
                 initial_angle_y=30.0,
                 damping_x=0.02, 
                 damping_y=0.02, 
                 gravity=9.8,
                 pivot_height_ratio=0.1):
        """
        Initialize pendulum physics engine.
        
        Args:
            canvas_width: Width of the canvas in pixels
            canvas_height: Height of the canvas in pixels
            length: Pendulum arm length in pixels
            initial_angle_x: Initial angle in X direction (degrees)
            initial_angle_y: Initial angle in Y direction (degrees)
            damping_x: Damping coefficient for X oscillation (0.0-1.0)
            damping_y: Damping coefficient for Y oscillation (0.0-1.0)
            gravity: Gravitational acceleration multiplier
            pivot_height_ratio: Where pivot is located (0=top, 1=bottom)
        """
        self.canvas_width = canvas_width
        self.canvas_height = canvas_height
        self.length = length
        self.damping_x = damping_x
        self.damping_y = damping_y
        self.gravity = gravity
        
        # Pivot point (center top of canvas)
        self.pivot_x = canvas_width / 2
        self.pivot_y = canvas_height * pivot_height_ratio
        
        # Convert initial angles to radians
        self.theta_x = math.radians(initial_angle_x)
        self.theta_y = math.radians(initial_angle_y)
        
        # Angular velocities
        self.omega_x = 0.0
        self.omega_y = 0.0
        
        # Natural frequency based on pendulum length and gravity
        # ω = √(g/L)
        self.natural_freq = math.sqrt(self.gravity / (self.length / 100.0))
        
        # Time tracking
        self.time = 0.0
        self.dt = 1.0 / 60.0  # Time step (assuming 60 FPS)
        
        # Position history for trail rendering
        self.position_history = []
        self.max_history = 500
        
        # Current bob position (calculated)
        self.bob_x = 0
        self.bob_y = 0
        self._update_bob_position()
    
    def _update_bob_position(self):
        """Calculate bob position from current angles."""
        # Project spherical coordinates to 2D canvas
        # x = L * sin(θx) * cos(θy)
        # y = L * (1 - cos(θx) * cos(θy))  (inverted, y increases downward)
        
        self.bob_x = self.pivot_x + self.length * math.sin(self.theta_x)
        self.bob_y = self.pivot_y + self.length * (1 - math.cos(self.theta_x) * math.cos(self.theta_y)) / 2
        
        # Add elliptical motion component for more interesting patterns
        self.bob_x += self.length * 0.3 * math.sin(self.theta_y)
        self.bob_y += self.length * 0.2 * (1 - math.cos(self.theta_y))
        
        # Clamp to canvas bounds with padding
        padding = 50
        self.bob_x = max(padding, min(self.canvas_width - padding, self.bob_x))
        self.bob_y = max(padding, min(self.canvas_height - padding, self.bob_y))
    
    def update(self, dt=None):
        """
        Update pendulum state using physics simulation.
        
        Uses the equation of motion for a damped harmonic oscillator:
        θ'' + 2ζω₀θ' + ω₀²θ = 0
        
        where ζ is the damping ratio and ω₀ is the natural frequency.
        
        Args:
            dt: Time step (uses default if None)
            
        Returns:
            tuple: (bob_x, bob_y) current bob position
        """
        if dt is None:
            dt = self.dt
        
        self.time += dt
        
        # Angular acceleration from gravitational restoring force
        # α = -ω₀² * sin(θ) ≈ -ω₀² * θ for small angles
        # Using sin(θ) for large angle accuracy
        
        alpha_x = -self.natural_freq**2 * math.sin(self.theta_x)
        alpha_y = -self.natural_freq**2 * math.sin(self.theta_y)
        
        # Add damping (air resistance)
        # F_damping = -c * v, where c is damping coefficient
        alpha_x -= self.damping_x * self.omega_x * self.natural_freq
        alpha_y -= self.damping_y * self.omega_y * self.natural_freq
        
        # Update angular velocities (Euler integration)
        self.omega_x += alpha_x * dt
        self.omega_y += alpha_y * dt
        
        # Update angles
        self.theta_x += self.omega_x * dt
        self.theta_y += self.omega_y * dt
        
        # Update bob position
        self._update_bob_position()
        
        # Store in history
        self.position_history.append((self.bob_x, self.bob_y, self.time))
        if len(self.position_history) > self.max_history:
            self.position_history.pop(0)
        
        return (self.bob_x, self.bob_y)
    
    def get_position(self):
        """Get current bob position."""
        return (self.bob_x, self.bob_y)
    
    def get_velocity(self):
        """Get current bob velocity in canvas coordinates."""
        # Approximate velocity from angular velocities
        vx = self.length * self.omega_x * math.cos(self.theta_x)
        vy = self.length * self.omega_y * math.sin(self.theta_y)
        return (vx, vy)
    
    def get_speed(self):
        """Get current bob speed magnitude."""
        vx, vy = self.get_velocity()
        return math.sqrt(vx**2 + vy**2)
    
    def get_kinetic_energy(self):
        """Get normalized kinetic energy (0.0-1.0)."""
        speed = self.get_speed()
        max_speed = self.length * self.natural_freq  # Approximate max
        return min(1.0, speed / max_speed)
    
    def get_pivot_position(self):
        """Get pivot point position."""
        return (self.pivot_x, self.pivot_y)
    
    def get_position_history(self):
        """Get position history for trail rendering."""
        return self.position_history
    
    def get_angle_amplitude(self):
        """Get current amplitude of oscillation (normalized 0-1)."""
        amp_x = abs(self.theta_x) / math.pi
        amp_y = abs(self.theta_y) / math.pi
        return max(amp_x, amp_y)
    
    def is_nearly_stopped(self, threshold=0.001):
        """Check if pendulum has nearly stopped."""
        energy = self.get_kinetic_energy()
        amplitude = self.get_angle_amplitude()
        return energy < threshold and amplitude < threshold
    
    def reset(self, initial_angle_x=None, initial_angle_y=None):
        """Reset pendulum to initial state."""
        if initial_angle_x is not None:
            self.theta_x = math.radians(initial_angle_x)
        if initial_angle_y is not None:
            self.theta_y = math.radians(initial_angle_y)
        
        self.omega_x = 0.0
        self.omega_y = 0.0
        self.time = 0.0
        self.position_history.clear()
        self._update_bob_position()
    
    def set_parameters(self, length=None, damping_x=None, damping_y=None, gravity=None):
        """Update physics parameters."""
        if length is not None:
            self.length = length
        if damping_x is not None:
            self.damping_x = damping_x
        if damping_y is not None:
            self.damping_y = damping_y
        if gravity is not None:
            self.gravity = gravity
            self.natural_freq = math.sqrt(self.gravity / (self.length / 100.0))
        
        self._update_bob_position()
