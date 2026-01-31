#!/usr/bin/env python3
"""
Pixel Sorting Art - Control Panel (PySide6)
============================================
Modern PySide6-based GUI for configuring and launching the pixel sorting art simulation.
Features vaporwave/cyberpunk theme with responsive layout and drag & drop support.

NOTE: This file serves as a compatibility layer that imports from the modularized components:
- custom_widgets.py: Custom UI widgets (ToggleSwitch, ImageUploadWidget, selectors, etc.)
- video_thread.py: VideoGenerationThread for FFmpeg video generation
- control_panel_main.py: Main ControlPanel window and entry point

For new development, import directly from the specific modules.
"""

# Import and re-export everything from modularized components for backward compatibility
from custom_widgets import (
    ToggleSwitch,
    ImageUploadWidget,
    ColorStyleSelector,
    SortingAlgorithmSelector,
    SortDirectionSelector,
    SortCriteriaSelector,
    ClickableImageLabel,
    load_icon,
    THEME
)
from video_thread import (
    VideoGenerationThread,
    VideoGenerationThreadAdvanced,
    get_quality_crf
)
from control_panel_main import ControlPanel, main

# Re-export for backward compatibility
__all__ = [
    # Custom widgets
    'ToggleSwitch',
    'ImageUploadWidget',
    'ColorStyleSelector',
    'SortingAlgorithmSelector',
    'SortDirectionSelector',
    'SortCriteriaSelector',
    'ClickableImageLabel',
    'load_icon',
    'THEME',
    # Video generation
    'VideoGenerationThread',
    'VideoGenerationThreadAdvanced',
    'get_quality_crf',
    # Main panel
    'ControlPanel',
    'main'
]

if __name__ == '__main__':
    main()
