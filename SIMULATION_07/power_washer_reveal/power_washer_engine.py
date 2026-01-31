"""
Power Washer Reveal Engine
==========================
A high-fidelity power washer simulation that creates an "oddly satisfying" reveal effect.
Uses procedural mud/grime textures, realistic water physics, and gravity-based drip animations.
"""

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import cv2
from typing import Tuple, List, Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
import math
import random


class BrushType(Enum):
    """Types of power washer brush patterns."""
    CIRCULAR = "circular"
    FAN = "fan"
    TURBO = "turbo"
    PENCIL = "pencil"


class MudDensity(Enum):
    """Mud density presets."""
    LIGHT = 0.3
    MEDIUM = 0.6
    HEAVY = 0.85
    EXTREME = 1.0


@dataclass
class Drip:
    """Represents a water drip that flows down from cleaned areas."""
    x: float
    y: float
    velocity_y: float = 0.0
    velocity_x: float = 0.0
    width: float = 3.0
    strength: float = 1.0
    lifetime: float = 1.0
    trail: List[Tuple[float, float]] = field(default_factory=list)
    active: bool = True


@dataclass
class WashPath:
    """Pre-programmed cinematic wash path."""
    points: List[Tuple[float, float]]
    pressures: List[float]
    brush_types: List[BrushType]
    speeds: List[float]
    current_index: int = 0
    t: float = 0.0


class PerlinNoise:
    """Perlin noise generator for procedural textures."""
    
    def __init__(self, seed: int = None):
        if seed is not None:
            np.random.seed(seed)
        self.permutation = np.arange(256, dtype=np.int32)
        np.random.shuffle(self.permutation)
        self.permutation = np.tile(self.permutation, 2)
    
    def _fade(self, t: np.ndarray) -> np.ndarray:
        """Fade function for smooth interpolation."""
        return t * t * t * (t * (t * 6 - 15) + 10)
    
    def _lerp(self, a: np.ndarray, b: np.ndarray, t: np.ndarray) -> np.ndarray:
        """Linear interpolation."""
        return a + t * (b - a)
    
    def _gradient(self, h: np.ndarray, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        """Compute gradient dot product."""
        vectors = np.array([[1, 1], [-1, 1], [1, -1], [-1, -1],
                           [1, 0], [-1, 0], [0, 1], [0, -1]])
        g = vectors[h % 8]
        return g[..., 0] * x + g[..., 1] * y
    
    def noise2d(self, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        """Generate 2D Perlin noise."""
        xi = x.astype(np.int32) & 255
        yi = y.astype(np.int32) & 255
        xf = x - x.astype(np.int32)
        yf = y - y.astype(np.int32)
        
        u = self._fade(xf)
        v = self._fade(yf)
        
        aa = self.permutation[self.permutation[xi] + yi]
        ab = self.permutation[self.permutation[xi] + yi + 1]
        ba = self.permutation[self.permutation[xi + 1] + yi]
        bb = self.permutation[self.permutation[xi + 1] + yi + 1]
        
        x1 = self._lerp(self._gradient(aa, xf, yf),
                        self._gradient(ba, xf - 1, yf), u)
        x2 = self._lerp(self._gradient(ab, xf, yf - 1),
                        self._gradient(bb, xf - 1, yf - 1), u)
        
        return self._lerp(x1, x2, v)
    
    def octave_noise(self, x: np.ndarray, y: np.ndarray, 
                     octaves: int = 4, persistence: float = 0.5) -> np.ndarray:
        """Generate multi-octave Perlin noise (fractal Brownian motion)."""
        total = np.zeros_like(x, dtype=np.float64)
        frequency = 1.0
        amplitude = 1.0
        max_value = 0.0
        
        for _ in range(octaves):
            total += self.noise2d(x * frequency, y * frequency) * amplitude
            max_value += amplitude
            amplitude *= persistence
            frequency *= 2.0
        
        return total / max_value


class PowerWasherEngine:
    """
    High-fidelity power washer reveal simulation engine.
    
    Creates an "oddly satisfying" effect by simulating:
    - Multi-layer procedural mud/grime textures
    - Realistic high-pressure water stream physics
    - Gravity-based residual drip animations
    """
    
    def __init__(
        self,
        image_path: str,
        target_width: int = 1920,
        target_height: int = 1080,
        mud_density: MudDensity = MudDensity.HEAVY,
        mud_color_base: Tuple[int, int, int] = (89, 68, 48),
        mud_color_variation: float = 0.3,
        specular_intensity: float = 0.4,
        displacement_strength: float = 0.15,
        drip_enabled: bool = True,
        drip_probability: float = 0.3,
        seed: int = None
    ):
        """
        Initialize the power washer engine.
        
        Args:
            image_path: Path to the target image to reveal
            target_width: Output frame width
            target_height: Output frame height
            mud_density: Density of the mud layer
            mud_color_base: Base RGB color for mud
            mud_color_variation: Color variation amount (0-1)
            specular_intensity: Intensity of specular highlights (0-1)
            displacement_strength: Strength of displacement mapping (0-1)
            drip_enabled: Whether to enable drip physics
            drip_probability: Probability of spawning drips when washing
            seed: Random seed for reproducibility
        """
        self.target_width = target_width
        self.target_height = target_height
        self.mud_density = mud_density
        self.mud_color_base = mud_color_base
        self.mud_color_variation = mud_color_variation
        self.specular_intensity = specular_intensity
        self.displacement_strength = displacement_strength
        self.drip_enabled = drip_enabled
        self.drip_probability = drip_probability
        self.seed = seed if seed is not None else random.randint(0, 2**31)
        
        # Initialize random state
        np.random.seed(self.seed)
        random.seed(self.seed)
        
        # Load and prepare target image
        self._load_target_image(image_path)
        
        # Initialize noise generator
        self.perlin = PerlinNoise(seed=self.seed)
        
        # Generate mud layers
        self.generate_mud_layer()
        
        # Initialize reveal mask (0 = covered, 1 = revealed)
        self.reveal_mask = np.zeros((self.target_height, self.target_width), dtype=np.float32)
        
        # Drip system
        self.drips: List[Drip] = []
        self.drip_trail_map = np.zeros((self.target_height, self.target_width), dtype=np.float32)
        
        # Cinematic path
        self.wash_path: Optional[WashPath] = None
        self.path_active = False
        
        # Statistics
        self.total_revealed = 0.0
        self.wash_operations = 0
        
        # Pre-computed brush kernels
        self._precompute_brush_kernels()
    
    def _load_target_image(self, image_path: str) -> None:
        """Load and resize the target image."""
        img = Image.open(image_path).convert('RGBA')
        
        # Calculate aspect-preserving resize
        img_ratio = img.width / img.height
        target_ratio = self.target_width / self.target_height
        
        if img_ratio > target_ratio:
            new_width = self.target_width
            new_height = int(self.target_width / img_ratio)
        else:
            new_height = self.target_height
            new_width = int(self.target_height * img_ratio)
        
        img = img.resize((new_width, new_height), Image.LANCZOS)
        
        # Center on canvas
        self.target_image = np.zeros((self.target_height, self.target_width, 4), dtype=np.uint8)
        x_offset = (self.target_width - new_width) // 2
        y_offset = (self.target_height - new_height) // 2
        
        img_array = np.array(img)
        self.target_image[y_offset:y_offset + new_height, 
                          x_offset:x_offset + new_width] = img_array
        
        # Store bounds for optimization
        self.image_bounds = (x_offset, y_offset, x_offset + new_width, y_offset + new_height)
    
    def generate_mud_layer(self) -> None:
        """
        Generate multi-layer procedural mud/grime texture.
        
        Creates:
        - Base mud color layer with noise variation
        - Specular highlight layer
        - Displacement/height map for 3D effect
        - Detail texture layer
        """
        h, w = self.target_height, self.target_width
        
        # Create coordinate grids for noise
        x = np.linspace(0, 10, w)
        y = np.linspace(0, 10, h)
        xx, yy = np.meshgrid(x, y)
        
        # Layer 1: Base mud pattern (large scale)
        base_noise = self.perlin.octave_noise(xx, yy, octaves=4, persistence=0.5)
        base_noise = (base_noise + 1) / 2  # Normalize to 0-1
        
        # Layer 2: Detail texture (fine grain)
        detail_x = np.linspace(0, 50, w)
        detail_y = np.linspace(0, 50, h)
        detail_xx, detail_yy = np.meshgrid(detail_x, detail_y)
        detail_noise = self.perlin.octave_noise(detail_xx, detail_yy, octaves=6, persistence=0.6)
        detail_noise = (detail_noise + 1) / 2
        
        # Layer 3: Specular highlights
        spec_x = np.linspace(0, 8, w)
        spec_y = np.linspace(0, 8, h)
        spec_xx, spec_yy = np.meshgrid(spec_x, spec_y)
        specular_noise = self.perlin.octave_noise(spec_xx + 100, spec_yy + 100, octaves=3, persistence=0.4)
        specular_noise = np.clip((specular_noise + 0.5) * 2, 0, 1)
        
        # Layer 4: Displacement/height map
        disp_x = np.linspace(0, 15, w)
        disp_y = np.linspace(0, 15, h)
        disp_xx, disp_yy = np.meshgrid(disp_x, disp_y)
        self.displacement_map = self.perlin.octave_noise(disp_xx + 200, disp_yy + 200, octaves=5, persistence=0.55)
        self.displacement_map = (self.displacement_map + 1) / 2
        
        # Combine noise layers for mud thickness
        mud_thickness = (base_noise * 0.5 + detail_noise * 0.3 + self.displacement_map * 0.2)
        mud_thickness = mud_thickness ** 0.8  # Adjust contrast
        
        # Apply density setting
        density_value = self.mud_density.value if isinstance(self.mud_density, MudDensity) else self.mud_density
        self.mud_thickness = np.clip(mud_thickness * density_value + (1 - density_value) * 0.3, 0, 1)
        
        # Generate color variations
        color_noise = self.perlin.octave_noise(xx + 50, yy + 50, octaves=3, persistence=0.4)
        color_noise = (color_noise + 1) / 2
        
        # Create RGB mud texture
        self.mud_layer = np.zeros((h, w, 4), dtype=np.uint8)
        
        base_r, base_g, base_b = self.mud_color_base
        variation = self.mud_color_variation
        
        # Apply color with variation
        r_variation = (color_noise * 2 - 1) * variation * 50
        g_variation = (color_noise * 2 - 1) * variation * 40
        b_variation = (color_noise * 2 - 1) * variation * 30
        
        self.mud_layer[:, :, 0] = np.clip(base_r + r_variation + detail_noise * 20, 0, 255).astype(np.uint8)
        self.mud_layer[:, :, 1] = np.clip(base_g + g_variation + detail_noise * 15, 0, 255).astype(np.uint8)
        self.mud_layer[:, :, 2] = np.clip(base_b + b_variation + detail_noise * 10, 0, 255).astype(np.uint8)
        self.mud_layer[:, :, 3] = 255
        
        # Add specular highlights
        self.specular_layer = (specular_noise * self.specular_intensity * 255).astype(np.uint8)
        
        # Add darker crevices based on displacement
        crevice_darkness = (1 - self.displacement_map) * 0.3
        self.mud_layer[:, :, 0] = np.clip(self.mud_layer[:, :, 0].astype(np.float32) * (1 - crevice_darkness), 0, 255).astype(np.uint8)
        self.mud_layer[:, :, 1] = np.clip(self.mud_layer[:, :, 1].astype(np.float32) * (1 - crevice_darkness), 0, 255).astype(np.uint8)
        self.mud_layer[:, :, 2] = np.clip(self.mud_layer[:, :, 2].astype(np.float32) * (1 - crevice_darkness), 0, 255).astype(np.uint8)
        
        # Store original for wet effects
        self.mud_layer_original = self.mud_layer.copy()
    
    def _precompute_brush_kernels(self, max_radius: int = 100) -> None:
        """Pre-compute brush kernels for different sizes and types."""
        self.brush_kernels: Dict[Tuple[BrushType, int], np.ndarray] = {}
        
        for brush_type in BrushType:
            for radius in range(5, max_radius + 1, 5):
                kernel = self._create_brush_kernel(radius, brush_type)
                self.brush_kernels[(brush_type, radius)] = kernel
    
    def _create_brush_kernel(self, radius: int, brush_type: BrushType) -> np.ndarray:
        """Create a brush kernel with feathered edges."""
        size = radius * 2 + 1
        kernel = np.zeros((size, size), dtype=np.float32)
        center = radius
        
        y, x = np.ogrid[:size, :size]
        dist = np.sqrt((x - center) ** 2 + (y - center) ** 2)
        
        if brush_type == BrushType.CIRCULAR:
            # Circular brush with gaussian falloff
            kernel = np.exp(-((dist / radius) ** 2) * 3)
            kernel[dist > radius] = 0
            
        elif brush_type == BrushType.FAN:
            # Fan-shaped brush (wider spread)
            angle = np.arctan2(y - center, x - center)
            fan_width = np.pi / 3  # 60 degree spread
            angle_factor = np.cos(np.clip(angle / fan_width * np.pi / 2, -np.pi/2, np.pi/2))
            kernel = np.exp(-((dist / radius) ** 2) * 2) * angle_factor
            kernel[dist > radius] = 0
            kernel = np.maximum(kernel, 0)
            
        elif brush_type == BrushType.TURBO:
            # Turbo rotating nozzle - creates spiral pattern
            angle = np.arctan2(y - center, x - center)
            spiral = np.sin(angle * 6 + dist * 0.3) * 0.3 + 0.7
            kernel = np.exp(-((dist / radius) ** 2) * 4) * spiral
            kernel[dist > radius] = 0
            
        elif brush_type == BrushType.PENCIL:
            # Pencil jet - very focused stream
            kernel = np.exp(-((dist / (radius * 0.3)) ** 2) * 2)
            kernel[dist > radius * 0.5] *= np.exp(-((dist[dist > radius * 0.5] - radius * 0.5) / (radius * 0.5)) ** 2)
            kernel[dist > radius] = 0
        
        # Normalize
        if kernel.max() > 0:
            kernel = kernel / kernel.max()
        
        return kernel
    
    def _get_brush_kernel(self, radius: int, brush_type: BrushType) -> np.ndarray:
        """Get or create a brush kernel."""
        # Round to nearest precomputed size
        rounded_radius = max(5, min(100, (radius // 5) * 5))
        
        key = (brush_type, rounded_radius)
        if key in self.brush_kernels:
            kernel = self.brush_kernels[key]
            # Scale if needed
            if rounded_radius != radius:
                size = radius * 2 + 1
                kernel = cv2.resize(kernel, (size, size), interpolation=cv2.INTER_LINEAR)
            return kernel
        
        return self._create_brush_kernel(radius, brush_type)
    
    def process_wash(
        self,
        x: float,
        y: float,
        pressure: float = 1.0,
        brush_type: BrushType = BrushType.CIRCULAR,
        brush_radius: int = 30
    ) -> None:
        """
        Process power washing at the specified position.
        
        Args:
            x: X coordinate of wash center
            y: Y coordinate of wash center
            pressure: Wash pressure (0-1), affects erosion strength
            brush_type: Type of brush pattern
            brush_radius: Radius of the brush in pixels
        """
        x, y = int(x), int(y)
        
        # Bounds check
        if x < 0 or x >= self.target_width or y < 0 or y >= self.target_height:
            return
        
        # Get brush kernel
        kernel = self._get_brush_kernel(brush_radius, brush_type)
        kernel_size = kernel.shape[0]
        half_size = kernel_size // 2
        
        # Calculate affected region
        x1 = max(0, x - half_size)
        y1 = max(0, y - half_size)
        x2 = min(self.target_width, x + half_size + 1)
        y2 = min(self.target_height, y + half_size + 1)
        
        # Adjust kernel slice
        kx1 = half_size - (x - x1)
        ky1 = half_size - (y - y1)
        kx2 = kx1 + (x2 - x1)
        ky2 = ky1 + (y2 - y1)
        
        kernel_slice = kernel[ky1:ky2, kx1:kx2]
        
        # Apply pressure-based erosion
        # Pressure affects how much mud is removed per wash
        erosion_strength = pressure * 0.15
        
        # Factor in mud thickness (thicker mud requires more washing)
        thickness_factor = self.mud_thickness[y1:y2, x1:x2]
        resistance = 0.5 + thickness_factor * 0.5
        
        # Calculate erosion amount
        erosion = kernel_slice * erosion_strength / resistance
        
        # Update reveal mask
        current_mask = self.reveal_mask[y1:y2, x1:x2]
        new_mask = np.minimum(current_mask + erosion, 1.0)
        self.reveal_mask[y1:y2, x1:x2] = new_mask
        
        # Spawn drips based on washing
        if self.drip_enabled and random.random() < self.drip_probability * pressure:
            self._spawn_drip(x, y, pressure, brush_radius)
        
        self.wash_operations += 1
        self._update_revealed_percentage()
    
    def _spawn_drip(self, x: float, y: float, pressure: float, radius: int) -> None:
        """Spawn a water drip at the wash location."""
        # Random offset within brush area
        angle = random.random() * 2 * np.pi
        dist = random.random() * radius * 0.5
        
        drip_x = x + np.cos(angle) * dist
        drip_y = y + np.sin(angle) * dist
        
        # Drip properties based on pressure
        drip = Drip(
            x=drip_x,
            y=drip_y,
            velocity_y=random.uniform(1, 3) * pressure,
            velocity_x=random.uniform(-0.5, 0.5),
            width=random.uniform(2, 5) * pressure,
            strength=pressure * random.uniform(0.5, 1.0),
            lifetime=1.0,
            trail=[(drip_x, drip_y)]
        )
        
        self.drips.append(drip)
    
    def update_drips(self, dt: float = 1/60) -> None:
        """
        Update residual drip physics.
        
        Args:
            dt: Time delta in seconds
        """
        gravity = 200  # pixels per second squared
        drag = 0.98
        
        drips_to_remove = []
        
        for drip in self.drips:
            if not drip.active:
                drips_to_remove.append(drip)
                continue
            
            # Apply gravity
            drip.velocity_y += gravity * dt
            
            # Apply drag
            drip.velocity_x *= drag
            drip.velocity_y *= drag
            
            # Update position
            drip.x += drip.velocity_x * dt
            drip.y += drip.velocity_y * dt
            
            # Add to trail
            drip.trail.append((drip.x, drip.y))
            if len(drip.trail) > 50:
                drip.trail.pop(0)
            
            # Reveal along drip path
            self._apply_drip_reveal(drip)
            
            # Update lifetime
            drip.lifetime -= dt * 0.5
            drip.strength *= 0.995
            
            # Check bounds and lifetime
            if (drip.y >= self.target_height or drip.x < 0 or 
                drip.x >= self.target_width or drip.lifetime <= 0 or
                drip.strength < 0.01):
                drip.active = False
        
        # Remove inactive drips
        for drip in drips_to_remove:
            self.drips.remove(drip)
    
    def _apply_drip_reveal(self, drip: Drip) -> None:
        """Apply reveal effect along drip trail."""
        x, y = int(drip.x), int(drip.y)
        
        if x < 0 or x >= self.target_width or y < 0 or y >= self.target_height:
            return
        
        # Create small reveal area around drip
        radius = int(drip.width)
        y1 = max(0, y - radius)
        y2 = min(self.target_height, y + radius + 1)
        x1 = max(0, x - radius)
        x2 = min(self.target_width, x + radius + 1)
        
        # Create gaussian falloff
        yy, xx = np.ogrid[y1:y2, x1:x2]
        dist = np.sqrt((xx - x) ** 2 + (yy - y) ** 2)
        falloff = np.exp(-(dist / max(1, drip.width)) ** 2)
        
        # Apply reveal
        erosion = falloff * drip.strength * 0.02
        current_mask = self.reveal_mask[y1:y2, x1:x2]
        self.reveal_mask[y1:y2, x1:x2] = np.minimum(current_mask + erosion, 1.0)
        
        # Update drip trail map for visual effect
        self.drip_trail_map[y1:y2, x1:x2] = np.maximum(
            self.drip_trail_map[y1:y2, x1:x2],
            falloff * drip.strength * 0.5
        )
    
    def get_current_frame(self) -> np.ndarray:
        """
        Return the current composited frame.
        
        Returns:
            RGBA numpy array of the current frame
        """
        # Start with target image
        frame = self.target_image.copy().astype(np.float32)
        
        # Calculate mud opacity based on reveal mask
        mud_opacity = (1 - self.reveal_mask)[:, :, np.newaxis]
        
        # Create wet mud effect (darker where recently washed)
        wet_factor = self.drip_trail_map[:, :, np.newaxis] * 0.3
        wet_mud = self.mud_layer.astype(np.float32) * (1 - wet_factor)
        
        # Apply displacement effect for 3D appearance
        if self.displacement_strength > 0:
            # Simulate light direction for displacement
            light_dir = np.array([1, 1, 2])
            light_dir = light_dir / np.linalg.norm(light_dir)
            
            # Calculate normals from displacement map
            dy, dx = np.gradient(self.displacement_map)
            normals = np.stack([-dx * self.displacement_strength, 
                               -dy * self.displacement_strength,
                               np.ones_like(dx)], axis=-1)
            norm_len = np.linalg.norm(normals, axis=-1, keepdims=True)
            normals = normals / (norm_len + 1e-8)
            
            # Calculate lighting
            lighting = np.sum(normals * light_dir, axis=-1)
            lighting = np.clip(lighting, 0, 1)[:, :, np.newaxis]
            
            # Apply lighting to mud
            wet_mud[:, :, :3] = wet_mud[:, :, :3] * (0.7 + lighting * 0.3)
        
        # Add specular highlights
        specular = self.specular_layer[:, :, np.newaxis] * mud_opacity
        wet_mud[:, :, :3] = np.clip(wet_mud[:, :, :3] + specular, 0, 255)
        
        # Composite mud over target image
        alpha = mud_opacity
        frame[:, :, :3] = frame[:, :, :3] * (1 - alpha) + wet_mud[:, :, :3] * alpha
        frame[:, :, 3] = 255
        
        # Draw active drips
        for drip in self.drips:
            if drip.active and len(drip.trail) > 1:
                # Draw drip trail as water streak
                for i in range(1, len(drip.trail)):
                    x1, y1 = int(drip.trail[i-1][0]), int(drip.trail[i-1][1])
                    x2, y2 = int(drip.trail[i][0]), int(drip.trail[i][1])
                    
                    if (0 <= x1 < self.target_width and 0 <= y1 < self.target_height and
                        0 <= x2 < self.target_width and 0 <= y2 < self.target_height):
                        # Fade trail based on position
                        fade = i / len(drip.trail)
                        water_color = np.array([200, 220, 255, int(100 * fade * drip.strength)])
                        
                        # Simple line drawing
                        cv2.line(frame.astype(np.uint8), (x1, y1), (x2, y2), 
                                water_color.tolist(), int(drip.width * fade))
        
        # Decay drip trail map
        self.drip_trail_map *= 0.98
        
        return np.clip(frame, 0, 255).astype(np.uint8)
    
    def _update_revealed_percentage(self) -> None:
        """Update the total revealed percentage."""
        self.total_revealed = np.mean(self.reveal_mask)
    
    def is_complete(self, threshold: float = 0.95) -> bool:
        """
        Check if the reveal is complete.
        
        Args:
            threshold: Percentage threshold to consider complete (0-1)
            
        Returns:
            True if reveal percentage exceeds threshold
        """
        return self.total_revealed >= threshold
    
    def get_revealed_percentage(self) -> float:
        """Get the current revealed percentage."""
        return self.total_revealed * 100
    
    def set_wash_path(self, points: List[Tuple[float, float]], 
                      pressures: List[float] = None,
                      brush_types: List[BrushType] = None,
                      speeds: List[float] = None) -> None:
        """
        Set a pre-programmed cinematic wash path.
        
        Args:
            points: List of (x, y) coordinates for the path
            pressures: Pressure values at each point (default: all 1.0)
            brush_types: Brush type at each point (default: CIRCULAR)
            speeds: Speed values at each point (default: all 1.0)
        """
        n = len(points)
        
        self.wash_path = WashPath(
            points=points,
            pressures=pressures if pressures else [1.0] * n,
            brush_types=brush_types if brush_types else [BrushType.CIRCULAR] * n,
            speeds=speeds if speeds else [1.0] * n
        )
        self.path_active = True
    
    def generate_sweep_path(self, 
                           pattern: str = "horizontal",
                           num_passes: int = 5,
                           randomize: bool = True) -> None:
        """
        Generate a sweep path pattern.
        
        Args:
            pattern: "horizontal", "vertical", "spiral", "random"
            num_passes: Number of passes for sweep patterns
            randomize: Add randomization to path
        """
        points = []
        margin = 50
        
        if pattern == "horizontal":
            for i in range(num_passes):
                y = margin + (self.target_height - 2 * margin) * i / (num_passes - 1) if num_passes > 1 else self.target_height // 2
                
                if i % 2 == 0:
                    x_start, x_end = margin, self.target_width - margin
                else:
                    x_start, x_end = self.target_width - margin, margin
                
                steps = 50
                for j in range(steps):
                    t = j / (steps - 1)
                    x = x_start + (x_end - x_start) * t
                    offset_y = np.sin(t * np.pi * 4) * 10 if randomize else 0
                    points.append((x, y + offset_y))
        
        elif pattern == "vertical":
            for i in range(num_passes):
                x = margin + (self.target_width - 2 * margin) * i / (num_passes - 1) if num_passes > 1 else self.target_width // 2
                
                if i % 2 == 0:
                    y_start, y_end = margin, self.target_height - margin
                else:
                    y_start, y_end = self.target_height - margin, margin
                
                steps = 50
                for j in range(steps):
                    t = j / (steps - 1)
                    y = y_start + (y_end - y_start) * t
                    offset_x = np.sin(t * np.pi * 4) * 10 if randomize else 0
                    points.append((x + offset_x, y))
        
        elif pattern == "spiral":
            cx, cy = self.target_width // 2, self.target_height // 2
            max_radius = min(cx, cy) - margin
            revolutions = 5
            points_per_rev = 60
            
            for i in range(revolutions * points_per_rev):
                t = i / (revolutions * points_per_rev)
                angle = t * revolutions * 2 * np.pi
                radius = max_radius * (1 - t)
                
                x = cx + np.cos(angle) * radius
                y = cy + np.sin(angle) * radius
                points.append((x, y))
        
        elif pattern == "random":
            num_points = 200
            for _ in range(num_points):
                x = random.uniform(margin, self.target_width - margin)
                y = random.uniform(margin, self.target_height - margin)
                points.append((x, y))
        
        self.set_wash_path(points)
    
    def update_path(self, dt: float = 1/60) -> Optional[Tuple[float, float, float, BrushType]]:
        """
        Update the cinematic path and return current wash parameters.
        
        Args:
            dt: Time delta in seconds
            
        Returns:
            Tuple of (x, y, pressure, brush_type) or None if path complete
        """
        if not self.path_active or self.wash_path is None:
            return None
        
        path = self.wash_path
        n = len(path.points)
        
        if path.current_index >= n - 1:
            self.path_active = False
            return None
        
        # Interpolate between current and next point
        p1 = path.points[path.current_index]
        p2 = path.points[min(path.current_index + 1, n - 1)]
        
        t = path.t
        x = p1[0] + (p2[0] - p1[0]) * t
        y = p1[1] + (p2[1] - p1[1]) * t
        
        pressure = path.pressures[path.current_index]
        brush_type = path.brush_types[path.current_index]
        speed = path.speeds[path.current_index]
        
        # Update path progress
        path.t += dt * speed * 2
        if path.t >= 1.0:
            path.t = 0.0
            path.current_index += 1
        
        return (x, y, pressure, brush_type)
    
    def reset(self) -> None:
        """Reset the simulation to initial state."""
        self.reveal_mask = np.zeros((self.target_height, self.target_width), dtype=np.float32)
        self.drips = []
        self.drip_trail_map = np.zeros((self.target_height, self.target_width), dtype=np.float32)
        self.wash_path = None
        self.path_active = False
        self.total_revealed = 0.0
        self.wash_operations = 0
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get simulation statistics."""
        return {
            "revealed_percentage": self.total_revealed * 100,
            "wash_operations": self.wash_operations,
            "active_drips": len([d for d in self.drips if d.active]),
            "total_drips_spawned": len(self.drips),
            "is_complete": self.is_complete()
        }


def create_demo_path(width: int, height: int) -> List[Tuple[float, float]]:
    """Create a demo wash path for testing."""
    points = []
    cx, cy = width // 2, height // 2
    
    # Create a satisfying sweep pattern
    for t in np.linspace(0, 1, 300):
        x = 50 + (width - 100) * t
        y = cy + np.sin(t * np.pi * 6) * 100
        points.append((x, y))
    
    return points


if __name__ == "__main__":
    # Demo usage
    print("Power Washer Engine Demo")
    print("=" * 50)
    
    # Create a test image
    test_image = Image.new('RGBA', (800, 600), (100, 150, 200, 255))
    draw = ImageDraw.Draw(test_image)
    draw.rectangle([200, 150, 600, 450], fill=(255, 200, 100, 255))
    draw.ellipse([300, 200, 500, 400], fill=(200, 100, 150, 255))
    
    # Save test image
    test_path = "test_reveal_image.png"
    test_image.save(test_path)
    
    # Initialize engine
    engine = PowerWasherEngine(
        image_path=test_path,
        target_width=800,
        target_height=600,
        mud_density=MudDensity.HEAVY,
        drip_enabled=True
    )
    
    print(f"Engine initialized")
    print(f"Initial revealed: {engine.get_revealed_percentage():.2f}%")
    
    # Simulate some washing
    for i in range(100):
        x = 100 + i * 6
        y = 300 + np.sin(i * 0.2) * 50
        engine.process_wash(x, y, pressure=0.8, brush_type=BrushType.CIRCULAR, brush_radius=40)
        engine.update_drips(dt=1/60)
    
    print(f"After washing: {engine.get_revealed_percentage():.2f}%")
    print(f"Statistics: {engine.get_statistics()}")
    
    # Get frame
    frame = engine.get_current_frame()
    print(f"Frame shape: {frame.shape}")
    
    # Clean up
    import os
    os.remove(test_path)
    
    print("\nDemo complete!")
