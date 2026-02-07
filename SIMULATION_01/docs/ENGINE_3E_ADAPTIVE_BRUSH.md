# Adaptive Brush Simulation Engine (Engine 3E)

## Executive Summary

This document proposes an **Adaptive Brush Simulation Engine** that focuses on hyper-realistic brush behavior simulation. Instead of just revealing pixels, this engine simulates actual pencil physics: graphite deposit, paper texture interaction, pressure dynamics, and stroke overlapping.

**Core Idea**: Simulate the physical properties of pencil drawing for maximum realism.

---

## Problem Analysis

### What Makes Pencil Drawings Look Natural?

Real pencil strokes have:
- **Pressure variation**: Darker at center, lighter at edges
- **Paper texture**: Grain shows through in lighter areas
- **Graphite buildup**: Multiple passes create darker values
- **Stroke edges**: Soft falloff, not hard cutoffs
- **Stroke variation**: Natural hand tremor, not perfect lines

Current engines apply uniform reveal without simulating these physical properties.

---

## Solution Architecture

### Core Philosophy: Physics-Based Simulation

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        INPUT IMAGE                                       │
│              (High-contrast pencil artwork)                              │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    STAGE 1: STROKE PATH EXTRACTION                       │
├─────────────────────────────────────────────────────────────────────────┤
│  • Extract skeleton paths (contours, shading regions)                   │
│  • Estimate stroke width and pressure from intensity                    │
│  • Group paths by intended visual effect                                │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    STAGE 2: BRUSH PHYSICS SIMULATION                     │
├─────────────────────────────────────────────────────────────────────────┤
│  • Simulate pencil tip shape (round, chisel, flat)                      │
│  • Calculate graphite deposit based on pressure                         │
│  • Apply paper texture interaction                                      │
│  • Handle stroke overlap accumulation                                   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    STAGE 3: DYNAMIC PRESSURE CONTROL                     │
├─────────────────────────────────────────────────────────────────────────┤
│  • Analyze target intensity per stroke segment                          │
│  • Vary pressure along stroke length                                    │
│  • Apply natural "attack-sustain-release" envelope                      │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    STAGE 4: STROKE-BY-STROKE RENDERING                   │
├─────────────────────────────────────────────────────────────────────────┤
│  • Render each stroke with full brush simulation                        │
│  • Accumulate graphite on virtual canvas                                │
│  • Apply paper texture masking                                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        FINAL OUTPUT                                      │
│     Physically-simulated natural pencil drawing animation                │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Technical Components

### 1. Pencil Tip Simulation

```python
import numpy as np
from dataclasses import dataclass
from enum import Enum

class TipShape(Enum):
    ROUND = "round"      # Standard sharpened pencil
    CHISEL = "chisel"    # Worn, flat tip
    BLUNT = "blunt"      # Very worn, soft marks

@dataclass
class PencilTip:
    """
    Simulates the physical properties of a pencil tip.
    """
    shape: TipShape
    hardness: float      # 0=soft (6B), 1=hard (4H)
    sharpness: float     # 0=dull, 1=sharp
    graphite_load: float # Current graphite on tip
    
    def get_deposit_pattern(self, pressure: float, angle: float):
        """
        Calculate the graphite deposit pattern for given pressure.
        
        Returns: 2D array representing deposit intensity (kernel)
        """
        base_size = int(5 + (1 - self.sharpness) * 10)
        kernel = np.zeros((base_size * 2, base_size * 2))
        
        if self.shape == TipShape.ROUND:
            # Circular deposit, darker at center
            for y in range(kernel.shape[0]):
                for x in range(kernel.shape[1]):
                    dist = np.sqrt((x - base_size)**2 + (y - base_size)**2)
                    if dist < base_size:
                        # Gaussian falloff from center
                        kernel[y, x] = np.exp(-(dist/base_size)**2 * 2)
        
        elif self.shape == TipShape.CHISEL:
            # Elongated deposit based on angle
            cos_a, sin_a = np.cos(angle), np.sin(angle)
            for y in range(kernel.shape[0]):
                for x in range(kernel.shape[1]):
                    dx, dy = x - base_size, y - base_size
                    # Rotate coordinates
                    rx = dx * cos_a + dy * sin_a
                    ry = -dx * sin_a + dy * cos_a
                    # Elliptical falloff
                    dist = np.sqrt((rx * 0.3)**2 + ry**2)
                    if dist < base_size:
                        kernel[y, x] = np.exp(-(dist/base_size)**2 * 2)
        
        # Scale by pressure and graphite
        kernel *= pressure * self.graphite_load
        
        return kernel
```

### 2. Paper Texture System

```python
class PaperTexture:
    """
    Simulates paper surface texture that affects graphite adhesion.
    """
    
    def __init__(self, texture_type='cold_press', resolution=(1024, 1024)):
        self.texture_type = texture_type
        self.resolution = resolution
        self.texture_map = self._generate_texture()
        
    def _generate_texture(self):
        """
        Generate procedural paper texture.
        """
        h, w = self.resolution
        
        if self.texture_type == 'smooth':
            # Minimal texture variation
            texture = np.ones((h, w)) * 0.95
            noise = np.random.normal(0, 0.02, (h, w))
            texture += noise
            
        elif self.texture_type == 'cold_press':
            # Medium texture with grain
            texture = np.ones((h, w)) * 0.8
            # Multi-scale noise for realistic grain
            for scale in [4, 8, 16, 32]:
                noise = np.random.normal(0, 0.1/scale, (h//scale, w//scale))
                noise = cv2.resize(noise, (w, h))
                texture += noise
                
        elif self.texture_type == 'rough':
            # Heavy texture, lots of grain
            texture = np.ones((h, w)) * 0.6
            for scale in [2, 4, 8, 16]:
                noise = np.random.normal(0, 0.15/scale, (h//scale, w//scale))
                noise = cv2.resize(noise, (w, h))
                texture += noise
        
        return np.clip(texture, 0, 1)
    
    def apply_to_deposit(self, deposit, position):
        """
        Modify graphite deposit based on paper texture at position.
        """
        y, x = position
        h, w = deposit.shape
        
        # Get texture region
        texture_region = self.texture_map[y:y+h, x:x+w]
        
        # Graphite adheres more to raised areas
        modified = deposit * texture_region
        
        return modified
```

### 3. Pressure Dynamics

```python
class PressureDynamicsController:
    """
    Simulates natural pressure variation along strokes.
    """
    
    def __init__(self):
        # Attack-sustain-release envelope
        self.attack_time = 0.1    # 10% of stroke to reach full pressure
        self.release_time = 0.15  # 15% of stroke to release
        
    def calculate_pressure_envelope(self, stroke_length: int, 
                                     target_intensity: float):
        """
        Generate pressure values along a stroke.
        
        Returns: Array of pressure values [0-1] for each point
        """
        pressures = np.zeros(stroke_length)
        
        attack_points = int(stroke_length * self.attack_time)
        release_points = int(stroke_length * self.release_time)
        sustain_points = stroke_length - attack_points - release_points
        
        # Attack: ramp up
        pressures[:attack_points] = np.linspace(0.2, target_intensity, attack_points)
        
        # Sustain: maintain with slight variation
        sustain_noise = np.random.normal(0, 0.05, sustain_points)
        pressures[attack_points:attack_points+sustain_points] = target_intensity + sustain_noise
        
        # Release: ramp down
        pressures[-release_points:] = np.linspace(target_intensity, 0.1, release_points)
        
        # Add natural hand tremor
        tremor = np.sin(np.linspace(0, 20*np.pi, stroke_length)) * 0.03
        pressures += tremor
        
        return np.clip(pressures, 0, 1)
    
    def apply_velocity_pressure(self, velocities, base_pressures):
        """
        Modify pressure based on stroke velocity.
        Faster strokes = lighter marks (less time for graphite deposit)
        """
        velocity_factor = 1.0 / (1.0 + velocities * 0.5)
        return base_pressures * velocity_factor
```

### 4. Graphite Accumulation System

```python
class GraphiteAccumulator:
    """
    Manages cumulative graphite deposit on the virtual canvas.
    Multiple strokes in same area get progressively darker.
    """
    
    def __init__(self, canvas_size):
        self.canvas = np.zeros(canvas_size, dtype=np.float32)
        self.max_density = 1.0  # Maximum darkness
        self.saturation_curve = 0.7  # How quickly it saturates
        
    def deposit_stroke(self, stroke_path, pencil_tip, paper, base_pressure):
        """
        Deposit graphite along a stroke path.
        """
        for i, point in enumerate(stroke_path):
            # Get deposit pattern for this point
            pressure = base_pressure[i]
            angle = self._estimate_angle(stroke_path, i)
            deposit = pencil_tip.get_deposit_pattern(pressure, angle)
            
            # Apply paper texture
            deposit = paper.apply_to_deposit(deposit, point)
            
            # Accumulate with saturation curve
            self._accumulate(point, deposit)
    
    def _accumulate(self, position, deposit):
        """
        Add deposit to canvas with diminishing returns.
        Simulates graphite saturation.
        """
        y, x = position
        h, w = deposit.shape
        
        # Get current canvas region
        region = self.canvas[y:y+h, x:x+w]
        
        # Diminishing returns as area gets darker
        remaining_capacity = self.max_density - region
        effective_deposit = deposit * remaining_capacity * self.saturation_curve
        
        # Add to canvas
        self.canvas[y:y+h, x:x+w] = np.clip(region + effective_deposit, 0, self.max_density)
    
    def get_current_image(self):
        """
        Convert graphite density to visible image.
        """
        # Invert (graphite is dark on white paper)
        image = 255 * (1 - self.canvas)
        return image.astype(np.uint8)
```

---

## Brush Presets

| Preset | Tip Shape | Hardness | Sharpness | Best For |
|--------|-----------|----------|-----------|----------|
| **Fine Line** | Round | 0.7 (2H) | 0.9 | Contours, details |
| **Soft Shade** | Blunt | 0.3 (4B) | 0.3 | Smooth gradients |
| **Hatching** | Chisel | 0.5 (HB) | 0.6 | Texture, hatching |
| **Deep Shadow** | Round | 0.2 (6B) | 0.5 | Dark shadows |
| **Sketch** | Blunt | 0.4 (2B) | 0.4 | Quick sketches |

---

## Modular File Structure

```
SIMULATION_01/
├── coloring_book_drawer/
│   ├── engines/
│   │   └── adaptive_brush/                # Engine 3E: Adaptive Brush
│   │       ├── __init__.py                # Exports AdaptiveBrushEngine
│   │       ├── engine.py                  # Main engine class
│   │       ├── config.py                  # Configuration
│   │       │
│   │       ├── physics/                   # Physical simulation
│   │       │   ├── __init__.py
│   │       │   ├── pencil_tip.py          # Tip shape simulation
│   │       │   ├── paper_texture.py       # Paper surface
│   │       │   ├── graphite_deposit.py    # Deposit calculation
│   │       │   └── accumulator.py         # Cumulative rendering
│   │       │
│   │       ├── dynamics/                  # Stroke dynamics
│   │       │   ├── __init__.py
│   │       │   ├── pressure_controller.py # Pressure envelope
│   │       │   ├── velocity_model.py      # Speed effects
│   │       │   └── tremor_noise.py        # Natural hand tremor
│   │       │
│   │       ├── brush_presets/             # Pre-configured brushes
│   │       │   ├── __init__.py
│   │       │   ├── presets.py             # Preset definitions
│   │       │   └── custom_loader.py       # User-defined brushes
│   │       │
│   │       └── rendering/                 # Output rendering
│   │           ├── __init__.py
│   │           ├── canvas.py              # Virtual canvas
│   │           └── frame_export.py        # Frame generation
│   │
│   ├── main.py
│   └── control_panel_main.py
│
├── docs/
│   └── ENGINE_3E_ADAPTIVE_BRUSH.md        # This document
│
└── requirements.txt
```

### Dependencies

```
# requirements.txt additions
scipy>=1.10.0          # Signal processing
noise>=1.2.2           # Perlin noise for textures (optional)
```

---

## Advantages & Disadvantages

### Advantages

| Advantage | Description |
|-----------|-------------|
| **Hyper-Realistic** | Closest to actual pencil behavior |
| **Customizable** | Full control over brush physics |
| **Authentic Look** | Paper texture, pressure variation |
| **Artistic Control** | Multiple brush presets |

### Disadvantages

| Disadvantage | Description |
|--------------|-------------|
| **Compute Heavy** | Per-pixel simulation is slow |
| **Complex Tuning** | Many parameters to configure |
| **Memory Usage** | Accumulation buffer overhead |
| **Not Always Necessary** | Over-engineering for simple art |

---

## Performance Optimization

| Technique | Speedup | Trade-off |
|-----------|---------|-----------|
| Kernel caching | 2-3x | Memory usage |
| Batch stroke rendering | 3-5x | Slightly less accurate |
| GPU deposit accumulation | 10-20x | Requires CUDA |
| Lower resolution simulation | 2-4x | Reduced fine details |

---

## Comparison with Other Engines

| Aspect | Engine 3A (Gradient) | Engine 3E (Brush) |
|--------|---------------------|------------------|
| **Rendering** | Mask-based reveal | Physical simulation |
| **Realism** | Good | Excellent |
| **Performance** | Fast | Slow |
| **Complexity** | Medium | High |
| **Customization** | Medium | Very High |

---

## Conclusion

The Adaptive Brush Simulation Engine provides the most physically accurate pencil simulation by modeling tip shape, paper texture, pressure dynamics, and graphite accumulation. While computationally intensive, it produces the most authentic-looking results.

**Best suited for**: High-quality renders where realism is paramount.

**Fallback to**: Engine 3A for faster processing with acceptable quality.
