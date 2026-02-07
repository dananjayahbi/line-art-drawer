"""
Engine 3E: Adaptive Brush Simulation
======================================
Physics-based pencil simulation with realistic tip modeling,
paper texture interaction, pressure dynamics, and graphite
accumulation with saturation behavior.

Usage:
    from engines.adaptive_brush import AdaptiveBrushEngine, AdaptiveBrushConfig
    
    engine = AdaptiveBrushEngine(
        image_path="artwork.png",
        width=1280, height=720,
        tip_shape="round",
        pencil_hardness=0.5,
        paper_type="cold_press"
    )
    engine.process_image()
    
    while engine.reveal_next_batch(100):
        frame = engine.get_current_frame()
"""

from .engine import AdaptiveBrushEngine
from .config import AdaptiveBrushConfig, TipShape, PaperType

__all__ = [
    "AdaptiveBrushEngine",
    "AdaptiveBrushConfig",
    "TipShape",
    "PaperType",
]
