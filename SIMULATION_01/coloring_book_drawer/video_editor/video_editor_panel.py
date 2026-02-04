"""
Video Editor Panel Module
==========================
Main video editing window with video browsing, music selection, and merge capabilities.

Layout:
- Window divided vertically into 2 sections
- Right side: Video player/preview
- Left side: 
  - Top half: Tabbed video thumbnails (Videos / Processed)
  - Bottom half: Music list with play controls and seek slider
"""

import os
from pathlib import Path
from typing import Optional, List

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QSlider, QFrame, QScrollArea, QSplitter,
    QListWidget, QListWidgetItem, QMessageBox, QProgressDialog,
    QSizePolicy, QGroupBox, QApplication, QTabWidget
)
from PySide6.QtCore import Qt, QSize, Signal, QTimer, QThread, QObject
from PySide6.QtGui import QPixmap, QIcon, QFont, QColor

from .video_manager import VideoManager, VideoInfo
from .music_manager import MusicManager, MusicInfo
from .video_player_widget import VideoPlayerWidget
from .video_merger import VideoMerger, MergeResult


# Get paths
SIMULATION_DIR = Path(__file__).resolve().parent.parent
BASE_DIR = SIMULATION_DIR.parent
VIDEOS_DIR = BASE_DIR / "output" / "videos"
THUMBNAILS_DIR = BASE_DIR / "output" / "thumbnails"
PROCESSED_DIR = BASE_DIR / "output" / "processed"
MUSIC_DIR = SIMULATION_DIR / "assets" / "background_music_library"
ICONS_DIR = SIMULATION_DIR / "assets" / "icons"


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
    
    def __init__(self, merger: VideoMerger, video_path: Path, music_path: Path):
        super().__init__()
        self.merger = merger
        self.video_path = video_path
        self.music_path = music_path
    
    def run(self):
        result = self.merger.merge(
            self.video_path,
            self.music_path,
            fade_audio=True,
            fade_duration=2.0,
            progress_callback=lambda p: self.progress.emit(p)
        )
        self.finished.emit(result)


class VideoThumbnailWidget(QFrame):
    """Widget displaying a video thumbnail with info."""
    
    clicked = Signal(object)  # VideoInfo
    
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
        
        # Thumbnail
        self.thumb_label = QLabel()
        self.thumb_label.setAlignment(Qt.AlignCenter)
        self.thumb_label.setFixedSize(160, 100)
        self.thumb_label.setStyleSheet("background-color: #2d2d2d; border-radius: 4px;")
        
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
        
        layout.addWidget(self.thumb_label)
        
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
    """Widget for a music item in the list with play button."""
    
    play_clicked = Signal(object)  # MusicInfo
    selected = Signal(object)  # MusicInfo
    
    def __init__(self, music_info: MusicInfo, parent=None):
        super().__init__(parent)
        self.music_info = music_info
        self.is_playing = False
        self.is_selected = False
        
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(10)
        
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
        layout.addWidget(self.play_btn)
        
        # Music icon
        music_icon_label = QLabel()
        music_icon_label.setPixmap(load_icon("music").pixmap(16, 16))
        layout.addWidget(music_icon_label)
        
        # Name - darker color for better visibility
        self.name_label = QLabel(self.music_info.display_name)
        self.name_label.setStyleSheet("color: #1a1a1a; font-size: 12px; font-weight: 500;")
        self.name_label.setToolTip(self.music_info.filename)
        layout.addWidget(self.name_label, stretch=1)
        
        # Duration
        duration_str = self._format_duration(self.music_info.duration)
        self.duration_label = QLabel(duration_str)
        self.duration_label.setStyleSheet("color: #505050; font-size: 11px;")
        layout.addWidget(self.duration_label)
        
        self.setCursor(Qt.PointingHandCursor)
        self._update_style()
    
    def _format_duration(self, seconds: float) -> str:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"
    
    def _update_style(self):
        if self.is_selected:
            bg_color = "#b8d4b0"  # Lighter green for selected
            border = "2px solid #8fad88"
        else:
            bg_color = "#d0d0d0"  # Light gray background for visibility
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
        
        # State
        self.selected_video: Optional[VideoInfo] = None
        self.selected_music: Optional[MusicInfo] = None
        self.video_widgets: List[VideoThumbnailWidget] = []
        self.processed_widgets: List[VideoThumbnailWidget] = []
        self.music_widgets: List[MusicListItem] = []
        self.current_playing_music: Optional[MusicInfo] = None
        
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
        """Create the music list section with seek slider."""
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
        
        # Music playback controls with seek slider
        playback_frame = QFrame()
        playback_frame.setStyleSheet("""
            QFrame {
                background-color: #2d2d2d;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        playback_layout = QVBoxLayout(playback_frame)
        playback_layout.setContentsMargins(10, 8, 10, 8)
        playback_layout.setSpacing(8)
        
        # Now playing label
        self.now_playing_label = QLabel("No music playing")
        self.now_playing_label.setStyleSheet("color: #909090; font-size: 11px;")
        self.now_playing_label.setAlignment(Qt.AlignCenter)
        playback_layout.addWidget(self.now_playing_label)
        
        # Seek slider row
        seek_row = QHBoxLayout()
        seek_row.setSpacing(8)
        
        self.music_time_label = QLabel("00:00")
        self.music_time_label.setStyleSheet("color: #b0b0b0; font-size: 11px; min-width: 40px;")
        seek_row.addWidget(self.music_time_label)
        
        self.music_seek_slider = QSlider(Qt.Horizontal)
        self.music_seek_slider.setRange(0, 1000)
        self.music_seek_slider.setValue(0)
        self.music_seek_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                background: #404040;
                height: 4px;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #8fad88;
                width: 12px;
                margin: -4px 0;
                border-radius: 6px;
            }
            QSlider::sub-page:horizontal {
                background: #8fad88;
                border-radius: 2px;
            }
        """)
        self.music_seek_slider.sliderPressed.connect(self._on_music_seek_pressed)
        self.music_seek_slider.sliderReleased.connect(self._on_music_seek_released)
        self.music_seek_slider.sliderMoved.connect(self._on_music_seek_moved)
        seek_row.addWidget(self.music_seek_slider, stretch=1)
        
        self.music_duration_label = QLabel("00:00")
        self.music_duration_label.setStyleSheet("color: #b0b0b0; font-size: 11px; min-width: 40px;")
        seek_row.addWidget(self.music_duration_label)
        
        playback_layout.addLayout(seek_row)
        
        # Control buttons row
        controls_row = QHBoxLayout()
        controls_row.setSpacing(10)
        controls_row.addStretch()
        
        # Stop button
        self.music_stop_btn = QPushButton()
        self.music_stop_btn.setIcon(load_icon("stop"))
        self.music_stop_btn.setIconSize(QSize(16, 16))
        self.music_stop_btn.setFixedSize(32, 32)
        self.music_stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #404040;
                border: none;
                border-radius: 16px;
            }
            QPushButton:hover {
                background-color: #505050;
            }
        """)
        self.music_stop_btn.clicked.connect(self._stop_music)
        controls_row.addWidget(self.music_stop_btn)
        
        # Volume icon
        vol_label = QLabel()
        vol_label.setPixmap(load_icon("volume").pixmap(16, 16))
        controls_row.addWidget(vol_label)
        
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(70)
        self.volume_slider.setFixedWidth(80)
        self.volume_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                background: #404040;
                height: 4px;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #8fad88;
                width: 12px;
                margin: -4px 0;
                border-radius: 6px;
            }
        """)
        self.volume_slider.valueChanged.connect(self._on_volume_changed)
        controls_row.addWidget(self.volume_slider)
        
        controls_row.addStretch()
        playback_layout.addLayout(controls_row)
        
        group_layout.addWidget(playback_frame)
        
        # Toolbar
        toolbar = QHBoxLayout()
        
        self.music_count_label = QLabel("0 tracks")
        self.music_count_label.setStyleSheet("color: #909090; font-size: 11px;")
        toolbar.addWidget(self.music_count_label)
        
        toolbar.addStretch()
        
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
        group_layout.addWidget(self.video_player, stretch=1)
        
        # Video info
        self.video_info_label = QLabel("No video selected")
        self.video_info_label.setAlignment(Qt.AlignCenter)
        self.video_info_label.setStyleSheet("color: #909090; font-size: 11px;")
        group_layout.addWidget(self.video_info_label)
        
        parent_layout.addWidget(group)
    
    def _load_content(self):
        """Load videos and music."""
        self._load_videos()
        self._load_processed()
        self._load_music()
    
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
        
        # Set initial volume
        self.music_manager.set_volume(self.volume_slider.value() / 100.0)
        
        # Add to list
        for music_info in music_list:
            widget = MusicListItem(music_info)
            widget.play_clicked.connect(self._on_music_play)
            widget.selected.connect(self._on_music_selected)
            
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
    
    def _on_music_selected(self, music_info: MusicInfo):
        """Handle music selection."""
        self.selected_music = music_info
        
        # Update widget styles
        for widget in self.music_widgets:
            widget.set_selected(widget.music_info == music_info)
        
        # Update merge button
        self._update_merge_button()
    
    def _on_music_play(self, music_info: MusicInfo):
        """Handle music play button click."""
        current = self.music_manager.get_current_playing()
        
        # If same music is playing, toggle
        if current == music_info.path and self.music_manager.is_playing():
            self.music_manager.stop()
            self.music_timer.stop()
            for widget in self.music_widgets:
                widget.set_playing(False)
            self.now_playing_label.setText("No music playing")
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
                self.now_playing_label.setText(f"Playing: {music_info.display_name}")
                self.music_duration_label.setText(self._format_time(music_info.duration))
                self.music_timer.start(100)  # Update every 100ms
        
        # Also select the music
        self._on_music_selected(music_info)
    
    def _stop_music(self):
        """Stop music playback."""
        self.music_manager.stop()
        self.music_timer.stop()
        for widget in self.music_widgets:
            widget.set_playing(False)
        self.now_playing_label.setText("No music playing")
        self.music_seek_slider.setValue(0)
        self.music_time_label.setText("00:00")
        self.current_playing_music = None
    
    def _on_volume_changed(self, value: int):
        """Handle volume slider change."""
        self.music_manager.set_volume(value / 100.0)
    
    def _update_music_progress(self):
        """Update the music seek slider position."""
        if not self.music_manager.is_playing() or not self.current_playing_music:
            return
        
        # Note: pygame mixer doesn't provide position info easily
        # This is a simplified implementation
        pass
    
    def _on_music_seek_pressed(self):
        """Handle seek slider press."""
        pass
    
    def _on_music_seek_released(self):
        """Handle seek slider release."""
        pass
    
    def _on_music_seek_moved(self, value: int):
        """Handle seek slider movement."""
        if self.current_playing_music:
            position = (value / 1000) * self.current_playing_music.duration
            self.music_time_label.setText(self._format_time(position))
    
    def _format_time(self, seconds: float) -> str:
        """Format seconds as MM:SS."""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"
    
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
        
        # Confirm
        reply = QMessageBox.question(
            self,
            "Merge Video",
            f"Merge video:\n{self.selected_video.filename}\n\n"
            f"With music:\n{self.selected_music.display_name}\n\n"
            f"The music will be trimmed from the end to match the video length.\n"
            f"Audio will fade in/out at start and end.\n\n"
            f"Continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # Show progress
        self.merge_btn.setEnabled(False)
        self.merge_btn.setText("  Merging...")
        
        # Create worker and thread
        self.merge_thread = QThread()
        self.merge_worker = MergeWorker(
            self.video_merger,
            self.selected_video.path,
            self.selected_music.path
        )
        self.merge_worker.moveToThread(self.merge_thread)
        
        # Connect signals
        self.merge_thread.started.connect(self.merge_worker.run)
        self.merge_worker.finished.connect(self._on_merge_complete)
        self.merge_worker.finished.connect(self.merge_thread.quit)
        self.merge_worker.finished.connect(self.merge_worker.deleteLater)
        self.merge_thread.finished.connect(self.merge_thread.deleteLater)
        
        # Start
        self.merge_thread.start()
    
    def _on_merge_complete(self, result: MergeResult):
        """Handle merge completion."""
        self.merge_btn.setEnabled(True)
        self.merge_btn.setText("  Merge Video with Music")
        self.merge_btn.setIcon(load_icon("merge"))
        
        if result.success:
            QMessageBox.information(
                self,
                "Merge Complete",
                f"Video merged successfully!\n\n"
                f"Saved to:\n{result.output_path}\n\n"
                f"Processing time: {result.duration:.1f}s"
            )
            # Refresh processed tab
            self._refresh_processed()
            # Switch to processed tab
            self.video_tabs.setCurrentIndex(1)
        else:
            QMessageBox.critical(
                self,
                "Merge Failed",
                f"Failed to merge video:\n\n{result.error_message}"
            )
    
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
