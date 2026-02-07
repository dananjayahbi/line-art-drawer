# Pencil Shading Engine Documentation

## Overview

The **Pencil Shading Engine** is an advanced rendering system for the Coloring Book Drawer that handles complex pencil artwork with textures, shadows, and gradients. Unlike the original `PixelRevealEngine` which works best for simple line drawings, this engine creates natural-looking pencil drawing animations for shaded artwork.

## Problem Statement

The original system had issues with complex artwork:
- ✅ **Simple line art**: Worked perfectly - draws lines smoothly
- ❌ **Complex shaded artwork**: Created unnatural "bubble" artifacts when revealing shaded regions

This happened because the original engine treated all pixels equally, revealing them in circular masks along skeleton paths - great for lines, terrible for gradients and textures.

## Solution Architecture

### Multi-Layer Decomposition

The Pencil Shading Engine decomposes images into distinct layers, each with its own drawing strategy:

```
┌─────────────────────────────────────────────────────────────┐
│                    INPUT IMAGE                               │
│         (Pencil drawing with shading/textures)              │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   LAYER DECOMPOSITION                        │
├─────────────────────────────────────────────────────────────┤
│  1. Edge Layer     → Strong lines/contours (Canny detection)│
│  2. Shade Layer    → Gradual tones/textures (intensity map) │
│  3. Intensity Map  → Darkness levels for each pixel         │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  DRAWING PHASES                              │
├─────────────────────────────────────────────────────────────┤
│  Phase 1: OUTLINE           - Draw main edges/contours      │
│  Phase 2: HATCHING          - First layer of shading        │
│  Phase 3: CROSS_HATCHING    - Darker areas (45° offset)     │
│  Phase 4: DETAIL_SHADING    - Very dark regions             │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   FINAL OUTPUT                               │
│            Natural pencil-drawn animation                    │
└─────────────────────────────────────────────────────────────┘
```

### Drawing Phases

#### Phase 1: Outline
- **Purpose**: Draw the main edges and contours of the artwork
- **Method**: Skeleton-based path tracing (same as original engine)
- **Speed**: Slow and deliberate for precision

#### Phase 2: Hatching
- **Purpose**: Add first layer of shading
- **Method**: Parallel strokes at configurable angle (default 45°)
- **Speed**: Faster than outlines

#### Phase 3: Cross-Hatching
- **Purpose**: Build up darker areas with perpendicular strokes
- **Method**: Strokes at opposite angle (-45° by default)
- **Trigger**: Only areas with intensity > 0.35
- **Speed**: Fast

#### Phase 4: Detail Shading
- **Purpose**: Final pass for very dark regions
- **Method**: Additional hatching at 22.5° offset
- **Trigger**: Only areas with intensity > 0.6
- **Speed**: Slow for precision

## Adaptive Speed Control

Each phase has its own speed configuration:

```python
class SpeedConfig:
    outline_points_per_update: int = 8      # Slow, precise
    hatching_points_per_update: int = 20    # Medium speed
    cross_hatch_points_per_update: int = 25 # Fast
    detail_points_per_update: int = 5       # Slow for precision
    blending_points_per_update: int = 40    # Very fast
```

The speed automatically changes based on the current drawing phase, creating a natural rhythm where:
- **Edges/lines** are drawn slowly and carefully
- **Broad shading** is applied quickly
- **Fine details** return to slow, precise strokes

## Natural Pencil Effects

### Soft Brush Edges
Instead of hard circular masks, the engine uses Gaussian falloff:

```python
def _draw_soft_circle(self, x, y, radius, opacity, intensity):
    # Soft falloff using Gaussian-like function
    sigma = radius * self.brush_softness
    falloff = np.exp(-0.5 * (dist / max(0.5, sigma))**2)
```

This creates:
- Soft, blended edges
- No visible "bubbles"
- Natural pencil-like appearance

### Pressure Variation
Stroke pressure varies along paths:
```python
pressure = 0.7 + 0.3 * math.sin(i * 0.1)
```

This simulates natural hand movement and pressure changes.

### Width Variation
Stroke width adapts to local intensity:
```python
width = 1.5 + intensity * 2.0  # Thicker for darker areas
```

## Configuration Options

### Command Line Arguments

```bash
python main.py --image <path> [options]

# Shading Engine Options:
--force-shading          # Always use shading engine
--shading-sensitivity    # Detection sensitivity (0.0-1.0)
--hatching-angle         # Primary hatching angle in degrees
--stroke-spacing         # Spacing between strokes (pixels)
```

### GUI Controls

The Control Panel includes a new "Shading Engine" section:
- **Force Shading Engine**: Toggle to always use advanced engine
- **Shading Sensitivity**: How sensitive to detect shaded regions
- **Hatching Angle**: Primary angle for shading strokes (0-90°)
- **Stroke Spacing**: Distance between hatching lines (1-10px)

## Auto-Detection

The system automatically analyzes uploaded images and selects the appropriate engine:

```python
def _analyze_and_select_engine(self):
    # Analyze image for:
    # - Edge coverage (Canny edge detection)
    # - Shade coverage (dark non-edge pixels)
    # - Gradient regions (local variance)
    
    if shade_coverage > 0.10 or gradient_coverage > 0.05:
        return "shading"  # Use PencilShadingEngine
    else:
        return "simple"   # Use PixelRevealEngine
```

**Decision Criteria:**
- Shade coverage > 10% → Use shading engine
- Gradient regions > 5% → Use shading engine
- Otherwise → Use original line art engine

## File Structure

```
coloring_book_drawer/
├── pencil_shading_engine.py  # NEW: Advanced shading engine
├── pixel_reveal_engine.py    # Original line art engine
├── main.py                   # Updated: Engine auto-selection
├── control_panel_main.py     # Updated: Shading UI controls
└── ...
```

## Usage Examples

### Simple Line Art (Auto-detected)
```bash
python main.py --image line_art.png
# → Uses PixelRevealEngine automatically
```

### Complex Shaded Artwork (Auto-detected)
```bash
python main.py --image shaded_pencil_drawing.png
# → Uses PencilShadingEngine automatically
```

### Force Shading Engine
```bash
python main.py --image any_image.png --force-shading
# → Always uses PencilShadingEngine
```

### Custom Hatching Configuration
```bash
python main.py --image artwork.png \
    --hatching-angle 30 \
    --stroke-spacing 2 \
    --shading-sensitivity 0.7
```

## Technical Implementation

### Key Classes

#### `PencilShadingEngine`
Main engine class that orchestrates the multi-layer drawing process.

#### `StrokePoint`
Data class representing a single point in a pencil stroke:
```python
@dataclass
class StrokePoint:
    x: float
    y: float
    pressure: float       # 0.0-1.0
    angle: float          # Stroke direction
    width: float          # Stroke width
    phase: DrawingPhase   # Current phase
    intensity: float      # Target darkness
```

#### `DrawingPhase`
Enum for the different drawing phases:
```python
class DrawingPhase(Enum):
    OUTLINE = "outline"
    HATCHING = "hatching"
    CROSS_HATCHING = "cross_hatching"
    DETAIL_SHADING = "detail"
    BLENDING = "blending"
```

### Key Methods

- `process_image()`: Main pipeline entry point
- `_decompose_layers()`: Separates edges from shading
- `_build_outline_strokes()`: Creates skeleton-based outline paths
- `_build_shading_strokes()`: Generates hatching patterns
- `_generate_hatching_strokes()`: Creates parallel stroke lines
- `_draw_soft_circle()`: Renders soft-edged brush strokes
- `get_current_frame()`: Returns current animation frame

## Performance Considerations

- **Memory**: Stores intensity maps and stroke sequences
- **Processing Time**: ~2-5 seconds for image analysis
- **Animation Speed**: Configurable via speed multiplier
- **GPU**: Optional acceleration for compositing

## Future Improvements

1. **Adaptive hatching direction**: Follow contour lines
2. **Texture-aware strokes**: Different patterns for different textures
3. **Color support**: Extend to colored pencil drawings
4. **Pressure sensitivity curves**: More realistic pressure simulation
5. **Custom brush textures**: Import pencil texture overlays
