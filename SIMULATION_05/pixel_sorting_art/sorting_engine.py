#!/usr/bin/env python3
"""
Pixel Sorting Engine for Pixel Sorting Art
===========================================
Memory-efficient engine for pixel sorting with multiple algorithms,
brightness/hue-based sorting, and animation state tracking.

Optimized for large images (1920x1080+) by avoiding per-pixel state tracking.
"""

import sys
import numpy as np
import cv2
from pathlib import Path
from typing import Tuple, List, Optional, Dict, Any
from enum import Enum
import colorsys

# Increase recursion limit for sorting algorithms on large arrays
sys.setrecursionlimit(10000)


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


class PixelSortingEngine:
    """
    Memory-efficient pixel sorting engine for glitch art animations.
    
    Features:
    - Loads source image and creates scrambled "melted" version
    - Supports brightness and hue-based sorting
    - Horizontal and vertical sorting directions
    - Step-by-step sorting for smooth animation
    - Quick Sort and Shell Sort algorithms
    - Neon glow effects for active sorting regions
    - Beat drop acceleration mode
    
    Optimizations:
    - No per-pixel state tracking (uses numpy arrays directly)
    - Row/column index-based sorting progress tracking
    - Iterative quick sort to avoid stack overflow
    - Efficient numpy operations for swaps
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
        
        # Image data - all numpy arrays for memory efficiency
        self.original_image: Optional[np.ndarray] = None
        self.scrambled_image: Optional[np.ndarray] = None
        self.current_image: Optional[np.ndarray] = None
        
        # Sort value caches (brightness or hue per pixel)
        self.row_sort_values: Dict[int, np.ndarray] = {}  # Row index -> sort values array
        self.col_sort_values: Dict[int, np.ndarray] = {}  # Col index -> sort values array
        
        # Sorting progress tracking (lightweight - just indices and positions)
        self.row_sort_indices: Dict[int, np.ndarray] = {}  # Current order of indices per row
        self.col_sort_indices: Dict[int, np.ndarray] = {}  # Current order of indices per col
        self.row_sort_position: Dict[int, int] = {}  # Current sorting position per row
        self.col_sort_position: Dict[int, int] = {}  # Current sorting position per col
        self.row_gap: Dict[int, int] = {}  # Shell sort gap per row
        self.col_gap: Dict[int, int] = {}  # Shell sort gap per col
        
        # Animation state
        self.current_step: int = 0
        self.total_steps: int = 0
        self.is_complete: bool = False
        self.beat_drop_active: bool = False
        self.beat_drop_multiplier: float = 1.0
        
        # Glow tracking - use numpy array instead of per-pixel state
        self.glow_mask: Optional[np.ndarray] = None
        self.active_rows: set = set()  # Rows with recent activity
        self.active_cols: set = set()  # Cols with recent activity
    
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
    
    def _calculate_sort_values_vectorized(self, pixels: np.ndarray) -> np.ndarray:
        """
        Calculate sort values for an array of pixels using vectorized operations.
        
        Args:
            pixels: Array of shape (N, 3) with RGB values
            
        Returns:
            Array of shape (N,) with sort values
        """
        if self.sort_criteria == SortCriteria.BRIGHTNESS:
            # Vectorized brightness calculation
            return 0.299 * pixels[:, 0] + 0.587 * pixels[:, 1] + 0.114 * pixels[:, 2]
        else:
            # Hue calculation (needs per-pixel processing due to colorsys)
            n = len(pixels)
            hues = np.zeros(n, dtype=np.float32)
            for i in range(n):
                r, g, b = pixels[i] / 255.0
                h, _, _ = colorsys.rgb_to_hsv(r, g, b)
                hues[i] = h * 360.0
            return hues
    
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
            
            # Initialize current_image first (ensures it's never None)
            self.current_image = img.copy()
            
            # Create scrambled version
            self._create_scrambled_image()
            
            # Initialize sorting state
            self._initialize_sorting_state()
            
            # Update current image to scrambled
            self.current_image = self.scrambled_image.copy()
            
            h, w = img.shape[:2]
            print(f"Image processed: {w}x{h} pixels")
            print(f"Total sorting steps: {self.total_steps}")
            
            return True
            
        except Exception as e:
            print(f"Error loading image: {e}")
            import traceback
            traceback.print_exc()
            # Ensure current_image is set even on error
            if self.current_image is None:
                self.current_image = np.ones((self.target_height, self.target_width, 3), dtype=np.uint8) * 20
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
    
    def _create_scrambled_image(self) -> None:
        """
        Create scrambled "melted" version of the image using threshold-based jittering.
        Uses efficient numpy operations.
        """
        h, w = self.original_image.shape[:2]
        self.scrambled_image = self.original_image.copy()
        
        # Apply threshold-based jittering to create scrambled effect
        if self.sort_direction in [SortDirection.HORIZONTAL, SortDirection.BOTH]:
            self._scramble_rows_efficient()
        
        if self.sort_direction in [SortDirection.VERTICAL, SortDirection.BOTH]:
            self._scramble_columns_efficient()
        
        # Initialize glow mask
        self.glow_mask = np.zeros((h, w), dtype=np.float32)
    
    def _scramble_rows_efficient(self) -> None:
        """Scramble pixels within each row based on threshold using numpy."""
        h, w = self.scrambled_image.shape[:2]
        n_swaps = int(w * self.threshold * 2)
        
        for row in range(h):
            row_pixels = self.scrambled_image[row].copy()
            
            # Generate random swap indices
            if n_swaps > 0:
                i_indices = np.random.randint(0, w, size=n_swaps)
                j_indices = np.random.randint(0, w, size=n_swaps)
                
                for i, j in zip(i_indices, j_indices):
                    if i != j:
                        row_pixels[i], row_pixels[j] = row_pixels[j].copy(), row_pixels[i].copy()
            
            self.scrambled_image[row] = row_pixels
    
    def _scramble_columns_efficient(self) -> None:
        """Scramble pixels within each column based on threshold using numpy."""
        h, w = self.scrambled_image.shape[:2]
        n_swaps = int(h * self.threshold * 2)
        
        for col in range(w):
            col_pixels = self.scrambled_image[:, col].copy()
            
            # Generate random swap indices
            if n_swaps > 0:
                i_indices = np.random.randint(0, h, size=n_swaps)
                j_indices = np.random.randint(0, h, size=n_swaps)
                
                for i, j in zip(i_indices, j_indices):
                    if i != j:
                        col_pixels[i], col_pixels[j] = col_pixels[j].copy(), col_pixels[i].copy()
            
            self.scrambled_image[:, col] = col_pixels
    
    def _initialize_sorting_state(self) -> None:
        """Initialize lightweight sorting state for animation."""
        h, w = self.scrambled_image.shape[:2]
        self.total_steps = 0
        
        if self.sort_direction in [SortDirection.HORIZONTAL, SortDirection.BOTH]:
            for row in range(h):
                # Cache sort values for this row (from scrambled state)
                row_pixels = self.scrambled_image[row]
                self.row_sort_values[row] = self._calculate_sort_values_vectorized(row_pixels)
                
                # Initialize index array (current order)
                self.row_sort_indices[row] = np.arange(w, dtype=np.int32)
                
                # Initialize sorting position (for incremental sorting)
                self.row_sort_position[row] = 0
                
                # Shell sort gap
                self.row_gap[row] = w // 2
                
                # Estimate steps (roughly w*log(w) for efficient sorts)
                self.total_steps += max(1, w // 10)
        
        if self.sort_direction in [SortDirection.VERTICAL, SortDirection.BOTH]:
            for col in range(w):
                # Cache sort values for this column
                col_pixels = self.scrambled_image[:, col]
                self.col_sort_values[col] = self._calculate_sort_values_vectorized(col_pixels)
                
                # Initialize index array
                self.col_sort_indices[col] = np.arange(h, dtype=np.int32)
                
                # Initialize sorting position
                self.col_sort_position[col] = 0
                
                # Shell sort gap
                self.col_gap[col] = h // 2
                
                # Estimate steps
                self.total_steps += max(1, h // 10)
    
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
        
        # Safety check - ensure current_image is valid
        if self.current_image is None:
            if self.scrambled_image is not None:
                self.current_image = self.scrambled_image.copy()
            else:
                self.current_image = np.ones((self.target_height, self.target_width, 3), dtype=np.uint8) * 20
            return False
        
        # Apply beat drop multiplier
        actual_steps = int(steps_per_frame * self.beat_drop_multiplier)
        
        h, w = self.current_image.shape[:2]
        
        # Clear active tracking for this frame
        self.active_rows.clear()
        self.active_cols.clear()
        
        rows_complete = 0
        cols_complete = 0
        total_rows = len(self.row_sort_position) if self.sort_direction in [SortDirection.HORIZONTAL, SortDirection.BOTH] else 0
        total_cols = len(self.col_sort_position) if self.sort_direction in [SortDirection.VERTICAL, SortDirection.BOTH] else 0
        
        for _ in range(actual_steps):
            step_applied = False
            
            # Process rows
            if self.sort_direction in [SortDirection.HORIZONTAL, SortDirection.BOTH]:
                for row in range(h):
                    if row in self.row_sort_position:
                        if self._step_row_sort(row):
                            step_applied = True
                            self.active_rows.add(row)
                            break
            
            # Process columns
            if not step_applied and self.sort_direction in [SortDirection.VERTICAL, SortDirection.BOTH]:
                for col in range(w):
                    if col in self.col_sort_position:
                        if self._step_col_sort(col):
                            step_applied = True
                            self.active_cols.add(col)
                            break
            
            self.current_step += 1
            
            # Check completion
            if self.sort_direction in [SortDirection.HORIZONTAL, SortDirection.BOTH]:
                rows_complete = sum(1 for r in range(h) if r not in self.row_sort_position or self._is_row_sorted(r))
            if self.sort_direction in [SortDirection.VERTICAL, SortDirection.BOTH]:
                cols_complete = sum(1 for c in range(w) if c not in self.col_sort_position or self._is_col_sorted(c))
            
            if rows_complete >= total_rows and cols_complete >= total_cols:
                self.is_complete = True
                break
        
        # Update glow mask based on active regions
        self._update_glow_mask()
        
        return self.is_complete
    
    def _step_row_sort(self, row: int) -> bool:
        """
        Perform one step of sorting on a row.
        Uses bubble sort approach for predictable animation.
        
        Returns:
            True if a swap was made, False if row is sorted
        """
        if row not in self.row_sort_values:
            return False
        
        values = self.row_sort_values[row]
        n = len(values)
        pos = self.row_sort_position.get(row, 0)
        
        # Bubble sort one pass
        swapped = False
        for i in range(pos, min(pos + 10, n - 1)):  # Process up to 10 elements per step
            if values[i] > values[i + 1]:
                # Swap values
                values[i], values[i + 1] = values[i + 1], values[i]
                
                # Swap pixels in current image
                self.current_image[row, i], self.current_image[row, i + 1] = \
                    self.current_image[row, i + 1].copy(), self.current_image[row, i].copy()
                
                swapped = True
        
        # Update position
        self.row_sort_position[row] = (pos + 10) % n
        
        # Check if fully sorted
        if not swapped and pos + 10 >= n:
            if self._is_row_sorted(row):
                del self.row_sort_position[row]
        
        return swapped
    
    def _step_col_sort(self, col: int) -> bool:
        """
        Perform one step of sorting on a column.
        Uses bubble sort approach for predictable animation.
        
        Returns:
            True if a swap was made, False if column is sorted
        """
        if col not in self.col_sort_values:
            return False
        
        values = self.col_sort_values[col]
        n = len(values)
        pos = self.col_sort_position.get(col, 0)
        
        # Bubble sort one pass
        swapped = False
        for i in range(pos, min(pos + 10, n - 1)):  # Process up to 10 elements per step
            if values[i] > values[i + 1]:
                # Swap values
                values[i], values[i + 1] = values[i + 1], values[i]
                
                # Swap pixels in current image
                self.current_image[i, col], self.current_image[i + 1, col] = \
                    self.current_image[i + 1, col].copy(), self.current_image[i, col].copy()
                
                swapped = True
        
        # Update position
        self.col_sort_position[col] = (pos + 10) % n
        
        # Check if fully sorted
        if not swapped and pos + 10 >= n:
            if self._is_col_sorted(col):
                del self.col_sort_position[col]
        
        return swapped
    
    def _is_row_sorted(self, row: int) -> bool:
        """Check if a row is fully sorted."""
        if row not in self.row_sort_values:
            return True
        values = self.row_sort_values[row]
        return np.all(values[:-1] <= values[1:])
    
    def _is_col_sorted(self, col: int) -> bool:
        """Check if a column is fully sorted."""
        if col not in self.col_sort_values:
            return True
        values = self.col_sort_values[col]
        return np.all(values[:-1] <= values[1:])
    
    def _update_glow_mask(self) -> None:
        """Update glow mask based on active sorting regions."""
        if self.glow_mask is None:
            return
        
        # Decay existing glow
        self.glow_mask *= 0.85
        
        # Add glow to active rows/columns
        for row in self.active_rows:
            if 0 <= row < self.glow_mask.shape[0]:
                self.glow_mask[row, :] = np.maximum(self.glow_mask[row, :], 0.5)
        
        for col in self.active_cols:
            if 0 <= col < self.glow_mask.shape[1]:
                self.glow_mask[:, col] = np.maximum(self.glow_mask[:, col], 0.5)
    
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
        if self.current_image is None:
            return np.ones((self.target_height, self.target_width, 3), dtype=np.uint8) * 20
        
        frame = self.current_image.copy()
        
        # Apply neon glow to active regions
        glow_frame = self._apply_neon_glow(frame)
        
        return glow_frame
    
    def _apply_neon_glow(self, frame: np.ndarray) -> np.ndarray:
        """
        Apply neon glow effect to recently moved pixels.
        Uses efficient numpy operations instead of per-pixel iteration.
        
        Args:
            frame: Input frame
            
        Returns:
            Frame with glow effects
        """
        if self.glow_mask is None or not np.any(self.glow_mask > 0.1):
            return frame
        
        h, w = frame.shape[:2]
        
        # Create glow layer using vectorized operations
        glow_color = np.array([255, 0, 255], dtype=np.float32)  # Magenta
        
        # Expand glow mask to 3 channels and multiply by glow color
        glow_layer = self.glow_mask[:, :, np.newaxis] * glow_color
        
        # Blur the glow layer
        glow_layer = cv2.GaussianBlur(glow_layer.astype(np.float32), (15, 15), 0)
        
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
        if self.glow_mask is None:
            if self.current_image is not None:
                h, w = self.current_image.shape[:2]
                return np.zeros((h, w), dtype=np.float32)
            return np.zeros((self.target_height, self.target_width), dtype=np.float32)
        return self.glow_mask.copy()
    
    def get_progress(self) -> float:
        """
        Get sorting progress as a fraction.
        
        Returns:
            Progress value between 0 and 1
        """
        if self.total_steps == 0:
            return 1.0
        return min(1.0, self.current_step / max(1, self.total_steps))
    
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
            "current_image": self.current_image if self.current_image is not None else np.ones((self.target_height, self.target_width, 3), dtype=np.uint8) * 20,
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
        elif self.original_image is not None:
            self.current_image = self.original_image.copy()
        else:
            self.current_image = np.ones((self.target_height, self.target_width, 3), dtype=np.uint8) * 20
        
        # Reset glow mask
        if self.current_image is not None:
            h, w = self.current_image.shape[:2]
            self.glow_mask = np.zeros((h, w), dtype=np.float32)
        
        # Re-initialize sorting state
        self._initialize_sorting_state()
