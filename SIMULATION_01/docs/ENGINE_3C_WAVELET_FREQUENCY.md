# Frequency-Based Wavelet Engine (Engine 3C)

## Executive Summary

This document proposes a **Frequency-Based Wavelet Engine** that decomposes pencil artwork into frequency bands and reveals them progressively from low-frequency (general shapes) to high-frequency (fine details). This mimics how artists naturally work from rough sketch to refined details.

**Core Idea**: Use wavelet decomposition to naturally separate "sketch" from "details" and reveal them in order.

---

## Problem Analysis

### Signal Processing Perspective

Pencil artwork can be viewed as a 2D signal with:
- **Low frequencies**: Overall shapes, large shadow areas, general composition
- **Mid frequencies**: Shading gradients, medium-sized features
- **High frequencies**: Fine lines, textures, small details

Traditional engines don't leverage this natural hierarchy.

---

## Solution Architecture

### Core Philosophy: Frequency-Based Progressive Reveal

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        INPUT IMAGE                                       │
│              (High-contrast pencil artwork)                              │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    STAGE 1: WAVELET DECOMPOSITION                        │
├─────────────────────────────────────────────────────────────────────────┤
│  • Apply 2D Discrete Wavelet Transform (DWT)                            │
│  • Decompose into multiple resolution levels (4-6 levels)              │
│  • Separate: approximation (LL) + details (LH, HL, HH)                 │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    STAGE 2: BAND ANALYSIS                                │
├─────────────────────────────────────────────────────────────────────────┤
│  • Level 1 (lowest freq): Major shapes, silhouette                      │
│  • Level 2-3 (mid freq): Shading, gradients                             │
│  • Level 4-5 (high freq): Fine details, textures                        │
│  • Level 6+ (highest): Noise, micro-details                             │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    STAGE 3: PROGRESSIVE RECONSTRUCTION                   │
├─────────────────────────────────────────────────────────────────────────┤
│  • Start with lowest frequency band only                                │
│  • Progressively add higher frequency bands                             │
│  • Blend smoothly between levels                                        │
│  • Apply stroke-like reveal within each band                            │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    STAGE 4: STROKE SIMULATION                            │
├─────────────────────────────────────────────────────────────────────────┤
│  • Within each band, reveal using skeleton paths                        │
│  • Low-freq bands: broad strokes, fast reveal                           │
│  • High-freq bands: fine strokes, slow precise reveal                   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        FINAL OUTPUT                                      │
│     Sketch-to-detail natural progression animation                       │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Technical Components

### 1. Wavelet Decomposition

```python
import pywt
import numpy as np

class WaveletDecomposer:
    """
    Decomposes image into frequency bands using 2D DWT.
    """
    def __init__(self, wavelet='db4', levels=5):
        self.wavelet = wavelet
        self.levels = levels
        
    def decompose(self, gray_image):
        """
        Perform multi-level 2D DWT decomposition.
        
        Returns list of coefficient tuples:
        [(cA_n, (cH_n, cV_n, cD_n)), ..., (cA_1, (cH_1, cV_1, cD_1))]
        
        Where:
        - cA: Approximation (low-low frequency)
        - cH: Horizontal details (low-high)
        - cV: Vertical details (high-low)
        - cD: Diagonal details (high-high)
        """
        coeffs = pywt.wavedec2(gray_image, self.wavelet, level=self.levels)
        return coeffs
    
    def reconstruct_partial(self, coeffs, up_to_level):
        """
        Reconstruct image using only coefficients up to specified level.
        Zeros out higher-frequency details.
        """
        modified_coeffs = []
        
        # First element is lowest-level approximation
        modified_coeffs.append(coeffs[0])
        
        for i, detail_tuple in enumerate(coeffs[1:], 1):
            if i <= up_to_level:
                # Include these details
                modified_coeffs.append(detail_tuple)
            else:
                # Zero out higher-frequency details
                zeros = tuple(np.zeros_like(d) for d in detail_tuple)
                modified_coeffs.append(zeros)
        
        return pywt.waverec2(modified_coeffs, self.wavelet)
```

### 2. Progressive Band Reveal

```python
class ProgressiveBandRevealer:
    """
    Manages the progressive reveal of frequency bands.
    """
    def __init__(self, coeffs, original_image):
        self.coeffs = coeffs
        self.original = original_image
        self.num_levels = len(coeffs) - 1
        
        # Pre-compute reconstructions at each level
        self.level_images = []
        for level in range(1, self.num_levels + 1):
            partial = self.reconstruct_partial(coeffs, level)
            self.level_images.append(partial)
    
    def get_image_at_progress(self, progress):
        """
        Get blended image at given progress (0-1).
        
        progress 0.0: Just lowest frequency (rough sketch)
        progress 1.0: Full image with all details
        """
        # Map progress to level and blend factor
        level_float = progress * (self.num_levels - 1)
        level_low = int(level_float)
        level_high = min(level_low + 1, self.num_levels - 1)
        blend = level_float - level_low
        
        # Blend between two adjacent level reconstructions
        img_low = self.level_images[level_low]
        img_high = self.level_images[level_high]
        
        blended = img_low * (1 - blend) + img_high * blend
        return blended.astype(np.uint8)
```

### 3. Band-Specific Stroke Simulation

```python
class BandStrokeSimulator:
    """
    Simulates drawing strokes within each frequency band.
    Different bands get different stroke characteristics.
    """
    
    BAND_CONFIGS = {
        1: {'brush_size': 15, 'speed': 3.0, 'softness': 0.9},  # Low freq
        2: {'brush_size': 10, 'speed': 2.0, 'softness': 0.7},
        3: {'brush_size': 6, 'speed': 1.5, 'softness': 0.5},
        4: {'brush_size': 3, 'speed': 1.0, 'softness': 0.3},   # Mid freq
        5: {'brush_size': 1.5, 'speed': 0.7, 'softness': 0.2}, # High freq
    }
    
    def generate_strokes_for_band(self, band_image, band_level):
        """
        Generate stroke sequence for a specific frequency band.
        """
        config = self.BAND_CONFIGS.get(band_level, self.BAND_CONFIGS[3])
        
        # Extract significant features in this band
        features = self.extract_band_features(band_image)
        
        # Generate stroke paths
        strokes = self.create_stroke_paths(features, config)
        
        return strokes
    
    def extract_band_features(self, band_image):
        """
        Extract non-zero/significant regions in the band.
        """
        threshold = np.std(band_image) * 0.5
        significant = np.abs(band_image) > threshold
        return significant
```

### 4. Blended Animation Controller

```python
class WaveletAnimationController:
    """
    Coordinates the full animation combining band progression and strokes.
    """
    def __init__(self, original_image):
        self.original = original_image
        self.gray = cv2.cvtColor(original_image, cv2.COLOR_RGB2GRAY)
        
        # Decompose
        self.decomposer = WaveletDecomposer(levels=5)
        self.coeffs = self.decomposer.decompose(self.gray)
        
        # Setup revealers
        self.band_revealer = ProgressiveBandRevealer(self.coeffs, self.gray)
        self.stroke_sim = BandStrokeSimulator()
        
        # Animation state
        self.progress = 0.0
        self.current_band = 1
        
    def get_frame(self, progress):
        """
        Get animation frame at given progress.
        
        Combines:
        1. Frequency band reconstruction (overall structure)
        2. Stroke-based reveal (natural drawing effect)
        """
        # Get base image from frequency reconstruction
        base_image = self.band_revealer.get_image_at_progress(progress)
        
        # Apply stroke mask for natural reveal effect
        stroke_mask = self.get_stroke_mask(progress)
        
        # Blend original with base through stroke mask
        frame = self.blend_with_strokes(base_image, stroke_mask)
        
        return frame
```

---

## Wavelet Selection Guide

| Wavelet | Characteristics | Best For |
|---------|----------------|----------|
| `db4` (Daubechies-4) | Good balance, smooth | General artwork |
| `sym8` (Symlet-8) | Near-symmetric | Portraits |
| `bior2.2` (Biorthogonal) | Linear phase | Edges, lines |
| `coif4` (Coiflet-4) | Near-symmetric, smooth | Gradients |
| `haar` | Simplest, blocky | Quick preview |

---

## Modular File Structure

```
SIMULATION_01/
├── coloring_book_drawer/
│   ├── engines/
│   │   └── wavelet_frequency/             # Engine 3C: Frequency-Based
│   │       ├── __init__.py                # Exports WaveletEngine
│   │       ├── engine.py                  # Main engine class
│   │       ├── config.py                  # Configuration
│   │       │
│   │       ├── decomposition/             # Wavelet processing
│   │       │   ├── __init__.py
│   │       │   ├── wavelet_decomposer.py  # DWT decomposition
│   │       │   ├── band_analyzer.py       # Frequency band analysis
│   │       │   └── partial_reconstruct.py # Level-based reconstruction
│   │       │
│   │       ├── animation/                 # Animation control
│   │       │   ├── __init__.py
│   │       │   ├── band_revealer.py       # Progressive band reveal
│   │       │   ├── stroke_simulator.py    # Band-specific strokes
│   │       │   └── blend_controller.py    # Animation blending
│   │       │
│   │       └── rendering/                 # Output rendering
│   │           ├── __init__.py
│   │           └── frame_compositor.py    # Final frame composition
│   │
│   ├── main.py
│   └── control_panel_main.py
│
├── docs/
│   └── ENGINE_3C_WAVELET_FREQUENCY.md     # This document
│
└── requirements.txt
```

### Dependencies

```
# requirements.txt additions
PyWavelets>=1.4.0      # Wavelet transforms
scipy>=1.10.0          # Signal processing utilities
```

---

## Advantages & Disadvantages

### Advantages

| Advantage | Description |
|-----------|-------------|
| **Natural Hierarchy** | Mirrors artist workflow (sketch → details) |
| **Mathematically Sound** | Based on established signal processing |
| **Smooth Transitions** | Natural blending between detail levels |
| **Fast Processing** | Wavelet transforms are efficient |
| **Predictable** | Deterministic, reproducible results |

### Disadvantages

| Disadvantage | Description |
|--------------|-------------|
| **Block Artifacts** | Some wavelets cause blocky appearance |
| **Uniform Application** | Same decomposition applied everywhere |
| **Limited Stroke Control** | Less control over individual strokes |
| **Post-Processing Needed** | May need additional stroke simulation |

---

## Performance Characteristics

| Aspect | Performance |
|--------|-------------|
| Decomposition time | 50-200 ms |
| Per-level reconstruction | 20-50 ms |
| Memory usage | 2-3x image size |
| Animation smoothness | Excellent |

---

## Implementation Roadmap

### Phase 1: Core Wavelet System (Week 1)
1. Implement DWT decomposition
2. Build partial reconstruction
3. Test on sample images

### Phase 2: Animation (Week 2)
1. Progressive band reveal
2. Band-specific stroke simulation
3. Blending controller

### Phase 3: Integration (Week 3)
1. Engine class wrapper
2. GUI controls
3. Performance optimization

---

## Comparison with Other Engines

| Aspect | Engine 3A (Gradient) | Engine 3C (Wavelet) |
|--------|---------------------|-------------------|
| **Approach** | Spatial analysis | Frequency analysis |
| **Hierarchy** | Region-based | Scale-based |
| **Stroke Control** | Fine-grained | Coarse-grained |
| **Processing Speed** | Medium | Fast |
| **Natural Progression** | Good | Excellent |
| **Artifact Risk** | Low | Medium (blocky) |

---

## Conclusion

The Frequency-Based Wavelet Engine offers a unique approach by leveraging signal processing to create a natural sketch-to-detail progression. It's particularly effective for artwork with clear hierarchical detail levels and provides very smooth transitions.

**Best suited for**: Artwork with clear composition hierarchy, fast processing needs.

**Fallback to**: Engine 3A if wavelet artifacts are visible.
