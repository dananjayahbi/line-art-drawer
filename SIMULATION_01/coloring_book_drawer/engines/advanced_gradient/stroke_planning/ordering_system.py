"""
Stroke Ordering System
=======================
Intelligently orders all strokes for natural drawing appearance.
Follows the principle: Structure → Form → Detail
Implements the 6-phase hierarchical reveal system.
"""

import math
import random
from typing import List, Dict
from .contour_strokes import StrokePoint
from ..config import AdvancedGradientConfig


class StrokeOrderingSystem:
    """
    Orders strokes for natural drawing appearance.
    Creates a 6-phase reveal sequence that mimics real artist workflow.
    """

    def __init__(self, config: AdvancedGradientConfig = None):
        self.config = config or AdvancedGradientConfig()
        random.seed(42)

    def build_ordered_sequence(self, stroke_groups: Dict[str, List[StrokePoint]]) -> List[StrokePoint]:
        """
        Create the final ordered reveal sequence from all stroke groups.

        Args:
            stroke_groups: Dict mapping phase names to stroke lists:
                - 'primary_contour': Main edges and boundaries
                - 'gradient': Smooth tonal regions
                - 'highlight': Very light areas
                - 'texture': Hair, fabric, textured areas
                - 'shadow': Deep shadow regions
                - 'detail': Fine secondary edges

        Returns:
            Single ordered list of StrokePoints for animation
        """
        sequence = []

        # ═══════════════════════════════════════════════════════
        # PHASE 1: Quick Sketch (5% of animation)
        # Primary contours - establishes the subject immediately
        # ═══════════════════════════════════════════════════════
        primary_contours = stroke_groups.get('primary_contour', [])
        if primary_contours:
            phase1 = self._cluster_spatially(primary_contours)
            sequence.extend(phase1)
            print(f"    Phase 1 (Quick Sketch): {len(phase1)} points")

        # ═══════════════════════════════════════════════════════
        # PHASE 2: Form Building (35% of animation)
        # Light gradient regions - establishes 3D form and lighting
        # ═══════════════════════════════════════════════════════
        highlights = stroke_groups.get('highlight', [])
        gradients = stroke_groups.get('gradient', [])

        phase2 = []
        if highlights:
            phase2.extend(highlights)
        if gradients:
            # Sort gradients: light areas first
            sorted_gradients = sorted(gradients, key=lambda p: p.intensity)
            phase2.extend(sorted_gradients)

        if phase2:
            sequence.extend(phase2)
            print(f"    Phase 2 (Form Building): {len(phase2)} points")

        # ═══════════════════════════════════════════════════════
        # PHASE 3: Texture Development (25% of animation)
        # Direction-aware hatching for textured areas
        # ═══════════════════════════════════════════════════════
        textures = stroke_groups.get('texture', [])
        if textures:
            phase3 = self._cluster_by_region(textures)
            sequence.extend(phase3)
            print(f"    Phase 3 (Texture Work): {len(phase3)} points")

        # ═══════════════════════════════════════════════════════
        # PHASE 4: Shadow Deepening (25% of animation)
        # Dense multi-layer overlapping for dark areas
        # ═══════════════════════════════════════════════════════
        shadows = stroke_groups.get('shadow', [])
        if shadows:
            # Sort by intensity - darken progressively
            phase4 = sorted(shadows, key=lambda p: p.intensity)
            sequence.extend(phase4)
            print(f"    Phase 4 (Shadow Depth): {len(phase4)} points")

        # ═══════════════════════════════════════════════════════
        # PHASE 5: Fine Details (8% of animation)
        # Secondary edges, fine textures
        # ═══════════════════════════════════════════════════════
        details = stroke_groups.get('detail', [])
        if details:
            phase5 = self._cluster_spatially(details)
            sequence.extend(phase5)
            print(f"    Phase 5 (Fine Details): {len(phase5)} points")

        # ═══════════════════════════════════════════════════════
        # PHASE 6: Final Enhancement (2% of animation)
        # Touch-up remaining uncovered dark pixels
        # ═══════════════════════════════════════════════════════
        enhancement = stroke_groups.get('enhancement', [])
        if enhancement:
            sequence.extend(enhancement)
            print(f"    Phase 6 (Enhancement): {len(enhancement)} points")

        print(f"  [Ordering] Total ordered sequence: {len(sequence)} points")
        return sequence

    def _cluster_spatially(self, strokes: List[StrokePoint]) -> List[StrokePoint]:
        """Cluster strokes spatially to minimize pen jumps."""
        if not strokes or len(strokes) <= 1:
            return strokes

        # Simple grid-based clustering
        grid_size = 50
        clusters = {}

        for s in strokes:
            gx = int(s.x / grid_size)
            gy = int(s.y / grid_size)
            key = (gy, gx)
            clusters.setdefault(key, []).append(s)

        # Sort clusters in serpentine pattern
        sorted_keys = sorted(clusters.keys(),
                             key=lambda k: (k[0], k[1] if k[0] % 2 == 0 else -k[1]))

        result = []
        for key in sorted_keys:
            cluster = clusters[key]
            # Sort within cluster by proximity
            if result:
                last = result[-1]
                cluster.sort(key=lambda p: (p.x - last.x) ** 2 + (p.y - last.y) ** 2)
            result.extend(cluster)

        return result

    def _cluster_by_region(self, strokes: List[StrokePoint]) -> List[StrokePoint]:
        """
        Cluster strokes by spatial regions for region-at-a-time reveal.
        Uses larger grid cells than _cluster_spatially for region grouping.
        """
        if not strokes:
            return strokes

        grid_size = 80  # Larger grid for regional grouping
        clusters = {}

        for s in strokes:
            gx = int(s.x / grid_size)
            gy = int(s.y / grid_size)
            key = (gy, gx)
            clusters.setdefault(key, []).append(s)

        # Sort by grid position with some randomization within
        sorted_keys = sorted(clusters.keys(),
                             key=lambda k: (k[0], k[1] if k[0] % 2 == 0 else -k[1]))

        result = []
        for key in sorted_keys:
            cluster = clusters[key]
            # Light-to-dark within each cluster
            cluster.sort(key=lambda p: p.intensity)
            result.extend(cluster)

        return result

    def get_phase_for_progress(self, progress: float) -> str:
        """
        Get the current drawing phase name for a given progress value.

        Args:
            progress: 0.0-1.0 animation progress

        Returns:
            Human-readable phase name
        """
        cfg = self.config
        if progress < cfg.phase_1_pct:
            return "Quick Sketch"
        elif progress < cfg.phase_1_pct + cfg.phase_2_pct:
            return "Form Building"
        elif progress < cfg.phase_1_pct + cfg.phase_2_pct + cfg.phase_3_pct:
            return "Texture Work"
        elif progress < (cfg.phase_1_pct + cfg.phase_2_pct +
                         cfg.phase_3_pct + cfg.phase_4_pct):
            return "Shadow Depth"
        elif progress < (cfg.phase_1_pct + cfg.phase_2_pct +
                         cfg.phase_3_pct + cfg.phase_4_pct + cfg.phase_5_pct):
            return "Fine Details"
        else:
            return "Enhancement"

    def get_speed_for_progress(self, progress: float) -> float:
        """
        Get the speed multiplier for the current animation progress.
        Creates artistic rhythm by varying speed per phase.
        """
        cfg = self.config.phase_speeds
        phase = self.get_phase_for_progress(progress)

        speed_map = {
            "Quick Sketch": cfg.phase_1_speed,
            "Form Building": cfg.phase_2_speed,
            "Texture Work": cfg.phase_3_speed,
            "Shadow Depth": cfg.phase_4_speed,
            "Fine Details": cfg.phase_5_speed,
            "Enhancement": cfg.phase_6_speed,
        }
        return speed_map.get(phase, 1.0)
