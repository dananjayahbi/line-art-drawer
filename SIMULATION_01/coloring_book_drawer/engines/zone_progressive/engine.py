"""
Zone-Based Progressive Engine (Engine 3D) - Main Orchestrator
===============================================================
Identifies focal points and importance zones in artwork,
then reveals the drawing radiating outward from interest centers.

Pipeline:
  Stage 1: Saliency Detection → focal points
  Stage 2: Zone Partitioning → zone map with priorities
  Stage 3: Zone-Ordered Stroke Planning → per-zone reveal sequences
  Stage 4: Radial Reveal Animation → progressive composited output

Interface matches PixelRevealEngine / PencilShadingEngine / AdvancedGradientEngine:
  - process_image(progress_callback=None)
  - reveal_next_batch(points_per_update)  → bool
  - get_current_frame()                   → np.ndarray (H,W,3) uint8 RGB
  - get_points_per_update()               → int
  - get_current_pen_position()            → (x, y)
  - get_progress()                        → float 0-1
  - reset()
  - .original_image, .reveal_mask, .current_reveal_idx  (properties)
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Callable, Optional, Tuple

from .config import ZoneProgressiveConfig

# Detection
from .detection.saliency import SaliencyDetector
from .detection.focal_finder import FocalFinder
from .detection.portrait_detector import PortraitFocalDetector

# Zoning
from .zoning.priority_calculator import PriorityCalculator
from .zoning.partitioner import ZonePartitioner
from .zoning.zone_merger import ZoneMerger

# Animation
from .animation.revealer import ZoneOrderedRevealer
from .animation.stroke_generator import ZoneStrokeGenerator
from .animation.transition_blender import TransitionBlender

# Rendering
from .rendering.frame_compositor import FrameCompositor


class ZoneProgressiveEngine:
    """
    Engine 3D: Zone-Based Progressive Reveal
    
    Analyzes visual importance/saliency, then reveals from
    most important regions outward. Creates an engaging "unveiling"
    effect that naturally draws viewer attention.
    """
    
    def __init__(self, image_path: str, width: int, height: int,
                 padding: int = 40, use_gpu: bool = False,
                 num_zones: int = 10,
                 saliency_threshold: float = 0.3,
                 max_focal_points: int = 5,
                 animation_mode: str = "multi_focal",
                 transition_width: float = 0.1,
                 stroke_density: float = 0.8,
                 enable_portrait: bool = True):
        """
        Args:
            image_path: Path to the input artwork
            width: Display width in pixels
            height: Display height in pixels
            padding: Padding around the image
            use_gpu: Whether to attempt GPU acceleration
            num_zones: Number of reveal zones (more = finer progression)
            saliency_threshold: Min saliency for focal point detection (0-1)
            max_focal_points: Maximum number of focal centers
            animation_mode: "single_focal", "multi_focal", "spiral", "burst"
            transition_width: Zone boundary transition width (0-1)
            stroke_density: Density of reveal strokes (0-1)
            enable_portrait: Enable face/eye detection for portraits
        """
        self.image_path = str(image_path)
        self.display_width = width
        self.display_height = height
        self.padding = padding
        
        # Build config from parameters
        self.config = ZoneProgressiveConfig.from_params(
            num_zones=num_zones,
            saliency_threshold=saliency_threshold,
            max_focal_points=max_focal_points,
            animation_mode=animation_mode,
            transition_width=transition_width,
            stroke_density=stroke_density,
            enable_portrait=enable_portrait,
            use_gpu=use_gpu
        )
        
        # Will be set during process_image()
        self.original_image = None    # (H, W, 3) uint8 RGB — padded & scaled
        self.reveal_mask = None       # (H, W) float32 — current reveal state
        self.current_reveal_idx = 0   # For compatibility with main.py reset
        
        # Internal state
        self._saliency_map = None
        self._focal_points = None
        self._zone_ids = None
        self._zone_masks = None
        self._revealer = None         # ZoneOrderedRevealer
        self._compositor = None       # FrameCompositor
        self._blender = None          # TransitionBlender
        self._reveal_sequence = None  # Flat (N, 2) reveal sequence for pen tracking
        self._pen_position = (width // 2, height // 2)
        self._total_reveal_points = 0
        self._processed = False
    
    # ──────────────────────────────────────────────────────────────────────
    #  STAGE 0: Image Loading & Scaling
    # ──────────────────────────────────────────────────────────────────────
    
    def _load_and_scale_image(self) -> np.ndarray:
        """Load image, scale to fit display, and center with padding."""
        img = cv2.imread(self.image_path)
        if img is None:
            raise FileNotFoundError(f"Cannot load image: {self.image_path}")
        
        # Convert BGR → RGB
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # Calculate target area (with padding)
        target_w = self.display_width - 2 * self.padding
        target_h = self.display_height - 2 * self.padding
        
        h, w = img.shape[:2]
        scale = min(target_w / w, target_h / h)
        
        new_w = int(w * scale)
        new_h = int(h * scale)
        
        # Resize
        resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        
        # Create white canvas and center the image
        canvas = np.full((self.display_height, self.display_width, 3), 255, dtype=np.uint8)
        
        x_offset = (self.display_width - new_w) // 2
        y_offset = (self.display_height - new_h) // 2
        
        canvas[y_offset:y_offset + new_h, x_offset:x_offset + new_w] = resized
        
        return canvas
    
    # ──────────────────────────────────────────────────────────────────────
    #  MAIN PROCESSING PIPELINE
    # ──────────────────────────────────────────────────────────────────────
    
    def process_image(self, progress_callback: Optional[Callable] = None):
        """
        Run the full processing pipeline.
        
        Args:
            progress_callback: Optional callback(step: int, name: str) for loading screen
        """
        def report(step, name):
            print(f"    [{step}/6] {name}")
            if progress_callback:
                progress_callback(step, name)
        
        # Stage 0: Load image
        report(1, "Loading and scaling image...")
        self.original_image = self._load_and_scale_image()
        h, w = self.original_image.shape[:2]
        self.reveal_mask = np.zeros((h, w), dtype=np.float32)
        
        # Create grayscale for analysis
        gray = cv2.cvtColor(self.original_image, cv2.COLOR_RGB2GRAY)
        
        # Create ink mask (non-white pixels = content)
        ink_mask = gray < 240
        
        # Stage 1: Saliency Detection
        report(2, "Computing saliency map...")
        saliency_detector = SaliencyDetector(self.config.focal)
        self._saliency_map = saliency_detector.compute_combined_saliency(self.original_image)
        
        # Stage 1b: Focal point detection
        report(3, "Finding focal points...")
        focal_finder = FocalFinder(self.config.focal)
        saliency_focals = focal_finder.find_focal_points(self._saliency_map)
        
        # Try portrait detection for enhanced focals
        portrait_focals = []
        if self.config.focal.enable_portrait_detection:
            portrait_detector = PortraitFocalDetector(self.config.focal)
            if portrait_detector.available:
                portrait_focals = portrait_detector.detect_portrait_focals(self.original_image)
        
        # Merge focal lists (portrait takes priority)
        self._focal_points = focal_finder.merge_focal_lists(portrait_focals, saliency_focals)
        
        focal_types = [f['type'] for f in self._focal_points]
        print(f"    Found {len(self._focal_points)} focal points: {focal_types}")
        
        # Stage 2: Zone Partitioning
        report(4, "Creating reveal zones...")
        priority_calc = PriorityCalculator(self.config.zone)
        priority_map = priority_calc.compute_priority_map(
            (h, w), self._focal_points, self._saliency_map
        )
        
        partitioner = ZonePartitioner(self.config.zone)
        self._zone_ids = partitioner.create_zones(priority_map)
        
        # Merge tiny zones
        merger = ZoneMerger(self.config.zone)
        self._zone_ids = merger.merge_small_zones(self._zone_ids, min_fraction=0.005)
        self._zone_ids = merger.smooth_zone_boundaries(self._zone_ids, iterations=1)
        
        # Create smooth masks
        self._zone_masks = partitioner.create_zone_masks(self._zone_ids)
        zone_counts = partitioner.get_zone_pixel_counts(self._zone_ids)
        
        num_actual_zones = int(self._zone_ids.max()) + 1
        print(f"    Created {num_actual_zones} zones (requested {self.config.zone.num_zones})")
        
        # Stage 3: Stroke Planning
        report(5, "Planning reveal sequences...")
        stroke_gen = ZoneStrokeGenerator(self.config.animation)
        zone_sequences = stroke_gen.generate_zone_sequence(
            self._zone_ids, priority_map, self._focal_points, ink_mask
        )
        
        # Build flat reveal sequence for pen tracking
        self._reveal_sequence = stroke_gen.build_full_reveal_sequence(zone_sequences)
        self._total_reveal_points = len(self._reveal_sequence)
        
        print(f"    Total reveal points: {self._total_reveal_points}")
        
        # Stage 4: Initialize Revealer & Compositor
        report(6, "Initializing reveal system...")
        self._revealer = ZoneOrderedRevealer(
            self._zone_masks, zone_counts, self.config.animation
        )
        self._compositor = FrameCompositor(self.original_image, self.config.rendering)
        self._blender = TransitionBlender(self.config.animation)
        
        self._processed = True
        self.current_reveal_idx = 0
        
        print("    ✅ Zone Progressive Engine ready!")
    
    # ──────────────────────────────────────────────────────────────────────
    #  REVEAL INTERFACE (matches other engines)
    # ──────────────────────────────────────────────────────────────────────
    
    def reveal_next_batch(self, points_per_update: int = 100) -> bool:
        """
        Reveal the next batch of points.
        
        Args:
            points_per_update: Number of pixels to reveal
            
        Returns:
            True if more to reveal, False if complete
        """
        if not self._processed or not self._revealer:
            return False
        
        has_more = self._revealer.reveal_next_batch(points_per_update)
        
        # Update reveal mask from revealer
        raw_mask = self._revealer.get_reveal_mask()
        
        # Apply transition blending for smoother edges
        self.reveal_mask = self._blender.blend_zone_edges(raw_mask)
        
        # Update pen position from reveal sequence
        self.current_reveal_idx = min(
            self.current_reveal_idx + points_per_update,
            self._total_reveal_points
        )
        
        if self._total_reveal_points > 0 and self.current_reveal_idx < self._total_reveal_points:
            idx = min(self.current_reveal_idx, self._total_reveal_points - 1)
            row, col = self._reveal_sequence[idx]
            self._pen_position = (int(col), int(row))  # (x, y)
        
        return has_more
    
    def get_current_frame(self) -> np.ndarray:
        """
        Get the current composited frame.
        
        Returns:
            (H, W, 3) uint8 RGB frame
        """
        if not self._processed:
            # Return white canvas
            return np.full((self.display_height, self.display_width, 3), 255, dtype=np.uint8)
        
        feather = self.config.rendering.mask_feather_radius
        return self._compositor.compose_frame_with_feathering(self.reveal_mask, feather)
    
    def get_points_per_update(self) -> int:
        """
        Get the recommended points per update for this engine.
        Zone-based engine uses larger batches since zones are area-based.
        
        Returns:
            Recommended points per update
        """
        if not self._processed or self._total_reveal_points == 0:
            return 100
        
        # Aim for about 300 frames worth of content (5 seconds at 60fps)
        base = max(50, self._total_reveal_points // 300)
        
        return base
    
    def get_current_pen_position(self) -> Tuple[int, int]:
        """
        Get the current pen cursor position.
        
        Returns:
            (x, y) pixel position
        """
        return self._pen_position
    
    def get_progress(self) -> float:
        """
        Get overall reveal progress.
        
        Returns:
            Float 0.0 to 1.0
        """
        if not self._revealer:
            return 0.0
        return self._revealer.get_progress()
    
    def reset(self):
        """Reset the reveal to the beginning."""
        if self.original_image is not None:
            h, w = self.original_image.shape[:2]
            self.reveal_mask = np.zeros((h, w), dtype=np.float32)
        
        self.current_reveal_idx = 0
        self._pen_position = (self.display_width // 2, self.display_height // 2)
        
        if self._revealer:
            self._revealer.reset()
