"""
Pixel Reveal Engine - Backward compatibility stub.
====================================================
This module has been moved to engines/pixel_reveal/.
This file re-exports all public symbols for backward compatibility.
"""

# Re-export from new location
from engines.pixel_reveal.engine import PixelRevealEngine

__all__ = ['PixelRevealEngine']
