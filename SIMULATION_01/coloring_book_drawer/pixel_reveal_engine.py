#!/usr/bin/env python3
"""
Pixel Reveal Engine for Coloring Book Drawer
=============================================
Progressively reveals original image pixels in a drawing-like order.

The key insight: We're NOT redrawing strokes - we're revealing the 
original pixels using a mask that expands along skeleton paths.
This guarantees the final result is IDENTICAL to the original.
"""

import numpy as np
import cv2

# Scikit-image for skeleton extraction
try:
    from skimage.morphology import skeletonize, medial_axis
    from skimage import img_as_ubyte
    HAS_SKIMAGE = True
except ImportError:
    HAS_SKIMAGE = False
    print("scikit-image not found. Using OpenCV fallback for skeletonization.")


class PixelRevealEngine:
    """
    Progressively reveals original image pixels in a drawing-like order.
    """
    
    def __init__(self, image_path, target_width, target_height, padding=40, use_gpu=True):
        self.image_path = image_path
        self.target_width = target_width
        self.target_height = target_height
        self.padding = padding
        self.use_gpu = use_gpu
        
        # Processing results
        self.original_image = None      # RGB image to reveal
        self.binary_mask = None         # Where ink exists
        self.skeleton = None            # Centerline of strokes
        self.skeleton_distance = None   # Thickness at each skeleton point
        self.reveal_sequence = []       # Ordered list of (y, x, radius) points
        
        # Animation state
        self.reveal_mask = None         # Current reveal mask
        self.current_reveal_idx = 0     # Current position in reveal sequence
        self.brush_scale = 1.3          # Slightly larger brush for full coverage
        
        # Background color (white)
        self.bg_color = np.array([255, 255, 255], dtype=np.uint8)
    
    def process_image(self):
        """
        Main processing pipeline:
        1. Load and resize image
        2. Create binary ink mask
        3. Extract skeleton with distance transform
        4. Build ordered reveal sequence
        """
        print("Processing image for pixel-reveal animation...")
        
        # Load original image
        img = cv2.imread(str(self.image_path))
        if img is None:
            raise ValueError(f"Could not load image: {self.image_path}")
        
        # Convert to RGB (from BGR)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # Resize to fit canvas with padding
        img = self._resize_to_canvas(img)
        self.original_image = img
        
        # Create binary mask of ink regions
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        
        # Threshold to get ink (dark pixels)
        # Ink is dark on white background
        _, binary = cv2.threshold(gray, 220, 255, cv2.THRESH_BINARY_INV)
        
        # Clean up small noise
        kernel = np.ones((2, 2), np.uint8)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
        
        self.binary_mask = binary > 0
        
        # Extract skeleton with distance transform
        print("Extracting skeleton with medial axis transform...")
        self._extract_skeleton_with_distance()
        
        # Build ordered reveal sequence from skeleton
        print("Building reveal sequence...")
        self._build_reveal_sequence()
        
        # Initialize reveal mask
        h, w = self.original_image.shape[:2]
        self.reveal_mask = np.zeros((h, w), dtype=np.float32)
        self.current_reveal_idx = 0
        
        print(f"Ready! {len(self.reveal_sequence)} reveal points extracted.")
        return True
    
    def _resize_to_canvas(self, img):
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
    
    def _extract_skeleton_with_distance(self):
        """Extract skeleton and distance transform from ink regions."""
        if HAS_SKIMAGE:
            # Use scikit-image medial_axis which returns distance
            skeleton, distance = medial_axis(self.binary_mask, return_distance=True)
            self.skeleton = skeleton
            self.skeleton_distance = distance * skeleton
        else:
            # OpenCV fallback
            binary_uint8 = (self.binary_mask * 255).astype(np.uint8)
            
            # Distance transform
            distance = cv2.distanceTransform(binary_uint8, cv2.DIST_L2, 5)
            
            # Skeletonize using OpenCV
            try:
                skeleton = cv2.ximgproc.thinning(binary_uint8, 
                                                  thinningType=cv2.ximgproc.THINNING_ZHANGSUEN)
            except AttributeError:
                skeleton = self._morphological_skeleton(binary_uint8)
            
            self.skeleton = skeleton > 0
            self.skeleton_distance = distance * (skeleton > 0)
    
    def _morphological_skeleton(self, binary):
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
    
    def _build_reveal_sequence(self):
        """
        Build an ordered sequence of (y, x, radius) points for progressive reveal.
        Uses graph-based path traversal for natural drawing order.
        """
        # Get skeleton points
        skeleton_points = np.argwhere(self.skeleton)
        
        if len(skeleton_points) == 0:
            self.reveal_sequence = []
            return
        
        # Build graph from skeleton
        print(f"  Building graph from {len(skeleton_points)} skeleton points...")
        paths = self._extract_ordered_paths()
        
        # Sort paths for natural drawing order (top-to-bottom, left-to-right)
        paths = self._sort_paths_naturally(paths)
        
        # Flatten paths into reveal sequence with NO subsampling for smooth animation
        # Using every single skeleton point ensures maximum smoothness
        subsample = 1  # Use every point (changed from 2 for smoother animation)
        self.reveal_sequence = []
        
        for path in paths:
            # Always include endpoints
            if len(path) > 0:
                self.reveal_sequence.append(path[0])
            
            # Subsample middle points
            for i in range(subsample, len(path) - 1, subsample):
                self.reveal_sequence.append(path[i])
            
            # Always include last point
            if len(path) > 1:
                self.reveal_sequence.append(path[-1])
        
        print(f"  Created {len(self.reveal_sequence)} reveal points from {len(paths)} paths")
    
    def _extract_ordered_paths(self):
        """Extract skeleton as ordered paths using graph traversal."""
        # Build adjacency structure
        point_set = set(map(tuple, np.argwhere(self.skeleton)))
        
        # 8-connectivity neighbors
        neighbors_offsets = [
            (-1, -1), (-1, 0), (-1, 1),
            (0, -1),           (0, 1),
            (1, -1),  (1, 0),  (1, 1)
        ]
        
        # Build graph
        adjacency = {}
        for pt in point_set:
            adjacency[pt] = []
            for dy, dx in neighbors_offsets:
                neighbor = (pt[0] + dy, pt[1] + dx)
                if neighbor in point_set:
                    adjacency[pt].append(neighbor)
        
        # Find endpoints (degree 1) - natural stroke starts
        endpoints = [pt for pt, neighbors in adjacency.items() if len(neighbors) == 1]
        
        # If no endpoints (all cycles), use any point
        if not endpoints and point_set:
            endpoints = [next(iter(point_set))]
        
        # Trace paths from endpoints
        paths = []
        visited = set()
        
        def trace_path(start):
            """Trace a path from start until we hit a visited point or dead end."""
            path = []
            current = start
            
            while current not in visited:
                visited.add(current)
                y, x = current
                radius = max(1.0, self.skeleton_distance[y, x] * self.brush_scale)
                path.append((y, x, radius))
                
                # Find next unvisited neighbor
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
        
        # Handle remaining unvisited points (cycles)
        remaining = point_set - visited
        while remaining:
            start = next(iter(remaining))
            path = trace_path(start)
            if len(path) > 2:
                paths.append(path)
            remaining = point_set - visited
        
        return paths
    
    def _sort_paths_naturally(self, paths):
        """Sort paths for natural drawing order."""
        if not paths:
            return paths
        
        def path_sort_key(path):
            # Use starting point
            y, x, _ = path[0]
            # Primary: top to bottom (bucket by rows)
            # Secondary: left to right
            return (y // 30, x)  # 30px row buckets
        
        return sorted(paths, key=path_sort_key)
    
    def reveal_next_batch(self, points_per_update=50):
        """
        Reveal the next batch of points with interpolation for smooth strokes.
        Returns True if there are more points to reveal, False if done.
        """
        if self.current_reveal_idx >= len(self.reveal_sequence):
            return False
        
        end_idx = min(self.current_reveal_idx + points_per_update, len(self.reveal_sequence))
        
        # Reveal this batch of points with interpolation between consecutive points
        prev_point = None
        for i in range(self.current_reveal_idx, end_idx):
            y, x, radius = self.reveal_sequence[i]
            
            # If we have a previous point, interpolate between them for smooth strokes
            if prev_point is not None:
                py, px, pr = prev_point
                # Calculate distance between points
                dist = np.sqrt((x - px)**2 + (y - py)**2)
                
                # If points are far apart, add interpolated circles
                if dist > 2.0:  # Threshold for interpolation
                    steps = int(np.ceil(dist / 1.5))  # Interpolate every 1.5 pixels
                    for step in range(1, steps):
                        t = step / steps
                        interp_x = px + t * (x - px)
                        interp_y = py + t * (y - py)
                        interp_r = pr + t * (radius - pr)
                        cv2.circle(self.reveal_mask, 
                                 (int(interp_x), int(interp_y)), 
                                 int(np.ceil(interp_r)), 1.0, -1)
            
            # Draw the actual point
            cv2.circle(self.reveal_mask, (int(x), int(y)), int(np.ceil(radius)), 1.0, -1)
            prev_point = (y, x, radius)
        
        self.current_reveal_idx = end_idx
        return True
    
    def get_current_frame(self):
        """
        Get the current frame with revealed pixels.
        Returns an RGB numpy array.
        """
        # Only reveal ink regions
        effective_mask = self.reveal_mask * self.binary_mask.astype(np.float32)
        
        # Expand mask to 3 channels
        mask_3ch = np.stack([effective_mask] * 3, axis=-1)
        
        # Compose: white background + revealed original pixels
        frame = (self.bg_color * (1 - mask_3ch) + self.original_image * mask_3ch)
        
        return frame.astype(np.uint8)
    
    def get_progress(self):
        """Get current reveal progress as a float 0-1."""
        if len(self.reveal_sequence) == 0:
            return 1.0
        return self.current_reveal_idx / len(self.reveal_sequence)
    
    def is_complete(self):
        """Check if reveal animation is complete."""
        return self.current_reveal_idx >= len(self.reveal_sequence)
