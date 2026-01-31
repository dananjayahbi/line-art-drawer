#!/usr/bin/env python3
"""
Pendulum Paint Art - Control Panel (PySide6)
==============================================
Modern PySide6-based GUI for configuring and launching the pendulum paint simulation.
Features responsive layout, drag & drop support, and modern styling.

NOTE: This file serves as a compatibility layer that imports from the modularized components:
- custom_widgets.py: Custom UI widgets (ToggleSwitch, ImageUploadWidget, ColorPickerButton, etc.)
- video_thread.py: VideoGenerationThread for FFmpeg video generation
- control_panel_main.py: Main ControlPanel window and entry point

For new development, import directly from the specific modules.
"""

# Import and re-export everything from modularized components for backward compatibility
from custom_widgets import (
    ToggleSwitch, 
    ImageUploadWidget, 
    ColorPickerButton,
    load_icon
)
from video_thread import VideoGenerationThread
from control_panel_main import ControlPanel, main

# Re-export for backward compatibility
__all__ = [
    'ToggleSwitch',
    'ImageUploadWidget', 
    'ColorPickerButton',
    'VideoGenerationThread',
    'ControlPanel',
    'load_icon',
    'main'
]

if __name__ == '__main__':
    main()
