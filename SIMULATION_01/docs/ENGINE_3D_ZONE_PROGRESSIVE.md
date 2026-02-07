# Zone-Based Progressive Engine (Engine 3D)

## Executive Summary

This document proposes a **Zone-Based Progressive Engine** that identifies focal points and importance zones in the artwork, then reveals the drawing radiating outward from these interest centers. This creates an engaging "unveiling" effect that naturally draws viewer attention.

**Core Idea**: Analyze visual importance/saliency, then reveal from most important regions outward.

---

## Problem Analysis

### Viewer Attention Patterns

Research on visual attention shows:
- Eyes naturally go to high-contrast areas first
- Faces and eyes are strongest attractors
- Composition follows natural focal points

Current engines ignore this, revealing top-to-bottom or by phase instead of by importance.

---

## Solution Architecture

### Core Philosophy: Importance-First Reveal

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        INPUT IMAGE                                       │
│              (High-contrast pencil artwork)                              │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    STAGE 1: SALIENCY DETECTION                           │
├─────────────────────────────────────────────────────────────────────────┤
│  • Compute image saliency map                                           │
│  • Identify focal points (local maxima)                                 │
│  • Optional: Face/eye detection for portraits                           │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    STAGE 2: ZONE PARTITIONING                            │
├─────────────────────────────────────────────────────────────────────────┤
│  • Create radial zones from each focal point                            │
│  • Assign priority based on distance + saliency                         │
│  • Merge overlapping zones intelligently                                │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    STAGE 3: ZONE-ORDERED STROKE PLANNING                 │
├─────────────────────────────────────────────────────────────────────────┤
│  • Generate strokes within each zone                                    │
│  • Order zones by reveal priority                                       │
│  • Smooth transitions between zone boundaries                           │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    STAGE 4: RADIAL REVEAL ANIMATION                      │
├─────────────────────────────────────────────────────────────────────────┤
│  • Reveal from focal points outward                                     │
│  • Multiple focal points reveal simultaneously                          │
│  • Background fills in last                                             │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        FINAL OUTPUT                                      │
│     Focal-point-first dramatic reveal animation                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Technical Components

### 1. Saliency Detection

```python
import cv2
import numpy as np

class SaliencyDetector:
    """
    Detects visually salient (important) regions in the image.
    """
    
    def compute_saliency(self, image):
        """
        Compute saliency map using spectral residual method.
        
        Returns: Saliency map (0-1) where 1 = most salient
        """
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY).astype(float)
        
        # FFT for spectral analysis
        f = np.fft.fft2(gray)
        fshift = np.fft.fftshift(f)
        
        # Log magnitude and phase
        magnitude = np.log(np.abs(fshift) + 1)
        phase = np.angle(fshift)
        
        # Spectral residual
        avg_magnitude = cv2.blur(magnitude, (3, 3))
        spectral_residual = magnitude - avg_magnitude
        
        # Inverse FFT to get saliency
        saliency_complex = np.exp(spectral_residual + 1j * phase)
        saliency_shift = np.fft.ifftshift(saliency_complex)
        saliency = np.fft.ifft2(saliency_shift)
        saliency = np.abs(saliency) ** 2
        
        # Normalize and smooth
        saliency = cv2.GaussianBlur(saliency, (9, 9), 2.5)
        saliency = (saliency - saliency.min()) / (saliency.max() - saliency.min())
        
        return saliency
    
    def find_focal_points(self, saliency_map, max_points=5, min_distance=100):
        """
        Find local maxima in saliency map as focal points.
        """
        from scipy.ndimage import maximum_filter
        from scipy.ndimage import label
        
        # Find local maxima
        local_max = maximum_filter(saliency_map, size=50)
        peaks = (saliency_map == local_max) & (saliency_map > 0.3)
        
        # Extract coordinates
        coords = np.argwhere(peaks)
        
        # Filter by minimum distance and select top points
        focal_points = self._filter_by_distance(coords, saliency_map, 
                                                  max_points, min_distance)
        
        return focal_points
```

### 2. Face/Eye Detection Enhancement

```python
class PortraitFocalDetector:
    """
    Enhanced focal point detection for portraits.
    Uses face and eye detection to prioritize key features.
    """
    
    def __init__(self):
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        self.eye_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_eye.xml'
        )
    
    def detect_portrait_focals(self, image):
        """
        Detect focal points prioritizing:
        1. Eyes (highest priority)
        2. Face center
        3. General saliency
        """
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        focal_points = []
        
        # Detect faces
        faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
        
        for (x, y, w, h) in faces:
            face_region = gray[y:y+h, x:x+w]
            
            # Detect eyes within face
            eyes = self.eye_cascade.detectMultiScale(face_region)
            
            for (ex, ey, ew, eh) in eyes:
                # Eye center is highest priority focal point
                eye_center = (x + ex + ew//2, y + ey + eh//2)
                focal_points.append({
                    'point': eye_center,
                    'priority': 1.0,  # Highest
                    'type': 'eye'
                })
            
            # Face center is secondary
            face_center = (x + w//2, y + h//2)
            focal_points.append({
                'point': face_center,
                'priority': 0.8,
                'type': 'face'
            })
        
        return focal_points
```

### 3. Zone Partitioning

```python
class ZonePartitioner:
    """
    Partitions image into reveal zones based on focal points.
    """
    
    def __init__(self, num_zones=10):
        self.num_zones = num_zones
    
    def create_zones(self, image_shape, focal_points, saliency_map):
        """
        Create radial zones emanating from focal points.
        
        Returns: Zone map where each pixel has a zone ID (lower = reveal first)
        """
        h, w = image_shape[:2]
        zone_map = np.full((h, w), self.num_zones, dtype=np.float32)
        
        # Create coordinate grids
        yy, xx = np.mgrid[0:h, 0:w]
        
        for focal in focal_points:
            fx, fy = focal['point']
            priority = focal['priority']
            
            # Calculate distance from this focal point
            dist = np.sqrt((xx - fx)**2 + (yy - fy)**2)
            
            # Normalize distance to 0-1 (0 at focal, 1 at furthest)
            max_dist = np.sqrt(h**2 + w**2)
            normalized_dist = dist / max_dist
            
            # Combine with focal priority
            zone_value = normalized_dist * (2 - priority)
            
            # Take minimum (closest focal point wins)
            zone_map = np.minimum(zone_map, zone_value)
        
        # Factor in saliency (more salient = lower zone number)
        zone_map = zone_map * (1.5 - saliency_map * 0.5)
        
        # Discretize into zones
        zone_ids = np.digitize(zone_map, np.linspace(0, 1, self.num_zones))
        
        return zone_ids
```

### 4. Zone-Ordered Reveal

```python
class ZoneOrderedRevealer:
    """
    Reveals the image zone by zone, from focal points outward.
    """
    
    def __init__(self, original_image, zone_map):
        self.original = original_image
        self.zone_map = zone_map
        self.num_zones = zone_map.max() + 1
        
        # Pre-compute zone masks
        self.zone_masks = []
        for z in range(self.num_zones):
            mask = (zone_map == z).astype(np.float32)
            # Smooth edges for natural transition
            mask = cv2.GaussianBlur(mask, (5, 5), 1.5)
            self.zone_masks.append(mask)
        
        self.current_zone = 0
        self.zone_progress = 0.0
    
    def reveal_next_batch(self, points_per_update=100):
        """
        Reveal next batch of points within current zone.
        """
        if self.current_zone >= self.num_zones:
            return False
        
        # Progress within current zone
        self.zone_progress += points_per_update / 1000.0  # Normalize
        
        if self.zone_progress >= 1.0:
            self.current_zone += 1
            self.zone_progress = 0.0
        
        return True
    
    def get_current_frame(self):
        """
        Get frame showing all revealed zones plus partial current zone.
        """
        reveal_mask = np.zeros(self.zone_map.shape, dtype=np.float32)
        
        # Fully revealed zones
        for z in range(self.current_zone):
            reveal_mask = np.maximum(reveal_mask, self.zone_masks[z])
        
        # Partially revealed current zone
        if self.current_zone < self.num_zones:
            partial = self.zone_masks[self.current_zone] * self.zone_progress
            reveal_mask = np.maximum(reveal_mask, partial)
        
        # Apply mask
        mask_3ch = np.stack([reveal_mask] * 3, axis=-1)
        bg = np.ones_like(self.original) * 255
        frame = bg * (1 - mask_3ch) + self.original * mask_3ch
        
        return frame.astype(np.uint8)
```

---

## Animation Modes

| Mode | Description | Best For |
|------|-------------|----------|
| **Single Focal** | One center point, radial reveal | Centered compositions |
| **Multi Focal** | Multiple points, simultaneous | Portraits (eyes) |
| **Spiral** | Focal to edge in spiral pattern | Dramatic effect |
| **Burst** | Quick focal reveal, slow background | Action scenes |

---

## Modular File Structure

```
SIMULATION_01/
├── coloring_book_drawer/
│   ├── engines/
│   │   └── zone_progressive/              # Engine 3D: Zone-Based
│   │       ├── __init__.py                # Exports ZoneProgressiveEngine
│   │       ├── engine.py                  # Main engine class
│   │       ├── config.py                  # Configuration
│   │       │
│   │       ├── detection/                 # Focal point detection
│   │       │   ├── __init__.py
│   │       │   ├── saliency.py            # Saliency map computation
│   │       │   ├── focal_finder.py        # Local maxima extraction
│   │       │   └── portrait_detector.py   # Face/eye detection
│   │       │
│   │       ├── zoning/                    # Zone creation
│   │       │   ├── __init__.py
│   │       │   ├── partitioner.py         # Zone partitioning
│   │       │   ├── priority_calculator.py # Priority assignment
│   │       │   └── zone_merger.py         # Overlapping zone handling
│   │       │
│   │       ├── animation/                 # Reveal animation
│   │       │   ├── __init__.py
│   │       │   ├── revealer.py            # Zone-ordered reveal
│   │       │   ├── stroke_generator.py    # Per-zone strokes
│   │       │   └── transition_blender.py  # Smooth zone transitions
│   │       │
│   │       └── rendering/                 # Output
│   │           ├── __init__.py
│   │           └── frame_compositor.py    # Frame composition
│   │
│   ├── main.py
│   └── control_panel_main.py
│
├── docs/
│   └── ENGINE_3D_ZONE_PROGRESSIVE.md      # This document
│
└── requirements.txt
```

### Dependencies

```
# requirements.txt additions
scipy>=1.10.0          # Signal processing, peak finding
opencv-contrib-python  # Advanced CV features (optional)
```

---

## Advantages & Disadvantages

### Advantages

| Advantage | Description |
|-----------|-------------|
| **Dramatic Effect** | Creates engaging "unveiling" animation |
| **Viewer Attention** | Aligns with natural eye movement |
| **Portrait Optimized** | Excellent for faces with eye detection |
| **Flexible** | Multiple animation modes available |

### Disadvantages

| Disadvantage | Description |
|--------------|-------------|
| **Focal Detection** | May miss important areas |
| **Zone Boundaries** | Can be visible if not smoothed |
| **Less Drawing-Like** | More "reveal" than "draw" effect |
| **Overhead** | Saliency computation adds latency |

---

## Performance Characteristics

| Aspect | Performance |
|--------|-------------|
| Saliency computation | 100-300 ms |
| Face detection | 50-150 ms |
| Zone partitioning | 20-50 ms |
| Per-frame reveal | 5-10 ms |

---

## Comparison with Other Engines

| Aspect | Engine 3A (Gradient) | Engine 3D (Zone) |
|--------|---------------------|------------------|
| **Reveal Order** | Phase-based | Importance-based |
| **Focal Awareness** | None | Core feature |
| **Animation Style** | Drawing | Unveiling |
| **Portrait Quality** | Good | Excellent |
| **Processing** | Medium | Fast |

---

## Conclusion

The Zone-Based Progressive Engine creates visually dramatic animations by revealing artwork from visually important regions outward. It's particularly powerful for portraits where eyes and faces can be detected and prioritized.

**Best suited for**: Portraits, centered compositions, dramatic reveals.

**Fallback to**: Engine 3A for more traditional drawing-style animation.
