#!/usr/bin/env python3
"""
Magnetic Field Physics Engine
==============================
Core physics simulation for magnetic iron filings with inverse-square law
attraction, particle inertia, friction, and dipole orientation.

Physics Model:
- Magnetic force: F = (k * strength) / r² where r is distance
- Particle velocity with inertia and friction damping
- Dipole orientation alignment along field lines
- Portrait attraction map for controlled particle placement
"""

import numpy as np
from pathlib import Path
import cv2
from PIL import Image

# GPU acceleration
HAS_GPU = False
GPU_INFO = "No GPU acceleration"

try:
    import cupy as cp
    from cupyx.scipy import ndimage as cp_ndimage
    
    try:
        device = cp.cuda.Device(0)
        cuda_version = cp.cuda.runtime.runtimeGetVersion()
        cuda_major = cuda_version // 1000
        cuda_minor = (cuda_version % 1000) // 10
        
        test_arr = cp.array([1, 2, 3])
        _ = cp.asnumpy(test_arr)
        
        HAS_GPU = True
        GPU_INFO = f"GPU: {device}, CUDA {cuda_major}.{cuda_minor}"
        print(f"[OK] GPU acceleration enabled: {GPU_INFO}")
    except Exception as e:
        print(f"CuPy available but GPU init failed: {e}")
        HAS_GPU = False
except ImportError:
    print("CuPy not installed. Using CPU for physics calculations.")


class Particle:
    """Single magnetic particle with physics properties."""
    
    __slots__ = ['x', 'y', 'vx', 'vy', 'angle', 'size', 'mass', 'attracted']
    
    def __init__(self, x, y, size=2.0, mass=1.0):
        self.x = x
        self.y = y
        self.vx = 0.0
        self.vy = 0.0
        self.angle = np.random.uniform(0, 2 * np.pi)  # Dipole orientation
        self.size = size
        self.mass = mass
        self.attracted = False  # Whether particle has reached attraction zone


class MagneticFieldEngine:
    """
    Core physics engine for magnetic iron filings simulation.
    
    Implements:
    - Inverse-square law magnetic attraction: F = k / r²
    - Particle inertia and velocity damping
    - Portrait-based attraction mapping
    - Field line alignment for realistic chain formation
    """
    
    def __init__(self, image_path, canvas_width, canvas_height, 
                 particle_count=10000, padding=30, use_gpu=True):
        """
        Initialize the magnetic field engine.
        
        Args:
            image_path: Path to portrait image (attraction map source)
            canvas_width: Width of simulation canvas
            canvas_height: Height of simulation canvas
            particle_count: Number of iron filings to simulate
            padding: Margin around the portrait
            use_gpu: Whether to use GPU acceleration
        """
        self.image_path = Path(image_path)
        self.canvas_width = canvas_width
        self.canvas_height = canvas_height
        self.particle_count = particle_count
        self.padding = padding
        self.use_gpu = use_gpu and HAS_GPU
        
        # Physics parameters
        self.magnetic_constant = 5000.0  # k in F = k/r²
        self.friction = 0.98  # Velocity damping per frame
        self.inertia = 0.95  # How much previous velocity is retained
        self.max_velocity = 15.0  # Velocity cap
        self.min_distance = 5.0  # Minimum distance to prevent singularities
        self.attraction_threshold = 0.3  # Attraction map threshold
        
        # Visual parameters
        self.particle_base_size = 2.0
        self.particle_size_variance = 0.5
        
        # State
        self.particles = []
        self.attraction_map = None  # Grayscale portrait for attraction
        self.field_lines = None  # Pre-computed field line directions
        self.original_image = None
        self.portrait_offset_x = 0
        self.portrait_offset_y = 0
        self.portrait_width = 0
        self.portrait_height = 0
        
        # Cursor/magnet position
        self.magnet_x = canvas_width // 2
        self.magnet_y = canvas_height // 2
        self.magnet_active = False
        self.magnet_strength = 1.0
        
        # Animation state
        self.simulation_complete = False
        self.particles_settled = 0
        
    def process_image(self):
        """Load and process the portrait image to create attraction map."""
        if not self.image_path.exists():
            raise FileNotFoundError(f"Image not found: {self.image_path}")
        
        # Load image
        img = Image.open(self.image_path)
        
        # Convert to grayscale
        if img.mode != 'L':
            img = img.convert('L')
        
        # Calculate sizing to fit canvas with padding
        available_width = self.canvas_width - (2 * self.padding)
        available_height = self.canvas_height - (2 * self.padding)
        
        # Scale to fit
        img_ratio = img.width / img.height
        canvas_ratio = available_width / available_height
        
        if img_ratio > canvas_ratio:
            # Width constrained
            new_width = available_width
            new_height = int(available_width / img_ratio)
        else:
            # Height constrained
            new_height = available_height
            new_width = int(available_height * img_ratio)
        
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Store dimensions and offset for centering
        self.portrait_width = new_width
        self.portrait_height = new_height
        self.portrait_offset_x = (self.canvas_width - new_width) // 2
        self.portrait_offset_y = (self.canvas_height - new_height) // 2
        
        # Convert to numpy array
        img_array = np.array(img, dtype=np.float32)
        
        # Invert: dark areas (portrait features) become high attraction
        # Normalize to 0-1 range
        self.attraction_map = 1.0 - (img_array / 255.0)
        
        # Apply Gaussian blur for smooth attraction gradients
        self.attraction_map = cv2.GaussianBlur(self.attraction_map, (15, 15), 0)
        
        # Store original for display
        self.original_image = np.array(Image.open(self.image_path).convert('RGB'))
        self.original_image = cv2.resize(self.original_image, (new_width, new_height))
        
        # Compute field lines (gradient of attraction map)
        self._compute_field_lines()
        
        # Initialize particles
        self._initialize_particles()
        
        print(f"Loaded portrait: {new_width}x{new_height}")
        print(f"Created attraction map with {self.particle_count} particles")
    
    def _compute_field_lines(self):
        """Compute field line directions from attraction map gradient."""
        # Compute gradients
        gy, gx = np.gradient(self.attraction_map)
        
        # Normalize to get direction vectors
        magnitude = np.sqrt(gx**2 + gy**2) + 1e-8
        self.field_dir_x = gx / magnitude
        self.field_dir_y = gy / magnitude
        
        # Field magnitude for particle alignment
        self.field_magnitude = magnitude
    
    def _initialize_particles(self):
        """Initialize particles randomly around the canvas edges."""
        self.particles = []
        
        for _ in range(self.particle_count):
            # Spawn particles at random positions (edges preferred initially)
            spawn_type = np.random.randint(4)
            
            if spawn_type == 0:  # Top edge
                x = np.random.uniform(0, self.canvas_width)
                y = np.random.uniform(-50, 0)
            elif spawn_type == 1:  # Bottom edge
                x = np.random.uniform(0, self.canvas_width)
                y = np.random.uniform(self.canvas_height, self.canvas_height + 50)
            elif spawn_type == 2:  # Left edge
                x = np.random.uniform(-50, 0)
                y = np.random.uniform(0, self.canvas_height)
            else:  # Right edge
                x = np.random.uniform(self.canvas_width, self.canvas_width + 50)
                y = np.random.uniform(0, self.canvas_height)
            
            # Varied particle sizes
            size = self.particle_base_size + np.random.uniform(
                -self.particle_size_variance, self.particle_size_variance
            )
            
            # Varied mass (affects inertia)
            mass = 0.8 + np.random.uniform(0, 0.4)
            
            particle = Particle(x, y, size, mass)
            
            # Initial random velocity toward center
            center_dir_x = (self.canvas_width / 2 - x)
            center_dir_y = (self.canvas_height / 2 - y)
            dist = np.sqrt(center_dir_x**2 + center_dir_y**2) + 1e-8
            
            particle.vx = (center_dir_x / dist) * np.random.uniform(1, 3)
            particle.vy = (center_dir_y / dist) * np.random.uniform(1, 3)
            
            self.particles.append(particle)
    
    def set_magnet_position(self, x, y, active=True):
        """Update the magnet/cursor position."""
        self.magnet_x = x
        self.magnet_y = y
        self.magnet_active = active
    
    def update(self):
        """
        Update all particle positions for one frame.
        Applies magnetic forces and attraction map influence.
        
        Returns:
            bool: True if simulation should continue, False if complete
        """
        if self.attraction_map is None:
            return True
        
        settled_count = 0
        
        for particle in self.particles:
            # Calculate force from attraction map
            fx, fy = self._calculate_attraction_force(particle)
            
            # Add cursor/magnet influence if active
            if self.magnet_active:
                mx, my = self._calculate_magnet_force(particle)
                fx += mx
                fy += my
            
            # Apply force (F = ma, a = F/m)
            ax = fx / particle.mass
            ay = fy / particle.mass
            
            # Update velocity with inertia
            particle.vx = particle.vx * self.inertia + ax
            particle.vy = particle.vy * self.inertia + ay
            
            # Apply friction
            particle.vx *= self.friction
            particle.vy *= self.friction
            
            # Clamp velocity
            speed = np.sqrt(particle.vx**2 + particle.vy**2)
            if speed > self.max_velocity:
                particle.vx = (particle.vx / speed) * self.max_velocity
                particle.vy = (particle.vy / speed) * self.max_velocity
            
            # Update position
            particle.x += particle.vx
            particle.y += particle.vy
            
            # Update dipole angle to align with field
            self._align_particle_angle(particle)
            
            # Check if particle is settled (low velocity in attraction zone)
            if speed < 0.5 and self._is_in_attraction_zone(particle):
                particle.attracted = True
                settled_count += 1
        
        self.particles_settled = settled_count
        
        # Simulation complete when most particles settled
        if settled_count >= self.particle_count * 0.95:
            self.simulation_complete = True
            return False
        
        return True
    
    def _calculate_attraction_force(self, particle):
        """
        Calculate force on particle from attraction map.
        
        Uses inverse-square law: F = k * attraction_strength / r²
        Direction is toward the nearest high-attraction point.
        """
        # Get particle position relative to portrait
        px = particle.x - self.portrait_offset_x
        py = particle.y - self.portrait_offset_y
        
        # Check if within attraction map bounds
        if (0 <= px < self.portrait_width and 0 <= py < self.portrait_height):
            # Sample attraction at particle position
            ix = int(px)
            iy = int(py)
            
            attraction = self.attraction_map[iy, ix]
            
            # Get field direction at this point
            dir_x = self.field_dir_x[iy, ix]
            dir_y = self.field_dir_y[iy, ix]
            
            # Force proportional to attraction strength
            force_magnitude = self.magnetic_constant * attraction * 0.01
            
            fx = dir_x * force_magnitude
            fy = dir_y * force_magnitude
            
            return fx, fy
        else:
            # Outside portrait - attract toward center
            dx = self.canvas_width / 2 - particle.x
            dy = self.canvas_height / 2 - particle.y
            dist = np.sqrt(dx**2 + dy**2) + self.min_distance
            
            # Gentle attraction to center
            force = 50.0 / (dist * 0.1)
            
            return (dx / dist) * force, (dy / dist) * force
    
    def _calculate_magnet_force(self, particle):
        """
        Calculate force from cursor-controlled magnet.
        
        Uses inverse-square law: F = (k * strength) / r²
        """
        dx = self.magnet_x - particle.x
        dy = self.magnet_y - particle.y
        
        dist_sq = dx**2 + dy**2
        dist = np.sqrt(dist_sq)
        
        # Prevent singularity
        if dist < self.min_distance:
            dist = self.min_distance
            dist_sq = dist * dist
        
        # Inverse-square law: F = k / r²
        force = (self.magnetic_constant * self.magnet_strength) / dist_sq
        
        # Clamp force
        force = min(force, 20.0)
        
        # Direction toward magnet
        fx = (dx / dist) * force
        fy = (dy / dist) * force
        
        return fx, fy
    
    def _align_particle_angle(self, particle):
        """Align particle dipole with local field direction."""
        # Get position relative to portrait
        px = particle.x - self.portrait_offset_x
        py = particle.y - self.portrait_offset_y
        
        if (0 <= px < self.portrait_width and 0 <= py < self.portrait_height):
            ix = int(px)
            iy = int(py)
            
            # Target angle from field direction
            target_angle = np.arctan2(
                self.field_dir_y[iy, ix],
                self.field_dir_x[iy, ix]
            )
            
            # Smoothly rotate toward target
            angle_diff = target_angle - particle.angle
            
            # Normalize angle difference
            while angle_diff > np.pi:
                angle_diff -= 2 * np.pi
            while angle_diff < -np.pi:
                angle_diff += 2 * np.pi
            
            particle.angle += angle_diff * 0.1
        else:
            # Outside portrait - align with velocity
            if abs(particle.vx) > 0.1 or abs(particle.vy) > 0.1:
                target_angle = np.arctan2(particle.vy, particle.vx)
                angle_diff = target_angle - particle.angle
                
                while angle_diff > np.pi:
                    angle_diff -= 2 * np.pi
                while angle_diff < -np.pi:
                    angle_diff += 2 * np.pi
                
                particle.angle += angle_diff * 0.05
    
    def _is_in_attraction_zone(self, particle):
        """Check if particle is within the high-attraction portrait area."""
        px = particle.x - self.portrait_offset_x
        py = particle.y - self.portrait_offset_y
        
        if (0 <= px < self.portrait_width and 0 <= py < self.portrait_height):
            ix = int(px)
            iy = int(py)
            return self.attraction_map[iy, ix] > self.attraction_threshold
        
        return False
    
    def get_particles_data(self):
        """
        Get all particle data for rendering.
        
        Returns:
            List of tuples: (x, y, angle, size, attracted)
        """
        return [
            (p.x, p.y, p.angle, p.size, p.attracted)
            for p in self.particles
        ]
    
    def get_progress(self):
        """Get simulation progress as percentage."""
        if self.particle_count == 0:
            return 100.0
        return (self.particles_settled / self.particle_count) * 100.0
    
    def get_attraction_map_preview(self):
        """Get the attraction map as a viewable image."""
        if self.attraction_map is None:
            return None
        
        # Convert to 8-bit grayscale
        preview = (self.attraction_map * 255).astype(np.uint8)
        return preview
    
    def get_field_visualization(self):
        """
        Generate field line visualization for cinematic mode.
        
        Returns:
            numpy array: RGB image with field lines visualized
        """
        if self.attraction_map is None:
            return None
        
        h, w = self.attraction_map.shape
        vis = np.zeros((h, w, 3), dtype=np.uint8)
        
        # Draw streamlines
        step = 15
        for y in range(0, h, step):
            for x in range(0, w, step):
                # Get field direction
                dx = self.field_dir_x[y, x] * 10
                dy = self.field_dir_y[y, x] * 10
                
                # Draw line segment
                x2 = int(x + dx)
                y2 = int(y + dy)
                
                if 0 <= x2 < w and 0 <= y2 < h:
                    # Color based on field strength
                    strength = int(self.field_magnitude[y, x] * 255)
                    color = (strength, strength // 2, strength // 3)
                    cv2.line(vis, (x, y), (x2, y2), color, 1)
        
        return vis
