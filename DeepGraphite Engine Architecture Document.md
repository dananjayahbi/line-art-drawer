# DeepGraphite Engine: Architecture Document

## 1. Executive Summary

The DeepGraphite Engine is a stroke-based rendering system designed to simulate high-fidelity pencil artistry. Unlike the previous engine which used algorithmic hatching (Canny edges + math-based lines), DeepGraphite utilizes **Stroke-Based Rendering (SBR)** powered by computer vision.

It treats the input image not as a collection of pixels, but as a "target state" that an AI agent attempts to reconstruct using a dictionary of virtual pencil brushes.

## 2. Hardware Utilization Strategy

- **CPU (i7):** Orchestration, file I/O, and sequence management.
- **GPU (GTX 1660ti - 6GB VRAM):** This is the workhorse. It will be used for:
    - **Tensor Flow Field calculation:** Calculating the direction of strokes.
    - **Differentiable Rendering:** Rapidly testing thousands of stroke positions.
    - **Neural Inference:** Running saliency detection to know "where to look."

## 3. Core Philosophy: The "Layered Painter" Model

To solve the "ugly version" and "patchy" issues, this engine mimics a human workflow strictly:

1. **Global Structure:** Very faint, loose sketching.
2. **Block-in:** Large, soft side-shading to establish value.
3. **Refinement:** Directional strokes following the form (e.g., curvature of the face).
4. **Details:** High-pressure, sharp strokes for eyes and deep shadows.

## 4. System Architecture

### Module A: The Vision Analyzer (Pre-processing)

Before drawing, the system must "understand" the image. We will generate four guidance maps.

1. **Saliency Map (Attention Map):**
    - *Tech:* Pre-trained CNN (e.g., U-2-Net or simple OpenCV Saliency).
    - *Purpose:* Determines "Importance." The eyes and face have high saliency; the background has low. This dictates *when* things are drawn (draw eyes first/slowly).
2. **Edge Tangent Flow (ETF) Field:**
    - *Tech:* Structure Tensor computation (runs on GPU).
    - *Purpose:* Determines "Direction." In your hoodie image, the cloth folds curve. Standard hatching is straight (45°). ETF calculates a vector field so strokes *curve* with the hoodie and *flow* down the hair.
3. **Tone Segmentation Map:**
    - *Tech:* K-Means Clustering.
    - *Purpose:* Separates the image into 3 zones: Highlights, Mid-tones, Deep Darks.
4. **Grain Extraction:**
    - *Purpose:* Extract the high-frequency noise from the original image to overlay later, ensuring the "texture" of the original drawing is preserved.

### Module B: The Stroke Engine (The "Agent")

This is the replacement for your `_generate_hatching_strokes` function. Instead of math, it uses **Randomized Greedy Search** or a **Paint Transformer** approach.

### Phase 1: The Sketcher (Bézier Curve Fitting)

- **Input:** Canny edges / Holistically-Nested Edge Detection (HED).
- **Action:** Fit long, sweeping Bézier curves to the edges.
- **Visual:** Low opacity, "sketchy" lines.

### Phase 2: The Shader (The "Paint Transformer" approach)

This is the core innovation. We divide the image into patches (e.g., 32x32 pixels).

- **Input:** A patch of the target image + the ETF (flow) map.
- **Process:**
    1. The engine places a "virtual brush" (a sprite of a pencil smudge).
    2. It rotates the brush to match the ETF (so shading follows the curve of the face).
    3. It scales the brush based on the Tone Map (large brush for cheeks, small for eyes).
    4. **Comparison:** It checks: "Does adding this stroke make the canvas look more like the target?"
    5. **Optimization:** If yes, it adds the stroke to the `StrokeList`.

### Module C: The Sequencer (Temporal Logic)

Realism comes from the *order* of operations. The `StrokeList` is unordered. The Sequencer sorts it.

1. **Layer Sorting:** Sort strokes by brush size (Large -> Small).
2. **Spatial Sorting:** Cluster strokes using a Hilbert Curve or K-Nearest Neighbors to minimize "jumping" around the canvas.
3. **Saliency Weighting:** Adjust speed.
    - High Saliency (Eyes): Draw slow, lift pen often.
    - Low Saliency (Hoodie shading): Draw fast, continuous rapid shading.

### Module D: The Renderer (Output)

Instead of drawing standard OpenCV circles, we use **Texture Synthesis**.

1. **Paper Texture:** Multiply the canvas by a high-res paper grain texture.
2. **Graphite Texture:** The "brush" is not a solid color. It is a greyscale alpha mask of actual graphite scans (e.g., `HB_pencil_texture.png`, `4B_shader_texture.png`).
3. **Compositing:**
    - *Stroke Color:* Instead of black, sample the color *from the original image* at the stroke coordinates. This solves your "ugly version" problem. The stroke provides the *shape*, but the original image provides the *fidelity*.

## 5. Technical Implementation Roadmap

### Step 1: Flow Field Implementation (Critical for Realism)

You must implement **Edge Tangent Flow (ETF)**.

- *Why:* The current engine looks robotic because strokes don't wrap around 3D objects.
- *How:* Calculate the structure tensor of the image. The eigenvectors give you the direction of the "flow" at every pixel. Your pencil strokes will follow these vectors.

### Step 2: The "Stroke Primitive" Class

Replace `StrokePoint` with a richer object:

```
@dataclass
class AdvancedStroke:
    path: List[Tuple[float, float]] # Bézier control points
    width_profile: List[float]      # Variable width along path
    pressure_profile: List[float]   # Variable opacity
    texture_id: str                 # 'hard_lead', 'soft_shader', 'smudge'
    flow_angle: float               # Rotation of the brush texture
```

### Step 3: Optimization Loop (The "Painter")

Instead of iterating pixels, iterate *brushes*.

1. Resize input to 512x512 (for speed on GPU).
2. Run the Painter algorithm (e.g., a simplified algorithm based on *Stroke Based Rendering* papers).
3. Upscale the vector strokes back to original resolution (4K+).
4. Apply the strokes to the canvas.

## 6. Comparison: Old vs. New

| Feature | Old Engine (PencilShadingEngine) | New Engine (DeepGraphite) |
| --- | --- | --- |
| **Logic** | Threshold & Masking | Inverse Rendering / Optimization |
| **Stroke Direction** | Fixed (45° / -45°) | **Flow-Guided** (Follows image contours) |
| **Stroke Type** | 1px Lines | **Textured Sprites** (Smudges, Hatches) |
| **Fidelity** | Low (Loss of detail in shadows) | **High** (Samples original texture) |
| **Motion** | Robotic / Scanning | **Human-like** (Sketch -> Block -> Detail) |

## 7. Recommended Python Stack

- **PyTorch:** For calculating Saliency maps and potentially running a pre-trained "Paint Transformer" if you choose the deep learning route.
- **CuPy:** (You already have this). Keep it for fast array matrix math on the 1660ti.
- **OpenCV:** For Saliency (simple version) and ETF calculation.
- **Cairo / Skia (via PyCairo):** Superior vector drawing compared to OpenCV's raster drawing. It handles Bézier curves and brush textures much better.

## 8. Immediate Next Step

Do not try to build the whole Neural Network at once. Start by upgrading the **Directionality**:

1. Keep the logic of determining *where* to shade.
2. Replace the fixed 45° angle with **ETF (Flow Field)**.
3. If the strokes curve with the face, the quality will jump 500% immediately.