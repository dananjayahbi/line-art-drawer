"""
Hybrid Multi-Strategy Engine (Engine 3F)
==========================================
The most complex engine: analyses the image by region, classifies each
region's visual characteristics, assigns the optimal rendering strategy,
and orchestrates a coordinated multi-strategy reveal.

Pipeline:
  Stage 1: Segmentation   — Split image into meaningful regions
  Stage 2: Classification  — Classify each region (gradient/texture/edge/shadow/highlight/focal)
  Stage 3: Assignment      — Assign the best strategy per region
  Stage 4: Orchestration   — Generate coordinated, blended reveal
"""

import numpy as np
from typing import Optional, Callable, Tuple, List

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

from .config import HybridMultiConfig
from .classification.segmenter import ImageSegmenter
from .classification.classifier import RegionClassifier, RegionInfo
from .classification.focal_detector import FocalDetector
from .assignment.strategy_assigner import StrategyAssigner
from .assignment.preference_rules import PreferenceRules
from .orchestration.orchestrator import MultiStrategyOrchestrator
from .orchestration.stroke_merger import StrokeMerger
from .orchestration.transition_blender import TransitionBlender
from .rendering.unified_renderer import UnifiedRenderer


class HybridMultiEngine:
    """
    Engine 3F: Hybrid Multi-Strategy

    Analyses each region of the artwork and selects the optimal drawing
    strategy, then coordinates a unified reveal across all regions with
    smooth boundary transitions.
    """

    def __init__(self, image_path: str, width: int, height: int,
                 padding: int = 40, use_gpu: bool = False,
                 num_segments: int = 100,
                 min_region_area: int = 500,
                 transition_width: int = 10,
                 blend_smoothness: float = 0.7,
                 strategy_mode: str = "auto",
                 focal_detection: bool = True):
        """
        Args:
            image_path: Path to the input artwork.
            width: Display width in pixels.
            height: Display height in pixels.
            padding: Padding around the image.
            use_gpu: Whether to attempt GPU acceleration.
            num_segments: Target number of superpixel segments.
            min_region_area: Minimum region area in pixels.
            transition_width: Pixel width of boundary blending zones.
            blend_smoothness: Gaussian smoothness for blending (0-1).
            strategy_mode: "auto", "gradient_only", "brush_only", or "full".
            focal_detection: Enable face/saliency-based focal detection.
        """
        self.image_path = str(image_path)
        self.display_width = width
        self.display_height = height
        self.padding = padding

        # Build master config from flat parameters
        self.config = HybridMultiConfig.from_params(
            num_segments=num_segments,
            min_region_area=min_region_area,
            transition_width=transition_width,
            blend_smoothness=blend_smoothness,
            strategy_mode=strategy_mode,
            focal_detection=focal_detection,
            use_gpu=use_gpu,
        )

        # ── Public state (engine interface) ───────────────────────────
        self.original_image: Optional[np.ndarray] = None  # (H,W,3) uint8 RGB
        self.reveal_mask: Optional[np.ndarray] = None      # (H,W) bool
        self.current_reveal_idx: int = 0

        # ── Internal pipeline components ──────────────────────────────
        self._segmenter: Optional[ImageSegmenter] = None
        self._classifier: Optional[RegionClassifier] = None
        self._focal_detector: Optional[FocalDetector] = None
        self._assigner: Optional[StrategyAssigner] = None
        self._orchestrator: Optional[MultiStrategyOrchestrator] = None
        self._merger: Optional[StrokeMerger] = None
        self._blender: Optional[TransitionBlender] = None
        self._renderer: Optional[UnifiedRenderer] = None

        # ── Region data ───────────────────────────────────────────────
        self._regions: List[RegionInfo] = []
        self._gray: Optional[np.ndarray] = None  # grayscale (H,W)

        # ── Progress tracking ─────────────────────────────────────────
        self._total_steps: int = 1000   # Number of reveal increments
        self._current_step: int = 0
        self._pen_position: Tuple[int, int] = (width // 2, height // 2)
        self._processed: bool = False

    # ──────────────────────────────────────────────────────────────────
    #  Image Loading & Scaling
    # ──────────────────────────────────────────────────────────────────

    def _load_and_scale_image(self) -> np.ndarray:
        """Load, scale, and pad the image to fit the display."""
        if not HAS_CV2:
            raise ImportError("OpenCV is required for image loading")

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

        canvas = np.full(
            (self.display_height, self.display_width, 3), 255, dtype=np.uint8
        )
        x_offset = (self.display_width - new_w) // 2
        y_offset = (self.display_height - new_h) // 2
        canvas[y_offset:y_offset + new_h, x_offset:x_offset + new_w] = resized

        return canvas

    # ──────────────────────────────────────────────────────────────────
    #  Stage 1: Segmentation
    # ──────────────────────────────────────────────────────────────────

    def _run_segmentation(self, gray: np.ndarray) -> np.ndarray:
        """Segment the image into super-pixel regions."""
        self._segmenter = ImageSegmenter(self.config.segmentation)
        # segment() requires both the color image and grayscale
        segments = self._segmenter.segment(self.original_image, gray)
        return segments

    # ──────────────────────────────────────────────────────────────────
    #  Stage 2: Classification
    # ──────────────────────────────────────────────────────────────────

    def _run_classification(self, gray: np.ndarray,
                            segments: np.ndarray) -> List[RegionInfo]:
        """Classify each segment by visual characteristics."""
        # Focal detection (optional)
        focal_mask = None
        if self.config.classification.focal_detection:
            self._focal_detector = FocalDetector(self.config.classification)
            focal_mask = self._focal_detector.detect_focal_mask(
                gray, self.original_image
            )

        # Classify regions
        self._classifier = RegionClassifier(self.config.classification)
        regions = self._classifier.classify_regions(gray, segments, focal_mask)

        return regions

    # ──────────────────────────────────────────────────────────────────
    #  Stage 3: Strategy Assignment
    # ──────────────────────────────────────────────────────────────────

    def _run_assignment(self, regions: List[RegionInfo]) -> List[RegionInfo]:
        """Assign optimal rendering strategy to each region."""
        self._assigner = StrategyAssigner(self.config.assignment)
        regions = self._assigner.assign_strategies(regions)
        return regions

    # ──────────────────────────────────────────────────────────────────
    #  Stage 4: Orchestration Setup
    # ──────────────────────────────────────────────────────────────────

    def _setup_orchestration(self, gray: np.ndarray,
                              regions: List[RegionInfo]):
        """Initialize the rendering pipeline components."""
        self._orchestrator = MultiStrategyOrchestrator(
            gray, regions, self.config
        )
        self._merger = StrokeMerger()
        self._blender = TransitionBlender(self.config.transition)
        self._renderer = UnifiedRenderer(self.config.rendering)
        self._renderer.initialize(self.original_image)

    # ──────────────────────────────────────────────────────────────────
    #  PROCESS IMAGE (main entry)
    # ──────────────────────────────────────────────────────────────────

    def process_image(self, progress_callback: Optional[Callable] = None):
        """
        Run the full analysis and preparation pipeline.

        Args:
            progress_callback: Optional callback(step: int, name: str)
        """
        def report(step, name):
            print(f"    [{step}/5] {name}")
            if progress_callback:
                progress_callback(step, name)

        # Stage 0: Load image
        report(1, "Loading and scaling image...")
        self.original_image = self._load_and_scale_image()
        h, w = self.original_image.shape[:2]
        self.reveal_mask = np.zeros((h, w), dtype=bool)

        self._gray = cv2.cvtColor(self.original_image, cv2.COLOR_RGB2GRAY)

        # Stage 1: Segmentation
        report(2, "Segmenting image into regions...")
        segments = self._run_segmentation(self._gray)
        num_segments = len(np.unique(segments))
        print(f"    Found {num_segments} segments")

        # Stage 2: Classification
        report(3, "Classifying regions...")
        self._regions = self._run_classification(self._gray, segments)
        print(f"    Classified {len(self._regions)} regions")

        # Print region type summary
        type_counts = {}
        for r in self._regions:
            name = r.region_type.value
            type_counts[name] = type_counts.get(name, 0) + 1
        for rtype, count in sorted(type_counts.items()):
            print(f"      {rtype}: {count}")

        # Stage 3: Strategy assignment
        report(4, "Assigning strategies...")
        self._regions = self._run_assignment(self._regions)
        if self._assigner:
            summary = self._assigner.get_strategy_summary(self._regions)
            for strat, count in sorted(summary.items()):
                print(f"      {strat}: {count} regions")

        # Stage 4: Setup orchestration
        report(5, "Setting up orchestration pipeline...")
        self._setup_orchestration(self._gray, self._regions)

        # Compute total steps for smooth animation
        # Keep total steps moderate to avoid excessive computation
        # Each step triggers full region reveal + blending, so fewer steps = faster
        self._total_steps = min(500, max(100, len(self._regions) * 20))

        self._processed = True
        self._current_step = 0
        self.current_reveal_idx = 0

        print(f"    Total animation steps: {self._total_steps}")
        print("    ✅ Hybrid Multi-Strategy Engine ready!")

    # ──────────────────────────────────────────────────────────────────
    #  REVEAL INTERFACE
    # ──────────────────────────────────────────────────────────────────

    def reveal_next_batch(self, points_per_update: int = 100) -> bool:
        """
        Advance the reveal by one batch of animation steps.

        Args:
            points_per_update: Number of reveal increments.

        Returns:
            True if more to render, False if complete.
        """
        if not self._processed or self._orchestrator is None:
            return False

        if self._current_step >= self._total_steps:
            return False

        # Map points_per_update to step increments
        # Each call advances several steps to keep animation fluid
        step_increment = max(1, points_per_update)
        end_step = min(self._current_step + step_increment, self._total_steps)

        # Compute progress for this step
        progress = end_step / self._total_steps

        # Generate per-region reveals at this progress
        region_reveals = self._orchestrator.generate_region_reveals(progress)

        # Blend boundary transitions
        composite_mask = self._blender.blend_region_reveals(
            region_reveals, self._regions
        )

        # Ensure composite matches image dimensions
        h, w = self.original_image.shape[:2]
        if composite_mask.shape != (h, w):
            if HAS_CV2:
                composite_mask = cv2.resize(
                    composite_mask.astype(np.float32), (w, h)
                )
            else:
                composite_mask = np.zeros((h, w), dtype=np.float32)

        # Update the renderer
        self._renderer.update_reveal(composite_mask, self._regions)

        # Update public state
        self.reveal_mask = self._renderer.get_binary_mask()
        self._pen_position = self._renderer.get_pen_position()
        self._current_step = end_step
        self.current_reveal_idx = end_step

        return end_step < self._total_steps

    def get_current_frame(self) -> np.ndarray:
        """
        Get the current composited frame.

        Returns:
            (H, W, 3) uint8 RGB frame.
        """
        if not self._processed or self._renderer is None:
            return np.full(
                (self.display_height, self.display_width, 3),
                255, dtype=np.uint8,
            )

        frame = self._renderer.get_current_frame()

        # The renderer works in BGR (from original), ensure RGB
        if frame is not None and len(frame.shape) == 3:
            return frame
        return np.full(
            (self.display_height, self.display_width, 3),
            255, dtype=np.uint8,
        )

    def get_points_per_update(self) -> int:
        """
        Get recommended points per update for smooth animation.

        Returns:
            Points per frame.
        """
        if not self._processed or self._total_steps == 0:
            return 100

        # Each call to reveal_next_batch advances by this many steps
        # Aim for the animation to complete in ~200 frames at speed=1
        base = max(1, self._total_steps // 200)
        return base

    def get_current_pen_position(self) -> Tuple[int, int]:
        """
        Get the current pen cursor position.

        Returns:
            (x, y) pixel position.
        """
        return self._pen_position

    def get_progress(self) -> float:
        """
        Get overall reveal progress.

        Returns:
            Float 0.0 to 1.0.
        """
        if self._total_steps == 0:
            return 0.0
        return min(1.0, self._current_step / self._total_steps)

    def reset(self):
        """Reset the engine to the beginning."""
        self._current_step = 0
        self.current_reveal_idx = 0
        self._pen_position = (self.display_width // 2, self.display_height // 2)

        if self.original_image is not None:
            h, w = self.original_image.shape[:2]
            self.reveal_mask = np.zeros((h, w), dtype=bool)

        if self._renderer is not None:
            self._renderer.reset()
            self._renderer.initialize(self.original_image)
