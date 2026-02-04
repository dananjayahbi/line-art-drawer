"""
Video Editor Module
====================
Provides video editing functionality including:
- Video browsing with thumbnails
- Background music selection
- Video-music merging
"""

from .video_editor_panel import VideoEditorPanel
from .video_manager import VideoManager
from .music_manager import MusicManager
from .video_merger import VideoMerger
from .video_player_widget import VideoPlayerWidget

__all__ = ['VideoEditorPanel', 'VideoManager', 'MusicManager', 'VideoMerger', 'VideoPlayerWidget']
