"""
Advanced Gradient Shading Engine (Engine 3)
=============================================
Main orchestrator that coordinates all analysis, stroke planning,
and rendering components for high-fidelity pencil art simulation.

This engine handles complex, high-contrast pencil artwork with
natural-looking shading and shadows using progressive gradient reveal.

Key innovations:
- Structure tensor for direction-aware strokes
- Continuous intensity mapping for smooth gradients
- Multi-pass shadow accumulation for rich darks
- Superpixel region segmentation for texture awareness
- Phase-based brush presets for natural variation
"""

import numpy as np
import cv2
import time
import math
from pathlib import Path
from typing import List, Tuple, Optional, Dict

# Analysis modules
from .analysis.structure_tensor import StructureTensorAnalyzer
from .analysis.edge_detector import MultiScaleEdgeDetector
from .analysis.region_segmenter import RegionSegmenter
from .analysis.intensity_mapper import ContinuousIntensityMapper

# Stroke planning modules
from .stroke_planning.contour_strokes import ContourStrokeGenerator, StrokePoint
from .stroke_planning.gradient_strokes import GradientStrokeGenerator
from .stroke_planning.texture_strokes import TextureStrokeGenerator
from .stroke_planning.shadow_strokes import ShadowStrokeGenerator
from .stroke_planning.ordering_system import StrokeOrderingSystem

# Rendering modules
from .rendering.reveal_renderer import RevealRenderer

# Configuration
from .config import AdvancedGradientConfig

# GPU utilities
from .gpu.fallback import GPUAccelerator


class AdvancedGradientEngine:
    """
    Advanced Gradient Shading Engine (Engine 3).
    
    Orchestrates the full pipeline:
    1. Advanced Analysis (structure tensor, multi-scale edges, regions, intensity)
    2. Region Decomposition (contours, gradients, textures, shadows, highlights)
    3. Stroke Path Generation (contour, gradient, texture, shadow, detail strokes)
    4. Intelligent Ordering (6-phase hierarchical reveal)
    5. Progressive Reveal (soft brush compositing)
    
    Compatible with the existing simulation framework (same interface as
    PixelRevealEngine and PencilShadingEngine).
    """

    def __init__(self, image_path: str, target_width: int, target_height: int,
                 padding: int = 40, use_gpu: bool = True,
                 config: AdvancedGradientConfig = None,
                 # Expose key config params directly for CLI/GUI
                 contour_sensitivity: float = 0.5,
                 gradient_smoothness: float = 0.7,
                 texture_detection_strength: float = 0.6,
                 shadow_passes: int = 3,
                 shadow_angle_variation: float = 30.0,
                 brush_softness_contour: float = 0.3,
                 brush_softness_shading: float = 0.7,
                 pressure_variation: float = 0.5):
        
        self.image_path = image_path
        self.target_width = target_width
        self.target_height = target_height
        self.padding = padding

        # GPU acceleration
        self.gpu = GPUAccelerator(use_gpu)
        self.use_gpu = self.gpu.use_gpu
        
        if self.use_gpu:
            print(f"  [AdvancedGradient] GPU acceleration ENABLED - {self.gpu.gpu_info}")
        else:
            print(f"  [AdvancedGradient] Using CPU processing")

        # Configuration
        if config:
            self.config = config
        else:
            self.config = AdvancedGradientConfig(
                contour_sensitivity=contour_sensitivity,
                gradient_smoothness=gradient_smoothness,
                texture_detection_strength=texture_detection_strength,
                shadow_passes=shadow_passes,
                shadow_angle_variation=shadow_angle_variation,
                brush_softness_contour=brush_softness_contour,
                brush_softness_shading=brush_softness_shading,
                pressure_variation=pressure_variation,
            )

        # Image data
        self.original_image = None
        self.grayscale = None
        self.binary_mask = None

        # Analysis results
        self.orientation = None
        self.coherence = None
        self.edges = None
        self.regions = None
        self.intensity_mapper = None

        # Stroke data
        self.reveal_sequence: List[StrokePoint] = []
        self.current_reveal_idx = 0

        # Renderer
        self.renderer = None

        # Ordering system
        self.ordering = StrokeOrderingSystem(self.config)

        # Background color
        self.bg_color = np.array([255, 255, 255], dtype=np.uint8)

    def process_image(self, progress_callback=None) -> bool:
        """
        Process the image through the full analysis → stroke → ordering pipeline.
        
        Args:
            progress_callback: Optional callable(step: int, name: str) for UI updates
            
        Returns:
            True if processing succeeded
        """
        def update_progress(step: int, name: str):
            print(f"\n[{step}/6] {name}")
            if progress_callback:
                progress_callback(step, name)

        print("=" * 60)
        print("ADVANCED GRADIENT SHADING ENGINE (Engine 3) - Processing")
        print("=" * 60)

        total_start = time.time()

        # ═══════════════════════════════════════════════
        # STAGE 1: Load and preprocess
        # ═══════════════════════════════════════════════
        update_progress(1, "Loading and preprocessing image...")
        if not self._load_and_preprocess():
            return False

        # ═══════════════════════════════════════════════
        # STAGE 2: Advanced Analysis
        # ═══════════════════════════════════════════════
        update_progress(2, "Running advanced analysis (structure tensor, edges, regions)...")
        self._run_analysis()

        # ═══════════════════════════════════════════════
        # STAGE 3: Stroke Path Generation
        # ═══════════════════════════════════════════════
        update_progress(3, "Generating stroke paths for all regions...")
        stroke_groups = self._generate_all_strokes()

        # ═══════════════════════════════════════════════
        # STAGE 4: Intelligent Ordering
        # ═══════════════════════════════════════════════
        update_progress(4, "Building intelligent reveal order (6 phases)...")
        self.reveal_sequence = self.ordering.build_ordered_sequence(stroke_groups)

        # ═══════════════════════════════════════════════
        # STAGE 5: Enhancement Pass Generation
        # ═══════════════════════════════════════════════
        update_progress(5, "Generating enhancement coverage strokes...")
        self._generate_enhancement_strokes()

        # ═══════════════════════════════════════════════
        # STAGE 6: Initialize Animation
        # ═══════════════════════════════════════════════
        update_progress(6, "Initializing animation state...")
        self._init_animation_state()

        total_elapsed = time.time() - total_start

        print("\n" + "=" * 60)
        print(f"Engine 3 processing complete in {total_elapsed:.2f}s")
        print(f"Total stroke points: {len(self.reveal_sequence)}")
        print("=" * 60)

        return True

    def _load_and_preprocess(self) -> bool:
        """Load image and prepare for processing."""
        img = cv2.imread(str(self.image_path))
        if img is None:
            print(f"ERROR: Could not load image: {self.image_path}")
            return False

        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = self._resize_to_canvas(img)
        self.original_image = img
        self.grayscale = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        self.binary_mask = self.grayscale < 240

        print(f"  Image size: {img.shape[1]}x{img.shape[0]}")
        print(f"  Non-white pixels: {np.sum(self.binary_mask):,} "
              f"({100 * np.mean(self.binary_mask):.1f}%)")

        return True

    def _resize_to_canvas(self, img: np.ndarray) -> np.ndarray:
        """Resize image to fit canvas with padding."""
        h, w = img.shape[:2]
        available_w = self.target_width - 2 * self.padding
        available_h = self.target_height - 2 * self.padding
        scale = min(available_w / w, available_h / h)
        new_w = int(w * scale)
        new_h = int(h * scale)
        resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
        canvas = np.ones((self.target_height, self.target_width, 3), dtype=np.uint8) * 255
        offset_x = (self.target_width - new_w) // 2
        offset_y = (self.target_height - new_h) // 2
        canvas[offset_y:offset_y + new_h, offset_x:offset_x + new_w] = resized
        return canvas

    def _run_analysis(self):
        """Run all analysis components."""
        start = time.time()

        # Structure tensor analysis
        print("  Computing gradient flow field (structure tensor)...")
        st_analyzer = StructureTensorAnalyzer(use_gpu=self.use_gpu)
        st_result = st_analyzer.analyze(self.grayscale)
        self.orientation = st_result['orientation']
        self.coherence = st_result['coherence']
        print(f"    Orientation range: [{np.min(self.orientation):.2f}, {np.max(self.orientation):.2f}]")
        print(f"    Mean coherence: {np.mean(self.coherence):.3f}")

        # Multi-scale edge detection
        print("  Detecting edges at multiple scales...")
        edge_detector = MultiScaleEdgeDetector(use_gpu=self.use_gpu)
        self.edges = edge_detector.detect(self.grayscale)
        primary_count = np.sum(self.edges['primary'])
        secondary_count = np.sum(self.edges['secondary'])
        print(f"    Primary edges: {primary_count:,} pixels")
        print(f"    Secondary edges: {secondary_count:,} pixels")

        # Region segmentation
        print("  Segmenting regions (superpixels)...")
        segmenter = RegionSegmenter(use_gpu=self.use_gpu)
        self.regions = segmenter.segment(self.grayscale)

        # Count region types
        type_counts = {}
        for label, info in self.regions.items():
            rtype = info['type']
            type_counts[rtype] = type_counts.get(rtype, 0) + 1
        for rtype, count in sorted(type_counts.items()):
            print(f"    {rtype}: {count} regions")

        # Intensity mapping
        print("  Building continuous intensity map...")
        self.intensity_mapper = ContinuousIntensityMapper(use_gpu=self.use_gpu)
        self.intensity_mapper.compute(self.grayscale)

        elapsed = time.time() - start
        print(f"  Analysis completed in {elapsed:.2f}s")

    def _generate_all_strokes(self) -> Dict[str, List[StrokePoint]]:
        """Generate strokes from all stroke generators."""
        start = time.time()
        intensity_map = self.intensity_mapper.get_continuous_map()

        stroke_groups = {}

        # Contour strokes (primary + detail)
        print("  Generating contour strokes...")
        contour_gen = ContourStrokeGenerator(use_gpu=self.use_gpu)
        contour_result = contour_gen.generate(
            self.edges['primary'], self.edges['secondary'],
            intensity_map, self.coherence
        )
        stroke_groups['primary_contour'] = contour_result.get('primary_contour', [])
        stroke_groups['detail'] = contour_result.get('detail', [])

        # Gradient strokes
        print("  Generating gradient strokes...")
        gradient_gen = GradientStrokeGenerator(use_gpu=self.use_gpu)
        stroke_groups['gradient'] = gradient_gen.generate(
            self.regions, intensity_map,
            self.orientation, self.coherence,
            gradient_smoothness=self.config.gradient_smoothness
        )
        stroke_groups['highlight'] = gradient_gen.generate_highlight_strokes(
            self.regions, intensity_map
        )

        # Texture strokes
        print("  Generating texture strokes...")
        texture_gen = TextureStrokeGenerator(use_gpu=self.use_gpu)
        stroke_groups['texture'] = texture_gen.generate(
            self.regions, intensity_map,
            self.orientation, self.coherence,
            stroke_spacing=3,
            texture_strength=self.config.texture_detection_strength
        )

        # Shadow strokes
        print("  Generating shadow strokes...")
        shadow_gen = ShadowStrokeGenerator(use_gpu=self.use_gpu)
        stroke_groups['shadow'] = shadow_gen.generate(
            self.regions, intensity_map,
            self.orientation, self.coherence,
            shadow_passes=self.config.shadow_passes,
            angle_variation=self.config.shadow_angle_variation,
            stroke_spacing=3
        )

        elapsed = time.time() - start
        total_pts = sum(len(v) for v in stroke_groups.values())
        print(f"  Stroke generation completed in {elapsed:.2f}s ({total_pts} total points)")

        return stroke_groups

    def _generate_enhancement_strokes(self):
        """
        Generate enhancement strokes to fill any remaining uncovered pixels.
        This is Phase 6 - a quick final pass over dark areas not yet fully revealed.
        """
        if not self.reveal_sequence:
            return

        intensity_map = self.intensity_mapper.get_continuous_map()
        h, w = intensity_map.shape

        # Find dark pixels that might not be covered by existing strokes
        dark_mask = intensity_map > 0.7
        dark_pixels = np.argwhere(dark_mask)

        if len(dark_pixels) == 0:
            return

        # Sample a subset for enhancement
        sample_rate = max(1, len(dark_pixels) // 500)
        sampled = dark_pixels[::sample_rate]

        enhancement = []
        for y, x in sampled:
            enhancement.append(StrokePoint(
                x=float(x), y=float(y),
                pressure=0.5,
                angle=0.0,
                width=1.5,
                phase='shadow',
                intensity=float(intensity_map[y, x])
            ))

        self.reveal_sequence.extend(enhancement)
        print(f"  [Enhancement] Added {len(enhancement)} enhancement points")

    def _init_animation_state(self):
        """Initialize the animation renderer."""
        h, w = self.original_image.shape[:2]
        self.renderer = RevealRenderer((h, w))
        self.current_reveal_idx = 0
        print(f"  Animation ready: {len(self.reveal_sequence)} points to reveal")

    # ═══════════════════════════════════════════════════════
    # PUBLIC API - Compatible with simulation framework
    # ═══════════════════════════════════════════════════════

    def reveal_next_batch(self, points_per_update: int = None) -> bool:
        """
        Reveal next batch of stroke points.
        
        Args:
            points_per_update: Number of points to reveal this frame
            
        Returns:
            True if there are more points to reveal, False if complete
        """
        if self.current_reveal_idx >= len(self.reveal_sequence):
            return False

        if points_per_update is None:
            points_per_update = self.get_points_per_update()

        end_idx = min(self.current_reveal_idx + points_per_update,
                      len(self.reveal_sequence))

        prev_point = None
        for i in range(self.current_reveal_idx, end_idx):
            point = self.reveal_sequence[i]

            self.renderer.draw_stroke_point(
                x=point.x, y=point.y,
                pressure=point.pressure,
                width=point.width,
                intensity=point.intensity,
                phase=point.phase,
                prev_x=prev_point.x if prev_point else None,
                prev_y=prev_point.y if prev_point else None,
                prev_pressure=prev_point.pressure if prev_point else None,
                prev_width=prev_point.width if prev_point else None,
                prev_intensity=prev_point.intensity if prev_point else None,
            )
            prev_point = point

        self.current_reveal_idx = end_idx
        return True

    def get_points_per_update(self) -> int:
        """Get the recommended points per update based on current phase."""
        if self.current_reveal_idx >= len(self.reveal_sequence):
            return 0

        progress = self.get_progress()
        speed = self.ordering.get_speed_for_progress(progress)

        # Base rate scaled by phase speed
        base_rate = 15
        return max(1, int(base_rate * speed))

    def get_current_frame(self) -> np.ndarray:
        """Get the current composited frame as RGB numpy array."""
        if self.renderer is None:
            return np.ones((self.target_height, self.target_width, 3),
                           dtype=np.uint8) * 255

        return self.renderer.composite_frame(self.original_image, self.binary_mask)

    def get_progress(self) -> float:
        """Get animation progress (0.0 to 1.0)."""
        if len(self.reveal_sequence) == 0:
            return 1.0
        return self.current_reveal_idx / len(self.reveal_sequence)

    def get_current_pen_position(self) -> Tuple[int, int]:
        """Get current pen position for cursor display."""
        if 0 < self.current_reveal_idx <= len(self.reveal_sequence):
            point = self.reveal_sequence[self.current_reveal_idx - 1]
            return (int(point.x), int(point.y))
        elif self.reveal_sequence:
            point = self.reveal_sequence[0]
            return (int(point.x), int(point.y))
        return (self.target_width // 2, self.target_height // 2)

    def get_current_phase_name(self) -> str:
        """Get human-readable name of current drawing phase."""
        return self.ordering.get_phase_for_progress(self.get_progress())

    def is_complete(self) -> bool:
        """Check if animation is complete."""
        return self.current_reveal_idx >= len(self.reveal_sequence)

    def reset(self):
        """Reset animation to beginning."""
        if self.renderer:
            self.renderer.reset()
        self.current_reveal_idx = 0
