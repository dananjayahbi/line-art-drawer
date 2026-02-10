"""
Video Editor Panel Module
==========================
Main video editing window with video browsing, music selection, logo overlay,
and merge capabilities.

Layout:
- Window divided vertically into 2 sections
- Right side: Video player/preview with draggable logo overlay
- Left side: 
  - Top half: Tabbed video thumbnails (Videos / Processed)
  - Bottom half: Music list and logo controls
"""

import os
from pathlib import Path
from typing import Optional, List

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QSlider, QFrame, QScrollArea, QSplitter,
    QListWidget, QListWidgetItem, QMessageBox, QProgressDialog,
    QSizePolicy, QGroupBox, QApplication, QTabWidget, QComboBox,
    QFileDialog, QCheckBox
)
from PySide6.QtCore import Qt, QSize, Signal, QTimer, QThread, QObject, QPoint
from PySide6.QtGui import QPixmap, QIcon, QFont, QColor

from .video_manager import VideoManager, VideoInfo
from .music_manager import MusicManager, MusicInfo
from .video_player_widget import VideoPlayerWidget
from .video_merger import VideoMerger, MergeResult
from .logo_manager import LogoManager, LogoInfo

# Import VideoProgressDialog from parent package
import sys
_parent_dir = str(Path(__file__).resolve().parent.parent)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)
from custom_widgets import VideoProgressDialog


# Get paths
SIMULATION_DIR = Path(__file__).resolve().parent.parent
BASE_DIR = SIMULATION_DIR.parent
VIDEOS_DIR = BASE_DIR / "output" / "videos"
THUMBNAILS_DIR = BASE_DIR / "output" / "thumbnails"
PROCESSED_DIR = BASE_DIR / "output" / "processed"
MUSIC_DIR = SIMULATION_DIR / "assets" / "background_music_library"
ICONS_DIR = SIMULATION_DIR / "assets" / "icons"
LOGOS_DIR = SIMULATION_DIR / "assets" / "logos"


def load_icon(name: str) -> QIcon:
    """Load an icon from the icons folder."""
    icon_path = ICONS_DIR / f"{name}.svg"
    if icon_path.exists():
        return QIcon(str(icon_path))
    return QIcon()


class MergeWorker(QObject):
    """Worker for running merge operation in a separate thread."""
    finished = Signal(object)  # MergeResult
    progress = Signal(float)
    
    def __init__(
        self, 
        merger: VideoMerger, 
        video_path: Path, 
        music_path: Path,
        logo_path: Optional[Path] = None,
        logo_x_percent: int = 50,
        logo_y_percent: int = 90,
        logo_scale: float = 0.15,
        logo_opacity: float = 0.85
    ):
        super().__init__()
        self.merger = merger
        self.video_path = video_path
        self.music_path = music_path
        self.logo_path = logo_path
        self.logo_x_percent = logo_x_percent
        self.logo_y_percent = logo_y_percent
        self.logo_scale = logo_scale
        self.logo_opacity = logo_opacity
    
    def run(self):
        result = self.merger.merge(
            self.video_path,
            self.music_path,
            fade_audio=True,
            fade_duration=2.0,
            logo_path=self.logo_path,
            logo_x_percent=self.logo_x_percent,
            logo_y_percent=self.logo_y_percent,
            logo_scale=self.logo_scale,
            logo_opacity=self.logo_opacity,
            progress_callback=lambda p: self.progress.emit(p)
        )
        self.finished.emit(result)


class VideoThumbnailWidget(QFrame):
    """Widget displaying a video thumbnail with info and delete button."""
    
    clicked = Signal(object)  # VideoInfo
    delete_requested = Signal(object)  # VideoInfo
    
    def __init__(self, video_info: VideoInfo, parent=None):
        super().__init__(parent)
        self.video_info = video_info
        self.selected = False
        
        self._setup_ui()
        self._update_style()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        
        # Thumbnail container with delete button overlay
        thumb_container = QWidget()
        thumb_container.setFixedSize(160, 100)
        
        # Thumbnail
        self.thumb_label = QLabel(thumb_container)
        self.thumb_label.setAlignment(Qt.AlignCenter)
        self.thumb_label.setFixedSize(160, 100)
        self.thumb_label.setStyleSheet("background-color: #2d2d2d; border-radius: 4px;")
        self.thumb_label.move(0, 0)
        
        if self.video_info.thumbnail_path and self.video_info.thumbnail_path.exists():
            pixmap = QPixmap(str(self.video_info.thumbnail_path))
            scaled = pixmap.scaled(160, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.thumb_label.setPixmap(scaled)
        else:
            # Use movie icon
            self.thumb_label.setPixmap(load_icon("movie").pixmap(48, 48))
            self.thumb_label.setStyleSheet("""
                background-color: #2d2d2d; 
                border-radius: 4px;
            """)
        
        # Delete button (top-right corner) with icon
        self.delete_btn = QPushButton(thumb_container)
        self.delete_btn.setFixedSize(22, 22)
        self.delete_btn.setIcon(load_icon("delete"))
        self.delete_btn.setIconSize(QSize(14, 14))
        self.delete_btn.move(134, 4)
        self.delete_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(200, 50, 50, 0.85);
                border: none;
                border-radius: 11px;
            }
            QPushButton:hover {
                background-color: rgba(220, 60, 60, 1.0);
            }
        """)
        self.delete_btn.setToolTip("Delete video")
        self.delete_btn.clicked.connect(self._on_delete_clicked)
        self.delete_btn.setCursor(Qt.PointingHandCursor)
        
        layout.addWidget(thumb_container)
        
        # Filename (truncated)
        name = self.video_info.filename
        if len(name) > 20:
            name = name[:17] + "..."
        self.name_label = QLabel(name)
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setStyleSheet("color: #e0e0e0; font-size: 11px;")
        self.name_label.setToolTip(self.video_info.filename)
        layout.addWidget(self.name_label)
        
        # Duration
        duration_str = self._format_duration(self.video_info.duration)
        self.duration_label = QLabel(duration_str)
        self.duration_label.setAlignment(Qt.AlignCenter)
        self.duration_label.setStyleSheet("color: #909090; font-size: 10px;")
        layout.addWidget(self.duration_label)
        
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(180, 150)
    
    def _on_delete_clicked(self):
        """Handle delete button click."""
        self.delete_requested.emit(self.video_info)
    
    def _format_duration(self, seconds: float) -> str:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"
    
    def _update_style(self):
        if self.selected:
            self.setStyleSheet("""
                VideoThumbnailWidget {
                    background-color: #3d5a3d;
                    border: 2px solid #8fad88;
                    border-radius: 8px;
                }
            """)
        else:
            self.setStyleSheet("""
                VideoThumbnailWidget {
                    background-color: #2a2a2a;
                    border: 1px solid #404040;
                    border-radius: 8px;
                }
                VideoThumbnailWidget:hover {
                    background-color: #353535;
                    border: 1px solid #505050;
                }
            """)
    
    def set_selected(self, selected: bool):
        self.selected = selected
        self._update_style()
    
    def mousePressEvent(self, event):
        self.clicked.emit(self.video_info)
        super().mousePressEvent(event)


class MusicListItem(QWidget):
    """Widget for a music item in the list with inline play controls and seek bar."""
    
    play_clicked = Signal(object)  # MusicInfo
    selected = Signal(object)  # MusicInfo
    delete_clicked = Signal(object)  # MusicInfo
    seek_requested = Signal(float)  # position in seconds
    
    def __init__(self, music_info: MusicInfo, parent=None):
        super().__init__(parent)
        self.music_info = music_info
        self.is_playing = False
        self.is_selected = False
        
        self._setup_ui()
    
    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 6, 8, 6)
        main_layout.setSpacing(4)
        
        # Top row: play button, music icon, name, duration, delete button
        top_row = QHBoxLayout()
        top_row.setSpacing(8)
        
        # Play button with icon
        self.play_btn = QPushButton()
        self.play_btn.setFixedSize(32, 32)
        self.play_btn.setIcon(load_icon("play"))
        self.play_btn.setIconSize(QSize(16, 16))
        self.play_btn.setStyleSheet("""
            QPushButton {
                background-color: #404040;
                color: white;
                border: none;
                border-radius: 16px;
            }
            QPushButton:hover {
                background-color: #505050;
            }
        """)
        self.play_btn.clicked.connect(lambda: self.play_clicked.emit(self.music_info))
        top_row.addWidget(self.play_btn)
        
        # Music icon
        music_icon_label = QLabel()
        music_icon_label.setPixmap(load_icon("music").pixmap(16, 16))
        top_row.addWidget(music_icon_label)
        
        # Name - darker color for better visibility
        self.name_label = QLabel(self.music_info.display_name)
        self.name_label.setStyleSheet("color: #1a1a1a; font-size: 12px; font-weight: 500;")
        self.name_label.setToolTip(self.music_info.filename)
        top_row.addWidget(self.name_label, stretch=1)
        
        # Duration
        duration_str = self._format_duration(self.music_info.duration)
        self.duration_label = QLabel(duration_str)
        self.duration_label.setStyleSheet("color: #505050; font-size: 11px;")
        top_row.addWidget(self.duration_label)
        
        # Delete button
        self.delete_btn = QPushButton()
        self.delete_btn.setFixedSize(24, 24)
        self.delete_btn.setIcon(load_icon("delete"))
        self.delete_btn.setIconSize(QSize(14, 14))
        self.delete_btn.setToolTip("Delete this track")
        self.delete_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 12px;
            }
            QPushButton:hover {
                background-color: #c85050;
            }
        """)
        self.delete_btn.clicked.connect(lambda: self.delete_clicked.emit(self.music_info))
        top_row.addWidget(self.delete_btn)
        
        main_layout.addLayout(top_row)
        
        # Inline seek bar row (hidden by default, shown when playing)
        self.seek_widget = QWidget()
        seek_layout = QHBoxLayout(self.seek_widget)
        seek_layout.setContentsMargins(40, 0, 28, 2)  # Indent to align under name
        seek_layout.setSpacing(6)
        
        self.time_label = QLabel("00:00")
        self.time_label.setStyleSheet("color: #606060; font-size: 10px; min-width: 35px;")
        seek_layout.addWidget(self.time_label)
        
        self.seek_slider = QSlider(Qt.Horizontal)
        self.seek_slider.setRange(0, 1000)
        self.seek_slider.setValue(0)
        self.seek_slider.setFixedHeight(16)
        self.seek_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                background: #b0b0b0;
                height: 3px;
                border-radius: 1px;
            }
            QSlider::handle:horizontal {
                background: #8fad88;
                width: 10px;
                margin: -4px 0;
                border-radius: 5px;
            }
            QSlider::sub-page:horizontal {
                background: #8fad88;
                border-radius: 1px;
            }
        """)
        self.seek_slider.sliderReleased.connect(self._on_seek_released)
        self.seek_slider.sliderMoved.connect(self._on_seek_moved)
        seek_layout.addWidget(self.seek_slider, stretch=1)
        
        self.total_label = QLabel(self._format_duration(self.music_info.duration))
        self.total_label.setStyleSheet("color: #606060; font-size: 10px; min-width: 35px;")
        seek_layout.addWidget(self.total_label)
        
        self.seek_widget.setVisible(False)
        main_layout.addWidget(self.seek_widget)
        
        self.setCursor(Qt.PointingHandCursor)
        self._update_style()
    
    def _format_duration(self, seconds: float) -> str:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"
    
    def _on_seek_released(self):
        """Handle seek slider release — request seek."""
        if self.music_info and self.music_info.duration > 0:
            position = (self.seek_slider.value() / 1000) * self.music_info.duration
            self.seek_requested.emit(position)
    
    def _on_seek_moved(self, value: int):
        """Update time label as user drags."""
        if self.music_info and self.music_info.duration > 0:
            position = (value / 1000) * self.music_info.duration
            self.time_label.setText(self._format_duration(position))
    
    def update_seek_position(self, position_seconds: float):
        """Update the seek bar and time label from outside (timer-driven)."""
        if not self.seek_slider.isSliderDown() and self.music_info.duration > 0:
            slider_value = int((position_seconds / self.music_info.duration) * 1000)
            self.seek_slider.setValue(min(slider_value, 1000))
            self.time_label.setText(self._format_duration(position_seconds))
    
    def reset_seek(self):
        """Reset seek bar to beginning."""
        self.seek_slider.setValue(0)
        self.time_label.setText("00:00")
    
    def _update_style(self):
        if self.is_selected:
            bg_color = "#b8d4b0"
            border = "2px solid #8fad88"
        else:
            bg_color = "#d0d0d0"
            border = "1px solid #a0a0a0"
        
        self.setStyleSheet(f"""
            MusicListItem {{
                background-color: {bg_color};
                border: {border};
                border-radius: 6px;
            }}
        """)
    
    def set_selected(self, selected: bool):
        self.is_selected = selected
        self._update_style()
    
    def set_playing(self, playing: bool):
        self.is_playing = playing
        self.seek_widget.setVisible(playing)
        if playing:
            self.play_btn.setIcon(load_icon("pause"))
            self.play_btn.setStyleSheet("""
                QPushButton {
                    background-color: #8fad88;
                    color: white;
                    border: none;
                    border-radius: 16px;
                }
                QPushButton:hover {
                    background-color: #7a9773;
                }
            """)
        else:
            self.play_btn.setIcon(load_icon("play"))
            self.play_btn.setStyleSheet("""
                QPushButton {
                    background-color: #404040;
                    color: white;
                    border: none;
                    border-radius: 16px;
                }
                QPushButton:hover {
                    background-color: #505050;
                }
            """)
            self.reset_seek()
    
    def mousePressEvent(self, event):
        self.selected.emit(self.music_info)
        super().mousePressEvent(event)


class VideoEditorPanel(QMainWindow):
    """Main video editor window."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Initialize managers
        self.video_manager = VideoManager(VIDEOS_DIR, THUMBNAILS_DIR)
        self.processed_video_manager = VideoManager(PROCESSED_DIR, THUMBNAILS_DIR)
        self.music_manager = MusicManager(MUSIC_DIR)
        self.video_merger = VideoMerger(PROCESSED_DIR)
        self.logo_manager = LogoManager()
        
        # State
        self.selected_video: Optional[VideoInfo] = None
        self.selected_music: Optional[MusicInfo] = None
        self.selected_logo: Optional[LogoInfo] = None
        self.video_widgets: List[VideoThumbnailWidget] = []
        self.processed_widgets: List[VideoThumbnailWidget] = []
        self.music_widgets: List[MusicListItem] = []
        self.current_playing_music: Optional[MusicInfo] = None
        self.logo_enabled = False  # Whether to include logo in merge
        
        # Merge thread
        self.merge_thread: Optional[QThread] = None
        
        # Music playback timer for seek slider
        self.music_timer = QTimer()
        self.music_timer.timeout.connect(self._update_music_progress)
        
        self._setup_window()
        self._setup_ui()
        self._load_content()
    
    def _setup_window(self):
        """Configure window properties."""
        self.setWindowTitle("Video Editor - Add Background Music")
        self.setMinimumSize(1024, 600)
        self.resize(1366, 768)
        
        # Dark theme
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
            }
            QWidget {
                color: #e0e0e0;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: #2d2d2d;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #505050;
                border-radius: 6px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #606060;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QTabWidget::pane {
                border: 1px solid #404040;
                border-radius: 6px;
                background-color: #252525;
            }
            QTabBar::tab {
                background-color: #2d2d2d;
                color: #a0a0a0;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }
            QTabBar::tab:selected {
                background-color: #3d3d3d;
                color: #e0e0e0;
            }
            QTabBar::tab:hover {
                background-color: #353535;
            }
        """)
    
    def _setup_ui(self):
        """Setup the main UI layout."""
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)
        
        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Horizontal)
        
        # LEFT SIDE - Video thumbnails and music list
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(15)
        
        # Videos section with tabs
        self._create_videos_section(left_layout)
        
        # Music section
        self._create_music_section(left_layout)
        
        # Logo section
        self._create_logo_section(left_layout)
        
        # Merge button
        self._create_merge_section(left_layout)
        
        splitter.addWidget(left_widget)
        
        # RIGHT SIDE - Video player
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        self._create_player_section(right_layout)
        
        splitter.addWidget(right_widget)
        
        # Set splitter proportions (40% left, 60% right)
        splitter.setSizes([500, 750])
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 6)
        
        main_layout.addWidget(splitter)
    
    def _create_videos_section(self, parent_layout):
        """Create the videos thumbnail section with tabs."""
        group = QGroupBox("Videos")
        group.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                border: 1px solid #404040;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        group_layout = QVBoxLayout(group)
        group_layout.setContentsMargins(10, 15, 10, 10)
        
        # Tab widget for Videos / Processed
        self.video_tabs = QTabWidget()
        
        # Tab 1: Original Videos
        videos_tab = QWidget()
        videos_tab_layout = QVBoxLayout(videos_tab)
        videos_tab_layout.setContentsMargins(5, 5, 5, 5)
        
        # Toolbar for videos
        toolbar1 = QHBoxLayout()
        self.video_count_label = QLabel("0 videos")
        self.video_count_label.setStyleSheet("color: #909090; font-size: 11px;")
        toolbar1.addWidget(self.video_count_label)
        toolbar1.addStretch()
        
        refresh_btn1 = QPushButton()
        refresh_btn1.setIcon(load_icon("refresh"))
        refresh_btn1.setIconSize(QSize(16, 16))
        refresh_btn1.setFixedSize(28, 28)
        refresh_btn1.setStyleSheet("""
            QPushButton {
                background-color: #404040;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #505050;
            }
        """)
        refresh_btn1.setToolTip("Refresh videos")
        refresh_btn1.clicked.connect(self._refresh_videos)
        toolbar1.addWidget(refresh_btn1)
        videos_tab_layout.addLayout(toolbar1)
        
        # Scroll area for video thumbnails
        scroll1 = QScrollArea()
        scroll1.setWidgetResizable(True)
        scroll1.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.videos_container = QWidget()
        self.videos_layout = QGridLayout(self.videos_container)
        self.videos_layout.setSpacing(10)
        self.videos_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        
        scroll1.setWidget(self.videos_container)
        videos_tab_layout.addWidget(scroll1, stretch=1)
        
        self.video_tabs.addTab(videos_tab, "Original")
        
        # Tab 2: Processed Videos
        processed_tab = QWidget()
        processed_tab_layout = QVBoxLayout(processed_tab)
        processed_tab_layout.setContentsMargins(5, 5, 5, 5)
        
        # Toolbar for processed
        toolbar2 = QHBoxLayout()
        self.processed_count_label = QLabel("0 videos")
        self.processed_count_label.setStyleSheet("color: #909090; font-size: 11px;")
        toolbar2.addWidget(self.processed_count_label)
        toolbar2.addStretch()
        
        refresh_btn2 = QPushButton()
        refresh_btn2.setIcon(load_icon("refresh"))
        refresh_btn2.setIconSize(QSize(16, 16))
        refresh_btn2.setFixedSize(28, 28)
        refresh_btn2.setStyleSheet("""
            QPushButton {
                background-color: #404040;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #505050;
            }
        """)
        refresh_btn2.setToolTip("Refresh processed videos")
        refresh_btn2.clicked.connect(self._refresh_processed)
        toolbar2.addWidget(refresh_btn2)
        processed_tab_layout.addLayout(toolbar2)
        
        # Scroll area for processed thumbnails
        scroll2 = QScrollArea()
        scroll2.setWidgetResizable(True)
        scroll2.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.processed_container = QWidget()
        self.processed_layout = QGridLayout(self.processed_container)
        self.processed_layout.setSpacing(10)
        self.processed_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        
        scroll2.setWidget(self.processed_container)
        processed_tab_layout.addWidget(scroll2, stretch=1)
        
        self.video_tabs.addTab(processed_tab, "Processed")
        
        group_layout.addWidget(self.video_tabs)
        parent_layout.addWidget(group, stretch=1)
    
    def _create_music_section(self, parent_layout):
        """Create the music list section with inline seek bar per track."""
        group = QGroupBox("Background Music")
        group.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                border: 1px solid #404040;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        group_layout = QVBoxLayout(group)
        group_layout.setContentsMargins(10, 15, 10, 10)
        
        # Toolbar with track count, upload, and stop buttons
        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)
        
        self.music_count_label = QLabel("0 tracks")
        self.music_count_label.setStyleSheet("color: #909090; font-size: 11px;")
        toolbar.addWidget(self.music_count_label)
        
        toolbar.addStretch()
        
        # Upload music button
        upload_music_btn = QPushButton()
        upload_music_btn.setIcon(load_icon("upload"))
        upload_music_btn.setIconSize(QSize(16, 16))
        upload_music_btn.setFixedSize(28, 28)
        upload_music_btn.setToolTip("Upload music files")
        upload_music_btn.setStyleSheet("""
            QPushButton {
                background-color: #404040;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #505050;
            }
        """)
        upload_music_btn.clicked.connect(self._upload_music)
        toolbar.addWidget(upload_music_btn)
        
        # Stop button
        self.music_stop_btn = QPushButton()
        self.music_stop_btn.setIcon(load_icon("stop"))
        self.music_stop_btn.setIconSize(QSize(16, 16))
        self.music_stop_btn.setFixedSize(28, 28)
        self.music_stop_btn.setToolTip("Stop playback")
        self.music_stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #404040;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #505050;
            }
        """)
        self.music_stop_btn.clicked.connect(self._stop_music)
        toolbar.addWidget(self.music_stop_btn)
        
        group_layout.addLayout(toolbar)
        
        # Scroll area for music list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.music_container = QWidget()
        self.music_layout = QVBoxLayout(self.music_container)
        self.music_layout.setSpacing(6)
        self.music_layout.setAlignment(Qt.AlignTop)
        
        scroll.setWidget(self.music_container)
        group_layout.addWidget(scroll, stretch=1)
        
        parent_layout.addWidget(group, stretch=1)
    
    def _create_logo_section(self, parent_layout):
        """Create the logo overlay section with dropdown and controls."""
        group = QGroupBox("Logo Overlay")
        group.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                border: 1px solid #404040;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        group_layout = QVBoxLayout(group)
        group_layout.setContentsMargins(10, 15, 10, 10)
        group_layout.setSpacing(8)
        
        # Logo dropdown with preview
        dropdown_row = QHBoxLayout()
        dropdown_row.setSpacing(8)
        
        # Logo preview
        self.logo_preview_label = QLabel()
        self.logo_preview_label.setFixedSize(48, 48)
        self.logo_preview_label.setAlignment(Qt.AlignCenter)
        self.logo_preview_label.setStyleSheet("""
            QLabel {
                background-color: #2d2d2d;
                border: 1px solid #404040;
                border-radius: 4px;
            }
        """)
        dropdown_row.addWidget(self.logo_preview_label)
        
        # Logo dropdown
        self.logo_combo = QComboBox()
        self.logo_combo.setStyleSheet("""
            QComboBox {
                background-color: #2d2d2d;
                border: 1px solid #505050;
                border-radius: 4px;
                padding: 6px 10px;
                min-width: 150px;
                color: #e0e0e0;
            }
            QComboBox:hover {
                border-color: #8fad88;
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 10px;
            }
            QComboBox::down-arrow {
                image: none;
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #2d2d2d;
                color: #e0e0e0;
                selection-background-color: #8fad88;
            }
        """)
        self.logo_combo.addItem("No Logo", None)
        self.logo_combo.currentIndexChanged.connect(self._on_logo_selected)
        dropdown_row.addWidget(self.logo_combo, stretch=1)
        
        # Upload button
        upload_btn = QPushButton("Upload")
        upload_btn.setFixedWidth(70)
        upload_btn.setStyleSheet("""
            QPushButton {
                background-color: #404040;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 10px;
            }
            QPushButton:hover {
                background-color: #505050;
            }
        """)
        upload_btn.clicked.connect(self._upload_logo)
        dropdown_row.addWidget(upload_btn)
        
        group_layout.addLayout(dropdown_row)
        
        # Controls row
        controls_row = QHBoxLayout()
        controls_row.setSpacing(8)
        
        # Enable checkbox
        self.logo_enable_checkbox = QCheckBox("Enable")
        self.logo_enable_checkbox.setStyleSheet("color: #b0b0b0;")
        self.logo_enable_checkbox.stateChanged.connect(self._on_logo_enable_changed)
        controls_row.addWidget(self.logo_enable_checkbox)
        
        controls_row.addStretch()
        
        # Set as default button
        self.set_default_btn = QPushButton("Set Default")
        self.set_default_btn.setEnabled(False)
        self.set_default_btn.setStyleSheet("""
            QPushButton {
                background-color: #404040;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 10px;
            }
            QPushButton:hover {
                background-color: #505050;
            }
            QPushButton:disabled {
                background-color: #303030;
                color: #606060;
            }
        """)
        self.set_default_btn.clicked.connect(self._set_logo_as_default)
        controls_row.addWidget(self.set_default_btn)
        
        # Show on preview button
        self.show_logo_btn = QPushButton("Show on Preview")
        self.show_logo_btn.setEnabled(False)
        self.show_logo_btn.setStyleSheet("""
            QPushButton {
                background-color: #8fad88;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 10px;
            }
            QPushButton:hover {
                background-color: #7a9773;
            }
            QPushButton:disabled {
                background-color: #404040;
                color: #707070;
            }
        """)
        self.show_logo_btn.clicked.connect(self._show_logo_on_preview)
        controls_row.addWidget(self.show_logo_btn)
        
        group_layout.addLayout(controls_row)
        
        # Scale slider row
        scale_row = QHBoxLayout()
        scale_row.setSpacing(8)
        
        scale_label = QLabel("Size:")
        scale_label.setStyleSheet("color: #b0b0b0;")
        scale_label.setFixedWidth(35)
        scale_row.addWidget(scale_label)
        
        self.logo_scale_slider = QSlider(Qt.Horizontal)
        self.logo_scale_slider.setMinimum(5)
        self.logo_scale_slider.setMaximum(50)
        self.logo_scale_slider.setValue(15)  # Default 15% scale
        self.logo_scale_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                background: #404040;
                height: 6px;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #8fad88;
                width: 16px;
                height: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }
            QSlider::handle:horizontal:hover {
                background: #a0c098;
            }
            QSlider::sub-page:horizontal {
                background: #8fad88;
                border-radius: 3px;
            }
        """)
        self.logo_scale_slider.valueChanged.connect(self._on_logo_scale_slider_changed)
        scale_row.addWidget(self.logo_scale_slider, stretch=1)
        
        self.logo_scale_value_label = QLabel("15%")
        self.logo_scale_value_label.setStyleSheet("color: #b0b0b0;")
        self.logo_scale_value_label.setFixedWidth(35)
        scale_row.addWidget(self.logo_scale_value_label)
        
        group_layout.addLayout(scale_row)
        
        # Position info
        self.logo_position_label = QLabel("Position: Drag logo on preview to adjust")
        self.logo_position_label.setStyleSheet("color: #707070; font-size: 10px;")
        group_layout.addWidget(self.logo_position_label)
        
        parent_layout.addWidget(group)
    
    def _create_merge_section(self, parent_layout):
        """Create the merge button section."""
        merge_frame = QFrame()
        merge_frame.setStyleSheet("""
            QFrame {
                background-color: #2a2a2a;
                border: 1px solid #404040;
                border-radius: 8px;
            }
        """)
        
        merge_layout = QVBoxLayout(merge_frame)
        merge_layout.setContentsMargins(15, 12, 15, 12)
        
        # Selection info
        self.selection_label = QLabel("Select a video and music track")
        self.selection_label.setAlignment(Qt.AlignCenter)
        self.selection_label.setStyleSheet("color: #909090; font-size: 12px;")
        merge_layout.addWidget(self.selection_label)
        
        # Merge button
        self.merge_btn = QPushButton("  Merge Video with Music")
        self.merge_btn.setIcon(load_icon("merge"))
        self.merge_btn.setIconSize(QSize(20, 20))
        self.merge_btn.setEnabled(False)
        self.merge_btn.setStyleSheet("""
            QPushButton {
                background-color: #8fad88;
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 12px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #7a9773;
            }
            QPushButton:disabled {
                background-color: #404040;
                color: #707070;
            }
        """)
        self.merge_btn.clicked.connect(self._do_merge)
        merge_layout.addWidget(self.merge_btn)
        
        parent_layout.addWidget(merge_frame)
    
    def _create_player_section(self, parent_layout):
        """Create the video player section."""
        group = QGroupBox("Preview")
        group.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                border: 1px solid #404040;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        group_layout = QVBoxLayout(group)
        group_layout.setContentsMargins(10, 15, 10, 10)
        
        # Video player
        self.video_player = VideoPlayerWidget()
        self.video_player.logo_position_changed.connect(self._on_logo_position_changed)
        self.video_player.logo_scale_changed.connect(self._on_logo_scale_changed)
        group_layout.addWidget(self.video_player, stretch=1)
        
        # Video info
        self.video_info_label = QLabel("No video selected")
        self.video_info_label.setAlignment(Qt.AlignCenter)
        self.video_info_label.setStyleSheet("color: #909090; font-size: 11px;")
        group_layout.addWidget(self.video_info_label)
        
        parent_layout.addWidget(group)
    
    def _load_content(self):
        """Load videos, music, and logos."""
        self._load_videos()
        self._load_processed()
        self._load_music()
        self._load_logos()
    
    def _load_videos(self):
        """Load and display videos from the videos directory."""
        # Clear existing
        for widget in self.video_widgets:
            widget.deleteLater()
        self.video_widgets.clear()
        
        # Clear layout
        while self.videos_layout.count():
            item = self.videos_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Load videos
        videos = self.video_manager.list_videos(generate_thumbnails=True)
        self.video_count_label.setText(f"{len(videos)} videos")
        
        # Add to grid (3 columns)
        cols = 3
        for i, video_info in enumerate(videos):
            widget = VideoThumbnailWidget(video_info)
            widget.clicked.connect(self._on_video_selected)
            widget.delete_requested.connect(self._on_video_delete_requested)
            
            row = i // cols
            col = i % cols
            self.videos_layout.addWidget(widget, row, col)
            self.video_widgets.append(widget)
    
    def _load_processed(self):
        """Load and display videos from the processed directory."""
        # Clear existing
        for widget in self.processed_widgets:
            widget.deleteLater()
        self.processed_widgets.clear()
        
        # Clear layout
        while self.processed_layout.count():
            item = self.processed_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Load processed videos
        videos = self.processed_video_manager.list_videos(generate_thumbnails=True)
        self.processed_count_label.setText(f"{len(videos)} videos")
        
        # Add to grid (3 columns)
        cols = 3
        for i, video_info in enumerate(videos):
            widget = VideoThumbnailWidget(video_info)
            widget.clicked.connect(self._on_video_selected)
            widget.delete_requested.connect(self._on_processed_video_delete_requested)
            
            row = i // cols
            col = i % cols
            self.processed_layout.addWidget(widget, row, col)
            self.processed_widgets.append(widget)
    
    def _load_music(self):
        """Load and display music."""
        # Clear existing
        for widget in self.music_widgets:
            widget.deleteLater()
        self.music_widgets.clear()
        
        # Clear layout
        while self.music_layout.count():
            item = self.music_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Load music
        music_list = self.music_manager.list_music()
        self.music_count_label.setText(f"{len(music_list)} tracks")
        
        # Set volume to max (user preference)
        self.music_manager.set_volume(1.0)
        
        # Add to list
        for music_info in music_list:
            widget = MusicListItem(music_info)
            widget.play_clicked.connect(self._on_music_play)
            widget.selected.connect(self._on_music_selected)
            widget.delete_clicked.connect(self._on_music_delete)
            widget.seek_requested.connect(self._on_music_seek_to)
            
            self.music_layout.addWidget(widget)
            self.music_widgets.append(widget)
    
    def _on_video_selected(self, video_info: VideoInfo):
        """Handle video selection."""
        # Update selection
        self.selected_video = video_info
        
        # Update widget styles in both tabs
        for widget in self.video_widgets:
            widget.set_selected(widget.video_info == video_info)
        for widget in self.processed_widgets:
            widget.set_selected(widget.video_info == video_info)
        
        # Load video in player
        self.video_player.load_video(video_info.path)
        
        # Update info label
        duration_str = self.video_manager.format_duration(video_info.duration)
        self.video_info_label.setText(
            f"{video_info.filename} | {video_info.width}x{video_info.height} | {duration_str}"
        )
        
        # Update merge button
        self._update_merge_button()
    
    def _on_video_delete_requested(self, video_info: VideoInfo):
        """Handle delete request for an original video."""
        self._delete_video(video_info, is_processed=False)
    
    def _on_processed_video_delete_requested(self, video_info: VideoInfo):
        """Handle delete request for a processed video."""
        self._delete_video(video_info, is_processed=True)
    
    def _delete_video(self, video_info: VideoInfo, is_processed: bool):
        """Delete a video with confirmation."""
        video_type = "processed" if is_processed else "original"
        
        # Confirmation dialog with styled message box
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Delete Video")
        msg_box.setText(
            f"Are you sure you want to delete this {video_type} video?\n\n"
            f"{video_info.filename}\n\n"
            f"This action cannot be undone."
        )
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg_box.setDefaultButton(QMessageBox.No)
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: #f0f0f0;
            }
            QMessageBox QLabel {
                color: #1a1a1a;
                font-size: 12px;
            }
            QPushButton {
                background-color: #c85050;
                color: white;
                padding: 6px 16px;
                border-radius: 4px;
                min-width: 60px;
            }
            QPushButton:hover {
                background-color: #a84040;
            }
        """)
        
        if msg_box.exec() != QMessageBox.Yes:
            return
        
        # If this video is currently loaded, stop playback
        if self.selected_video and self.selected_video.path == video_info.path:
            self.video_player.stop()
            self.selected_video = None
            self.video_info_label.setText("No video selected")
        
        # Delete the video using the appropriate manager
        manager = self.processed_video_manager if is_processed else self.video_manager
        if manager.delete_video(video_info.path):
            # Show success message
            success_msg = QMessageBox(self)
            success_msg.setWindowTitle("Video Deleted")
            success_msg.setText(f"Video deleted successfully:\n\n{video_info.filename}")
            success_msg.setIcon(QMessageBox.Information)
            success_msg.setStyleSheet("""
                QMessageBox {
                    background-color: #f0f0f0;
                }
                QMessageBox QLabel {
                    color: #1a1a1a;
                    font-size: 12px;
                }
                QPushButton {
                    background-color: #8fad88;
                    color: white;
                    padding: 6px 16px;
                    border-radius: 4px;
                    min-width: 60px;
                }
                QPushButton:hover {
                    background-color: #7a9773;
                }
            """)
            success_msg.exec()
            
            # Refresh the appropriate list
            if is_processed:
                self._refresh_processed()
            else:
                self._refresh_videos()
            
            # Update merge button
            self._update_merge_button()
        else:
            # Show error message
            error_msg = QMessageBox(self)
            error_msg.setWindowTitle("Delete Failed")
            error_msg.setText(f"Failed to delete video:\n\n{video_info.filename}")
            error_msg.setIcon(QMessageBox.Critical)
            error_msg.setStyleSheet("""
                QMessageBox {
                    background-color: #f0f0f0;
                }
                QMessageBox QLabel {
                    color: #1a1a1a;
                    font-size: 12px;
                }
                QPushButton {
                    background-color: #c85050;
                    color: white;
                    padding: 6px 16px;
                    border-radius: 4px;
                    min-width: 60px;
                }
            """)
            error_msg.exec()
    
    def _on_music_selected(self, music_info: MusicInfo):
        """Handle music selection."""
        self.selected_music = music_info
        
        # Update widget styles
        for widget in self.music_widgets:
            widget.set_selected(widget.music_info == music_info)
        
        # Update merge button
        self._update_merge_button()
    
    def _on_music_play(self, music_info: MusicInfo):
        """Handle music play button click — inline player per song row."""
        current = self.music_manager.get_current_playing()
        
        # If same music is playing, toggle stop
        if current == music_info.path and self.music_manager.is_playing():
            self.music_manager.stop()
            self.music_timer.stop()
            for widget in self.music_widgets:
                widget.set_playing(False)
            self.current_playing_music = None
        else:
            # Stop current and play new
            self.music_manager.stop()
            self.music_timer.stop()
            for widget in self.music_widgets:
                widget.set_playing(False)
            
            if self.music_manager.play(music_info.path):
                for widget in self.music_widgets:
                    if widget.music_info == music_info:
                        widget.set_playing(True)
                        break
                self.current_playing_music = music_info
                self.music_timer.start(100)  # Update every 100ms
        
        # Also select the music
        self._on_music_selected(music_info)
    
    def _stop_music(self):
        """Stop music playback."""
        self.music_manager.stop()
        self.music_timer.stop()
        for widget in self.music_widgets:
            widget.set_playing(False)
        self.current_playing_music = None
    
    def _update_music_progress(self):
        """Update the inline seek slider on the currently playing track widget."""
        if not self.music_manager.is_playing() or not self.current_playing_music:
            return
        
        # Get current position from pygame
        position = self.music_manager.get_position()
        
        # Update the seek bar on the playing widget
        for widget in self.music_widgets:
            if widget.music_info == self.current_playing_music and widget.is_playing:
                widget.update_seek_position(position)
                break
    
    def _on_music_seek_to(self, position: float):
        """Handle seek request from inline slider."""
        if self.current_playing_music:
            self.music_manager.set_position(position)
    
    def _upload_music(self):
        """Upload music files to the background music library."""
        import shutil
        
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Music Files",
            "",
            "Audio Files (*.mp3 *.wav *.ogg *.m4a *.flac);;All Files (*)"
        )
        
        if not files:
            return
        
        copied = 0
        skipped = 0
        
        for file_path in files:
            src = Path(file_path)
            dest = MUSIC_DIR / src.name
            
            if dest.exists():
                skipped += 1
                continue
            
            try:
                shutil.copy2(str(src), str(dest))
                copied += 1
            except Exception as e:
                print(f"[Music Upload] Failed to copy {src.name}: {e}")
        
        # Show result
        if copied > 0 or skipped > 0:
            parts = []
            if copied > 0:
                parts.append(f"{copied} file(s) uploaded")
            if skipped > 0:
                parts.append(f"{skipped} file(s) already exist")
            
            msg = QMessageBox(self)
            msg.setWindowTitle("Music Upload")
            msg.setText(", ".join(parts) + ".")
            msg.setIcon(QMessageBox.Information)
            msg.setStyleSheet("""
                QMessageBox { background-color: #f0f0f0; }
                QMessageBox QLabel { color: #1a1a1a; font-size: 12px; }
                QPushButton {
                    background-color: #8fad88; color: white;
                    padding: 6px 16px; border-radius: 4px; min-width: 60px;
                }
                QPushButton:hover { background-color: #7a9773; }
            """)
            msg.exec()
            
            # Refresh the music list
            self._load_music()
    
    def _on_music_delete(self, music_info: MusicInfo):
        """Handle delete request for a music track."""
        # Stop if this track is currently playing
        if self.current_playing_music and self.current_playing_music.path == music_info.path:
            self._stop_music()
        
        # Confirm
        msg = QMessageBox(self)
        msg.setWindowTitle("Delete Music")
        msg.setText(
            f"Are you sure you want to delete this track?\n\n"
            f"{music_info.display_name}\n\n"
            f"This action cannot be undone."
        )
        msg.setIcon(QMessageBox.Warning)
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.No)
        msg.setStyleSheet("""
            QMessageBox { background-color: #f0f0f0; }
            QMessageBox QLabel { color: #1a1a1a; font-size: 12px; }
            QPushButton {
                background-color: #c85050; color: white;
                padding: 6px 16px; border-radius: 4px; min-width: 60px;
            }
            QPushButton:hover { background-color: #a84040; }
        """)
        
        if msg.exec() != QMessageBox.Yes:
            return
        
        # Delete the file
        try:
            if music_info.path.exists():
                music_info.path.unlink()
            
            # If this was the selected music, deselect
            if self.selected_music and self.selected_music.path == music_info.path:
                self.selected_music = None
                self._update_merge_button()
            
            # Refresh the music list
            self._load_music()
        except Exception as e:
            error_msg = QMessageBox(self)
            error_msg.setWindowTitle("Delete Failed")
            error_msg.setText(f"Failed to delete track:\n\n{str(e)}")
            error_msg.setIcon(QMessageBox.Critical)
            error_msg.setStyleSheet("""
                QMessageBox { background-color: #f0f0f0; }
                QMessageBox QLabel { color: #1a1a1a; font-size: 12px; }
                QPushButton {
                    background-color: #c85050; color: white;
                    padding: 6px 16px; border-radius: 4px; min-width: 60px;
                }
            """)
            error_msg.exec()
    
    def _format_time(self, seconds: float) -> str:
        """Format seconds as MM:SS."""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"
    
    # ==================== LOGO METHODS ====================
    
    def _load_logos(self):
        """Load logos into the dropdown."""
        self.logo_combo.clear()
        self.logo_combo.addItem("No Logo", None)
        
        logos = self.logo_manager.list_logos()
        default_logo = self.logo_manager.settings.default_logo
        default_index = 0
        
        for i, logo_info in enumerate(logos):
            # Add item with display name
            item_text = logo_info.display_name
            if logo_info.width and logo_info.height:
                item_text += f" ({logo_info.width}x{logo_info.height})"
            
            self.logo_combo.addItem(item_text, logo_info)
            
            # Check if this is the default
            if default_logo and logo_info.filename == default_logo:
                default_index = i + 1  # +1 because of "No Logo" item
        
        # Select default
        if default_index > 0:
            self.logo_combo.setCurrentIndex(default_index)
        
        # Initialize scale slider with saved value
        saved_scale = int(self.logo_manager.settings.scale * 100)
        self.logo_scale_slider.setValue(saved_scale)
        self.logo_scale_value_label.setText(f"{saved_scale}%")
    
    def _on_logo_selected(self, index: int):
        """Handle logo selection from dropdown."""
        logo_info = self.logo_combo.currentData()
        self.selected_logo = logo_info
        
        # Update preview
        if logo_info and logo_info.path.exists():
            pixmap = QPixmap(str(logo_info.path))
            scaled = pixmap.scaled(44, 44, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.logo_preview_label.setPixmap(scaled)
            self.set_default_btn.setEnabled(True)
            self.show_logo_btn.setEnabled(True)
        else:
            self.logo_preview_label.clear()
            self.set_default_btn.setEnabled(False)
            self.show_logo_btn.setEnabled(False)
    
    def _on_logo_enable_changed(self, state: int):
        """Handle logo enable checkbox change."""
        self.logo_enabled = state == Qt.CheckState.Checked.value
        print(f"[Logo] Enable changed: state={state}, logo_enabled={self.logo_enabled}")
    
    def _upload_logo(self):
        """Open file dialog to upload a logo."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Logo Image",
            "",
            "Images (*.png *.jpg *.jpeg *.svg *.webp *.gif);;All Files (*)"
        )
        
        if file_path:
            logo_info = self.logo_manager.add_logo(Path(file_path))
            if logo_info:
                # Reload logos
                self._load_logos()
                
                # Select the new logo
                for i in range(self.logo_combo.count()):
                    item_data = self.logo_combo.itemData(i)
                    if item_data and item_data.filename == logo_info.filename:
                        self.logo_combo.setCurrentIndex(i)
                        break
                
                # Show success message
                msg = QMessageBox(self)
                msg.setWindowTitle("Logo Uploaded")
                msg.setText(f"Logo uploaded successfully:\n\n{logo_info.display_name}")
                msg.setIcon(QMessageBox.Information)
                msg.setStyleSheet("""
                    QMessageBox { background-color: #f0f0f0; }
                    QMessageBox QLabel { color: #1a1a1a; font-size: 12px; }
                    QPushButton {
                        background-color: #8fad88; color: white;
                        padding: 6px 16px; border-radius: 4px;
                    }
                """)
                msg.exec()
    
    def _set_logo_as_default(self):
        """Set the current logo as default."""
        if self.selected_logo:
            self.logo_manager.set_default_logo(self.selected_logo.filename)
            
            msg = QMessageBox(self)
            msg.setWindowTitle("Default Logo Set")
            msg.setText(f"'{self.selected_logo.display_name}' is now the default logo.")
            msg.setIcon(QMessageBox.Information)
            msg.setStyleSheet("""
                QMessageBox { background-color: #f0f0f0; }
                QMessageBox QLabel { color: #1a1a1a; font-size: 12px; }
                QPushButton {
                    background-color: #8fad88; color: white;
                    padding: 6px 16px; border-radius: 4px;
                }
            """)
            msg.exec()
    
    def _show_logo_on_preview(self):
        """Show the logo overlay on the video preview."""
        if not self.selected_logo:
            return
        
        # Enable logo and update video player
        self.logo_enable_checkbox.setChecked(True)
        self.video_player.set_logo_overlay(
            self.selected_logo.path,
            self.logo_manager.settings.position_x,
            self.logo_manager.settings.position_y,
            self.logo_manager.settings.scale,
            self.logo_manager.settings.opacity
        )
    
    def _on_logo_position_changed(self, x_percent: int, y_percent: int):
        """Handle logo position change from video player drag."""
        self.logo_manager.set_position(x_percent, y_percent)
        self.logo_position_label.setText(f"Position: {x_percent}%, {y_percent}%")
    
    def _on_logo_scale_changed(self, scale: float):
        """Handle logo scale change from video player wheel scroll."""
        self.logo_manager.set_scale(scale)
        scale_percent = int(scale * 100)
        # Update slider without triggering signal loop
        self.logo_scale_slider.blockSignals(True)
        self.logo_scale_slider.setValue(scale_percent)
        self.logo_scale_slider.blockSignals(False)
        self.logo_scale_value_label.setText(f"{scale_percent}%")
    
    def _on_logo_scale_slider_changed(self, value: int):
        """Handle logo scale slider change."""
        scale = value / 100.0
        self.logo_manager.set_scale(scale)
        self.logo_scale_value_label.setText(f"{value}%")
        
        # Update video player if logo is visible
        if self.video_player.logo_visible:
            self.video_player.logo_scale = scale
            # Redraw current frame
            if self.video_player.cap is not None and not self.video_player.is_playing:
                self.video_player._show_frame(self.video_player.current_frame)
    
    # ==================== MERGE METHODS ====================
    
    def _update_merge_button(self):
        """Update merge button state based on selection."""
        can_merge = self.selected_video is not None and self.selected_music is not None
        self.merge_btn.setEnabled(can_merge)
        
        if can_merge:
            video_name = self.selected_video.filename[:20]
            music_name = self.selected_music.display_name[:20]
            self.selection_label.setText(f"Video: {video_name}... + Music: {music_name}...")
        elif self.selected_video:
            self.selection_label.setText(f"Video selected. Choose a music track.")
        elif self.selected_music:
            self.selection_label.setText(f"Music selected. Choose a video.")
        else:
            self.selection_label.setText("Select a video and music track")
    
    def _refresh_videos(self):
        """Refresh the video list."""
        self.selected_video = None
        self._load_videos()
        self._update_merge_button()
    
    def _refresh_processed(self):
        """Refresh the processed videos list."""
        self._load_processed()
    
    def _do_merge(self):
        """Perform the video-music merge."""
        if not self.selected_video or not self.selected_music:
            return
        
        # Stop music playback
        self._stop_music()
        
        # Confirm with styled message box
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Merge Video")
        msg_box.setText(
            f"Merge video:\n{self.selected_video.filename}\n\n"
            f"With music:\n{self.selected_music.display_name}\n\n"
            f"The music will be trimmed from the end to match the video length.\n"
            f"Audio will fade in/out at start and end.\n\n"
            f"Continue?"
        )
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg_box.setDefaultButton(QMessageBox.Yes)
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: #f0f0f0;
            }
            QMessageBox QLabel {
                color: #1a1a1a;
                font-size: 12px;
            }
            QPushButton {
                background-color: #8fad88;
                color: white;
                padding: 6px 16px;
                border-radius: 4px;
                min-width: 60px;
            }
            QPushButton:hover {
                background-color: #7a9773;
            }
        """)
        
        if msg_box.exec() != QMessageBox.Yes:
            return
        
        # Show progress dialog
        self.merge_btn.setEnabled(False)
        self.merge_btn.setText("  Merging...")
        
        self.merge_progress_dialog = VideoProgressDialog(
            title="Video Merge", parent=self
        )
        self.merge_progress_dialog.start("Merging video with music...")
        
        # Get logo settings if enabled
        logo_path = None
        logo_x_percent = 50
        logo_y_percent = 90
        logo_scale = 0.15
        logo_opacity = 0.85
        
        print(f"[Merge] Logo enabled: {self.logo_enabled}")
        print(f"[Merge] Selected logo: {self.selected_logo}")
        
        if self.logo_enabled and self.selected_logo:
            logo_path = self.selected_logo.path
            settings = self.logo_manager.get_settings()
            logo_x_percent = settings.position_x
            logo_y_percent = settings.position_y
            logo_scale = settings.scale
            logo_opacity = settings.opacity
            print(f"[Merge] Logo path: {logo_path}")
            print(f"[Merge] Logo settings: x={logo_x_percent}, y={logo_y_percent}, scale={logo_scale}, opacity={logo_opacity}")
        
        # Create worker and thread
        self.merge_thread = QThread()
        self.merge_worker = MergeWorker(
            self.video_merger,
            self.selected_video.path,
            self.selected_music.path,
            logo_path=logo_path,
            logo_x_percent=logo_x_percent,
            logo_y_percent=logo_y_percent,
            logo_scale=logo_scale,
            logo_opacity=logo_opacity
        )
        self.merge_worker.moveToThread(self.merge_thread)
        
        # Connect signals
        self.merge_thread.started.connect(self.merge_worker.run)
        self.merge_worker.finished.connect(self._on_merge_complete)
        self.merge_worker.finished.connect(self.merge_thread.quit)
        self.merge_worker.finished.connect(self.merge_worker.deleteLater)
        self.merge_thread.finished.connect(self.merge_thread.deleteLater)
        
        # Connect progress to dialog
        self.merge_worker.progress.connect(self._on_merge_progress)
        self.merge_progress_dialog.cancelled.connect(self._on_merge_cancel)
        
        # Start
        self.merge_thread.start()
    
    def _on_merge_complete(self, result: MergeResult):
        """Handle merge completion."""
        self.merge_btn.setEnabled(True)
        self.merge_btn.setText("  Merge Video with Music")
        self.merge_btn.setIcon(load_icon("merge"))
        
        # Close progress dialog
        if hasattr(self, 'merge_progress_dialog') and self.merge_progress_dialog:
            if result.success:
                self.merge_progress_dialog.finish_success("Video Merged!")
            else:
                self.merge_progress_dialog.finish_error("Merge Failed")
        
        # Common message box style with black text
        msg_style = """
            QMessageBox {
                background-color: #f0f0f0;
            }
            QMessageBox QLabel {
                color: #1a1a1a;
                font-size: 12px;
            }
            QPushButton {
                background-color: #8fad88;
                color: white;
                padding: 6px 16px;
                border-radius: 4px;
                min-width: 60px;
            }
            QPushButton:hover {
                background-color: #7a9773;
            }
        """
        
        if result.success:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Merge Complete")
            msg_box.setText(
                f"Video merged successfully!\n\n"
                f"Saved to:\n{result.output_path}\n\n"
                f"Processing time: {result.duration:.1f}s"
            )
            msg_box.setIcon(QMessageBox.Information)
            msg_box.setStyleSheet(msg_style)
            msg_box.exec()
            
            # Refresh processed tab
            self._refresh_processed()
            # Switch to processed tab
            self.video_tabs.setCurrentIndex(1)
        else:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Merge Failed")
            msg_box.setText(f"Failed to merge video:\n\n{result.error_message}")
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setStyleSheet(msg_style)
            msg_box.exec()
    
    def _on_merge_progress(self, progress_value: float):
        """Handle merge progress updates from worker (0.0 to 1.0)."""
        if hasattr(self, 'merge_progress_dialog') and self.merge_progress_dialog:
            pct = int(progress_value * 100)
            self.merge_progress_dialog.update_progress(pct)
            if progress_value < 1.0:
                self.merge_progress_dialog.update_status(f"Encoding... {pct}%")
            else:
                self.merge_progress_dialog.update_status("Finalizing...")
    
    def _on_merge_cancel(self):
        """Handle merge cancel request."""
        if hasattr(self, 'merge_worker') and self.merge_worker:
            if hasattr(self.merge_worker, 'merger') and self.merge_worker.merger:
                self.merge_worker.merger.cancel()
    
    def closeEvent(self, event):
        """Clean up on window close."""
        self._stop_music()
        self.video_player.cleanup()
        self.music_manager.cleanup()
        super().closeEvent(event)
    
    def showMaximized(self):
        """Show the window maximized."""
        super().showMaximized()
    
    def show(self):
        """Show the window."""
        super().show()
        # Center on screen if not maximized
        if not self.isMaximized():
            screen = QApplication.primaryScreen().geometry()
            x = (screen.width() - self.width()) // 2
            y = (screen.height() - self.height()) // 2
            self.move(x, y)
