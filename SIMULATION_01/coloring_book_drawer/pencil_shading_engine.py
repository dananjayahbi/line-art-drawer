#!/usr/bin/env python3
"""
Pencil Shading Engine for Coloring Book Drawer
===============================================
Advanced engine for natural pencil drawing simulation that handles:
- Simple line drawings (existing behavior)
- Complex shaded artwork with textures, shadows, and gradients

KEY INSIGHT:
The original reveal engine treats all pixels equally, revealing them in
circular masks along skeleton paths. This works for line art but creates
unnatural "bubble" artifacts for shaded regions.

THIS ENGINE SOLVES IT BY:
1. Decomposing the image into LAYERS:
   - Edge/Line Layer: Strong edges that define shapes (drawn first)
   - Shading Layer: Gradual tones, textures, shadows (drawn second with pencil strokes)
   
2. Using DIFFERENT reveal strategies for each layer:
   - Lines: Skeleton-based reveal (original approach)
   - Shading: Gradient-aware hatching with natural pencil stroke patterns

3. Providing ADAPTIVE SPEED control:
   - Slower for detailed line work
   - Faster for broad shading strokes

4. Creating NATURAL PENCIL TEXTURE:
   - Directional strokes for shading
   - Pressure variation simulation
   - Multiple hatching layers for dark areas

Author: GitHub Copilot
Date: February 2026
"""

import numpy as np
import cv2
from pathlib import Path
from enum import Enum
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict
import math
import time

# GPU acceleration - try to import CuPy for CUDA support
HAS_GPU = False
GPU_INFO = "No GPU acceleration"
cp = None  # CuPy module placeholder

try:
    import cupy as cp_module
    cp = cp_module
    from cupyx.scipy import ndimage as cp_ndimage
    
    # Test GPU availability
    try:
        device = cp.cuda.Device(0)
        cuda_version = cp.cuda.runtime.runtimeGetVersion()
        cuda_major = cuda_version // 1000
        cuda_minor = (cuda_version % 1000) // 10
        
        # Quick test
        test_arr = cp.array([1, 2, 3])
        _ = cp.asnumpy(test_arr)
        
        HAS_GPU = True
        GPU_INFO = f"GPU: {device}, CUDA {cuda_major}.{cuda_minor}"
        print(f"[PencilShadingEngine] GPU acceleration enabled: {GPU_INFO}")
    except Exception as e:
        print(f"[PencilShadingEngine] CuPy available but GPU init failed: {e}")
        HAS_GPU = False
        cp = None
except ImportError:
    print("[PencilShadingEngine] CuPy not installed. Using CPU processing.")
    HAS_GPU = False
    cp = None

# Scikit-image for advanced processing
try:
    from skimage.morphology import skeletonize, medial_axis, disk
    from skimage.filters import sobel, gaussian
    from skimage.feature import canny
    from skimage import img_as_ubyte, img_as_float
    HAS_SKIMAGE = True
except ImportError:
    HAS_SKIMAGE = False
    print("Warning: scikit-image not found. Using OpenCV fallback.")


class DrawingPhase(Enum):
    """Represents different phases of the pencil drawing process."""
    OUTLINE = "outline"          # Drawing main edges and lines
    HATCHING = "hatching"        # First layer of shading strokes
    CROSS_HATCHING = "cross_hatching"  # Second layer for darker areas
    DETAIL_SHADING = "detail"    # Fine details and textures
    BLENDING = "blending"        # Final smooth blending pass


@dataclass
class StrokePoint:
    """Represents a single point in a pencil stroke."""
    x: float
    y: float
    pressure: float       # 0.0-1.0, affects opacity/darkness
    angle: float          # Stroke direction in radians
    width: float          # Stroke width based on local thickness
    phase: DrawingPhase   # Which drawing phase this belongs to
    intensity: float      # Target darkness level (0=white, 1=black)


@dataclass
class SpeedConfig:
    """Speed configuration for different drawing phases."""
    outline_speed: float = 1.0        # Speed multiplier for outlines
    hatching_speed: float = 2.0       # Speed multiplier for hatching
    cross_hatch_speed: float = 2.5    # Speed multiplier for cross-hatching
    detail_speed: float = 0.8         # Speed multiplier for details
    blending_speed: float = 3.0       # Speed multiplier for blending
    
    # Points revealed per update for each phase
    outline_points_per_update: int = 8
    hatching_points_per_update: int = 20
    cross_hatch_points_per_update: int = 25
    detail_points_per_update: int = 5
    blending_points_per_update: int = 40


class PencilShadingEngine:
    """
    Advanced engine for natural pencil drawing simulation.
    
    Handles both simple line drawings and complex shaded artwork
    by decomposing the image into layers and using appropriate
    reveal strategies for each layer type.
    """
    
    def __init__(self, image_path: str, target_width: int, target_height: int,
                 padding: int = 40, use_gpu: bool = True,
                 edge_threshold: float = 0.15,
                 shade_sensitivity: float = 0.5,
                 hatching_angle: float = 45.0,
                 cross_hatch_angle: float = -45.0,
                 stroke_spacing: int = 3,
                 min_shade_threshold: int = 240,
                 edge_phases_first: int = 1,
                 shading_order: str = "top_to_bottom"):
        """
        Initialize the Pencil Shading Engine.
        
        Args:
            image_path: Path to the input image
            target_width: Target canvas width
            target_height: Target canvas height
            padding: Padding around the image
            use_gpu: Whether to use GPU acceleration
            edge_threshold: Threshold for edge detection (0.0-1.0)
            shade_sensitivity: How sensitive to detect shading regions (0.0-1.0)
            hatching_angle: Primary hatching angle in degrees
            cross_hatch_angle: Secondary hatching angle in degrees
            stroke_spacing: Spacing between hatching strokes in pixels
            min_shade_threshold: Pixel value below which is considered shaded (0-255)
            edge_phases_first: Number of edge layers to complete before shading (1-3)
                              1 = Main outlines first, then shading
                              2 = Main outlines + hatching first, then remaining
                              3 = Main outlines + hatching + cross-hatching first
            shading_order: Order for shading strokes ("top_to_bottom", "natural", "random")
        """
        self.image_path = image_path
        self.target_width = target_width
        self.target_height = target_height
        self.padding = padding
        self.use_gpu = use_gpu and HAS_GPU  # Only use GPU if available
        
        # Log GPU status
        if self.use_gpu:
            print(f"  [GPU] GPU acceleration ENABLED - {GPU_INFO}")
        else:
            if use_gpu and not HAS_GPU:
                print("  [GPU] GPU requested but not available - using CPU")
            else:
                print("  [GPU] Using CPU processing")
        
        # Processing parameters
        self.edge_threshold = edge_threshold
        self.shade_sensitivity = shade_sensitivity
        self.hatching_angle = math.radians(hatching_angle)
        self.cross_hatch_angle = math.radians(cross_hatch_angle)
        self.stroke_spacing = stroke_spacing
        self.min_shade_threshold = min_shade_threshold
        
        # Phased drawing parameters
        self.edge_phases_first = max(1, min(3, edge_phases_first))  # Clamp to 1-3
        self.shading_order = shading_order  # "top_to_bottom", "natural", "random"
        
        # Image data
        self.original_image = None      # RGB original
        self.grayscale = None           # Grayscale version
        self.binary_mask = None         # Where ink exists (any non-white)
        
        # Layer decomposition
        self.edge_layer = None          # Strong edges/lines
        self.shade_layer = None         # Shading regions (gradients, textures)
        self.intensity_map = None       # Darkness levels for each pixel
        
        # Skeleton data for edge layer
        self.edge_skeleton = None
        self.edge_distance = None
        
        # Stroke sequences for each phase
        self.stroke_sequences: Dict[DrawingPhase, List[StrokePoint]] = {
            DrawingPhase.OUTLINE: [],
            DrawingPhase.HATCHING: [],
            DrawingPhase.CROSS_HATCHING: [],
            DrawingPhase.DETAIL_SHADING: [],
            DrawingPhase.BLENDING: [],
        }
        
        # Combined reveal sequence (all phases merged)
        self.reveal_sequence: List[StrokePoint] = []
        
        # Animation state
        self.reveal_mask = None         # Current accumulated reveal mask
        self.pressure_map = None        # Accumulated pressure/darkness map
        self.current_reveal_idx = 0
        self.current_phase = DrawingPhase.OUTLINE
        
        # Speed configuration
        self.speed_config = SpeedConfig()
        
        # Background color
        self.bg_color = np.array([255, 255, 255], dtype=np.uint8)
        
        # Brush settings
        self.brush_softness = 0.6       # How soft the brush edges are (0=hard, 1=very soft)
        self.pencil_texture_enabled = True
        
    def process_image(self, progress_callback=None) -> bool:
        """
        Main processing pipeline for the image.
        
        Args:
            progress_callback: Optional callback function(step: int, name: str) for progress updates
        
        Returns:
            True if processing succeeded, False otherwise
        """
        def update_progress(step: int, name: str):
            print(f"\n[{step}/6] {name}")
            if progress_callback:
                progress_callback(step, name)
        
        print("=" * 60)
        print("PENCIL SHADING ENGINE - Processing Image")
        print("=" * 60)
        
        # Step 1: Load and preprocess image
        update_progress(1, "Loading and preprocessing image...")
        if not self._load_and_preprocess():
            return False
        
        # Step 2: Analyze image complexity
        update_progress(2, "Analyzing image complexity...")
        complexity = self._analyze_complexity()
        print(f"  Image complexity: {complexity['type']}")
        print(f"  - Edge coverage: {complexity['edge_coverage']:.1%}")
        print(f"  - Shade coverage: {complexity['shade_coverage']:.1%}")
        print(f"  - Gradient regions: {complexity['gradient_regions']}")
        
        # Step 3: Decompose into layers
        update_progress(3, "Decomposing image into drawing layers...")
        self._decompose_layers()
        
        # Step 4: Build stroke sequences for each layer
        update_progress(4, "Building stroke sequences...")
        self._build_outline_strokes()
        try:
            self._build_shading_strokes()
        except Exception as e:
            print(f"  Warning: Shading stroke generation had an issue: {e}")
            print("  Continuing with outline strokes only...")
        
        # Step 5: Merge sequences with natural ordering
        update_progress(5, "Merging sequences with natural drawing order...")
        self._merge_sequences()
        
        # Step 6: Initialize animation state (ALWAYS do this)
        update_progress(6, "Initializing animation state...")
        self._init_animation_state()
        
        print("\n" + "=" * 60)
        print(f"Processing complete! {len(self.reveal_sequence)} stroke points generated.")
        print(f"  - Outline points: {len(self.stroke_sequences[DrawingPhase.OUTLINE])}")
        print(f"  - Hatching points: {len(self.stroke_sequences[DrawingPhase.HATCHING])}")
        print(f"  - Cross-hatching points: {len(self.stroke_sequences[DrawingPhase.CROSS_HATCHING])}")
        print(f"  - Detail points: {len(self.stroke_sequences[DrawingPhase.DETAIL_SHADING])}")
        print("=" * 60)
        
        return True
    
    def _load_and_preprocess(self) -> bool:
        """Load image and prepare for processing."""
        # Load image
        img = cv2.imread(str(self.image_path))
        if img is None:
            print(f"ERROR: Could not load image: {self.image_path}")
            return False
        
        # Convert BGR to RGB
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # Resize to fit canvas
        img = self._resize_to_canvas(img)
        self.original_image = img
        
        # Create grayscale version
        self.grayscale = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        
        # Create binary mask (any pixel darker than near-white)
        self.binary_mask = self.grayscale < self.min_shade_threshold
        
        # Create intensity map (normalized darkness levels)
        # 0 = white/no ink, 1 = black/full ink
        self.intensity_map = 1.0 - (self.grayscale.astype(np.float32) / 255.0)
        
        print(f"  Image size: {img.shape[1]}x{img.shape[0]}")
        print(f"  Ink pixels: {np.sum(self.binary_mask):,} ({100*np.mean(self.binary_mask):.1f}%)")
        
        return True
    
    def _resize_to_canvas(self, img: np.ndarray) -> np.ndarray:
        """Resize image to fit canvas while maintaining aspect ratio."""
        h, w = img.shape[:2]
        
        # Available space
        available_w = self.target_width - 2 * self.padding
        available_h = self.target_height - 2 * self.padding
        
        # Calculate scale
        scale_w = available_w / w
        scale_h = available_h / h
        scale = min(scale_w, scale_h)
        
        new_w = int(w * scale)
        new_h = int(h * scale)
        
        # Resize using high-quality interpolation
        resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
        
        # Create canvas and center the image
        canvas = np.ones((self.target_height, self.target_width, 3), dtype=np.uint8) * 255
        
        offset_x = (self.target_width - new_w) // 2
        offset_y = (self.target_height - new_h) // 2
        
        canvas[offset_y:offset_y + new_h, offset_x:offset_x + new_w] = resized
        
        return canvas
    
    def _analyze_complexity(self) -> dict:
        """Analyze the complexity of the image to determine drawing strategy."""
        # Detect edges using Canny or Sobel
        if HAS_SKIMAGE:
            edges = canny(self.grayscale, sigma=1.5)
        else:
            edges = cv2.Canny(self.grayscale, 50, 150) > 0
        
        # Calculate edge coverage
        edge_coverage = np.mean(edges)
        
        # Detect shading regions (areas with gradient/non-binary values)
        # Shading = dark pixels that are NOT edges
        shade_mask = (self.intensity_map > 0.1) & ~edges
        shade_coverage = np.mean(shade_mask)
        
        # Detect gradient regions (areas with varying intensity)
        # Use local variance to detect gradients
        kernel_size = 11
        local_mean = cv2.blur(self.grayscale.astype(np.float32), (kernel_size, kernel_size))
        local_sq_mean = cv2.blur((self.grayscale.astype(np.float32))**2, (kernel_size, kernel_size))
        local_variance = local_sq_mean - local_mean**2
        gradient_regions = np.sum(local_variance > 100)
        
        # Determine image type
        if shade_coverage < 0.05:
            img_type = "LINE_ART"
        elif shade_coverage < 0.2:
            img_type = "LINE_WITH_LIGHT_SHADING"
        elif shade_coverage < 0.5:
            img_type = "MODERATELY_SHADED"
        else:
            img_type = "HEAVILY_SHADED"
        
        return {
            "type": img_type,
            "edge_coverage": edge_coverage,
            "shade_coverage": shade_coverage,
            "gradient_regions": gradient_regions,
            "edges": edges,
            "shade_mask": shade_mask,
        }
    
    def _decompose_layers(self):
        """Decompose image into edge layer and shade layer."""
        # --- Edge Layer ---
        # Strong edges that define the shape (lines, contours)
        if HAS_SKIMAGE:
            # Use Canny for clean edges
            edges = canny(self.grayscale, sigma=1.0, 
                         low_threshold=self.edge_threshold * 100,
                         high_threshold=self.edge_threshold * 255)
        else:
            edges = cv2.Canny(self.grayscale, 
                             int(self.edge_threshold * 100),
                             int(self.edge_threshold * 255)) > 0
        
        # Dilate edges slightly for better skeleton extraction
        kernel = np.ones((2, 2), np.uint8)
        self.edge_layer = cv2.dilate(edges.astype(np.uint8) * 255, kernel, iterations=1) > 0
        
        # --- Shade Layer ---
        # Areas with shading but not strong edges
        # Apply Gaussian blur to original to smooth noise
        blurred = cv2.GaussianBlur(self.grayscale, (5, 5), 0)
        
        # Shade layer = dark pixels minus the edge layer
        shade_intensity = 1.0 - (blurred.astype(np.float32) / 255.0)
        
        # Remove edge regions from shade layer (already handled separately)
        edge_dilated = cv2.dilate(self.edge_layer.astype(np.uint8) * 255, 
                                   np.ones((3, 3), np.uint8), iterations=2) > 0
        shade_intensity[edge_dilated] = 0
        
        # Threshold to remove very light areas
        shade_intensity[shade_intensity < 0.08] = 0
        
        self.shade_layer = shade_intensity
        
        print(f"  Edge layer pixels: {np.sum(self.edge_layer):,}")
        print(f"  Shade layer coverage: {100*np.mean(self.shade_layer > 0):.1f}%")
        print(f"  Average shade intensity: {np.mean(self.shade_layer[self.shade_layer > 0]):.2f}")
    
    def _build_outline_strokes(self):
        """Build stroke sequence for the outline/edge layer."""
        if not np.any(self.edge_layer):
            print("  No edges detected, skipping outline strokes.")
            return
        
        # Extract skeleton from edge layer - this is the slow part
        skeleton_start = time.time()
        print("  Extracting skeleton (this may take a moment)...")
        
        if HAS_SKIMAGE:
            skeleton, distance = medial_axis(self.edge_layer, return_distance=True)
            self.edge_skeleton = skeleton
            self.edge_distance = distance * skeleton
        else:
            binary_uint8 = (self.edge_layer * 255).astype(np.uint8)
            distance = cv2.distanceTransform(binary_uint8, cv2.DIST_L2, 5)
            try:
                skeleton = cv2.ximgproc.thinning(binary_uint8)
            except:
                skeleton = self._morphological_skeleton(binary_uint8)
            self.edge_skeleton = skeleton > 0
            self.edge_distance = distance * (skeleton > 0)
        
        skeleton_elapsed = time.time() - skeleton_start
        print(f"  Skeleton extraction completed in {skeleton_elapsed:.2f}s")
        
        # Build ordered paths from skeleton
        paths_start = time.time()
        paths = self._extract_ordered_paths(self.edge_skeleton, self.edge_distance)
        paths_elapsed = time.time() - paths_start
        print(f"  Path extraction completed in {paths_elapsed:.2f}s ({len(paths)} paths)")
        
        # Convert paths to stroke points
        for path in paths:
            for i, (y, x, radius) in enumerate(path):
                # Calculate angle from movement direction
                if i > 0:
                    prev_y, prev_x, _ = path[i-1]
                    angle = math.atan2(y - prev_y, x - prev_x)
                elif i < len(path) - 1:
                    next_y, next_x, _ = path[i+1]
                    angle = math.atan2(next_y - y, next_x - x)
                else:
                    angle = 0
                
                # Pressure varies slightly along strokes
                pressure = 0.7 + 0.3 * math.sin(i * 0.1)
                
                stroke_point = StrokePoint(
                    x=x, y=y,
                    pressure=pressure,
                    angle=angle,
                    width=max(1.5, radius * 1.2),
                    phase=DrawingPhase.OUTLINE,
                    intensity=self.intensity_map[int(y), int(x)]
                )
                self.stroke_sequences[DrawingPhase.OUTLINE].append(stroke_point)
        
        print(f"  Generated {len(self.stroke_sequences[DrawingPhase.OUTLINE])} outline stroke points")
    
    def _build_shading_strokes(self):
        """Build stroke sequences for shading using hatching patterns."""
        if not np.any(self.shade_layer > 0):
            print("  No shading detected, skipping shading strokes.")
            return
        
        h, w = self.shade_layer.shape
        
        # --- HATCHING LAYER (Primary direction) ---
        hatching_strokes = self._generate_hatching_strokes(
            self.shade_layer,
            angle=self.hatching_angle,
            spacing=self.stroke_spacing,
            min_intensity=0.1
        )
        
        for stroke in hatching_strokes:
            for point in stroke:
                point.phase = DrawingPhase.HATCHING
            self.stroke_sequences[DrawingPhase.HATCHING].extend(stroke)
        
        print(f"  Generated {len(self.stroke_sequences[DrawingPhase.HATCHING])} hatching stroke points")
        
        # --- CROSS-HATCHING LAYER (Secondary direction, for darker areas) ---
        # Only apply to regions with intensity > 0.4
        dark_shade = np.where(self.shade_layer > 0.35, self.shade_layer, 0)
        
        if np.any(dark_shade > 0):
            cross_hatch_strokes = self._generate_hatching_strokes(
                dark_shade,
                angle=self.cross_hatch_angle,
                spacing=self.stroke_spacing + 1,
                min_intensity=0.35
            )
            
            for stroke in cross_hatch_strokes:
                for point in stroke:
                    point.phase = DrawingPhase.CROSS_HATCHING
                self.stroke_sequences[DrawingPhase.CROSS_HATCHING].extend(stroke)
            
            print(f"  Generated {len(self.stroke_sequences[DrawingPhase.CROSS_HATCHING])} cross-hatching points")
        
        # --- DETAIL LAYER (Very dark areas, multiple passes) ---
        very_dark = np.where(self.shade_layer > 0.6, self.shade_layer, 0)
        
        if np.any(very_dark > 0):
            # Use max(1, spacing-1) to prevent zero spacing
            detail_spacing = max(1, self.stroke_spacing - 1)
            detail_strokes = self._generate_hatching_strokes(
                very_dark,
                angle=self.hatching_angle + math.radians(22.5),
                spacing=detail_spacing,
                min_intensity=0.6
            )
            
            for stroke in detail_strokes:
                for point in stroke:
                    point.phase = DrawingPhase.DETAIL_SHADING
                self.stroke_sequences[DrawingPhase.DETAIL_SHADING].extend(stroke)
            
            print(f"  Generated {len(self.stroke_sequences[DrawingPhase.DETAIL_SHADING])} detail points")
    
    def _generate_hatching_strokes(self, intensity_map: np.ndarray, 
                                    angle: float, spacing: int,
                                    min_intensity: float) -> List[List[StrokePoint]]:
        """
        Generate hatching strokes across the intensity map.
        
        Creates parallel lines at the given angle that cover shaded regions,
        with stroke density proportional to local intensity.
        
        Args:
            intensity_map: 2D array of intensity values (0-1)
            angle: Hatching angle in radians
            spacing: Base spacing between strokes
            min_intensity: Minimum intensity to consider for hatching
            
        Returns:
            List of stroke sequences, each containing StrokePoint objects
        """
        # Use GPU-accelerated version if available
        if self.use_gpu and cp is not None:
            return self._generate_hatching_strokes_gpu(intensity_map, angle, spacing, min_intensity)
        
        return self._generate_hatching_strokes_cpu(intensity_map, angle, spacing, min_intensity)
    
    def _generate_hatching_strokes_gpu(self, intensity_map: np.ndarray,
                                        angle: float, spacing: int,
                                        min_intensity: float) -> List[List[StrokePoint]]:
        """GPU-accelerated hatching stroke generation."""
        start_time = time.time()
        
        h, w = intensity_map.shape
        strokes = []
        
        # Transfer intensity map to GPU
        intensity_gpu = cp.asarray(intensity_map)
        
        # Direction vectors for hatching
        dx = math.cos(angle)
        dy = math.sin(angle)
        perp_dx = -dy
        perp_dy = dx
        
        # Calculate line extent
        diagonal = math.sqrt(w**2 + h**2)
        
        # Guard against zero spacing
        if spacing <= 0:
            spacing = 3  # Default to 3 pixels
        
        num_lines = int(diagonal / spacing) + 1
        start_offset = -diagonal / 2
        
        # Generate all line coordinates on GPU
        t_values = cp.arange(-diagonal/2, diagonal/2, 1.5)
        num_points_per_line = len(t_values)
        
        # Process lines in batches for memory efficiency
        batch_size = 50
        for batch_start in range(0, num_lines, batch_size):
            batch_end = min(batch_start + batch_size, num_lines)
            
            for line_idx in range(batch_start, batch_end):
                offset = start_offset + line_idx * spacing
                cx = w / 2 + perp_dx * offset
                cy = h / 2 + perp_dy * offset
                
                # Calculate coordinates for this line (on GPU)
                x_coords = cx + dx * t_values
                y_coords = cy + dy * t_values
                
                # Convert to integer indices
                ix = cp.floor(x_coords).astype(cp.int32)
                iy = cp.floor(y_coords).astype(cp.int32)
                
                # Create bounds mask
                valid_mask = (ix >= 0) & (ix < w) & (iy >= 0) & (iy < h)
                
                # Get intensities for valid points
                intensities = cp.zeros(num_points_per_line, dtype=cp.float32)
                valid_indices = cp.where(valid_mask)[0]
                
                if len(valid_indices) > 0:
                    valid_ix = ix[valid_mask]
                    valid_iy = iy[valid_mask]
                    intensities[valid_mask] = intensity_gpu[valid_iy, valid_ix]
                
                # Move results back to CPU for stroke creation
                intensities_cpu = cp.asnumpy(intensities)
                x_coords_cpu = cp.asnumpy(x_coords)
                y_coords_cpu = cp.asnumpy(y_coords)
                valid_mask_cpu = cp.asnumpy(valid_mask)
                
                # Build strokes from contiguous segments
                stroke = []
                for i in range(num_points_per_line):
                    if valid_mask_cpu[i] and intensities_cpu[i] >= min_intensity:
                        pressure = min(1.0, intensities_cpu[i] * 1.2)
                        stroke_point = StrokePoint(
                            x=float(x_coords_cpu[i]),
                            y=float(y_coords_cpu[i]),
                            pressure=pressure,
                            angle=angle,
                            width=1.5 + intensities_cpu[i] * 2.0,
                            phase=DrawingPhase.HATCHING,
                            intensity=float(intensities_cpu[i])
                        )
                        stroke.append(stroke_point)
                    elif stroke:
                        if len(stroke) > 2:
                            strokes.append(stroke)
                        stroke = []
                
                if len(stroke) > 2:
                    strokes.append(stroke)
        
        elapsed = time.time() - start_time
        print(f"    [GPU] Hatching generation: {elapsed:.2f}s")
        
        return strokes
    
    def _generate_hatching_strokes_cpu(self, intensity_map: np.ndarray,
                                        angle: float, spacing: int,
                                        min_intensity: float) -> List[List[StrokePoint]]:
        """CPU-based hatching stroke generation (original implementation)."""
        start_time = time.time()
        h, w = intensity_map.shape
        strokes = []
        
        # Direction vectors for hatching
        dx = math.cos(angle)
        dy = math.sin(angle)
        
        # Perpendicular direction for line spacing
        perp_dx = -dy
        perp_dy = dx
        
        # Calculate line extent
        diagonal = math.sqrt(w**2 + h**2)
        
        # Guard against zero spacing
        if spacing <= 0:
            spacing = 3  # Default to 3 pixels
        
        # Generate parallel lines
        num_lines = int(diagonal / spacing) + 1
        start_offset = -diagonal / 2
        
        for line_idx in range(num_lines):
            # Starting point for this line (perpendicular offset from center)
            offset = start_offset + line_idx * spacing
            cx = w / 2 + perp_dx * offset
            cy = h / 2 + perp_dy * offset
            
            # Trace along the line direction
            stroke = []
            
            for t in np.arange(-diagonal/2, diagonal/2, 1.5):
                x = cx + dx * t
                y = cy + dy * t
                
                # Check bounds
                ix, iy = int(x), int(y)
                if 0 <= ix < w and 0 <= iy < h:
                    intensity = intensity_map[iy, ix]
                    
                    if intensity >= min_intensity:
                        # Add point to stroke
                        pressure = min(1.0, intensity * 1.2)  # Scale pressure with intensity
                        
                        stroke_point = StrokePoint(
                            x=x, y=y,
                            pressure=pressure,
                            angle=angle,
                            width=1.5 + intensity * 2.0,  # Width varies with intensity
                            phase=DrawingPhase.HATCHING,  # Will be overwritten
                            intensity=intensity
                        )
                        stroke.append(stroke_point)
                    elif stroke:
                        # End current stroke segment, start new one
                        if len(stroke) > 2:
                            strokes.append(stroke)
                        stroke = []
            
            # Add final stroke segment
            if len(stroke) > 2:
                strokes.append(stroke)
        
        elapsed = time.time() - start_time
        print(f"    [CPU] Hatching generation: {elapsed:.2f}s")
        
        return strokes
    
    def _extract_ordered_paths(self, skeleton: np.ndarray, 
                                distance: np.ndarray) -> List[List[Tuple[int, int, float]]]:
        """Extract ordered paths from skeleton with distance information."""
        # Get skeleton points
        skeleton_points = np.argwhere(skeleton)
        
        if len(skeleton_points) == 0:
            return []
        
        point_set = set(map(tuple, skeleton_points))
        
        # 8-connectivity neighbors
        neighbors_offsets = [
            (-1, -1), (-1, 0), (-1, 1),
            (0, -1),           (0, 1),
            (1, -1),  (1, 0),  (1, 1)
        ]
        
        # Build adjacency graph
        adjacency = {}
        for pt in point_set:
            adjacency[pt] = []
            for dy, dx in neighbors_offsets:
                neighbor = (pt[0] + dy, pt[1] + dx)
                if neighbor in point_set:
                    adjacency[pt].append(neighbor)
        
        # Find endpoints (degree 1)
        endpoints = [pt for pt, neighbors in adjacency.items() if len(neighbors) == 1]
        
        if not endpoints and point_set:
            endpoints = [next(iter(point_set))]
        
        # Trace paths
        paths = []
        visited = set()
        
        def trace_path(start):
            path = []
            current = start
            
            while current not in visited:
                visited.add(current)
                y, x = current
                radius = max(1.0, distance[y, x] * 1.3)
                path.append((y, x, radius))
                
                next_pt = None
                for neighbor in adjacency.get(current, []):
                    if neighbor not in visited:
                        next_pt = neighbor
                        break
                
                if next_pt is None:
                    break
                current = next_pt
            
            return path
        
        # Trace from all endpoints
        for ep in endpoints:
            if ep not in visited:
                path = trace_path(ep)
                if len(path) > 2:
                    paths.append(path)
        
        # Handle remaining cycles
        remaining = point_set - visited
        while remaining:
            start = next(iter(remaining))
            path = trace_path(start)
            if len(path) > 2:
                paths.append(path)
            remaining = point_set - visited
        
        # Sort paths for natural drawing order
        return self._sort_paths_naturally(paths)
    
    def _sort_paths_naturally(self, paths: List) -> List:
        """
        Sort paths for natural hand-drawn appearance.
        
        Instead of strict left-to-right typewriter order, uses:
        1. Clustering nearby paths together
        2. Random-but-logical ordering within regions  
        3. Greedy nearest-neighbor for smooth transitions
        """
        if not paths or len(paths) <= 1:
            return paths
        
        import random
        random.seed(42)  # Reproducible randomness
        
        # Calculate centroid for each path
        path_info = []
        for i, path in enumerate(paths):
            if len(path) > 0:
                # Use first point as reference
                y, x, _ = path[0]
                # Also calculate endpoint
                end_y, end_x, _ = path[-1]
                path_info.append({
                    'index': i,
                    'path': path,
                    'start_x': x,
                    'start_y': y,
                    'end_x': end_x,
                    'end_y': end_y,
                    'length': len(path)
                })
        
        if not path_info:
            return paths
        
        # Divide canvas into regions (grid-based clustering)
        num_regions_x = 4
        num_regions_y = 5
        
        # Get canvas bounds
        all_x = [p['start_x'] for p in path_info]
        all_y = [p['start_y'] for p in path_info]
        min_x, max_x = min(all_x), max(all_x)
        min_y, max_y = min(all_y), max(all_y)
        
        region_width = (max_x - min_x + 1) / num_regions_x
        region_height = (max_y - min_y + 1) / num_regions_y
        
        # Assign paths to regions
        regions = {}
        for p in path_info:
            rx = int((p['start_x'] - min_x) / max(1, region_width))
            ry = int((p['start_y'] - min_y) / max(1, region_height))
            rx = min(rx, num_regions_x - 1)
            ry = min(ry, num_regions_y - 1)
            
            key = (ry, rx)  # Row-major order
            if key not in regions:
                regions[key] = []
            regions[key].append(p)
        
        # Sort regions in a natural drawing pattern (spiral or serpentine)
        sorted_region_keys = sorted(regions.keys(), key=lambda k: (k[0], k[1] if k[0] % 2 == 0 else -k[1]))
        
        # Build final ordered list using greedy nearest-neighbor within each region
        sorted_paths = []
        current_pos = (min_x, min_y)  # Start at top-left
        
        for region_key in sorted_region_keys:
            region_paths = regions[region_key]
            
            # Shuffle slightly for natural variation (not strictly ordered)
            random.shuffle(region_paths)
            
            # Use nearest-neighbor within region
            remaining = region_paths.copy()
            while remaining:
                # Find path starting closest to current position
                best_idx = 0
                best_dist = float('inf')
                
                for i, p in enumerate(remaining):
                    dist = math.sqrt((p['start_x'] - current_pos[0])**2 + 
                                    (p['start_y'] - current_pos[1])**2)
                    if dist < best_dist:
                        best_dist = dist
                        best_idx = i
                
                best_path = remaining.pop(best_idx)
                sorted_paths.append(best_path['path'])
                current_pos = (best_path['end_x'], best_path['end_y'])
        
        return sorted_paths
    
    def _add_pen_lift_markers(self, stroke_sequences: Dict[DrawingPhase, List[StrokePoint]]) -> Dict[DrawingPhase, List[StrokePoint]]:
        """
        Add pen-lift markers between discontinuous strokes to prevent
        drawing lines across when pen moves to a new location.
        
        This is handled during reveal by checking distance between consecutive points.
        """
        # The actual pen-lift is handled in reveal_next_batch by checking
        # if the distance between consecutive points is too large
        # This method ensures the stroke sequences are properly segmented
        return stroke_sequences
    
    def _morphological_skeleton(self, binary: np.ndarray) -> np.ndarray:
        """Fallback skeletonization using morphological operations."""
        skeleton = np.zeros_like(binary)
        element = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
        temp = binary.copy()
        
        while True:
            eroded = cv2.erode(temp, element)
            opened = cv2.dilate(eroded, element)
            subset = cv2.subtract(temp, opened)
            skeleton = cv2.bitwise_or(skeleton, subset)
            temp = eroded.copy()
            if cv2.countNonZero(temp) == 0:
                break
        
        return skeleton
    
    def _merge_sequences(self):
        """
        Merge all stroke sequences into a single reveal sequence.
        
        The ordering strategy is:
        1. Complete edge phases first (based on edge_phases_first setting)
           - 1: Just OUTLINE first
           - 2: OUTLINE + HATCHING first
           - 3: OUTLINE + HATCHING + CROSS_HATCHING first
        2. Then remaining phases are added in top-to-bottom order (based on shading_order)
        
        This creates a natural drawing effect where the artist first draws
        all the main outlines/structure, then fills in shading.
        """
        print(f"\n  Merging sequences (edge_phases_first={self.edge_phases_first}, shading_order={self.shading_order})")
        
        # Define which phases are "edge" phases vs "shading" phases
        edge_phases = [DrawingPhase.OUTLINE]
        if self.edge_phases_first >= 2:
            edge_phases.append(DrawingPhase.HATCHING)
        if self.edge_phases_first >= 3:
            edge_phases.append(DrawingPhase.CROSS_HATCHING)
        
        # All other phases are shading phases
        all_phases = [
            DrawingPhase.OUTLINE,
            DrawingPhase.HATCHING,
            DrawingPhase.CROSS_HATCHING,
            DrawingPhase.DETAIL_SHADING,
        ]
        shading_phases = [p for p in all_phases if p not in edge_phases]
        
        self.reveal_sequence = []
        
        # PART 1: Add edge phases first (with natural sorting already applied)
        for phase in edge_phases:
            strokes = self.stroke_sequences[phase]
            if strokes:
                print(f"    Adding {len(strokes)} points for edge phase: {phase.name}")
                self.reveal_sequence.extend(strokes)
        
        edge_count = len(self.reveal_sequence)
        print(f"    Total edge points: {edge_count}")
        
        # PART 2: Add shading phases in configured order
        shading_strokes = []
        for phase in shading_phases:
            strokes = self.stroke_sequences[phase]
            if strokes:
                shading_strokes.extend(strokes)
        
        if shading_strokes:
            # Sort shading strokes based on shading_order
            if self.shading_order == "top_to_bottom":
                # Sort by Y position (top to bottom), then X (left to right)
                shading_strokes.sort(key=lambda p: (p.y, p.x))
                print(f"    Sorting {len(shading_strokes)} shading points: top-to-bottom")
            elif self.shading_order == "random":
                # Shuffle for random order (good for some effects)
                import random
                random.shuffle(shading_strokes)
                print(f"    Sorting {len(shading_strokes)} shading points: random")
            else:
                # "natural" - keep as-is (already sorted by _sort_paths_naturally)
                print(f"    Keeping {len(shading_strokes)} shading points in natural order")
            
            self.reveal_sequence.extend(shading_strokes)
        
        print(f"  Total reveal sequence: {len(self.reveal_sequence)} points")
        print(f"    - Edge phases: {edge_count} points (drawn first)")
        print(f"    - Shading phases: {len(shading_strokes)} points (drawn after edges)")
    
    def _init_animation_state(self):
        """Initialize the animation state."""
        h, w = self.original_image.shape[:2]
        self.reveal_mask = np.zeros((h, w), dtype=np.float32)
        self.pressure_map = np.zeros((h, w), dtype=np.float32)
        self.current_reveal_idx = 0
        self.current_phase = DrawingPhase.OUTLINE
    
    def get_points_per_update(self) -> int:
        """Get the number of points to reveal per update based on current phase."""
        if self.current_reveal_idx >= len(self.reveal_sequence):
            return 0
        
        current_point = self.reveal_sequence[self.current_reveal_idx]
        phase = current_point.phase
        
        config = self.speed_config
        
        if phase == DrawingPhase.OUTLINE:
            return config.outline_points_per_update
        elif phase == DrawingPhase.HATCHING:
            return config.hatching_points_per_update
        elif phase == DrawingPhase.CROSS_HATCHING:
            return config.cross_hatch_points_per_update
        elif phase == DrawingPhase.DETAIL_SHADING:
            return config.detail_points_per_update
        else:
            return config.blending_points_per_update
    
    def reveal_next_batch(self, points_per_update: Optional[int] = None) -> bool:
        """
        Reveal the next batch of stroke points.
        
        Args:
            points_per_update: Override points per update (if None, use phase-based)
            
        Returns:
            True if there are more points to reveal, False if done
        """
        if self.current_reveal_idx >= len(self.reveal_sequence):
            return False
        
        if points_per_update is None:
            points_per_update = self.get_points_per_update()
        
        end_idx = min(self.current_reveal_idx + points_per_update, 
                      len(self.reveal_sequence))
        
        # Process this batch of points
        prev_point = None
        
        for i in range(self.current_reveal_idx, end_idx):
            point = self.reveal_sequence[i]
            
            # Update current phase tracking
            self.current_phase = point.phase
            
            # Draw stroke segment
            self._draw_stroke_point(point, prev_point)
            
            prev_point = point
        
        self.current_reveal_idx = end_idx
        return True
    
    def _draw_stroke_point(self, point: StrokePoint, prev_point: Optional[StrokePoint]):
        """Draw a single stroke point with natural pencil effect."""
        x, y = int(point.x), int(point.y)
        
        if not (0 <= x < self.reveal_mask.shape[1] and 0 <= y < self.reveal_mask.shape[0]):
            return
        
        # Calculate effective radius based on phase and pressure
        base_radius = point.width
        
        if point.phase == DrawingPhase.OUTLINE:
            # Outlines use the skeleton-derived width
            radius = max(1.5, base_radius)
            opacity = point.pressure * 0.9
        else:
            # Hatching uses thinner strokes
            radius = max(1.0, base_radius * 0.7)
            opacity = point.pressure * 0.7
        
        # Draw with soft edges for natural look
        self._draw_soft_circle(x, y, radius, opacity, point.intensity)
        
        # Interpolate between points for smooth strokes
        # BUT only if the distance is reasonable (pen is not "lifted")
        if prev_point is not None:
            dist = math.sqrt((point.x - prev_point.x)**2 + (point.y - prev_point.y)**2)
            
            # PEN LIFT THRESHOLD: If distance is too large, don't interpolate
            # This prevents drawing lines across when pen moves to a new location
            pen_lift_threshold = 15.0  # pixels - if further than this, pen is "lifted"
            
            if dist > 1.5 and dist < pen_lift_threshold:
                # Normal interpolation for continuous strokes
                steps = int(dist / 1.0)
                for step in range(1, steps):
                    t = step / steps
                    ix = prev_point.x + t * (point.x - prev_point.x)
                    iy = prev_point.y + t * (point.y - prev_point.y)
                    ip = prev_point.pressure + t * (point.pressure - prev_point.pressure)
                    ir = prev_point.width + t * (point.width - prev_point.width)
                    
                    int_radius = max(1.0, ir * (0.7 if point.phase != DrawingPhase.OUTLINE else 1.0))
                    int_opacity = ip * (0.7 if point.phase != DrawingPhase.OUTLINE else 0.9)
                    int_intensity = prev_point.intensity + t * (point.intensity - prev_point.intensity)
                    
                    self._draw_soft_circle(int(ix), int(iy), int_radius, int_opacity, int_intensity)
    
    def _draw_soft_circle(self, x: int, y: int, radius: float, 
                          opacity: float, intensity: float):
        """
        Draw a circle with soft edges for natural pencil look.
        
        Uses Gaussian falloff from center for anti-aliased, soft brush effect.
        """
        h, w = self.reveal_mask.shape
        
        # Create a small patch around the point
        r_int = int(np.ceil(radius * (1.5 + self.brush_softness)))
        
        # Bounds check
        x1 = max(0, x - r_int)
        x2 = min(w, x + r_int + 1)
        y1 = max(0, y - r_int)
        y2 = min(h, y + r_int + 1)
        
        if x2 <= x1 or y2 <= y1:
            return
        
        # Create coordinate grid for the patch
        yy, xx = np.mgrid[y1:y2, x1:x2]
        
        # Distance from center
        dist = np.sqrt((xx - x)**2 + (yy - y)**2)
        
        # Soft falloff using Gaussian-like function
        if self.brush_softness > 0:
            # Soft edges
            sigma = radius * self.brush_softness
            falloff = np.exp(-0.5 * (dist / max(0.5, sigma))**2)
            mask_values = np.where(dist <= radius, 1.0, falloff)
            mask_values = np.clip(mask_values, 0, 1)
        else:
            # Hard edges
            mask_values = (dist <= radius).astype(np.float32)
        
        # Apply opacity and intensity
        contribution = mask_values * opacity * intensity
        
        # Update reveal mask (use maximum to avoid over-darkening)
        current = self.reveal_mask[y1:y2, x1:x2]
        self.reveal_mask[y1:y2, x1:x2] = np.maximum(current, contribution)
    
    def get_current_frame(self) -> np.ndarray:
        """
        Get the current frame with revealed pixels.
        
        Returns:
            RGB numpy array of the current frame
        """
        # The reveal mask now contains intensity values (how much to reveal)
        # We blend between white background and original image
        
        # Clamp reveal mask to valid range
        reveal = np.clip(self.reveal_mask, 0, 1)
        
        # Only reveal within the binary mask (where ink exists)
        effective_reveal = reveal * self.binary_mask.astype(np.float32)
        
        # Expand to 3 channels
        reveal_3ch = np.stack([effective_reveal] * 3, axis=-1)
        
        # Compose: background * (1 - reveal) + original * reveal
        frame = self.bg_color * (1 - reveal_3ch) + self.original_image * reveal_3ch
        
        return frame.astype(np.uint8)
    
    def get_progress(self) -> float:
        """Get current reveal progress as a float 0-1."""
        if len(self.reveal_sequence) == 0:
            return 1.0
        return self.current_reveal_idx / len(self.reveal_sequence)
    
    def get_current_pen_position(self) -> Tuple[int, int]:
        """Get the current pen position for cursor display."""
        if self.current_reveal_idx > 0 and self.current_reveal_idx <= len(self.reveal_sequence):
            point = self.reveal_sequence[self.current_reveal_idx - 1]
            return (int(point.x), int(point.y))
        elif len(self.reveal_sequence) > 0:
            point = self.reveal_sequence[0]
            return (int(point.x), int(point.y))
        return (self.target_width // 2, self.target_height // 2)
    
    def get_current_phase_name(self) -> str:
        """Get the name of the current drawing phase."""
        return self.current_phase.value.replace("_", " ").title()
    
    def is_complete(self) -> bool:
        """Check if reveal animation is complete."""
        return self.current_reveal_idx >= len(self.reveal_sequence)
    
    def reset(self):
        """Reset the animation to the beginning."""
        h, w = self.original_image.shape[:2]
        self.reveal_mask = np.zeros((h, w), dtype=np.float32)
        self.pressure_map = np.zeros((h, w), dtype=np.float32)
        self.current_reveal_idx = 0
        self.current_phase = DrawingPhase.OUTLINE


# Compatibility alias for backward compatibility with existing code
class AdvancedPixelRevealEngine(PencilShadingEngine):
    """Alias for backward compatibility."""
    pass
