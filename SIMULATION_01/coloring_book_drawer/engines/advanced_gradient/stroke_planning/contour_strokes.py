"""
Contour Stroke Generator
=========================
Generates stroke paths along detected edges/contours using skeleton extraction.
These strokes form the primary structure of the drawing (Phase 1).
"""

import numpy as np
import cv2
import math
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass


@dataclass
class StrokePoint:
    """A single point in a stroke path."""
    x: float
    y: float
    pressure: float      # 0.0-1.0
    angle: float         # radians
    width: float         # brush width
    phase: str           # 'contour', 'gradient', 'texture', 'shadow', 'detail'
    intensity: float     # target darkness 0=white, 1=black


class ContourStrokeGenerator:
    """
    Generates stroke paths along image contours (edges).
    Uses skeleton extraction and path tracing for natural drawing order.
    """

    def __init__(self, use_gpu: bool = False):
        self.use_gpu = use_gpu
        self._has_skimage = False
        try:
            from skimage.morphology import medial_axis
            self._has_skimage = True
        except ImportError:
            pass

    def generate(self, edge_primary: np.ndarray, edge_secondary: np.ndarray,
                 intensity_map: np.ndarray, coherence: np.ndarray = None) -> Dict[str, List[StrokePoint]]:
        """
        Generate contour strokes from edge maps.

        Args:
            edge_primary: Boolean mask of primary (coarse) edges
            edge_secondary: Boolean mask of secondary (fine-only) edges
            intensity_map: Continuous intensity map (0-1, dark=high)
            coherence: Optional coherence map from structure tensor

        Returns:
            Dict with 'primary_contour' and 'detail' stroke lists
        """
        result = {
            'primary_contour': [],
            'detail': [],
        }

        # Generate primary contour strokes
        if np.any(edge_primary):
            skeleton, distance = self._extract_skeleton(edge_primary)
            paths = self._extract_ordered_paths(skeleton, distance)
            for path in paths:
                strokes = self._path_to_strokes(path, intensity_map, 'contour')
                result['primary_contour'].extend(strokes)

        # Generate detail strokes from secondary edges
        if np.any(edge_secondary):
            skeleton_sec, distance_sec = self._extract_skeleton(edge_secondary)
            paths_sec = self._extract_ordered_paths(skeleton_sec, distance_sec)
            for path in paths_sec:
                strokes = self._path_to_strokes(path, intensity_map, 'detail')
                result['detail'].extend(strokes)

        print(f"  [ContourStrokes] Primary: {len(result['primary_contour'])} pts, "
              f"Detail: {len(result['detail'])} pts")
        return result

    def _extract_skeleton(self, edge_mask: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Extract skeleton and distance transform from edge mask."""
        binary = (edge_mask > 0).astype(np.uint8) * 255

        # Dilate slightly to connect broken edges
        kernel = np.ones((2, 2), np.uint8)
        binary = cv2.dilate(binary, kernel, iterations=1)

        if self._has_skimage:
            from skimage.morphology import medial_axis
            bool_mask = binary > 0
            if not np.any(bool_mask):
                return np.zeros_like(binary, dtype=bool), np.zeros_like(binary, dtype=np.float64)
            skeleton, distance = medial_axis(bool_mask, return_distance=True)
            return skeleton, distance * skeleton
        else:
            distance = cv2.distanceTransform(binary, cv2.DIST_L2, 5)
            try:
                skeleton = cv2.ximgproc.thinning(binary)
            except AttributeError:
                skeleton = self._morphological_skeleton(binary)
            return skeleton > 0, distance * (skeleton > 0)

    def _morphological_skeleton(self, binary: np.ndarray) -> np.ndarray:
        """Fallback morphological skeleton extraction."""
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

    def _extract_ordered_paths(self, skeleton: np.ndarray,
                                distance: np.ndarray) -> List[List[Tuple[int, int, float]]]:
        """Extract ordered paths from skeleton using graph traversal."""
        skeleton_points = np.argwhere(skeleton)
        if len(skeleton_points) == 0:
            return []

        point_set = set(map(tuple, skeleton_points))
        neighbors_offsets = [
            (-1, -1), (-1, 0), (-1, 1),
            (0, -1),           (0, 1),
            (1, -1),  (1, 0),  (1, 1)
        ]

        # Build adjacency
        adjacency = {}
        for pt in point_set:
            adjacency[pt] = []
            for dy, dx in neighbors_offsets:
                neighbor = (pt[0] + dy, pt[1] + dx)
                if neighbor in point_set:
                    adjacency[pt].append(neighbor)

        # Find endpoints (degree 1)
        endpoints = [pt for pt, nbrs in adjacency.items() if len(nbrs) == 1]
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
                radius = max(1.0, float(distance[y, x]) * 1.3)
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

        for ep in endpoints:
            if ep not in visited:
                path = trace_path(ep)
                if len(path) > 2:
                    paths.append(path)

        remaining = point_set - visited
        while remaining:
            start = next(iter(remaining))
            path = trace_path(start)
            if len(path) > 2:
                paths.append(path)
            remaining = point_set - visited

        return self._sort_paths_naturally(paths)

    def _sort_paths_naturally(self, paths: List) -> List:
        """Sort paths for natural drawing order (spatially clustered)."""
        if not paths or len(paths) <= 1:
            return paths

        import random
        random.seed(42)

        path_info = []
        for i, path in enumerate(paths):
            if path:
                y, x, _ = path[0]
                ey, ex, _ = path[-1]
                path_info.append({
                    'index': i, 'path': path,
                    'start_x': x, 'start_y': y,
                    'end_x': ex, 'end_y': ey,
                    'length': len(path)
                })

        if not path_info:
            return paths

        # Grid-based spatial sorting
        num_rx, num_ry = 4, 5
        all_x = [p['start_x'] for p in path_info]
        all_y = [p['start_y'] for p in path_info]
        min_x, max_x = min(all_x), max(all_x)
        min_y, max_y = min(all_y), max(all_y)
        rw = (max_x - min_x + 1) / num_rx
        rh = (max_y - min_y + 1) / num_ry

        regions = {}
        for p in path_info:
            rx = min(int((p['start_x'] - min_x) / max(1, rw)), num_rx - 1)
            ry = min(int((p['start_y'] - min_y) / max(1, rh)), num_ry - 1)
            key = (ry, rx)
            regions.setdefault(key, []).append(p)

        sorted_keys = sorted(regions.keys(),
                             key=lambda k: (k[0], k[1] if k[0] % 2 == 0 else -k[1]))

        sorted_paths = []
        cur = (min_x, min_y)
        for key in sorted_keys:
            remaining = regions[key].copy()
            while remaining:
                best_idx = 0
                best_dist = float('inf')
                for i, p in enumerate(remaining):
                    d = math.sqrt((p['start_x'] - cur[0]) ** 2 +
                                  (p['start_y'] - cur[1]) ** 2)
                    if d < best_dist:
                        best_dist = d
                        best_idx = i
                bp = remaining.pop(best_idx)
                sorted_paths.append(bp['path'])
                cur = (bp['end_x'], bp['end_y'])

        return sorted_paths

    def _path_to_strokes(self, path: List[Tuple[int, int, float]],
                         intensity_map: np.ndarray,
                         phase: str) -> List[StrokePoint]:
        """Convert a skeleton path to stroke points."""
        strokes = []
        h, w = intensity_map.shape

        for i, (y, x, radius) in enumerate(path):
            if not (0 <= y < h and 0 <= x < w):
                continue

            # Calculate angle from neighboring points
            if i > 0:
                py, px, _ = path[i - 1]
                angle = math.atan2(y - py, x - px)
            elif i < len(path) - 1:
                ny, nx, _ = path[i + 1]
                angle = math.atan2(ny - y, nx - x)
            else:
                angle = 0

            # Natural pressure variation
            pressure = 0.7 + 0.3 * math.sin(i * 0.1)

            strokes.append(StrokePoint(
                x=float(x), y=float(y),
                pressure=pressure,
                angle=angle,
                width=max(1.5, radius * 1.2),
                phase=phase,
                intensity=float(intensity_map[int(y), int(x)])
            ))

        return strokes
