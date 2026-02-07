# Pencil Shading Engine (Engine 2) — Tuning Guide

A comprehensive guide to adjusting the Pencil Shading Engine settings for different types of artwork. This engine is designed for complex shaded images — portraits, landscapes, and any artwork with gradients, textures, and shadows.

---

## Table of Contents

1. [Quick Start — Common Presets](#1-quick-start--common-presets)
2. [How the Engine Works](#2-how-the-engine-works)
3. [Parameter Reference](#3-parameter-reference)
4. [Tuning for Different Art Styles](#4-tuning-for-different-art-styles)
5. [Understanding the Drawing Phases](#5-understanding-the-drawing-phases)
6. [Parameter Interactions](#6-parameter-interactions)
7. [Troubleshooting](#7-troubleshooting)
8. [Advanced: Hidden Parameters](#8-advanced-hidden-parameters)

---

## 1. Quick Start — Common Presets

Don't want to read the whole guide? Here are recommended settings for common art types:

### 🖼️ Portraits (Faces, People)

| Setting | Value | Why |
|---------|-------|-----|
| Hatching Angle | **45°** | Classic diagonal shading natural for facial features |
| Stroke Spacing | **2–3** | Moderate density for smooth skin tones |
| Edge Phases First | **1** | Sketch outline first, then fill shading |
| Shading Order | **Top to Bottom** | Natural top-down reveal |
| Force Shading | **On** | Ensures shading engine is used even for lighter portraits |

### 🏔️ Landscapes (Nature, Buildings)

| Setting | Value | Why |
|---------|-------|-----|
| Hatching Angle | **30°** | Slightly flatter angle suggests horizontal planes |
| Stroke Spacing | **3–4** | Looser spacing for atmospheric effect |
| Edge Phases First | **2** | Shows basic form early |
| Shading Order | **Top to Bottom** | Sky→horizon→ground reveal |
| Force Shading | **On** | Landscapes often have subtle shading |

### ✏️ Manga / Anime (Clean Lines + Screentones)

| Setting | Value | Why |
|---------|-------|-----|
| Hatching Angle | **45°** | Matches traditional screentone direction |
| Stroke Spacing | **2** | Dense for solid black fills |
| Edge Phases First | **1** | Clean linework first |
| Shading Order | **Natural** | Natural sweep-based fill |
| Force Shading | **On** | Usually has some flat fills |

### 🐾 Simple Line Art (Coloring Pages, Logos)

| Setting | Value | Why |
|---------|-------|-----|
| Hatching Angle | **45°** | Doesn't matter much for line art |
| Stroke Spacing | **3** | Default is fine |
| Edge Phases First | **1** | All focus on outlines |
| Shading Order | **Top to Bottom** | Predictable reveal |
| Force Shading | **Off** | Let auto-detect choose Engine 1 (Pixel Reveal) |

### 🎨 Heavy Shading / Dark Art (High Contrast)

| Setting | Value | Why |
|---------|-------|-----|
| Hatching Angle | **60°** | Steep angle for dramatic shadows |
| Stroke Spacing | **1–2** | Maximum density for deep blacks |
| Edge Phases First | **1** | Outline first for structure |
| Shading Order | **Top to Bottom** | Systematic coverage |
| Force Shading | **On** | Must use shading engine |

---

## 2. How the Engine Works

The Pencil Shading Engine simulates how a real artist draws with pencils. It processes your image through these stages:

### Processing Pipeline

```
Your Image
    ↓
Step 1: Load & Preprocess
    → Convert to grayscale
    → Build intensity map (how dark each pixel is)
    → Create binary mask (what counts as "ink" vs "paper")
    ↓
Step 2: Analyze Complexity
    → Count edges, shade areas, gradient coverage
    → Determine what kind of artwork this is
    ↓
Step 3: Decompose into Layers
    → Edge Layer: outlines and boundaries (detected via Canny)
    → Shade Layer: everything that's shading (dark pixels minus edges)
    ↓
Step 4: Generate Strokes
    → OUTLINE strokes: follow skeleton of edges
    → HATCHING strokes: parallel lines across shaded areas
    → CROSS-HATCHING strokes: second pass at different angle for darker areas
    → DETAIL strokes: fine dense hatching for the darkest regions
    ↓
Step 5: Order Strokes for Animation
    → Apply edge_phases_first to decide what draws first
    → Apply shading_order to sort the shading strokes
    ↓
Step 6: Animate
    → Reveal strokes progressively with soft brush compositing
```

### The Key Concept: Layer-Based Shading

The engine splits your image into darkness zones. Each zone gets a different amount of hatching:

| Pixel Darkness | Hatching Layers | Visual Result |
|----------------|-----------------|---------------|
| **Very light** (< 10% dark) | None | Stays white/near-white |
| **Light** (10%–35% dark) | 1 layer (HATCHING only) | Light pencil texture |
| **Medium** (35%–60% dark) | 2 layers (HATCHING + CROSS_HATCHING) | Cross-hatched shading |
| **Dark** (> 60% dark) | 3 layers (all three) | Dense, dark fill |

This mimics how real artists build up pencil darkness by layering hatching in different directions.

---

## 3. Parameter Reference

### 3.1 Hatching Angle

**What it does:** Sets the direction of the primary hatching strokes (in degrees).

```
0°  = Horizontal strokes (←→)
45° = Diagonal strokes (↗↙)  ← Default
90° = Vertical strokes (↑↓)
```

**Visual impact:**

| Angle | Best for | Effect |
|-------|----------|--------|
| **0°** | Horizons, water, flat surfaces | Calm, horizontal energy |
| **15–30°** | Landscapes, backgrounds | Gentle, natural slope |
| **45°** | Portraits, general purpose | Classic pencil shading look |
| **60–75°** | Dramatic lighting, tall subjects | Steep, dynamic energy |
| **90°** | Rain, waterfalls, vertical subjects | Strong vertical emphasis |

**Important:** The cross-hatching angle is always fixed at -45°, regardless of the hatching angle you set. The detail shading angle is automatically set to `hatching_angle + 22.5°`.

**Recommendation:** Start with 45° and only change if the art style suggests a different direction.

---

### 3.2 Stroke Spacing

**What it does:** Controls the distance (in pixels) between parallel hatching lines.

```
1px = Very dense (tight parallel lines, dark fills, slow)
3px = Default (balanced density and speed)
10px = Very sparse (visible individual lines, light fills, fast)
```

**Visual impact:**

| Spacing | Density | Speed | Best for |
|---------|---------|-------|----------|
| **1** | Maximum | Slowest | Heavy shadows, solid black areas |
| **2** | High | Slow | Dark portraits, detailed shading |
| **3** | Balanced | Normal | General purpose ← **Default** |
| **4–5** | Moderate | Fast | Light shading, large images |
| **6–10** | Sparse | Fastest | Sketch-like, light pencil look |

**Performance note:** Spacing directly controls how many strokes are generated. Cutting spacing in half roughly **doubles** the total stroke count and processing time. For a typical 1000px image:

| Spacing | Approx. Hatching Lines | Total Points |
|---------|----------------------|--------------|
| 1 | ~1000 | Very high |
| 3 | ~333 | Moderate |
| 5 | ~200 | Low |
| 10 | ~100 | Very low |

**Also affects layer spacing:**
- HATCHING: uses your spacing value directly
- CROSS_HATCHING: uses spacing + 1px (slightly wider)
- DETAIL_SHADING: uses spacing - 1px (slightly tighter, min 1)

**Recommendation:** Use 2–3 for most artwork. Only go to 1 for very dark, heavily shaded pieces. Use 5+ for quick previews.

---

### 3.3 Edge Phases First

**What it does:** Controls how many drawing phases are classified as "edge" phases (drawn FIRST) before any shading begins.

| Value | Drawn First (Edge Phases) | Drawn After (Shading Phases) |
|-------|---------------------------|------------------------------|
| **1** | OUTLINE only | HATCHING → CROSS_HATCHING → DETAIL |
| **2** | OUTLINE + HATCHING | CROSS_HATCHING → DETAIL |
| **3** | OUTLINE + HATCHING + CROSS_HATCHING | DETAIL only |

**Visual effect on animation:**

- **1 (default):** The drawing starts with just the outline sketch. Then all shading fills in. This creates a clear "sketch → shade" artistic flow, like watching an artist draw in real time.

- **2:** The outline AND basic hatching appear first, giving the image basic form early. Then only cross-hatching and detail fill in. This looks like a faster progression — the image is recognizable sooner.

- **3:** Almost everything appears as "early structure" — only the darkest detail shading is saved for last. The image looks nearly complete early, with a final darkening pass at the end.

**Recommendation:** Use **1** for the most natural drawing experience. Use **2** if you want the image to "come together" faster. Use **3** only if you want a very quick reveal with minimal suspense.

---

### 3.4 Shading Order

**What it does:** Controls the spatial order in which shading strokes are revealed during animation.

| Mode | Behavior | Best for |
|------|----------|----------|
| **Top to Bottom** | Shading fills from top of image downward | Predictable, systematic reveal |
| **Natural** | Strokes appear in the order generated (sweep pattern) | Looks like an artist's hand sweeping across the page |
| **Random** | Shading appears at random positions | Organic, scattered reveal |

**Important:** This setting only affects the **shading phases** — the ones NOT classified as edge phases by the `Edge Phases First` setting. Edge phases always draw in their natural skeleton order.

**Recommendation:** 
- **Top to Bottom** is the safest choice for most artwork
- **Natural** creates the most "human artist" feel — try this if the drawing feels too mechanical
- **Random** is experimental — interesting for abstract effects but can look chaotic

---

### 3.5 Force Shading Engine

**What it does:** Overrides the automatic engine detection to always use the Pencil Shading Engine.

**When auto-detection works:**

The system automatically analyzes your image:
- **Simple line art** (< 10% shading, < 5% gradients) → Uses **Engine 1** (Pixel Reveal)
- **Shaded artwork** (> 10% shading or > 5% gradients) → Uses **Engine 2** (Pencil Shading)
- **Complex gradients** (> 8% high gradients + > 10% deep darks) → Uses **Engine 3** (Advanced Gradient)

**When to use Force Shading:**
- Your image is mostly line art but has some light shading you want the engine to draw
- Auto-detection keeps choosing Engine 1 but you prefer the hatching effect
- Testing/comparing engine output

**Note:** This only has effect when `Engine Type` is set to "Auto" in the control panel. If you explicitly select an engine type, Force Shading is ignored.

---

### 3.6 Shading Sensitivity

> ⚠️ **Important Note:** In the current implementation, this parameter is stored but **not actively used** by the internal algorithms. The engine uses fixed internal thresholds for layer decomposition. This parameter is available for future fine-tuning or if you have a modified engine version that utilizes it.

---

## 4. Tuning for Different Art Styles

### 4.1 Pencil Sketches (Hand-drawn, Loose Style)

**Characteristics:** Visible pencil strokes, varied line weight, expressive marks.

```
Hatching Angle:    45°
Stroke Spacing:    3–4  (visible individual strokes)
Edge Phases First: 1    (outline sketch first)
Shading Order:     Natural  (organic stroke flow)
```

**Why:** Wider spacing preserves the sketch-like quality. Natural order mimics hand-drawn flow.

---

### 4.2 Academic/Fine Art Pencil Drawings

**Characteristics:** Smooth gradients, controlled hatching, rich tonal range.

```
Hatching Angle:    45°
Stroke Spacing:    2    (dense for smooth tones)
Edge Phases First: 1    (structure first)
Shading Order:     Top to Bottom  (systematic build-up)
```

**Why:** Dense spacing creates the illusion of continuous tone. Systematic ordering gives a polished, professional look.

---

### 4.3 Charcoal / Very Dark Art

**Characteristics:** Heavy blacks, strong contrast, minimal white space.

```
Hatching Angle:    60°
Stroke Spacing:    1    (maximum density)
Edge Phases First: 1    (define structure first)
Shading Order:     Top to Bottom
```

**Why:** Spacing of 1 allows maximum darkness buildup. Steep angle gives dramatic weight. Be aware this will be **slow** due to high stroke count.

---

### 4.4 Light Pencil / Delicate Illustration

**Characteristics:** Minimal shading, fine lines, lots of white space.

```
Hatching Angle:    30°
Stroke Spacing:    5–6  (light, airy strokes)
Edge Phases First: 1
Shading Order:     Natural
Force Shading:     On  (ensure shading engine is used)
```

**Why:** Wide spacing keeps the delicate feel. Shallow angle is unobtrusive. Force Shading prevents auto-detect from switching to Engine 1.

---

### 4.5 Manga / Comic Book Art

**Characteristics:** Bold outlines, flat fills, screentone patterns.

```
Hatching Angle:    45°
Stroke Spacing:    2    (dense for flat fills)
Edge Phases First: 2    (show outlines + first shading early)
Shading Order:     Natural
Force Shading:     On
```

**Why:** Dense spacing fills screentone areas well. Edge Phases First = 2 makes the linework appear quickly with basic fills, then cross-hatching adds depth.

---

### 4.6 Technical/Architectural Drawing

**Characteristics:** Precise lines, minimal shading, cross-hatching for depth.

```
Hatching Angle:    0° or 90°  (match drafting convention)
Stroke Spacing:    3
Edge Phases First: 3    (almost everything as structure)
Shading Order:     Top to Bottom
```

**Why:** Horizontal/vertical angles match technical drawing conventions. Edge Phases First = 3 treats most content as structural, only adding fine detail shading at the end.

---

## 5. Understanding the Drawing Phases

### Phase Timeline

When the animation plays, the engine draws in this order:

```
Timeline: ─────────────────────────────────────────────────────→
          │  Edge Phases  │        Shading Phases        │
          │               │                              │
          ├── OUTLINE ────┤── HATCHING ── CROSS ── DETAIL ──┤
          │               │                              │
Speed:    │  Slow (8/f)   │  Med (20) │ Med (25) │Slow(5)│
          │  Deliberate   │  Filling  │  Deeper  │ Fine  │
```

### What Each Phase Draws

**OUTLINE (Phase 1)**
- Traces the skeleton of detected edges
- Uses sinusoidal pressure variation (0.4–1.0) for natural line weight
- Points are ordered to minimize pen "jumps" using grid-based spatial clustering
- This is always drawn first, regardless of settings

**HATCHING (Phase 2)**
- Parallel lines at the configured hatching angle
- Only drawn in areas with darkness ≥ 10%
- Stroke width: 1.5–3.5px (proportional to local darkness)
- Pressure: 0.3–0.8 (proportional to darkness)
- Points sampled every 1.5px along each line

**CROSS_HATCHING (Phase 3)**
- Second set of parallel lines at -45° (fixed angle)
- Only drawn in areas with darkness ≥ 35%
- Spacing is 1px wider than primary hatching
- Creates the characteristic diamond pattern of cross-hatching

**DETAIL_SHADING (Phase 4)**
- Third layer of hatching at hatching_angle + 22.5°
- Only drawn in areas with darkness ≥ 60%
- Spacing is 1px tighter than primary hatching (denser)
- Creates very dense, dark fill for shadow areas

**BLENDING (Phase 5)**
- Currently **not implemented** — reserved for future use
- Would smooth transitions between shading areas

---

## 6. Parameter Interactions

Understanding how parameters affect each other:

### Spacing × Art Darkness

| | Light Art | Medium Art | Dark Art |
|---|---|---|---|
| **Spacing 1** | Over-filled, too dark | Dense but good | ✅ Ideal — rich blacks |
| **Spacing 3** | ✅ Ideal — visible strokes | ✅ Good balance | Slightly sparse |
| **Spacing 5+** | ✅ Nice sketch feel | Visible gaps | Too sparse |

### Edge Phases First × Shading Order

| | Top to Bottom | Natural | Random |
|---|---|---|---|
| **EPF = 1** | Clean outline → systematic fill | Clean outline → sweep fill | Clean outline → scattered fill |
| **EPF = 2** | Quick form → detail fill | Quick form → sweep detail | Quick form → random detail |
| **EPF = 3** | Nearly complete → last details | Nearly complete → natural details | Nearly complete → random details |

### Hatching Angle × Cross-Hatch Angle (fixed -45°)

The angle between your hatching and the cross-hatch determines the diamond pattern:

| Hatching Angle | Angle Between | Visual Effect |
|----------------|---------------|---------------|
| **0°** | 45° | Tilted diamond pattern |
| **45°** | 90° | **Perfect** right-angle cross-hatch (most natural) |
| **90°** | 45° | Tilted diamond (same as 0°) |

**Recommendation:** 45° hatching angle produces the cleanest cross-hatching since it's perpendicular to the fixed -45° cross-hatch.

---

## 7. Troubleshooting

### "The shading looks too light / barely visible"

**Cause:** Stroke spacing too wide, or image is light with few dark areas.

**Fix:**
- Reduce stroke spacing to 1–2
- Ensure Force Shading is ON
- Try a darker image or increase contrast before feeding to the engine

---

### "The animation takes too long / too many strokes"

**Cause:** Stroke spacing too small for a large, dark image.

**Fix:**
- Increase stroke spacing to 4–6
- Use a smaller image resolution
- Set Edge Phases First to 3 (less shading content)

---

### "The hatching direction looks wrong for my image"

**Cause:** Default 45° angle doesn't suit the subject.

**Fix:**
- Match the angle to the dominant lines in your artwork
- Use 0° for horizontal subjects, 90° for vertical, 45° for general

---

### "The drawing looks too mechanical / artificial"

**Cause:** Systematic ordering makes it feel robotic.

**Fix:**
- Set Shading Order to "Natural" or "Random"
- This introduces more organic variation in how shading appears

---

### "Only outlines appear, no shading"

**Cause:** The image may be too light for shading detection, or auto-detect chose Engine 1.

**Fix:**
- Enable Force Shading Engine
- Or explicitly select "Pencil Shading" as the Engine Type
- Check that the image has areas darker than ~25% gray (pixel value < 190)

---

### "The shading fills in the wrong order"

**Cause:** Shading Order or Edge Phases First doesn't match your expectation.

**Fix:**
- Edge Phases First = 1 ensures outlines draw completely before any shading
- Shading Order = "Top to Bottom" for predictable, top-down fill
- If you want outlines and basic shading together: set Edge Phases First = 2

---

### "Cross-hatching appears in areas that should be light"

**Cause:** The engine's internal darkness threshold for cross-hatching is 35%.

**Fix:** This threshold isn't exposed in the UI. If cross-hatching appears in areas you consider "light," your image likely has pixels in the 35–60% darkness range that you perceive as light. Consider:
- Adjusting the image's brightness/contrast before processing
- Using wider stroke spacing to make cross-hatching less dense
- Using Engine 1 (Pixel Reveal) if the image is predominantly line art

---

## 8. Advanced: Hidden Parameters

These parameters exist in the engine code but are **not exposed** in the UI or CLI. They're documented here for developers or advanced users who want to modify the engine source code.

| Parameter | Default | Location in Code | What It Controls |
|-----------|---------|------------------|------------------|
| `cross_hatch_angle` | -45° | Constructor | Angle for cross-hatching (always -45°) |
| `edge_threshold_base` | 0.15 | Constructor | Canny edge detection sensitivity |
| `white_threshold` | 240 | Constructor | Pixel gray value threshold for "paper" |
| `brush_softness` | 0.6 | Instance variable | Gaussian softness of the drawing brush |
| `pen_lift_threshold` | 15.0px | Local constant | Max distance before pen "lifts" |
| `step_size` | 1.5px | Local constant | Sampling distance along hatching lines |
| `intensity_thresholds` | 0.1 / 0.35 / 0.6 | Hardcoded | Darkness levels triggering each hatching layer |
| `speed_config` | 8/20/25/5/40 | SpeedConfig | Points-per-update for each phase |
| `stroke_width` | 1.5 + 2.0 × intensity | Formula | Width varies by local pixel darkness |
| `dilation_kernel` | 3×3, 2 iterations | Local | How much edge mask is expanded before shade extraction |

### How to Modify Hidden Parameters

To change these, edit `engines/pencil_shading/engine.py`:

**Brush softness** (softer = more diffuse marks):
```python
# Line ~196: Change 0.6 to desired value (0.0 = hard, 1.0 = very soft)
self.brush_softness = 0.6
```

**Cross-hatch angle** (make it perpendicular to hatching):
```python
# Line ~112: Change -45.0 to match your hatching angle + 90
self.cross_hatch_angle = -45.0  
```

**Intensity thresholds** (change when cross-hatch/detail kick in):
```python
# Search for 0.35 and 0.6 in the shading stroke generation section
# Lower values = more layers in lighter areas
# Higher values = fewer layers, only in the darkest areas
```

---

## Summary: Most Important Settings

If you only adjust a few things, focus on these:

1. **Stroke Spacing** — This has the biggest impact on both visual quality and performance. Start with 3 and adjust.

2. **Hatching Angle** — Set to match your artwork's dominant direction. 45° is the safe default.

3. **Edge Phases First** — Controls the animation pacing between "sketch" and "shade" phases.

4. **Force Shading** — Enable if your image is light but you still want hatching-style reveal.

Everything else can stay at defaults for most artwork.
