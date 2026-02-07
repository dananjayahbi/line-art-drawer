"""
Image Segmenter
=================
Segments the input image into coherent regions using superpixel
algorithms, then merges small regions into neighbors.
"""

import numpy as np
from ..config import SegmentationConfig

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

try:
    from skimage.segmentation import slic
    from skimage.measure import regionprops, label
    HAS_SKIMAGE = True
except ImportError:
    HAS_SKIMAGE = False


class ImageSegmenter:
    """Segments an image into coherent regions for per-region strategy assignment."""
    
    def __init__(self, config: SegmentationConfig):
        self.config = config
        self.num_segments = config.num_segments
        self.min_area = config.min_region_area
        self.compactness = config.compactness
        self.merge_threshold = config.merge_threshold
        
    def segment(self, image: np.ndarray, gray: np.ndarray) -> np.ndarray:
        """
        Segment image into labeled regions.
        
        Args:
            image: (H, W, 3) RGB image
            gray: (H, W) grayscale image
            
        Returns:
            (H, W) int32 label map where each pixel has a region ID
        """
        if HAS_SKIMAGE:
            segments = self._slic_segment(image)
        else:
            segments = self._grid_segment(gray)
        
        # Merge small regions
        segments = self._merge_small_regions(segments, gray)
        
        # Relabel to ensure contiguous IDs starting from 0
        segments = self._relabel_contiguous(segments)
        
        return segments
    
    def _slic_segment(self, image: np.ndarray) -> np.ndarray:
        """Use SLIC superpixels for high-quality segmentation."""
        segments = slic(
            image,
            n_segments=self.num_segments,
            compactness=self.compactness,
            sigma=1.0,
            start_label=0
        )
        return segments.astype(np.int32)
    
    def _grid_segment(self, gray: np.ndarray) -> np.ndarray:
        """
        Fallback: grid-based segmentation with intensity clustering.
        Used when scikit-image is not available.
        """
        h, w = gray.shape
        
        # Calculate grid size to achieve approximate target segment count
        total_pixels = h * w
        pixels_per_segment = total_pixels / max(1, self.num_segments)
        cell_size = max(8, int(np.sqrt(pixels_per_segment)))
        
        segments = np.zeros((h, w), dtype=np.int32)
        seg_id = 0
        
        for y in range(0, h, cell_size):
            for x in range(0, w, cell_size):
                y_end = min(y + cell_size, h)
                x_end = min(x + cell_size, w)
                segments[y:y_end, x:x_end] = seg_id
                seg_id += 1
        
        # Refine: split cells with high intensity variance
        refined = segments.copy()
        max_id = seg_id
        
        for sid in range(seg_id):
            mask = segments == sid
            region_data = gray[mask]
            if len(region_data) == 0:
                continue
                
            variance = np.var(region_data)
            if variance > self.config.merge_threshold * 5000:
                # Split by intensity threshold (median)
                median_val = np.median(region_data)
                bright_mask = mask & (gray >= median_val)
                dark_mask = mask & (gray < median_val)
                
                if np.sum(bright_mask) > 0 and np.sum(dark_mask) > 0:
                    refined[bright_mask] = max_id
                    max_id += 1
        
        return refined
    
    def _merge_small_regions(self, segments: np.ndarray,
                              gray: np.ndarray) -> np.ndarray:
        """Merge regions smaller than min_area into their most similar neighbor."""
        unique_ids = np.unique(segments)
        merged = segments.copy()
        
        for seg_id in unique_ids:
            mask = merged == seg_id
            area = np.sum(mask)
            
            if area >= self.min_area:
                continue
            
            # Find neighboring region IDs
            if HAS_CV2:
                dilated = cv2.dilate(mask.astype(np.uint8), np.ones((3, 3), np.uint8))
                neighbor_mask = (dilated > 0) & ~mask
            else:
                # Manual dilation
                neighbor_mask = np.zeros_like(mask)
                neighbor_mask[1:] |= mask[:-1]
                neighbor_mask[:-1] |= mask[1:]
                neighbor_mask[:, 1:] |= mask[:, :-1]
                neighbor_mask[:, :-1] |= mask[:, 1:]
                neighbor_mask = neighbor_mask & ~mask
            
            neighbor_ids = np.unique(merged[neighbor_mask])
            neighbor_ids = neighbor_ids[neighbor_ids != seg_id]
            
            if len(neighbor_ids) == 0:
                continue
            
            # Find most similar neighbor by mean intensity
            region_mean = np.mean(gray[mask])
            best_id = neighbor_ids[0]
            best_diff = float('inf')
            
            for nid in neighbor_ids:
                n_mask = merged == nid
                n_mean = np.mean(gray[n_mask])
                diff = abs(region_mean - n_mean)
                if diff < best_diff:
                    best_diff = diff
                    best_id = nid
            
            merged[mask] = best_id
        
        return merged
    
    def _relabel_contiguous(self, segments: np.ndarray) -> np.ndarray:
        """Relabel segments to contiguous IDs 0, 1, 2, ..."""
        unique_ids = np.unique(segments)
        relabel_map = {old_id: new_id for new_id, old_id in enumerate(unique_ids)}
        
        relabeled = np.zeros_like(segments)
        for old_id, new_id in relabel_map.items():
            relabeled[segments == old_id] = new_id
        
        return relabeled
    
    def get_region_count(self, segments: np.ndarray) -> int:
        """Get number of unique regions."""
        return len(np.unique(segments))
