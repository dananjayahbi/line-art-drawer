"""
String Art Engine - Greedy Algorithm Implementation
Generates string art by iteratively selecting the darkest line paths
"""

import numpy as np
from typing import Tuple, List, Optional, Dict
from PIL import Image
import cv2
import math

# GPU acceleration support with NumPy fallback
try:
    import cupy as cp
    GPU_AVAILABLE = True
except ImportError:
    cp = np
    GPU_AVAILABLE = False


class StringArtEngine:
    """
    Implements the Greedy String Art algorithm.
    
    The algorithm works by:
    1. Placing nails evenly around a circle
    2. Starting from a random nail
    3. Iteratively selecting the line that traverses the darkest pixels
    4. Subtracting brightness along that line (simulating thread coverage)
    5. Repeating until max_lines is reached or convergence
    """
    
    def __init__(
        self,
        nail_count: int = 250,
        canvas_size: int = 800,
        max_lines: int = 3000,
        line_weight: float = 0.2,
        min_distance: int = 20,
        lookahead: Optional[int] = None,
        use_gpu: bool = True,
        convergence_threshold: float = 0.01,
        auto_contrast: bool = True
    ):
        """
        Initialize the String Art Engine.
        
        Args:
            nail_count: Number of nails to place around the circle (200-300 recommended)
            canvas_size: Size of the square canvas in pixels
            max_lines: Maximum number of lines to draw
            line_weight: How much brightness to subtract per line (0.0-1.0)
            min_distance: Minimum nail distance to avoid adjacent nails
            lookahead: Only check nearest N nails (None = check all)
            use_gpu: Use GPU acceleration if available
            convergence_threshold: Stop if darkness score drops below this
            auto_contrast: Apply automatic contrast enhancement
        """
        self.nail_count = nail_count
        self.canvas_size = canvas_size
        self.max_lines = max_lines
        self.line_weight = line_weight
        self.min_distance = min_distance
        self.lookahead = lookahead
        self.convergence_threshold = convergence_threshold
        self.auto_contrast = auto_contrast
        
        # GPU setup
        self.use_gpu = use_gpu and GPU_AVAILABLE
        self.xp = cp if self.use_gpu else np
        
        # Initialize state
        self.nail_positions = None
        self.current_canvas = None
        self.original_image = None
        self.current_nail_idx = 0
        self.line_sequence = []
        self.darkness_scores = []
        self.converged = False
        
        # Statistics
        self.stats = {
            'total_lines': 0,
            'avg_darkness': 0.0,
            'convergence_iteration': None
        }
        
    def load_image(self, image_path: str) -> None:
        """
        Load and preprocess the target image.
        
        Args:
            image_path: Path to the input image file
        """
        # Load image
        img = Image.open(image_path)
        
        # Convert to grayscale
        if img.mode != 'L':
            img = img.convert('L')
        
        # Resize to canvas dimensions
        img = img.resize((self.canvas_size, self.canvas_size), Image.Resampling.LANCZOS)
        
        # Convert to numpy array
        img_array = np.array(img, dtype=np.float32)
        
        # Normalize to 0-1 range
        img_array = img_array / 255.0
        
        # Apply auto-contrast if enabled
        if self.auto_contrast:
            img_array = self._apply_auto_contrast(img_array)
        
        # Invert so dark areas have high values
        img_array = 1.0 - img_array
        
        # Create circular mask
        img_array = self._apply_circular_mask(img_array)
        
        # Store original and working canvas
        if self.use_gpu:
            self.original_image = cp.array(img_array)
            self.current_canvas = cp.copy(self.original_image)
        else:
            self.original_image = img_array
            self.current_canvas = np.copy(img_array)
    
    def _apply_auto_contrast(self, image: np.ndarray) -> np.ndarray:
        """
        Apply automatic contrast enhancement.
        
        Args:
            image: Input image array (0-1 range)
            
        Returns:
            Contrast-enhanced image
        """
        # Calculate percentiles
        p2 = np.percentile(image, 2)
        p98 = np.percentile(image, 98)
        
        # Stretch contrast
        if p98 - p2 > 0.01:
            image = np.clip((image - p2) / (p98 - p2), 0, 1)
        
        return image
    
    def _apply_circular_mask(self, image: np.ndarray) -> np.ndarray:
        """
        Apply circular mask to focus on circular region.
        
        Args:
            image: Input image array
            
        Returns:
            Masked image
        """
        center = self.canvas_size // 2
        radius = self.canvas_size // 2 - 10
        
        y, x = np.ogrid[:self.canvas_size, :self.canvas_size]
        mask = (x - center)**2 + (y - center)**2 <= radius**2
        
        image = image * mask
        return image
    
    def calculate_nail_positions(self) -> np.ndarray:
        """
        Calculate positions of nails evenly spaced around a circle.
        
        Returns:
            Array of (x, y) nail positions, shape (nail_count, 2)
        """
        center = self.canvas_size / 2
        radius = self.canvas_size / 2 - 10
        
        angles = np.linspace(0, 2 * np.pi, self.nail_count, endpoint=False)
        
        x_positions = center + radius * np.cos(angles)
        y_positions = center + radius * np.sin(angles)
        
        positions = np.stack([x_positions, y_positions], axis=1)
        self.nail_positions = positions
        
        return positions
    
    def initialize(self, image_path: str, start_nail: Optional[int] = None) -> None:
        """
        Initialize the engine with an image and prepare for iteration.
        
        Args:
            image_path: Path to the target image
            start_nail: Starting nail index (random if None)
        """
        # Load and preprocess image
        self.load_image(image_path)
        
        # Calculate nail positions
        self.calculate_nail_positions()
        
        # Set starting nail
        if start_nail is None:
            start_nail = np.random.randint(0, self.nail_count)
        self.current_nail_idx = start_nail
        
        # Initialize sequence
        self.line_sequence = [start_nail]
        self.darkness_scores = []
        self.converged = False
        
        # Reset stats
        self.stats = {
            'total_lines': 0,
            'avg_darkness': 0.0,
            'convergence_iteration': None
        }
    
    def get_line_pixels(self, nail1_idx: int, nail2_idx: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Get pixel coordinates along a line between two nails using Bresenham's algorithm.
        
        Args:
            nail1_idx: Index of first nail
            nail2_idx: Index of second nail
            
        Returns:
            Tuple of (x_coords, y_coords) arrays
        """
        x0, y0 = self.nail_positions[nail1_idx]
        x1, y1 = self.nail_positions[nail2_idx]
        
        # Convert to integers
        x0, y0 = int(round(x0)), int(round(y0))
        x1, y1 = int(round(x1)), int(round(y1))
        
        # Bresenham's line algorithm
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        
        x_coords = []
        y_coords = []
        
        x, y = x0, y0
        
        while True:
            x_coords.append(x)
            y_coords.append(y)
            
            if x == x1 and y == y1:
                break
            
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy
        
        return np.array(x_coords), np.array(y_coords)
    
    def calculate_darkness_score(self, nail1_idx: int, nail2_idx: int) -> float:
        """
        Calculate the total darkness along a line between two nails.
        
        Args:
            nail1_idx: Index of first nail
            nail2_idx: Index of second nail
            
        Returns:
            Darkness score (higher = darker line)
        """
        x_coords, y_coords = self.get_line_pixels(nail1_idx, nail2_idx)
        
        # Ensure coordinates are within bounds
        valid_mask = (
            (x_coords >= 0) & (x_coords < self.canvas_size) &
            (y_coords >= 0) & (y_coords < self.canvas_size)
        )
        x_coords = x_coords[valid_mask]
        y_coords = y_coords[valid_mask]
        
        if len(x_coords) == 0:
            return 0.0
        
        if self.use_gpu:
            # Transfer to GPU if needed
            x_gpu = cp.array(x_coords)
            y_gpu = cp.array(y_coords)
            pixel_values = self.current_canvas[y_gpu, x_gpu]
            score = float(cp.sum(pixel_values))
        else:
            pixel_values = self.current_canvas[y_coords, x_coords]
            score = float(np.sum(pixel_values))
        
        return score
    
    def find_best_line(self) -> Tuple[int, float]:
        """
        Find the nail that creates the darkest line from current nail.
        Uses greedy algorithm with optional lookahead optimization.
        
        Returns:
            Tuple of (best_nail_idx, darkness_score)
        """
        current_nail = self.current_nail_idx
        
        # Determine which nails to check
        if self.lookahead is not None:
            # Calculate distances to all nails
            current_pos = self.nail_positions[current_nail]
            distances = np.linalg.norm(self.nail_positions - current_pos, axis=1)
            
            # Get indices of nearest nails (excluding current)
            nearest_indices = np.argsort(distances)[1:self.lookahead + 1]
        else:
            # Check all nails except current
            nearest_indices = np.arange(self.nail_count)
            nearest_indices = nearest_indices[nearest_indices != current_nail]
        
        # Apply minimum distance constraint
        if self.min_distance > 0:
            valid_nails = []
            for nail_idx in nearest_indices:
                distance = abs(nail_idx - current_nail)
                distance = min(distance, self.nail_count - distance)  # Consider wrap-around
                if distance >= self.min_distance:
                    valid_nails.append(nail_idx)
            nearest_indices = np.array(valid_nails)
        
        if len(nearest_indices) == 0:
            return current_nail, 0.0
        
        # Calculate darkness scores for all candidate nails
        best_score = -1.0
        best_nail = current_nail
        
        for nail_idx in nearest_indices:
            score = self.calculate_darkness_score(current_nail, nail_idx)
            if score > best_score:
                best_score = score
                best_nail = nail_idx
        
        return best_nail, best_score
    
    def subtract_brightness(self, nail1_idx: int, nail2_idx: int) -> None:
        """
        Reduce brightness along the line between two nails.
        This simulates the coverage of a physical thread.
        
        Args:
            nail1_idx: Index of first nail
            nail2_idx: Index of second nail
        """
        x_coords, y_coords = self.get_line_pixels(nail1_idx, nail2_idx)
        
        # Ensure coordinates are within bounds
        valid_mask = (
            (x_coords >= 0) & (x_coords < self.canvas_size) &
            (y_coords >= 0) & (y_coords < self.canvas_size)
        )
        x_coords = x_coords[valid_mask]
        y_coords = y_coords[valid_mask]
        
        if len(x_coords) == 0:
            return
        
        if self.use_gpu:
            x_gpu = cp.array(x_coords)
            y_gpu = cp.array(y_coords)
            self.current_canvas[y_gpu, x_gpu] *= (1.0 - self.line_weight)
        else:
            self.current_canvas[y_coords, x_coords] *= (1.0 - self.line_weight)
    
    def is_converged(self) -> bool:
        """
        Check if the algorithm has converged.
        
        Returns:
            True if converged, False otherwise
        """
        if len(self.darkness_scores) < 10:
            return False
        
        # Check recent average darkness
        recent_scores = self.darkness_scores[-10:]
        avg_recent = np.mean(recent_scores)
        
        # Normalize by canvas size
        normalized_score = avg_recent / (self.canvas_size * 2)
        
        return normalized_score < self.convergence_threshold
    
    def get_current_nail(self) -> int:
        """
        Get the current nail index.
        
        Returns:
            Current nail index
        """
        return self.current_nail_idx
    
    def select_next_nail(self) -> Dict:
        """
        Execute one iteration of the greedy selection algorithm.
        
        Returns:
            Dictionary with iteration results:
                - next_nail: Index of selected nail
                - darkness_score: Score of selected line
                - converged: Whether algorithm has converged
                - iteration: Current iteration number
        """
        if self.converged:
            return {
                'next_nail': self.current_nail_idx,
                'darkness_score': 0.0,
                'converged': True,
                'iteration': self.stats['total_lines']
            }
        
        # Find best next nail
        next_nail, darkness_score = self.find_best_line()
        
        # Subtract brightness along selected line
        self.subtract_brightness(self.current_nail_idx, next_nail)
        
        # Update state
        self.current_nail_idx = next_nail
        self.line_sequence.append(next_nail)
        self.darkness_scores.append(darkness_score)
        self.stats['total_lines'] += 1
        
        # Check convergence
        if self.is_converged():
            self.converged = True
            self.stats['convergence_iteration'] = self.stats['total_lines']
        
        # Update statistics
        if len(self.darkness_scores) > 0:
            self.stats['avg_darkness'] = float(np.mean(self.darkness_scores))
        
        return {
            'next_nail': next_nail,
            'darkness_score': darkness_score,
            'converged': self.converged,
            'iteration': self.stats['total_lines']
        }
    
    def run_full_algorithm(self, max_iterations: Optional[int] = None) -> Dict:
        """
        Run the complete greedy algorithm until completion.
        
        Args:
            max_iterations: Override max_lines if provided
            
        Returns:
            Dictionary with final statistics
        """
        if max_iterations is None:
            max_iterations = self.max_lines
        
        iteration = 0
        while iteration < max_iterations and not self.converged:
            self.select_next_nail()
            iteration += 1
            
            # Progress update every 100 iterations
            if iteration % 100 == 0:
                print(f"Iteration {iteration}/{max_iterations}, "
                      f"Avg Darkness: {self.stats['avg_darkness']:.2f}, "
                      f"Converged: {self.converged}")
        
        return self.get_statistics()
    
    def get_statistics(self) -> Dict:
        """
        Get current algorithm statistics.
        
        Returns:
            Dictionary with statistics
        """
        return {
            'total_lines': self.stats['total_lines'],
            'avg_darkness': self.stats['avg_darkness'],
            'converged': self.converged,
            'convergence_iteration': self.stats['convergence_iteration'],
            'nail_count': self.nail_count,
            'canvas_size': self.canvas_size,
            'using_gpu': self.use_gpu
        }
    
    def get_line_sequence(self) -> List[int]:
        """
        Get the sequence of nails (line endpoints).
        
        Returns:
            List of nail indices in order
        """
        return self.line_sequence
    
    def get_canvas_as_image(self) -> np.ndarray:
        """
        Get current canvas state as a displayable image.
        
        Returns:
            Canvas as numpy array (uint8, 0-255 range)
        """
        if self.use_gpu:
            canvas = cp.asnumpy(self.current_canvas)
        else:
            canvas = self.current_canvas
        
        # Invert back (so dark areas are dark)
        canvas = 1.0 - canvas
        
        # Convert to uint8
        canvas = np.clip(canvas * 255, 0, 255).astype(np.uint8)
        
        return canvas
    
    def render_string_art(self, line_color: Tuple[int, int, int] = (0, 0, 0),
                          background_color: Tuple[int, int, int] = (255, 255, 255),
                          line_thickness: int = 1) -> np.ndarray:
        """
        Render the string art as a clean image with lines.
        
        Args:
            line_color: RGB color for lines
            background_color: RGB color for background
            line_thickness: Thickness of lines in pixels
            
        Returns:
            Rendered image as numpy array (uint8, RGB)
        """
        # Create blank canvas
        canvas = np.full((self.canvas_size, self.canvas_size, 3), 
                        background_color, dtype=np.uint8)
        
        # Draw all lines
        for i in range(len(self.line_sequence) - 1):
            nail1 = self.line_sequence[i]
            nail2 = self.line_sequence[i + 1]
            
            pt1 = tuple(self.nail_positions[nail1].astype(int))
            pt2 = tuple(self.nail_positions[nail2].astype(int))
            
            cv2.line(canvas, pt1, pt2, line_color, line_thickness, cv2.LINE_AA)
        
        return canvas
    
    def save_result(self, output_path: str, render_type: str = 'canvas') -> None:
        """
        Save the result to a file.
        
        Args:
            output_path: Path to save the image
            render_type: 'canvas' (current state) or 'lines' (clean render)
        """
        if render_type == 'canvas':
            image = self.get_canvas_as_image()
            # Convert grayscale to RGB
            if len(image.shape) == 2:
                image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        else:
            image = self.render_string_art()
        
        # Save using PIL
        img = Image.fromarray(image)
        img.save(output_path)
    
    def reset(self) -> None:
        """
        Reset the engine to initial state (after image load).
        """
        if self.original_image is not None:
            if self.use_gpu:
                self.current_canvas = cp.copy(self.original_image)
            else:
                self.current_canvas = np.copy(self.original_image)
        
        self.current_nail_idx = np.random.randint(0, self.nail_count)
        self.line_sequence = [self.current_nail_idx]
        self.darkness_scores = []
        self.converged = False
        
        self.stats = {
            'total_lines': 0,
            'avg_darkness': 0.0,
            'convergence_iteration': None
        }


# Utility functions

def create_engine_from_config(config: Dict) -> StringArtEngine:
    """
    Create a StringArtEngine from a configuration dictionary.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Initialized StringArtEngine
    """
    return StringArtEngine(
        nail_count=config.get('nail_count', 250),
        canvas_size=config.get('canvas_size', 800),
        max_lines=config.get('max_lines', 3000),
        line_weight=config.get('line_weight', 0.2),
        min_distance=config.get('min_distance', 20),
        lookahead=config.get('lookahead', None),
        use_gpu=config.get('use_gpu', True),
        convergence_threshold=config.get('convergence_threshold', 0.01),
        auto_contrast=config.get('auto_contrast', True)
    )


def test_engine():
    """
    Simple test function for the engine.
    """
    print("String Art Engine Test")
    print("=" * 50)
    
    # Check GPU availability
    if GPU_AVAILABLE:
        print("✓ GPU (CuPy) available")
    else:
        print("✗ GPU not available, using NumPy")
    
    # Create engine
    engine = StringArtEngine(
        nail_count=200,
        canvas_size=400,
        max_lines=100,
        use_gpu=False  # Use CPU for test
    )
    
    print(f"✓ Engine created with {engine.nail_count} nails")
    
    # Calculate nail positions
    positions = engine.calculate_nail_positions()
    print(f"✓ Nail positions calculated: {positions.shape}")
    
    # Test line pixel calculation
    x_coords, y_coords = engine.get_line_pixels(0, 100)
    print(f"✓ Line pixels calculated: {len(x_coords)} pixels")
    
    print("\nEngine test completed successfully!")


if __name__ == "__main__":
    test_engine()
