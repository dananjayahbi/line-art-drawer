"""
Analysis sub-package for Engine 3 – Advanced Gradient Shading Engine.
=====================================================================
Provides the first-stage analysis components used by the engine pipeline:

* **StructureTensorAnalyzer** – per-pixel orientation & coherence via
  structure tensor eigenanalysis.
* **MultiScaleEdgeDetector** – two-tier (fine + coarse) edge detection.
* **RegionSegmenter** – SLIC superpixel segmentation with automatic
  region classification.
* **ContinuousIntensityMapper** – perceptual gamma-corrected intensity
  mapping for reveal priority & stroke density.
"""

from coloring_book_drawer.engines.advanced_gradient.analysis.structure_tensor import (
    StructureTensorAnalyzer,
)
from coloring_book_drawer.engines.advanced_gradient.analysis.edge_detector import (
    MultiScaleEdgeDetector,
)
from coloring_book_drawer.engines.advanced_gradient.analysis.region_segmenter import (
    RegionSegmenter,
)
from coloring_book_drawer.engines.advanced_gradient.analysis.intensity_mapper import (
    ContinuousIntensityMapper,
)

__all__ = [
    "StructureTensorAnalyzer",
    "MultiScaleEdgeDetector",
    "RegionSegmenter",
    "ContinuousIntensityMapper",
]
