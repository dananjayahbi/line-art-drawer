# Pencil Shading Engine V2 — Advancement Plan

A detailed analysis of the current engine's problems and a concrete plan to fix them in V2.

---

## Table of Contents

1. [Current Problems Overview](#1-current-problems-overview)
2. [Root Cause Analysis: Patchy Shading](#2-root-cause-analysis-patchy-shading)
3. [Root Cause Analysis: Manual Tuning Required](#3-root-cause-analysis-manual-tuning-required)
4. [Fix 1 — Feathered Edge Exclusion (Remove White Halos)](#4-fix-1--feathered-edge-exclusion-remove-white-halos)
5. [Fix 2 — Tapered Stroke Endpoints (Smooth Start/Stop)](#5-fix-2--tapered-stroke-endpoints-smooth-startstop)
6. [Fix 3 — Smoothed Intensity Sampling (No Pixel Noise)](#6-fix-3--smoothed-intensity-sampling-no-pixel-noise)
7. [Fix 4 — Natural Hand Wobble (Organic Spacing/Angle)](#7-fix-4--natural-hand-wobble-organic-spacingangle)
8. [Fix 5 — Soft Phase Thresholds (No Hard Boundaries)](#8-fix-5--soft-phase-thresholds-no-hard-boundaries)
9. [Fix 6 — Zone-Interleaved Drawing (No Phase Gaps)](#9-fix-6--zone-interleaved-drawing-no-phase-gaps)
10. [Fix 7 — Resolution-Aware Scaling](#10-fix-7--resolution-aware-scaling)
11. [Fix 8 — Auto-Tuner (Automated Settings)](#11-fix-8--auto-tuner-automated-settings)
12. [Implementation Priority](#12-implementation-priority)
13. [Design Principle: One Continuous Flow](#13-design-principle-one-continuous-flow)

---

## 1. Current Problems Overview

### Problem A: Patchy Shading

When the engine draws shaded areas, visible "patches" appear:
- **White halos** around outlines where shading can't reach
- **Hard edges** where shading suddenly starts/stops at intensity boundaries
- **Visible phase transitions** — you can see when the engine switches from hatching to cross-hatching
- **Grid patterns** — the spatial sorting grid becomes visible
- **Mechanical regularity** — perfectly straight, perfectly spaced lines look artificial

### Problem B: Manual Settings Tuning

Every image requires different settings:
- Bright images need different thresholds than dark images
- High-resolution images need scaled parameters
- Portraits benefit from different angles than landscapes
- Heavy shading needs denser spacing than line art

---

## 2. Root Cause Analysis: Patchy Shading

### Cause 1: Edge/Shade Gap (WHITE HALO) — CRITICAL

**Location:** `_decompose_layers()` method

The engine separates edges from shading by dilating the edge mask and zeroing out shading near edges:

```
Edge detection → Dilate (2×2, 1 iteration) → Edge layer
Shade layer → Dilate edges again (3×3, 2 iterations) → Zero shade near edges
```

This creates a **5–7 pixel dead zone** around every outline where no shading exists. The result is a visible white halo around every line — the most prominent cause of the patchy look.

**Visual:**
```
  Original:        Current Engine:        What We Want:
  ┌──────────┐     ┌──────────┐          ┌──────────┐
  │▓▓▓▓██▓▓▓▓│     │▓▓▓░░██░░▓│          │▓▓▓▓██▓▓▓▓│
  │▓▓▓▓██▓▓▓▓│     │▓▓▓░░██░░▓│          │▓▓▓▓██▓▓▓▓│
  │▓▓▓▓██▓▓▓▓│     │▓▓▓░░██░░▓│          │▓▓▓▓██▓▓▓▓│
  └──────────┘     └──────────┘          └──────────┘
   (shading meets    (white gap around     (shading meets
    edges cleanly)    every edge)           edges cleanly)
```

---

### Cause 2: Hard Stroke Termination — CRITICAL

**Location:** `_generate_hatching_lines()` method

When a hatching line crosses from a dark area to a light area, the stroke **instantly terminates**. No fade-out, no pressure taper — just a hard stop. Every intensity boundary becomes a visible edge in the shading.

Also, strokes with ≤ 2 points are discarded entirely, leaving gaps in narrow shaded regions.

---

### Cause 3: Single-Pixel Intensity Sampling — HIGH

**Location:** `_generate_hatching_lines()` method

Each hatching point samples intensity from exactly one pixel:
```python
intensity = intensity_map[iy, ix]
```

This means:
- Pixel-level noise in the image creates noisy stroke widths
- A gentle gradient in the original becomes a hard step in the shading
- Individual "hot pixels" can cause erratic strokes

---

### Cause 4: Hard Phase Thresholds — HIGH

**Location:** `_build_shading_strokes()` method

Three distinct shading layers activate at hard thresholds:

| Layer | Activates at Intensity | What Happens |
|-------|----------------------|--------------|
| HATCHING | ≥ 0.10 | First layer of parallel lines |
| CROSS_HATCHING | ≥ 0.35 | Second layer at different angle |
| DETAIL | ≥ 0.60 | Third dense layer |

At each threshold boundary, shading density **doubles** (one layer → two layers). This creates visible contour lines in the output where density suddenly changes.

---

### Cause 5: Sequential Phase Execution — HIGH

**Location:** `_merge_sequences()` method

The animation reveals ALL outlines → then ALL hatching → then ALL cross-hatching → then ALL detail. Each phase transition is a jarring visual shift. The user wants shading to build up naturally alongside the drawing — not as separate "waves."

---

### Cause 6: Mechanical Regularity — MEDIUM

**Location:** `_generate_hatching_lines()` method

- All lines are exactly the same spacing apart (zero jitter)
- All lines are at the exact same angle (zero rotation variation)
- All lines are perfectly straight (zero curvature)
- Fixed 1.5px sampling step along every line

Real pencil hatching has natural variation in all of these.

---

### Cause 7: Grid Sorting Boundaries — MEDIUM

**Location:** `_build_outline_strokes()` method

A 4×5 grid divides the canvas for stroke sorting. Each grid cell is drawn completely before the next, creating visible rectangular boundaries during animation.

---

## 3. Root Cause Analysis: Manual Tuning Required

### Why Auto-Detection Isn't Enough

The engine's `_analyze_complexity()` already computes useful metrics:
- Edge coverage percentage
- Shade coverage percentage  
- Gradient coverage percentage
- High gradient coverage percentage

But **none of these are used to adjust engine parameters**. They're only printed and discarded.

### What Differs Per Image

| Image Property | What Needs to Change | Currently |
|---------------|---------------------|-----------|
| **Average brightness** | `white_threshold` (what counts as "paper") | Fixed at 240 |
| **Contrast range** | `edge_threshold_base` (edge detection sensitivity) | Fixed at 0.15 |
| **Edge density** | `stroke_spacing`, dilation kernel sizes | Fixed |
| **Shade coverage** | Phase activation thresholds (0.10/0.35/0.60) | Fixed |
| **Image resolution** | All pixel-based parameters | Fixed (absolute pixels) |
| **Subject orientation** | `hatching_angle`, `cross_hatch_angle` | Fixed per-run |

---

## 4. Fix 1 — Feathered Edge Exclusion (Remove White Halos)

### The Problem
Binary zeroing of shade intensity near edges creates white halos.

### The Fix
Replace the hard edge mask with a **distance-based feather** that smoothly transitions shading to zero near edges:

```python
# In _decompose_layers(), replace the hard exclusion with:

# Compute distance from each pixel to the nearest edge
edge_binary = self.edge_layer.astype(np.uint8) * 255
inv_edge = cv2.bitwise_not(edge_binary)
edge_distance = cv2.distanceTransform(inv_edge, cv2.DIST_L2, 5)

# Create smooth falloff: 0 at edge, 1.0 at feather_width pixels away
feather_width = 4.0  # adjustable
edge_weight = np.clip(edge_distance / feather_width, 0.0, 1.0)

# Apply smooth weighting instead of binary zeroing
shade_intensity = shade_intensity * edge_weight
```

### Visual Result
Shading gradually fades as it approaches edges instead of hitting a hard wall. The white halos disappear entirely.

### Impact: ⭐⭐⭐⭐⭐ (eliminates the most visible artifact)

---

## 5. Fix 2 — Tapered Stroke Endpoints (Smooth Start/Stop)

### The Problem
Strokes start and stop at full pressure/width, creating hard endpoints at every intensity boundary.

### The Fix
Apply a pressure/width taper to the first and last N points of every stroke:

```python
def _taper_stroke(self, stroke, taper_pixels=8):
    """Apply pressure taper to start and end of stroke."""
    taper_length = min(taper_pixels, len(stroke) // 3)
    if taper_length < 1:
        return stroke
    
    for j in range(taper_length):
        t = j / taper_length
        # Fade in at start
        stroke[j].pressure *= t
        stroke[j].width *= (0.5 + 0.5 * t)
        # Fade out at end
        stroke[-(j + 1)].pressure *= t
        stroke[-(j + 1)].width *= (0.5 + 0.5 * t)
    
    return stroke
```

Additionally, when a stroke would terminate due to low intensity, **overshoot by 2–4 pixels** with declining pressure instead of stopping immediately:

```python
# When intensity drops below threshold, don't stop immediately
# Enter fade-out mode for a few extra pixels
fade_out_remaining = 4
fade_out_pressure = last_good_pressure
...
```

### Impact: ⭐⭐⭐⭐⭐ (eliminates hard shading boundaries)

---

## 6. Fix 3 — Smoothed Intensity Sampling (No Pixel Noise)

### The Problem
Intensity sampled at individual pixels creates noisy strokes.

### The Fix (Option A: Pre-blur)
Pre-blur the intensity map before hatching generation:

```python
# In _build_shading_strokes(), before generating hatching lines:
smoothed_intensity = cv2.GaussianBlur(intensity_map, (5, 5), 1.5)
```

### The Fix (Option B: Perpendicular sampling)
Sample intensity as an average of pixels perpendicular to the stroke direction:

```python
# Sample 5 pixels perpendicular to stroke direction
perp_dx, perp_dy = -dy, dx  # perpendicular to stroke angle
intensity = 0
for k in range(-2, 3):
    sx = ix + int(k * perp_dx)
    sy = iy + int(k * perp_dy)
    if 0 <= sx < w and 0 <= sy < h:
        intensity += intensity_map[sy, sx]
intensity /= 5
```

**Recommendation:** Option A is simpler and faster. Use a small kernel (5×5 or 7×7) — just enough to smooth pixel noise without destroying structure.

### Impact: ⭐⭐⭐⭐ (removes stroke-level noise and softens boundaries)

---

## 7. Fix 4 — Natural Hand Wobble (Organic Spacing/Angle)

### The Problem
Machine-perfect spacing, angle, and straightness look artificial.

### The Fix
Add controlled randomness using a seeded RNG (reproducible results):

```python
rng = np.random.RandomState(42)

# Per-line jitter
for line_idx in range(num_lines):
    # Spacing jitter: ±20%
    jitter = 1.0 + rng.uniform(-0.20, 0.20)
    offset = start_offset + line_idx * spacing * jitter
    
    # Angle jitter: ±2 degrees
    line_angle = angle + rng.uniform(-0.035, 0.035)  # ±2° in radians
    
    # Per-point wobble (perpendicular displacement)
    for each sample point:
        wobble = rng.normal(0, 0.4)  # sub-pixel perpendicular noise
        x += perp_dx * wobble
        y += perp_dy * wobble
```

### Parameters to jitter:

| Property | Jitter Amount | Effect |
|----------|---------------|--------|
| Line spacing | ±20% | Breaks mechanical regularity |
| Line angle | ±2° | Lines aren't perfectly parallel |
| Line straightness | Gaussian wobble σ=0.4px | Micro-curvature |
| Starting position | ±1px along line | Lines don't all share the same grid |

### Impact: ⭐⭐⭐ (transforms mechanical to organic look)

---

## 8. Fix 5 — Soft Phase Thresholds (No Hard Boundaries)

### The Problem
Cross-hatching activates at exactly intensity=0.35. Detail at exactly 0.60. These create visible contour lines.

### The Fix
Use a **sigmoid function** for soft activation:

```python
import math

def soft_threshold(intensity, threshold, steepness=15.0):
    """Smooth probability of layer activation."""
    return 1.0 / (1.0 + math.exp(-steepness * (intensity - threshold)))

# For cross-hatching:
# Instead of: if intensity > 0.35: include
# Do:         probability = soft_threshold(intensity, 0.35)
#             if random() < probability: include
```

At the boundary:
- intensity 0.30 → 32% chance of cross-hatching
- intensity 0.35 → 50% chance
- intensity 0.40 → 68% chance
- intensity 0.50 → 90% chance

This creates a gradual density transition instead of a sharp line.

### Impact: ⭐⭐⭐⭐ (eliminates visible contour artifacts between shading layers)

---

## 9. Fix 6 — Zone-Interleaved Drawing (No Phase Gaps)

### The Problem
All outlines → all hatching → all cross-hatching creates visible "waves" of content.

### The Fix
Instead of drawing phases sequentially, divide the canvas into spatial zones and **interleave all phases within each zone**:

```python
def _merge_sequences_interleaved(self):
    """Interleave phases within spatial zones."""
    zone_size = 80  # pixels
    zones = defaultdict(lambda: defaultdict(list))
    
    # Bucket strokes by zone AND phase
    for phase, strokes in self.stroke_sequences.items():
        for point in strokes:
            zx = int(point.x // zone_size)
            zy = int(point.y // zone_size)
            zones[(zy, zx)][phase].append(point)
    
    # Traverse zones in serpentine order
    self.reveal_sequence = []
    for zone_key in sorted(zones.keys(), 
                           key=lambda k: (k[0], k[1] if k[0]%2==0 else -k[1])):
        zone = zones[zone_key]
        
        # Within each zone: outline → hatching → cross-hatching → detail
        for phase in [OUTLINE, HATCHING, CROSS_HATCHING, DETAIL_SHADING]:
            if phase in zone:
                self.reveal_sequence.extend(zone[phase])
```

### What the user sees:
Instead of:
```
[All outlines everywhere] → [All hatching everywhere] → [All cross-hatch everywhere]
```

They see:
```
[Zone 1: outline→hatch→crosshatch] → [Zone 2: outline→hatch→crosshatch] → ...
```

Each area of the image gets fully "finished" before moving to the next area — exactly like how a real artist works on one section at a time.

### The Key: This Is "One Go" Drawing

This satisfies the user's requirement of **"everything should happen while drawing, in one go"** — because from any viewer's perspective, each area is drawn completely (lines + shading) as the pen passes through it. There are no separate "shading passes" visible.

### Impact: ⭐⭐⭐⭐⭐ (transforms the animation from mechanical to artistic)

---

## 10. Fix 7 — Resolution-Aware Scaling

### The Problem
All pixel-based parameters are absolute values that don't scale with image size.

### The Fix
Compute a scale factor from the image resolution and apply it to all pixel-based parameters:

```python
def _compute_scale(self):
    """Compute resolution-based scale factor."""
    ref_size = 1080  # reference height for which defaults were tuned
    actual_size = max(self.target_height, self.target_width)
    self.scale = actual_size / ref_size
    
    # Apply scaling
    self.stroke_spacing = max(1, round(self.stroke_spacing * self.scale))
    self.pen_lift_threshold = 15.0 * self.scale
    self.hatching_step = 1.5 * self.scale
    self.dilation_size = max(1, round(2 * self.scale))
    self.edge_exclusion_feather = 4.0 * self.scale
```

### Impact: ⭐⭐⭐ (images of any size get consistent results)

---

## 11. Fix 8 — Auto-Tuner (Automated Settings)

### The Problem
Users must manually adjust 6+ settings per image.

### The Fix
Add an optional auto-tune step that analyzes the image and sets parameters:

```python
def _auto_tune(self):
    """Analyze image and set optimal parameters automatically."""
    gray = self.grayscale
    
    # ─── Brightness Analysis ───
    mean_bright = np.mean(gray)
    p5, p50, p95 = np.percentile(gray, [5, 50, 95])
    dynamic_range = p95 - p5
    
    # Auto white_threshold: use 95th percentile
    self.white_threshold = int(min(250, p95))
    
    # Auto edge_threshold: scale by contrast
    self.edge_threshold_base = np.clip(dynamic_range / 255 * 0.3, 0.05, 0.4)
    
    # ─── Content Analysis ───
    content_mask = gray < self.white_threshold
    content_ratio = np.mean(content_mask)
    
    edges = cv2.Canny(gray, 50, 150)
    edge_ratio = np.sum(edges > 0) / gray.size
    
    dark_ratio = np.mean(gray < 128)
    
    # ─── Auto Spacing ───
    if content_ratio < 0.1:        # Very light / line art
        self.stroke_spacing = max(2, int(4 * self.scale))
    elif dark_ratio > 0.3:         # Heavy shading
        self.stroke_spacing = max(1, int(2 * self.scale))
    else:                          # Moderate
        self.stroke_spacing = max(1, int(3 * self.scale))
    
    # ─── Auto Hatching Angle ───
    # Find dominant gradient direction
    gx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=5)
    gy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=5)
    magnitudes = np.sqrt(gx**2 + gy**2)
    strong = magnitudes > np.percentile(magnitudes, 75)
    if np.any(strong):
        angles = np.arctan2(gy[strong], gx[strong])
        dominant = np.average(angles, weights=magnitudes[strong])
        # Hatch perpendicular to dominant gradient
        self.hatching_angle = dominant + math.pi / 2
        self.cross_hatch_angle = self.hatching_angle + math.pi / 2
    
    # ─── Auto Phase Thresholds ───
    if content_ratio > 0:
        content_values = gray[content_mask]
        inv_content = 1.0 - content_values / 255.0
        p33 = np.percentile(inv_content, 33)
        p66 = np.percentile(inv_content, 66)
        self.crosshatch_threshold = p33
        self.detail_threshold = p66
```

### Activation
The auto-tuner should be **optional** (checkbox in UI), so users who prefer manual control can keep their settings. When enabled, it runs after image loading and overrides the relevant parameters.

### Impact: ⭐⭐⭐⭐ (eliminates the need for per-image manual tuning)

---

## 12. Implementation Priority

Ordered by impact on the user's two main complaints:

### Phase 1: Critical Fixes (Eliminate Patches)

| Priority | Fix | Addresses | Effort |
|----------|-----|-----------|--------|
| **1** | Fix 1: Feathered Edge Exclusion | White halos around lines | Low |
| **2** | Fix 2: Tapered Stroke Endpoints | Hard shading boundaries | Medium |
| **3** | Fix 6: Zone-Interleaved Drawing | Phase transition "waves" | Medium |

These three fixes together eliminate the three most visible sources of patchiness. They should be implemented first.

### Phase 2: Refinement (Improve Quality)

| Priority | Fix | Addresses | Effort |
|----------|-----|-----------|--------|
| **4** | Fix 3: Smoothed Intensity Sampling | Noisy strokes | Low |
| **5** | Fix 5: Soft Phase Thresholds | Contour lines at thresholds | Low |
| **6** | Fix 4: Natural Hand Wobble | Mechanical appearance | Low |

### Phase 3: Automation (Reduce Manual Work)

| Priority | Fix | Addresses | Effort |
|----------|-----|-----------|--------|
| **7** | Fix 7: Resolution-Aware Scaling | Parameter scaling for different sizes | Low |
| **8** | Fix 8: Auto-Tuner | Manual setting adjustment | Medium |

---

## 13. Design Principle: One Continuous Flow

The user's key requirement: **"everything should happen while drawing, in one go."**

The V2 engine should feel like watching a single artist work — not like watching an algorithm run through phases. This means:

1. **No visible phase transitions** — use zone-interleaved drawing (Fix 6) so each area gets completely finished before moving on.

2. **No "shading appears separately from lines"** — within each zone, outlines and shading should appear together, building up naturally.

3. **No mechanical patterns** — jittered spacing, angle, and curvature (Fix 4) make every stroke look hand-drawn.

4. **No sudden density changes** — soft thresholds (Fix 5) and tapered endpoints (Fix 2) create smooth gradients.

5. **No white gaps** — feathered edge exclusion (Fix 1) ensures shading meets lines seamlessly.

The result: the animation looks like a human artist sketching with a pencil, working section by section, building up darkness naturally as they go.
