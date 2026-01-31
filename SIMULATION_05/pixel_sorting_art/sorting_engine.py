#!/usr/bin/env python3
"""
Pixel Sorting Engine for Pixel Sorting Art
===========================================
Comprehensive engine for pixel sorting with multiple algorithms,
brightness/hue-based sorting, and animation state tracking.
"""

import numpy as np
import cv2
from pathlib import Path
from typing import Tuple, List, Optional, Dict, Literal, Any
from dataclasses import dataclass, field
from enum import Enum
import colorsys


class SortingAlgorithm(Enum):
    """Available sorting algorithms."""
    QUICK_SORT = "quick_sort"
    SHELL_SORT = "shell_sort"


class SortDirection(Enum):
    """Sorting direction options."""
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"
    BOTH = "both"


class SortCriteria(Enum):
    """Pixel sorting criteria."""
    BRIGHTNESS = "brightness"
    HUE = "hue"


@dataclass
class PixelState:
    """Tracks the state of a single pixel during sorting."""
    original_pos: Tuple[int, int]  # (row, col) original position
    current_pos: Tuple[int, int]   # (row, col) current position in animation
    target_pos: Tuple[int, int]    # (row, col) final sorted position
    color: np.ndarray              # RGB color values
    sort_value: float              # Brightness or hue value
    is_sorted: bool = False        # Whether pixel has reached target
    glow_intensity: float = 0.0    # Neon glow intensity (0-1)


@dataclass
class SortingStep:
    """Represents a single step in the sorting animation."""
    swaps: List[Tuple[int, int]]   # List of (idx1, idx2) swap pairs
    comparisons: List[Tuple[int, int]] = field(default_factory=list)  # Comparisons made
    description: str = ""          # Debug description


class PixelSortingEngine:
    """
    Comprehensive pixel sorting engine for glitch art animations.
    
    Features:
    - Loads source image and creates scrambled "melted" version
    - Supports brightness and hue-based sorting
    - Horizontal and vertical sorting directions
    - Step-by-step sorting for smooth animation
    - Quick Sort and Shell Sort algorithms
    - Neon glow effects for unsorted pixels
    - Beat drop acceleration mode
    """
    
    def __init__(
        self,
        image_path: str,
        target_width: int = 1080,
        target_height: int = 1920,
        algorithm: str = "quick_sort",
        sort_direction: str = "horizontal",
        sort_criteria: str = "brightness",
        threshold: float = 0.3,
        padding: int = 40
    ):
        """
        Initialize the pixel sorting engine.
        
        Args:
            image_path: Path to the source image
            target_width: Target canvas width
            target_height: Target canvas height
            algorithm: Sorting algorithm ("quick_sort" or "shell_sort")
            sort_direction: Direction to sort ("horizontal", "vertical", or "both")
            sort_criteria: Criteria for sorting ("brightness" or "hue")
            threshold: Threshold for scramble intensity (0-1)
            padding: Padding around the image
        """
        self.image_path = Path(image_path)
        self.target_width = target_width
        self.target_height = target_height
        self.algorithm = SortingAlgorithm(algorithm)
        self.sort_direction = SortDirection(sort_direction)
        self.sort_criteria = SortCriteria(sort_criteria)
        self.threshold = threshold
        self.padding = padding
        
        # Image data
        self.original_image: Optional[np.ndarray] = None
        self.scrambled_image: Optional[np.ndarray] = None
        self.current_image: Optional[np.ndarray] = None
        
        # Pixel tracking for animation
        self.pixel_states: List[List[PixelState]] = []  # 2D grid of pixel states
        self.row_sorting_steps: Dict[int, List[SortingStep]] = {}  # Pre-computed steps per row
        self.col_sorting_steps: Dict[int, List[SortingStep]] = {}  # Pre-computed steps per col
        
        # Animation state
        self.current_step: int = 0
        self.total_steps: int = 0
        self.is_complete: bool = False
        self.beat_drop_active: bool = False
        self.beat_drop_multiplier: float = 1.0
        
        # Glow tracking
        self.unsorted_mask: Optional[np.ndarray] = None
    
    def calculate_brightness(self, r: float, g: float, b: float) -> float:
        """
        Calculate perceived brightness using ITU-R BT.601 formula.
        
        Y = 0.299R + 0.587G + 0.114B
        
        Args:
            r, g, b: RGB values (0-255)
            
        Returns:
            Brightness value (0-255)
        """
        return 0.299 * r + 0.587 * g + 0.114 * b
    
    def calculate_hue(self, r: float, g: float, b: float) -> float:
        """
        Calculate hue value from RGB.
        
        Args:
            r, g, b: RGB values (0-255)
            
        Returns:
            Hue value (0-360)
        """
        r_norm, g_norm, b_norm = r / 255.0, g / 255.0, b / 255.0
        h, _, _ = colorsys.rgb_to_hsv(r_norm, g_norm, b_norm)
        return h * 360.0
    
    def get_sort_value(self, r: float, g: float, b: float) -> float:
        """
        Get the sorting value for a pixel based on current criteria.
        
        Args:
            r, g, b: RGB values
            
        Returns:
            Sort value (brightness or hue)
        """
        if self.sort_criteria == SortCriteria.BRIGHTNESS:
            return self.calculate_brightness(r, g, b)
        else:
            return self.calculate_hue(r, g, b)
    
    def load_and_process_image(self) -> bool:
        """
        Load source image and prepare for sorting.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            print(f"Loading image: {self.image_path}")
            
            # Load image
            img = cv2.imread(str(self.image_path))
            if img is None:
                raise ValueError(f"Could not load image: {self.image_path}")
            
            # Convert BGR to RGB
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            # Resize to fit canvas
            img = self._resize_to_canvas(img)
            self.original_image = img.copy()
            
            # Initialize pixel states
            self._initialize_pixel_states()
            
            # Create scrambled version
            self._create_scrambled_image()
            
            # Pre-compute sorting steps
            self._precompute_sorting_steps()
            
            # Set current image to scrambled
            self.current_image = self.scrambled_image.copy()
            
            print(f"Image processed: {img.shape[1]}x{img.shape[0]} pixels")
            print(f"Total sorting steps: {self.total_steps}")
            
            return True
            
        except Exception as e:
            print(f"Error loading image: {e}")
            return False
    
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
        canvas = np.ones((self.target_height, self.target_width, 3), dtype=np.uint8) * 20
        
        offset_x = (self.target_width - new_w) // 2
        offset_y = (self.target_height - new_h) // 2
        
        canvas[offset_y:offset_y + new_h, offset_x:offset_x + new_w] = resized
        
        return canvas
    
    def _initialize_pixel_states(self) -> None:
        """Initialize pixel state tracking for all pixels."""
        h, w = self.original_image.shape[:2]
        self.pixel_states = []
        
        for row in range(h):
            row_states = []
            for col in range(w):
                color = self.original_image[row, col]
                sort_value = self.get_sort_value(float(color[0]), float(color[1]), float(color[2]))
                
                state = PixelState(
                    original_pos=(row, col),
                    current_pos=(row, col),
                    target_pos=(row, col),  # Will be updated after scrambling
                    color=color,
                    sort_value=sort_value,
                    is_sorted=False,
                    glow_intensity=0.0
                )
                row_states.append(state)
            self.pixel_states.append(row_states)
    
    def _create_scrambled_image(self) -> None:
        """
        Create scrambled "melted" version of the image using threshold-based jittering.
        """
        h, w = self.original_image.shape[:2]
        self.scrambled_image = self.original_image.copy()
        
        # Apply threshold-based jittering to create scrambled effect
        if self.sort_direction in [SortDirection.HORIZONTAL, SortDirection.BOTH]:
            self._scramble_rows()
        
        if self.sort_direction in [SortDirection.VERTICAL, SortDirection.BOTH]:
            self._scramble_columns()
        
        # Initialize unsorted mask (all pixels unsorted initially)
        self.unsorted_mask = np.ones((h, w), dtype=np.float32)
    
    def _scramble_rows(self) -> None:
        """Scramble pixels within each row based on threshold."""
        h, w = self.scrambled_image.shape[:2]
        
        for row in range(h):
            row_pixels = self.scrambled_image[row].copy()
            row_states = self.pixel_states[row]
            
            # Calculate scramble intensity based on threshold
            n_swaps = int(w * self.threshold * 2)
            
            for _ in range(n_swaps):
                # Random swap within row
                i = np.random.randint(0, w)
                j = np.random.randint(0, w)
                
                if i != j:
                    # Swap pixels
                    row_pixels[i], row_pixels[j] = row_pixels[j].copy(), row_pixels[i].copy()
                    
                    # Update states
                    row_states[i].current_pos, row_states[j].current_pos = \
                        row_states[j].current_pos, row_states[i].current_pos
                    row_states[i], row_states[j] = row_states[j], row_states[i]
            
            self.scrambled_image[row] = row_pixels
            self.pixel_states[row] = row_states
    
    def _scramble_columns(self) -> None:
        """Scramble pixels within each column based on threshold."""
        h, w = self.scrambled_image.shape[:2]
        
        for col in range(w):
            col_pixels = self.scrambled_image[:, col].copy()
            
            # Calculate scramble intensity based on threshold
            n_swaps = int(h * self.threshold * 2)
            
            for _ in range(n_swaps):
                # Random swap within column
                i = np.random.randint(0, h)
                j = np.random.randint(0, h)
                
                if i != j:
                    # Swap pixels
                    col_pixels[i], col_pixels[j] = col_pixels[j].copy(), col_pixels[i].copy()
                    
                    # Update states
                    self.pixel_states[i][col].current_pos, self.pixel_states[j][col].current_pos = \
                        self.pixel_states[j][col].current_pos, self.pixel_states[i][col].current_pos
                    self.pixel_states[i][col], self.pixel_states[j][col] = \
                        self.pixel_states[j][col], self.pixel_states[i][col]
            
            self.scrambled_image[:, col] = col_pixels
    
    def _precompute_sorting_steps(self) -> None:
        """Pre-compute all sorting steps for animation."""
        h, w = self.original_image.shape[:2]
        total = 0
        
        if self.sort_direction in [SortDirection.HORIZONTAL, SortDirection.BOTH]:
            for row in range(h):
                # Get sort values for this row
                values = [self.pixel_states[row][col].sort_value for col in range(w)]
                steps = self._generate_sorting_steps(values)
                self.row_sorting_steps[row] = steps
                total += len(steps)
        
        if self.sort_direction in [SortDirection.VERTICAL, SortDirection.BOTH]:
            for col in range(w):
                # Get sort values for this column
                values = [self.pixel_states[row][col].sort_value for row in range(h)]
                steps = self._generate_sorting_steps(values)
                self.col_sorting_steps[col] = steps
                total += len(steps)
        
        self.total_steps = total
    
    def _generate_sorting_steps(self, values: List[float]) -> List[SortingStep]:
        """
        Generate step-by-step sorting operations for animation.
        
        Args:
            values: List of values to sort
            
        Returns:
            List of SortingStep objects
        """
        if self.algorithm == SortingAlgorithm.QUICK_SORT:
            return self._quick_sort_steps(values)
        else:
            return self._shell_sort_steps(values)
    
    def _quick_sort_steps(self, values: List[float]) -> List[SortingStep]:
        """
        Generate Quick Sort steps for animation.
        
        Args:
            values: List of values to sort
            
        Returns:
            List of SortingStep objects
        """
        steps: List[SortingStep] = []
        arr = values.copy()
        
        def partition(low: int, high: int) -> int:
            pivot = arr[high]
            i = low - 1
            
            for j in range(low, high):
                steps.append(SortingStep(
                    swaps=[],
                    comparisons=[(j, high)],
                    description=f"Compare arr[{j}] with pivot arr[{high}]"
                ))
                
                if arr[j] <= pivot:
                    i += 1
                    if i != j:
                        arr[i], arr[j] = arr[j], arr[i]
                        steps.append(SortingStep(
                            swaps=[(i, j)],
                            comparisons=[],
                            description=f"Swap arr[{i}] and arr[{j}]"
                        ))
            
            if i + 1 != high:
                arr[i + 1], arr[high] = arr[high], arr[i + 1]
                steps.append(SortingStep(
                    swaps=[(i + 1, high)],
                    comparisons=[],
                    description=f"Swap pivot to position {i + 1}"
                ))
            
            return i + 1
        
        def quick_sort_recursive(low: int, high: int) -> None:
            if low < high:
                pi = partition(low, high)
                quick_sort_recursive(low, pi - 1)
                quick_sort_recursive(pi + 1, high)
        
        if len(arr) > 1:
            quick_sort_recursive(0, len(arr) - 1)
        
        return steps
    
    def _shell_sort_steps(self, values: List[float]) -> List[SortingStep]:
        """
        Generate Shell Sort steps for animation.
        
        Args:
            values: List of values to sort
            
        Returns:
            List of SortingStep objects
        """
        steps: List[SortingStep] = []
        arr = values.copy()
        n = len(arr)
        
        # Start with a large gap, then reduce
        gap = n // 2
        
        while gap > 0:
            for i in range(gap, n):
                temp = arr[i]
                j = i
                
                while j >= gap:
                    steps.append(SortingStep(
                        swaps=[],
                        comparisons=[(j - gap, j)],
                        description=f"Compare arr[{j - gap}] with arr[{j}] (gap={gap})"
                    ))
                    
                    if arr[j - gap] > temp:
                        arr[j] = arr[j - gap]
                        steps.append(SortingStep(
                            swaps=[(j - gap, j)],
                            comparisons=[],
                            description=f"Move arr[{j - gap}] to position {j}"
                        ))
                        j -= gap
                    else:
                        break
                
                arr[j] = temp
            
            gap //= 2
        
        return steps
    
    def step_sorting(self, steps_per_frame: int = 1) -> bool:
        """
        Advance sorting by a specified number of steps.
        
        Args:
            steps_per_frame: Number of sorting steps to perform
            
        Returns:
            True if sorting is complete, False otherwise
        """
        if self.is_complete:
            return True
        
        # Apply beat drop multiplier
        actual_steps = int(steps_per_frame * self.beat_drop_multiplier)
        
        h, w = self.current_image.shape[:2]
        
        for _ in range(actual_steps):
            if self.current_step >= self.total_steps:
                self.is_complete = True
                return True
            
            # Determine which row/col to process
            step_applied = False
            
            if self.sort_direction in [SortDirection.HORIZONTAL, SortDirection.BOTH]:
                for row, steps in self.row_sorting_steps.items():
                    if len(steps) > 0:
                        step = steps.pop(0)
                        self._apply_step_to_row(row, step)
                        step_applied = True
                        break
            
            if not step_applied and self.sort_direction in [SortDirection.VERTICAL, SortDirection.BOTH]:
                for col, steps in self.col_sorting_steps.items():
                    if len(steps) > 0:
                        step = steps.pop(0)
                        self._apply_step_to_col(col, step)
                        step_applied = True
                        break
            
            self.current_step += 1
        
        # Update glow intensities
        self._update_glow_intensities()
        
        return self.is_complete
    
    def _apply_step_to_row(self, row: int, step: SortingStep) -> None:
        """Apply a sorting step to a specific row."""
        for i, j in step.swaps:
            if 0 <= i < self.current_image.shape[1] and 0 <= j < self.current_image.shape[1]:
                # Swap pixels in current image
                self.current_image[row, i], self.current_image[row, j] = \
                    self.current_image[row, j].copy(), self.current_image[row, i].copy()
                
                # Update pixel states
                self.pixel_states[row][i], self.pixel_states[row][j] = \
                    self.pixel_states[row][j], self.pixel_states[row][i]
                
                # Update glow
                self.pixel_states[row][i].glow_intensity = 1.0
                self.pixel_states[row][j].glow_intensity = 1.0
    
    def _apply_step_to_col(self, col: int, step: SortingStep) -> None:
        """Apply a sorting step to a specific column."""
        for i, j in step.swaps:
            if 0 <= i < self.current_image.shape[0] and 0 <= j < self.current_image.shape[0]:
                # Swap pixels in current image
                self.current_image[i, col], self.current_image[j, col] = \
                    self.current_image[j, col].copy(), self.current_image[i, col].copy()
                
                # Update pixel states
                self.pixel_states[i][col], self.pixel_states[j][col] = \
                    self.pixel_states[j][col], self.pixel_states[i][col]
                
                # Update glow
                self.pixel_states[i][col].glow_intensity = 1.0
                self.pixel_states[j][col].glow_intensity = 1.0
    
    def _update_glow_intensities(self) -> None:
        """Decay glow intensities over time."""
        decay_rate = 0.9
        for row in self.pixel_states:
            for pixel in row:
                pixel.glow_intensity *= decay_rate
    
    def activate_beat_drop(self, multiplier: float = 5.0) -> None:
        """
        Activate beat drop acceleration mode.
        
        Args:
            multiplier: Speed multiplier during beat drop
        """
        self.beat_drop_active = True
        self.beat_drop_multiplier = multiplier
        print(f"Beat drop activated! Speed multiplier: {multiplier}x")
    
    def deactivate_beat_drop(self) -> None:
        """Deactivate beat drop mode."""
        self.beat_drop_active = False
        self.beat_drop_multiplier = 1.0
    
    def get_current_frame(self) -> np.ndarray:
        """
        Get the current frame with glow effects applied.
        
        Returns:
            Current frame as numpy array (RGB)
        """
        frame = self.current_image.copy()
        
        # Apply neon glow to pixels with high glow intensity
        glow_frame = self._apply_neon_glow(frame)
        
        return glow_frame
    
    def _apply_neon_glow(self, frame: np.ndarray) -> np.ndarray:
        """
        Apply neon glow effect to recently moved pixels.
        
        Args:
            frame: Input frame
            
        Returns:
            Frame with glow effects
        """
        h, w = frame.shape[:2]
        glow_layer = np.zeros_like(frame, dtype=np.float32)
        
        for row in range(h):
            for col in range(w):
                intensity = self.pixel_states[row][col].glow_intensity
                if intensity > 0.1:
                    # Create glow color (magenta/cyan for vaporwave)
                    glow_color = np.array([255, 0, 255], dtype=np.float32)  # Magenta
                    glow_layer[row, col] = glow_color * intensity
        
        # Blur the glow layer
        if np.any(glow_layer > 0):
            glow_layer = cv2.GaussianBlur(glow_layer, (15, 15), 0)
        
        # Blend glow with original frame
        result = frame.astype(np.float32) + glow_layer * 0.3
        result = np.clip(result, 0, 255).astype(np.uint8)
        
        return result
    
    def get_glow_mask(self) -> np.ndarray:
        """
        Get a mask of current glow intensities.
        
        Returns:
            2D numpy array of glow intensities (0-1)
        """
        h, w = self.current_image.shape[:2]
        mask = np.zeros((h, w), dtype=np.float32)
        
        for row in range(h):
            for col in range(w):
                mask[row, col] = self.pixel_states[row][col].glow_intensity
        
        return mask
    
    def get_progress(self) -> float:
        """
        Get sorting progress as a fraction.
        
        Returns:
            Progress value between 0 and 1
        """
        if self.total_steps == 0:
            return 1.0
        return min(1.0, self.current_step / self.total_steps)
    
    def get_sorting_state(self) -> Dict[str, Any]:
        """
        Get complete current sorting state for rendering.
        
        Returns:
            Dictionary containing current state information
        """
        return {
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "progress": self.get_progress(),
            "is_complete": self.is_complete,
            "beat_drop_active": self.beat_drop_active,
            "beat_drop_multiplier": self.beat_drop_multiplier,
            "current_image": self.current_image,
            "glow_mask": self.get_glow_mask()
        }
    
    def reset(self) -> None:
        """Reset sorting to initial scrambled state."""
        self.current_step = 0
        self.is_complete = False
        self.beat_drop_active = False
        self.beat_drop_multiplier = 1.0
        
        if self.scrambled_image is not None:
            self.current_image = self.scrambled_image.copy()
        
        # Reset glow intensities
        for row in self.pixel_states:
            for pixel in row:
                pixel.glow_intensity = 0.0
        
        # Re-precompute sorting steps
        self._precompute_sorting_steps()
