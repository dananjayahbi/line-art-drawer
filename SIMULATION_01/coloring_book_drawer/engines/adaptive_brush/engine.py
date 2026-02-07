"""
Adaptive Brush Simulation Engine (Engine 3E)
==============================================
Physics-based pencil simulation with tip shape modeling,
paper texture interaction, pressure dynamics, and graphite
accumulation with saturation behavior.

Pipeline:
  Stage 1: Stroke Extraction - Extract drawing paths from image
  Stage 2: Physics Setup - Initialize pencil tip, paper, accumulator
  Stage 3: Dynamics Computation - Compute pressure/velocity/tremor per stroke
  Stage 4: Rendering - Apply graphite deposits and compose frames
"""

import numpy as np
from typing import Optional, Callable, Tuple, List

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

try:
    from skimage.morphology import skeletonize
    HAS_SKIMAGE = True
except ImportError:
    HAS_SKIMAGE = False

from .config import AdaptiveBrushConfig, TipShape, PaperType
from .physics.pencil_tip import PencilTip
from .physics.paper_texture import PaperTexture
from .physics.graphite_deposit import GraphiteDeposit
from .physics.accumulator import GraphiteAccumulator
from .dynamics.pressure_controller import PressureDynamicsController
from .dynamics.velocity_model import VelocityModel
from .dynamics.tremor_noise import TremorNoise
from .rendering.canvas import VirtualCanvas
from .rendering.frame_export import FrameExporter


class AdaptiveBrushEngine:
    """
    Engine 3E: Adaptive Brush Simulation
    
    Simulates realistic pencil drawing with physics-based graphite
    deposit, paper texture interaction, and natural pressure dynamics.
    """
    
    def __init__(self, image_path: str, width: int, height: int,
                 padding: int = 40, use_gpu: bool = False,
                 tip_shape: str = "round",
                 pencil_hardness: float = 0.5,
                 pencil_sharpness: float = 0.7,
                 paper_type: str = "cold_press",
                 paper_texture_strength: float = 0.5,
                 pressure_variation: float = 0.5,
                 graphite_buildup: float = 0.7):
        """
        Args:
            image_path: Path to the input artwork
            width: Display width in pixels
            height: Display height in pixels
            padding: Padding around the image
            use_gpu: Whether to attempt GPU acceleration
            tip_shape: "round", "chisel", or "blunt"
            pencil_hardness: 0=soft(6B), 1=hard(4H)
            pencil_sharpness: 0=dull, 1=sharp
            paper_type: "smooth", "cold_press", or "rough"
            paper_texture_strength: How much texture affects deposit (0-1)
            pressure_variation: Amount of natural pressure variation (0-1)
            graphite_buildup: How quickly graphite saturates (0-1)
        """
        self.image_path = str(image_path)
        self.display_width = width
        self.display_height = height
        self.padding = padding
        
        # Build config from parameters
        self.config = AdaptiveBrushConfig.from_params(
            tip_shape=tip_shape,
            pencil_hardness=pencil_hardness,
            pencil_sharpness=pencil_sharpness,
            paper_type=paper_type,
            paper_texture_strength=paper_texture_strength,
            pressure_variation=pressure_variation,
            graphite_buildup=graphite_buildup,
            use_gpu=use_gpu
        )
        
        # Public state (matches engine interface)
        self.original_image = None    # (H, W, 3) uint8 RGB - padded & scaled
        self.reveal_mask = None       # (H, W) bool - current reveal state
        self.current_reveal_idx = 0   # For compatibility with main.py
        
        # Internal components
        self._pencil_tip = None       # PencilTip
        self._paper = None            # PaperTexture
        self._deposit_calc = None     # GraphiteDeposit
        self._accumulator = None      # GraphiteAccumulator
        self._pressure_ctrl = None    # PressureDynamicsController
        self._velocity_model = None   # VelocityModel
        self._tremor = None           # TremorNoise
        self._canvas = None           # VirtualCanvas
        self._exporter = None         # FrameExporter
        
        # Stroke data
        self._strokes = []            # List of (N, 2) stroke paths
        self._stroke_pressures = []   # Pressure envelope per stroke
        self._stroke_angles = []      # Angles per stroke
        self._target_darkness = None  # Grayscale target (0=dark, 1=light)
        self._ink_mask = None         # Boolean mask of content pixels
        
        # Progress tracking
        self._flat_points = None      # Flattened (M, 2) all stroke points
        self._flat_pressures = None   # Corresponding pressures
        self._flat_angles = None      # Corresponding angles
        self._total_points = 0        # Total rendering points
        self._rendered_points = 0     # Points rendered so far
        self._pen_position = (width // 2, height // 2)
        self._processed = False
    
    # ──────────────────────────────────────────────────────────────────────
    #  STAGE 0: Image Loading & Scaling
    # ──────────────────────────────────────────────────────────────────────
    
    def _load_and_scale_image(self) -> np.ndarray:
        """Load image, scale to fit display, and center with padding."""
        img = cv2.imread(self.image_path)
        if img is None:
            raise FileNotFoundError(f"Cannot load image: {self.image_path}")
        
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        target_w = self.display_width - 2 * self.padding
        target_h = self.display_height - 2 * self.padding
        
        h, w = img.shape[:2]
        scale = min(target_w / w, target_h / h)
        new_w = int(w * scale)
        new_h = int(h * scale)
        
        resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        
        canvas = np.full((self.display_height, self.display_width, 3), 255, dtype=np.uint8)
        x_offset = (self.display_width - new_w) // 2
        y_offset = (self.display_height - new_h) // 2
        canvas[y_offset:y_offset + new_h, x_offset:x_offset + new_w] = resized
        
        return canvas
    
    # ──────────────────────────────────────────────────────────────────────
    #  STAGE 1: Stroke Extraction
    # ──────────────────────────────────────────────────────────────────────
    
    def _extract_strokes(self, gray: np.ndarray, ink_mask: np.ndarray) -> List[np.ndarray]:
        """
        Extract ordered stroke paths from the image.
        Uses skeletonization to find center lines, then traces paths.
        """
        strokes = []
        
        # Create binary image from ink mask
        binary = ink_mask.astype(np.uint8) * 255
        
        # Try skeletonization for clean center lines
        if HAS_SKIMAGE:
            try:
                skeleton = skeletonize(ink_mask).astype(np.uint8)
            except Exception:
                skeleton = self._fallback_skeleton(binary)
        else:
            skeleton = self._fallback_skeleton(binary)
        
        # Find connected components in skeleton
        if HAS_CV2:
            num_labels, labels = cv2.connectedComponents(skeleton * 255 if skeleton.max() <= 1 else skeleton)
        else:
            num_labels = 1
            labels = skeleton
        
        # Trace each connected component as a stroke
        for label_id in range(1, num_labels):
            points = np.argwhere(labels == label_id)  # (N, 2) as (y, x)
            if len(points) < self.config.extraction.min_stroke_length:
                continue
                
            # Order points along the stroke path using nearest-neighbor
            ordered = self._order_stroke_points(points)
            strokes.append(ordered)
        
        # If no strokes found, create scan-line strokes from ink pixels
        if len(strokes) == 0:
            strokes = self._create_scanline_strokes(ink_mask)
        
        return strokes
    
    def _fallback_skeleton(self, binary: np.ndarray) -> np.ndarray:
        """Fallback skeletonization using morphological thinning with OpenCV."""
        if not HAS_CV2:
            return binary
        
        # Simple morphological skeleton
        skeleton = np.zeros_like(binary)
        element = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
        temp = binary.copy()
        
        for _ in range(100):  # Max iterations
            eroded = cv2.erode(temp, element)
            opened = cv2.dilate(eroded, element)
            diff = cv2.subtract(temp, opened)
            skeleton = cv2.bitwise_or(skeleton, diff)
            temp = eroded.copy()
            if cv2.countNonZero(temp) == 0:
                break
        
        return (skeleton > 0).astype(np.uint8)
    
    def _order_stroke_points(self, points: np.ndarray) -> np.ndarray:
        """Order scattered points into a sequential path using nearest-neighbor."""
        if len(points) <= 2:
            return points.astype(np.float32)
        
        # Start from the point with smallest y (top-most)
        start_idx = np.argmin(points[:, 0])
        
        ordered = [points[start_idx]]
        remaining = set(range(len(points)))
        remaining.remove(start_idx)
        
        current = points[start_idx]
        
        while remaining:
            # Find nearest unvisited point
            remaining_list = list(remaining)
            candidates = points[remaining_list]
            distances = ((candidates - current) ** 2).sum(axis=1)
            nearest_local_idx = np.argmin(distances)
            nearest_global_idx = remaining_list[nearest_local_idx]
            
            # Break if too far (gap in stroke)
            if distances[nearest_local_idx] > 100:  # 10px gap threshold
                # Start new implicit sub-stroke
                if len(remaining) > self.config.extraction.min_stroke_length:
                    remaining_array = points[list(remaining)]
                    start_in_remaining = np.argmin(remaining_array[:, 0])
                    nearest_global_idx = list(remaining)[start_in_remaining]
            
            ordered.append(points[nearest_global_idx])
            remaining.remove(nearest_global_idx)
            current = points[nearest_global_idx]
        
        return np.array(ordered, dtype=np.float32)
    
    def _create_scanline_strokes(self, ink_mask: np.ndarray) -> List[np.ndarray]:
        """Create simple scan-line strokes as fallback when skeletonization fails."""
        strokes = []
        h, w = ink_mask.shape
        
        # Scan horizontally with stride
        stride = max(2, int(4 * (1.0 - self.config.tip.sharpness + 0.3)))
        
        for row in range(0, h, stride):
            # Find runs of ink pixels in this row
            ink_cols = np.where(ink_mask[row])[0]
            if len(ink_cols) < 3:
                continue
            
            # Split into continuous runs
            runs = np.split(ink_cols, np.where(np.diff(ink_cols) > 3)[0] + 1)
            for run in runs:
                if len(run) < self.config.extraction.min_stroke_length:
                    continue
                points = np.column_stack([np.full(len(run), row), run]).astype(np.float32)
                strokes.append(points)
        
        return strokes
    
    # ──────────────────────────────────────────────────────────────────────
    #  STAGE 2-3: Physics & Dynamics Setup
    # ──────────────────────────────────────────────────────────────────────
    
    def _setup_physics(self, h: int, w: int):
        """Initialize all physics and dynamics components."""
        # Physics
        self._pencil_tip = PencilTip(self.config.tip)
        self._paper = PaperTexture(self.config.paper)
        self._paper.generate(h, w)
        self._accumulator = GraphiteAccumulator(self.config.accumulator)
        self._accumulator.initialize(h, w)
        self._deposit_calc = GraphiteDeposit(self._pencil_tip, self._paper)
        
        # Dynamics
        self._pressure_ctrl = PressureDynamicsController(self.config.pressure)
        self._velocity_model = VelocityModel(self.config.pressure)
        self._tremor = TremorNoise(self.config.pressure)
        
        # Rendering
        self._canvas = VirtualCanvas(h, w)
        self._exporter = FrameExporter(h, w)
    
    def _compute_stroke_dynamics(self, strokes: List[np.ndarray],
                                 gray: np.ndarray) -> tuple:
        """
        Compute pressure, velocity, and tremor for all strokes.
        
        Returns:
            (all_pressures, all_angles): Lists matching strokes
        """
        all_pressures = []
        all_angles = []
        
        for i, stroke in enumerate(strokes):
            n = len(stroke)
            seed = i * 31  # Deterministic but varied per stroke
            
            # Base pressure envelope (attack-sustain-release)
            base_pressure = self._pressure_ctrl.generate_pressure_envelope(
                n, base_pressure=0.7, seed=seed
            )
            
            # Velocity modifier
            velocities = self._velocity_model.compute_velocities(stroke)
            vel_modifier = self._velocity_model.velocity_pressure_modifier(velocities)
            
            # Target darkness modulation
            target_dark = np.zeros(n, dtype=np.float32)
            for j in range(n):
                y, x = int(stroke[j, 0]), int(stroke[j, 1])
                y = max(0, min(gray.shape[0]-1, y))
                x = max(0, min(gray.shape[1]-1, x))
                # Invert: darker pixel = higher target
                target_dark[j] = 1.0 - (gray[y, x] / 255.0)
            
            modulated = self._pressure_ctrl.modulate_with_darkness(
                base_pressure * vel_modifier, target_dark
            )
            
            # Tremor on pressure
            tremor_press = self._tremor.generate_pressure_tremor(n, seed=seed)
            final_pressure = np.clip(modulated * tremor_press, 0, 1)
            
            # Stroke angles
            angles = self._velocity_model.compute_angles(stroke)
            
            all_pressures.append(final_pressure)
            all_angles.append(angles)
        
        return all_pressures, all_angles
    
    def _apply_tremor_to_strokes(self, strokes: List[np.ndarray],
                                  h: int, w: int) -> List[np.ndarray]:
        """Apply hand tremor offsets to stroke paths."""
        perturbed = []
        for i, stroke in enumerate(strokes):
            pts = self._tremor.apply_to_points(stroke, seed=i * 17)
            # Clamp to canvas
            pts[:, 0] = np.clip(pts[:, 0], 0, h - 1)
            pts[:, 1] = np.clip(pts[:, 1], 0, w - 1)
            perturbed.append(pts)
        return perturbed
    
    # ──────────────────────────────────────────────────────────────────────
    #  MAIN PROCESSING PIPELINE
    # ──────────────────────────────────────────────────────────────────────
    
    def process_image(self, progress_callback: Optional[Callable] = None):
        """
        Run the full processing pipeline.
        
        Args:
            progress_callback: Optional callback(step: int, name: str)
        """
        def report(step, name):
            print(f"    [{step}/6] {name}")
            if progress_callback:
                progress_callback(step, name)
        
        # Stage 0: Load image
        report(1, "Loading and scaling image...")
        self.original_image = self._load_and_scale_image()
        h, w = self.original_image.shape[:2]
        self.reveal_mask = np.zeros((h, w), dtype=bool)
        
        gray = cv2.cvtColor(self.original_image, cv2.COLOR_RGB2GRAY)
        self._target_darkness = gray
        self._ink_mask = gray < self.config.extraction.dark_threshold
        
        # Stage 1: Extract strokes
        report(2, "Extracting stroke paths...")
        self._strokes = self._extract_strokes(gray, self._ink_mask)
        print(f"    Extracted {len(self._strokes)} strokes")
        
        # Stage 2: Setup physics
        report(3, "Initializing pencil physics...")
        self._setup_physics(h, w)
        
        # Stage 3: Compute dynamics
        report(4, "Computing pressure dynamics...")
        self._stroke_pressures, self._stroke_angles = self._compute_stroke_dynamics(
            self._strokes, gray
        )
        
        # Apply tremor to stroke paths
        report(5, "Applying hand tremor...")
        self._strokes = self._apply_tremor_to_strokes(self._strokes, h, w)
        
        # Flatten all strokes into single sequence for incremental reveal
        report(6, "Building render sequence...")
        self._flatten_strokes()
        
        self._processed = True
        self._rendered_points = 0
        self.current_reveal_idx = 0
        
        print(f"    Total render points: {self._total_points}")
        print("    ✅ Adaptive Brush Engine ready!")
    
    def _flatten_strokes(self):
        """Flatten all stroke points/pressures/angles into single arrays."""
        if not self._strokes:
            self._flat_points = np.zeros((0, 2), dtype=np.float32)
            self._flat_pressures = np.zeros(0, dtype=np.float32)
            self._flat_angles = np.zeros(0, dtype=np.float32)
            self._total_points = 0
            return
        
        self._flat_points = np.concatenate(self._strokes, axis=0)
        self._flat_pressures = np.concatenate(self._stroke_pressures, axis=0)
        self._flat_angles = np.concatenate(self._stroke_angles, axis=0)
        self._total_points = len(self._flat_points)
    
    # ──────────────────────────────────────────────────────────────────────
    #  REVEAL INTERFACE (matches other engines)
    # ──────────────────────────────────────────────────────────────────────
    
    def reveal_next_batch(self, points_per_update: int = 100) -> bool:
        """
        Render the next batch of stroke points.
        
        Args:
            points_per_update: Number of points to render
            
        Returns:
            True if more to render, False if complete
        """
        if not self._processed or self._total_points == 0:
            return False
        
        start = self._rendered_points
        end = min(start + points_per_update, self._total_points)
        
        if start >= self._total_points:
            return False
        
        # Render batch of points
        batch_points = self._flat_points[start:end]
        batch_pressures = self._flat_pressures[start:end]
        batch_angles = self._flat_angles[start:end]
        
        for i in range(len(batch_points)):
            y = int(batch_points[i, 0])
            x = int(batch_points[i, 1])
            pressure = float(batch_pressures[i])
            angle = float(batch_angles[i])
            
            deposit, ys, xs = self._deposit_calc.compute_deposit(
                y, x, pressure, angle
            )
            if deposit is not None:
                self._accumulator.apply_deposit(deposit, ys, xs)
        
        # Update reveal mask
        self.reveal_mask = self._accumulator.get_visible_mask(0.01)
        
        # Update pen position
        if len(batch_points) > 0:
            last_y = int(batch_points[-1, 0])
            last_x = int(batch_points[-1, 1])
            self._pen_position = (last_x, last_y)  # (x, y)
            self._exporter.update_pen_position(last_y, last_x)
        
        self._rendered_points = end
        self.current_reveal_idx = end
        
        return end < self._total_points
    
    def get_current_frame(self) -> np.ndarray:
        """
        Get the current composited frame.
        
        Returns:
            (H, W, 3) uint8 RGB frame
        """
        if not self._processed or self._canvas is None:
            return np.full((self.display_height, self.display_width, 3),
                           255, dtype=np.uint8)
        
        return self._canvas.composite_frame(
            self._accumulator, self.original_image, reveal_mode=True
        )
    
    def get_points_per_update(self) -> int:
        """
        Get recommended points per update.
        
        Returns:
            Points per frame for smooth animation
        """
        if not self._processed or self._total_points == 0:
            return 100
        
        # Aim for ~300 frames of content
        base = max(50, self._total_points // 300)
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
        Get overall drawing progress.
        
        Returns:
            Float 0.0 to 1.0
        """
        if self._total_points == 0:
            return 0.0
        return min(1.0, self._rendered_points / self._total_points)
    
    def reset(self):
        """Reset the drawing to the beginning."""
        self._rendered_points = 0
        self.current_reveal_idx = 0
        self._pen_position = (self.display_width // 2, self.display_height // 2)
        
        if self.original_image is not None:
            h, w = self.original_image.shape[:2]
            self.reveal_mask = np.zeros((h, w), dtype=bool)
        
        # Re-initialize accumulator
        if self._accumulator is not None and self.original_image is not None:
            h, w = self.original_image.shape[:2]
            self._accumulator.initialize(h, w)
        
        # Reset tremor phase
        if self._tremor is not None:
            self._tremor._phase = 0.0
