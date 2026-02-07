# Hybrid Multi-Strategy Engine (Engine 3F)

## Executive Summary

This document proposes a **Hybrid Multi-Strategy Engine** that intelligently combines multiple engine approaches based on local image characteristics. Different regions of the image can use different strategies, ensuring optimal quality across diverse artwork elements.

**Core Idea**: Analyze each region's characteristics and apply the best-suited engine strategy locally.

---

## Problem Analysis

### Why Hybrid?

Complex artwork contains diverse elements:
- **Smooth gradients** (skin, backgrounds) → Best for wavelet/gradient approach
- **Fine textures** (hair, fabric) → Best for direction-aware strokes  
- **Sharp edges** (contours) → Best for skeleton-based reveal
- **Deep shadows** → Best for multi-pass accumulation
- **Focal points** (eyes) → Best for importance-based reveal

No single strategy is optimal for all regions. A hybrid approach selects the best strategy per region.

---

## Solution Architecture

### Core Philosophy: Per-Region Strategy Selection

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        INPUT IMAGE                                       │
│              (High-contrast pencil artwork)                              │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    STAGE 1: REGION ANALYSIS                              │
├─────────────────────────────────────────────────────────────────────────┤
│  • Segment image into coherent regions                                  │
│  • Classify each region type (gradient, texture, edge, shadow)          │
│  • Detect focal points for priority ordering                            │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    STAGE 2: STRATEGY ASSIGNMENT                          │
├─────────────────────────────────────────────────────────────────────────┤
│  • Select optimal strategy per region                                   │
│  • Configure strategy parameters based on region characteristics        │
│  • Define transition zones between strategies                           │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    STAGE 3: UNIFIED STROKE PLANNING                      │
├─────────────────────────────────────────────────────────────────────────┤
│  • Generate strokes using assigned strategies per region                │
│  • Order strokes globally (respecting region priorities)                │
│  • Smooth transition strokes at region boundaries                       │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    STAGE 4: COORDINATED REVEAL                           │
├─────────────────────────────────────────────────────────────────────────┤
│  • Execute strokes in unified sequence                                  │
│  • Blend strategies smoothly at boundaries                              │
│  • Maintain consistent animation pacing                                 │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        FINAL OUTPUT                                      │
│     Best-of-all-strategies combined animation                            │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Technical Components

### 1. Region Classification System

```python
from enum import Enum
from dataclasses import dataclass

class RegionType(Enum):
    SMOOTH_GRADIENT = "smooth_gradient"    # Low variance, smooth tones
    TEXTURE = "texture"                    # High variance, patterns
    EDGE = "edge"                          # Strong gradients, contours
    DEEP_SHADOW = "deep_shadow"            # Very dark areas
    HIGHLIGHT = "highlight"                # Very bright areas
    FOCAL = "focal"                        # Detected as visually important

class StrategyType(Enum):
    GRADIENT_REVEAL = "gradient"           # Engine 3A approach
    WAVELET_DECOMPOSE = "wavelet"          # Engine 3C approach
    ZONE_PROGRESSIVE = "zone"              # Engine 3D approach
    BRUSH_SIMULATION = "brush"             # Engine 3E approach

@dataclass
class RegionInfo:
    region_id: int
    region_type: RegionType
    mask: np.ndarray
    centroid: tuple
    area: int
    mean_intensity: float
    intensity_variance: float
    edge_density: float
    assigned_strategy: StrategyType = None

class RegionClassifier:
    """
    Classifies image regions by their visual characteristics.
    """
    
    def classify_regions(self, gray_image, segments):
        """
        Analyze and classify each segmented region.
        """
        regions = []
        
        for region_id in np.unique(segments):
            mask = segments == region_id
            region_data = gray_image[mask]
            
            # Compute characteristics
            mean_intensity = np.mean(region_data)
            variance = np.var(region_data)
            edge_density = self._compute_edge_density(gray_image, mask)
            
            # Classify based on characteristics
            region_type = self._classify(mean_intensity, variance, edge_density)
            
            regions.append(RegionInfo(
                region_id=region_id,
                region_type=region_type,
                mask=mask,
                centroid=self._compute_centroid(mask),
                area=np.sum(mask),
                mean_intensity=mean_intensity,
                intensity_variance=variance,
                edge_density=edge_density
            ))
        
        return regions
    
    def _classify(self, mean_intensity, variance, edge_density):
        """
        Decision tree for region classification.
        """
        if mean_intensity > 230:
            return RegionType.HIGHLIGHT
        elif mean_intensity < 50:
            return RegionType.DEEP_SHADOW
        elif edge_density > 0.3:
            return RegionType.EDGE
        elif variance > 500:
            return RegionType.TEXTURE
        else:
            return RegionType.SMOOTH_GRADIENT
```

### 2. Strategy Assignment

```python
class StrategyAssigner:
    """
    Assigns optimal processing strategy to each region.
    """
    
    # Mapping from region type to preferred strategies (in priority order)
    STRATEGY_PREFERENCE = {
        RegionType.SMOOTH_GRADIENT: [StrategyType.GRADIENT_REVEAL, StrategyType.WAVELET_DECOMPOSE],
        RegionType.TEXTURE: [StrategyType.BRUSH_SIMULATION, StrategyType.GRADIENT_REVEAL],
        RegionType.EDGE: [StrategyType.GRADIENT_REVEAL, StrategyType.BRUSH_SIMULATION],
        RegionType.DEEP_SHADOW: [StrategyType.BRUSH_SIMULATION, StrategyType.GRADIENT_REVEAL],
        RegionType.HIGHLIGHT: [StrategyType.WAVELET_DECOMPOSE, StrategyType.GRADIENT_REVEAL],
        RegionType.FOCAL: [StrategyType.ZONE_PROGRESSIVE, StrategyType.GRADIENT_REVEAL],
    }
    
    def assign_strategies(self, regions, available_strategies=None):
        """
        Assign best available strategy to each region.
        """
        if available_strategies is None:
            available_strategies = set(StrategyType)
        
        for region in regions:
            preferences = self.STRATEGY_PREFERENCE.get(
                region.region_type, 
                [StrategyType.GRADIENT_REVEAL]
            )
            
            # Select first available preferred strategy
            for strategy in preferences:
                if strategy in available_strategies:
                    region.assigned_strategy = strategy
                    break
            
            # Fallback to gradient if nothing available
            if region.assigned_strategy is None:
                region.assigned_strategy = StrategyType.GRADIENT_REVEAL
        
        return regions
```

### 3. Multi-Strategy Orchestrator

```python
class MultiStrategyOrchestrator:
    """
    Coordinates multiple strategy engines for hybrid rendering.
    """
    
    def __init__(self):
        # Initialize available strategy engines
        self.engines = {
            StrategyType.GRADIENT_REVEAL: GradientRevealEngine(),
            StrategyType.WAVELET_DECOMPOSE: WaveletDecomposeEngine(),
            StrategyType.ZONE_PROGRESSIVE: ZoneProgressiveEngine(),
            StrategyType.BRUSH_SIMULATION: BrushSimulationEngine(),
        }
        
    def generate_strokes_for_region(self, region, image):
        """
        Generate strokes for a region using its assigned strategy.
        """
        engine = self.engines[region.assigned_strategy]
        
        # Extract region portion of image
        region_image = image.copy()
        region_image[~region.mask] = 255  # Mask out other regions
        
        # Generate strokes using assigned engine
        strokes = engine.generate_strokes(region_image, region.mask)
        
        # Tag strokes with region info
        for stroke in strokes:
            stroke.region_id = region.region_id
            stroke.strategy = region.assigned_strategy
        
        return strokes
    
    def generate_all_strokes(self, regions, image):
        """
        Generate strokes for all regions, then merge intelligently.
        """
        all_strokes = []
        
        for region in regions:
            region_strokes = self.generate_strokes_for_region(region, image)
            all_strokes.extend(region_strokes)
        
        # Global ordering with priority
        ordered_strokes = self.order_globally(all_strokes, regions)
        
        return ordered_strokes
    
    def order_globally(self, strokes, regions):
        """
        Order all strokes for natural animation.
        Respects focal regions, maintains local coherence.
        """
        # Priority order: focal > edge > gradient > texture > shadow > highlight
        TYPE_PRIORITY = {
            RegionType.FOCAL: 0,
            RegionType.EDGE: 1,
            RegionType.SMOOTH_GRADIENT: 2,
            RegionType.TEXTURE: 3,
            RegionType.DEEP_SHADOW: 4,
            RegionType.HIGHLIGHT: 5,
        }
        
        # Create region priority map
        region_priority = {r.region_id: TYPE_PRIORITY[r.region_type] for r in regions}
        
        # Sort strokes by region priority, then by local order
        strokes.sort(key=lambda s: (region_priority.get(s.region_id, 99), s.local_order))
        
        return strokes
```

### 4. Transition Zone Blending

```python
class TransitionBlender:
    """
    Handles smooth transitions at region boundaries.
    """
    
    def __init__(self, transition_width=10):
        self.transition_width = transition_width
    
    def create_transition_zones(self, regions):
        """
        Create feathered boundaries between adjacent regions.
        """
        h, w = regions[0].mask.shape
        transition_masks = {}
        
        for i, region_a in enumerate(regions):
            for region_b in regions[i+1:]:
                # Find boundary between regions
                boundary = self._find_boundary(region_a.mask, region_b.mask)
                
                if np.any(boundary):
                    # Create feathered transition zone
                    dist_a = cv2.distanceTransform(
                        (~region_a.mask).astype(np.uint8), 
                        cv2.DIST_L2, 5
                    )
                    dist_b = cv2.distanceTransform(
                        (~region_b.mask).astype(np.uint8), 
                        cv2.DIST_L2, 5
                    )
                    
                    # Blend factor (0 = region_a, 1 = region_b)
                    total_dist = dist_a + dist_b + 1e-6
                    blend_factor = dist_a / total_dist
                    
                    # Only apply in transition zone
                    in_zone = (dist_a < self.transition_width) & (dist_b < self.transition_width)
                    
                    transition_masks[(region_a.region_id, region_b.region_id)] = {
                        'zone': in_zone,
                        'blend': blend_factor
                    }
        
        return transition_masks
    
    def blend_strokes_at_boundary(self, strokes_a, strokes_b, transition_info):
        """
        Blend stroke characteristics at region boundary.
        """
        zone = transition_info['zone']
        blend_factor = transition_info['blend']
        
        blended_strokes = []
        
        # For strokes in transition zone, interpolate brush parameters
        for stroke in strokes_a + strokes_b:
            if self._stroke_in_zone(stroke, zone):
                # Get blend factor at stroke center
                blend = blend_factor[int(stroke.center_y), int(stroke.center_x)]
                
                # Interpolate parameters
                stroke.brush_size = lerp(strokes_a[0].brush_size, 
                                         strokes_b[0].brush_size, blend)
                stroke.softness = lerp(strokes_a[0].softness,
                                       strokes_b[0].softness, blend)
        
            blended_strokes.append(stroke)
        
        return blended_strokes
```

---

## Strategy Decision Matrix

| Region Type | Primary Strategy | Secondary Strategy | Rationale |
|-------------|-----------------|-------------------|-----------|
| **Smooth Gradient** | Gradient Reveal | Wavelet | Smooth tones need smooth reveal |
| **Texture** | Brush Simulation | Gradient | Texture needs physical brush feel |
| **Edge** | Gradient Reveal | Brush | Edges need direction-awareness |
| **Deep Shadow** | Brush Simulation | Gradient | Shadows need accumulation |
| **Highlight** | Wavelet | Gradient | Highlights can be quick |
| **Focal** | Zone Progressive | Gradient | Focal needs attention priority |

---

## Modular File Structure

```
SIMULATION_01/
├── coloring_book_drawer/
│   ├── engines/
│   │   ├── advanced_gradient/         # Engine 3A (used as sub-engine)
│   │   ├── neural_style/              # Engine 3B (used as sub-engine)
│   │   ├── wavelet_frequency/         # Engine 3C (used as sub-engine)
│   │   ├── zone_progressive/          # Engine 3D (used as sub-engine)
│   │   ├── adaptive_brush/            # Engine 3E (used as sub-engine)
│   │   │
│   │   └── hybrid_multi/              # Engine 3F: Hybrid Multi-Strategy
│   │       ├── __init__.py            # Exports HybridMultiEngine
│   │       ├── engine.py              # Main orchestrator
│   │       ├── config.py              # Configuration
│   │       │
│   │       ├── classification/        # Region analysis
│   │       │   ├── __init__.py
│   │       │   ├── segmenter.py       # Image segmentation
│   │       │   ├── classifier.py      # Region type classification
│   │       │   └── focal_detector.py  # Focal point detection
│   │       │
│   │       ├── assignment/            # Strategy assignment
│   │       │   ├── __init__.py
│   │       │   ├── strategy_assigner.py
│   │       │   └── preference_rules.py
│   │       │
│   │       ├── orchestration/         # Multi-engine coordination
│   │       │   ├── __init__.py
│   │       │   ├── orchestrator.py    # Multi-strategy orchestrator
│   │       │   ├── stroke_merger.py   # Global stroke ordering
│   │       │   └── transition_blender.py
│   │       │
│   │       └── rendering/             # Output
│   │           ├── __init__.py
│   │           └── unified_renderer.py
│   │
│   ├── main.py
│   └── control_panel_main.py
│
├── docs/
│   └── ENGINE_3F_HYBRID_MULTI.md      # This document
│
└── requirements.txt
```

### Dependencies

```
# requirements.txt additions
# Uses dependencies from all sub-engines:
scikit-image>=0.20.0   # Segmentation
scipy>=1.10.0          # Signal processing
PyWavelets>=1.4.0      # Wavelet transforms
# Optional for neural sub-engine:
torch>=2.0.0           # Neural network
```

---

## Advantages & Disadvantages

### Advantages

| Advantage | Description |
|-----------|-------------|
| **Best of All** | Uses optimal approach for each region |
| **Highly Adaptable** | Handles diverse artwork elements |
| **Extensible** | Easy to add new strategies |
| **Graceful Degradation** | Falls back if strategy unavailable |

### Disadvantages

| Disadvantage | Description |
|--------------|-------------|
| **Complexity** | Most complex to implement |
| **Overhead** | Region analysis adds latency |
| **Boundary Artifacts** | Risk of visible strategy transitions |
| **Parameter Tuning** | Many knobs across strategies |

---

## Performance Characteristics

| Stage | Duration |
|-------|----------|
| Segmentation | 100-300 ms |
| Classification | 50-100 ms |
| Strategy assignment | 10-30 ms |
| Per-region stroke gen | Varies by strategy |
| Total (typical) | 500 ms - 2 sec |

---

## Configuration Options

```python
HYBRID_ENGINE_CONFIG = {
    # Region analysis
    'segmentation_scale': 100,           # Superpixel count
    'min_region_area': 500,              # Minimum region size (pixels)
    
    # Strategy availability
    'available_strategies': ['gradient', 'wavelet', 'zone', 'brush'],
    'default_strategy': 'gradient',
    
    # Transition handling
    'transition_width': 10,              # Pixels for blending
    'blend_smoothness': 0.7,
    
    # Performance
    'parallel_regions': True,            # Process regions in parallel
    'max_workers': 4,
}
```

---

## Comparison with Other Engines

| Aspect | Single Strategy Engines | Engine 3F (Hybrid) |
|--------|------------------------|-------------------|
| **Consistency** | Same everywhere | Varies by region |
| **Optimality** | Compromise | Optimal per region |
| **Complexity** | Lower | Highest |
| **Flexibility** | Limited | Maximum |
| **Debugging** | Easier | Harder |

---

## Implementation Roadmap

### Phase 1: Integration Framework (Week 1-2)
1. Create engine abstraction interface
2. Wrap existing engines as sub-engines
3. Build region classification pipeline

### Phase 2: Orchestration (Week 2-3)
1. Implement strategy assignment
2. Build multi-engine orchestrator
3. Develop global stroke ordering

### Phase 3: Blending (Week 3-4)
1. Transition zone detection
2. Stroke blending at boundaries
3. Unified rendering pipeline

### Phase 4: Polish (Week 4-5)
1. Performance optimization
2. Parameter tuning
3. Edge case handling

---

## Conclusion

The Hybrid Multi-Strategy Engine represents the pinnacle of the engine architecture by intelligently combining all available approaches. While it's the most complex to implement, it offers the highest quality by ensuring each region is processed with its optimal strategy.

**Best suited for**: Maximum quality regardless of complexity.

**Recommended when**: Other single-strategy engines show weaknesses in different regions of the same artwork.
