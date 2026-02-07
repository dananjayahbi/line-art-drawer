"""
Region Classifier
===================
Classifies segmented image regions by their visual characteristics:
smooth gradient, texture, edge, deep shadow, highlight, or focal.
"""

import numpy as np
from dataclasses import dataclass
from typing import List, Tuple
from ..config import RegionType, ClassificationConfig

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False


@dataclass
class RegionInfo:
    """Information about a classified image region."""
    region_id: int
    region_type: RegionType
    mask: np.ndarray         # Boolean mask (H, W)
    centroid: Tuple[int, int]  # (y, x) center
    area: int                # Pixel count
    mean_intensity: float    # Average brightness [0, 255]
    intensity_variance: float  # Brightness variance
    edge_density: float      # Fraction of edge pixels
    assigned_strategy: object = None  # Set during assignment phase


class RegionClassifier:
    """Classifies image regions by visual characteristics."""
    
    def __init__(self, config: ClassificationConfig):
        self.config = config
        self.highlight_thresh = config.highlight_threshold
        self.shadow_thresh = config.shadow_threshold
        self.edge_thresh = config.edge_density_threshold
        self.variance_thresh = config.variance_threshold
        
    def classify_regions(self, gray: np.ndarray,
                          segments: np.ndarray,
                          focal_mask: np.ndarray = None) -> List[RegionInfo]:
        """
        Analyze and classify each segmented region.
        
        Args:
            gray: (H, W) grayscale image
            segments: (H, W) int label map
            focal_mask: (H, W) bool mask of focal areas (optional)
            
        Returns:
            List of RegionInfo for each region
        """
        # Precompute edge map
        edge_map = self._compute_edge_map(gray)
        
        regions = []
        unique_ids = np.unique(segments)
        
        for region_id in unique_ids:
            mask = segments == region_id
            region_data = gray[mask]
            
            if len(region_data) == 0:
                continue
            
            # Compute characteristics
            mean_intensity = float(np.mean(region_data))
            variance = float(np.var(region_data))
            edge_density = self._compute_edge_density(edge_map, mask)
            centroid = self._compute_centroid(mask)
            area = int(np.sum(mask))
            
            # Check if focal
            is_focal = False
            if focal_mask is not None:
                overlap = np.sum(mask & focal_mask)
                if overlap > 0.3 * area:
                    is_focal = True
            
            # Classify
            if is_focal:
                region_type = RegionType.FOCAL
            else:
                region_type = self._classify(mean_intensity, variance, edge_density)
            
            regions.append(RegionInfo(
                region_id=int(region_id),
                region_type=region_type,
                mask=mask,
                centroid=centroid,
                area=area,
                mean_intensity=mean_intensity,
                intensity_variance=variance,
                edge_density=edge_density
            ))
        
        return regions
    
    def _classify(self, mean_intensity: float, variance: float,
                  edge_density: float) -> RegionType:
        """Decision tree for region classification."""
        if mean_intensity > self.highlight_thresh:
            return RegionType.HIGHLIGHT
        elif mean_intensity < self.shadow_thresh:
            return RegionType.DEEP_SHADOW
        elif edge_density > self.edge_thresh:
            return RegionType.EDGE
        elif variance > self.variance_thresh:
            return RegionType.TEXTURE
        else:
            return RegionType.SMOOTH_GRADIENT
    
    def _compute_edge_map(self, gray: np.ndarray) -> np.ndarray:
        """Compute binary edge map using Canny or Sobel."""
        if HAS_CV2:
            edges = cv2.Canny(gray.astype(np.uint8), 50, 150)
            return (edges > 0).astype(np.float32)
        else:
            # Simple Sobel approximation
            gy = np.abs(np.diff(gray.astype(np.float32), axis=0))
            gx = np.abs(np.diff(gray.astype(np.float32), axis=1))
            
            h, w = gray.shape
            edge_mag = np.zeros((h, w), dtype=np.float32)
            edge_mag[:-1, :] += gy
            edge_mag[:, :-1] += gx
            
            threshold = np.percentile(edge_mag, 85)
            return (edge_mag > threshold).astype(np.float32)
    
    def _compute_edge_density(self, edge_map: np.ndarray,
                               mask: np.ndarray) -> float:
        """Compute fraction of edge pixels in a region."""
        region_area = np.sum(mask)
        if region_area == 0:
            return 0.0
        edge_count = np.sum(edge_map[mask] > 0)
        return float(edge_count / region_area)
    
    def _compute_centroid(self, mask: np.ndarray) -> Tuple[int, int]:
        """Compute the centroid (y, x) of a boolean mask."""
        coords = np.argwhere(mask)
        if len(coords) == 0:
            return (0, 0)
        return (int(np.mean(coords[:, 0])), int(np.mean(coords[:, 1])))
