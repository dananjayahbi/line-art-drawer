#!/usr/bin/env python3
"""
Sand Falling Art - Control Panel (PySide6)
===========================================
Compatibility layer for control panel imports.
"""

from custom_widgets import ToggleSwitch, ImageUploadWidget, load_icon
from video_thread import VideoGenerationThread
from control_panel_main import ControlPanel, main

__all__ = [
    'ToggleSwitch',
    'ImageUploadWidget',
    'VideoGenerationThread',
    'ControlPanel',
    'load_icon',
    'main'
]

if __name__ == '__main__':
    main()
