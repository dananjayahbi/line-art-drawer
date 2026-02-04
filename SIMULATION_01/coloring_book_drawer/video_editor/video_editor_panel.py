"""
Video Editor Panel Module
==========================
Main video editing window with video browsing, music selection, and merge capabilities.

Layout:
- Window divided vertically into 2 sections
- Right side: Video player/preview
- Left side: 
  - Top half: Video thumbnails grid
  - Bottom half: Music list with play controls
"""

import os
from pathlib import Path
from typing import Optional, List

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QSlider, QFrame, QScrollArea, QSplitter,
    QListWidget, QListWidgetItem, QMessageBox, QProgressDialog,
    QSizePolicy, QGroupBox, QApplication
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
            self.thumb_label.setText("🎬")
            self.thumb_label.setStyleSheet("""
                background-color: #2d2d2d; 
                border-radius: 4px;
                font-size: 32px;
                color: #606060;
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
        
        # Play button
        self.play_btn = QPushButton("▶")
        self.play_btn.setFixedSize(32, 32)
        self.play_btn.setStyleSheet("""
            QPushButton {
                background-color: #404040;
                color: white;
                border: none;
                border-radius: 16px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #505050;
            }
        """)
        self.play_btn.clicked.connect(lambda: self.play_clicked.emit(self.music_info))
        layout.addWidget(self.play_btn)
        
        # Name
        self.name_label = QLabel(self.music_info.display_name)
        self.name_label.setStyleSheet("color: #e0e0e0; font-size: 12px;")
        self.name_label.setToolTip(self.music_info.filename)
        layout.addWidget(self.name_label, stretch=1)
        
        # Duration
        duration_str = self._format_duration(self.music_info.duration)
        self.duration_label = QLabel(duration_str)
        self.duration_label.setStyleSheet("color: #909090; font-size: 11px;")
        layout.addWidget(self.duration_label)
        
        self.setCursor(Qt.PointingHandCursor)
        self._update_style()
    
    def _format_duration(self, seconds: float) -> str:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"
    
    def _update_style(self):
        if self.is_selected:
            bg_color = "#3d5a3d"
            border = "2px solid #8fad88"
        else:
            bg_color = "#2a2a2a"
            border = "1px solid #404040"
        
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
        self.play_btn.setText("⏸" if playing else "▶")
        if playing:
            self.play_btn.setStyleSheet("""
                QPushButton {
                    background-color: #8fad88;
                    color: white;
                    border: none;
                    border-radius: 16px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #7a9773;
                }
            """)
        else:
            self.play_btn.setStyleSheet("""
                QPushButton {
                    background-color: #404040;
                    color: white;
                    border: none;
                    border-radius: 16px;
                    font-size: 12px;
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
        self.music_manager = MusicManager(MUSIC_DIR)
        self.video_merger = VideoMerger(PROCESSED_DIR)
        
        # State
        self.selected_video: Optional[VideoInfo] = None
        self.selected_music: Optional[MusicInfo] = None
        self.video_widgets: List[VideoThumbnailWidget] = []
        self.music_widgets: List[MusicListItem] = []
        
        # Merge thread
        self.merge_thread: Optional[QThread] = None
        
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
        
        # Videos section
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
        """Create the videos thumbnail section."""
        group = QGroupBox("📹 Videos")
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
        
        # Toolbar
        toolbar = QHBoxLayout()
        
        self.video_count_label = QLabel("0 videos")
        self.video_count_label.setStyleSheet("color: #909090; font-size: 11px;")
        toolbar.addWidget(self.video_count_label)
        
        toolbar.addStretch()
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #404040;
                color: white;
                border: none;
                padding: 5px 12px;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #505050;
            }
        """)
        refresh_btn.clicked.connect(self._refresh_videos)
        toolbar.addWidget(refresh_btn)
        
        group_layout.addLayout(toolbar)
        
        # Scroll area for thumbnails
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.videos_container = QWidget()
        self.videos_layout = QGridLayout(self.videos_container)
        self.videos_layout.setSpacing(10)
        self.videos_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        
        scroll.setWidget(self.videos_container)
        group_layout.addWidget(scroll, stretch=1)
        
        parent_layout.addWidget(group, stretch=1)
    
    def _create_music_section(self, parent_layout):
        """Create the music list section."""
        group = QGroupBox("🎵 Background Music")
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
        
        # Toolbar
        toolbar = QHBoxLayout()
        
        self.music_count_label = QLabel("0 tracks")
        self.music_count_label.setStyleSheet("color: #909090; font-size: 11px;")
        toolbar.addWidget(self.music_count_label)
        
        toolbar.addStretch()
        
        # Volume control
        vol_label = QLabel("🔊")
        toolbar.addWidget(vol_label)
        
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
        toolbar.addWidget(self.volume_slider)
        
        stop_btn = QPushButton("⏹")
        stop_btn.setFixedSize(28, 28)
        stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #404040;
                color: white;
                border: none;
                border-radius: 14px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #505050;
            }
        """)
        stop_btn.clicked.connect(self._stop_music)
        toolbar.addWidget(stop_btn)
        
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
        self.merge_btn = QPushButton("🎬 Merge Video with Music")
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
        group = QGroupBox("🎥 Preview")
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
        self._load_music()
    
    def _load_videos(self):
        """Load and display videos."""
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
        
        # Update widget styles
        for widget in self.video_widgets:
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
            for widget in self.music_widgets:
                widget.set_playing(False)
        else:
            # Stop current and play new
            self.music_manager.stop()
            for widget in self.music_widgets:
                widget.set_playing(False)
            
            if self.music_manager.play(music_info.path):
                for widget in self.music_widgets:
                    if widget.music_info == music_info:
                        widget.set_playing(True)
                        break
        
        # Also select the music
        self._on_music_selected(music_info)
    
    def _stop_music(self):
        """Stop music playback."""
        self.music_manager.stop()
        for widget in self.music_widgets:
            widget.set_playing(False)
    
    def _on_volume_changed(self, value: int):
        """Handle volume slider change."""
        self.music_manager.set_volume(value / 100.0)
    
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
        self.merge_btn.setText("⏳ Merging...")
        
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
        self.merge_btn.setText("🎬 Merge Video with Music")
        
        if result.success:
            QMessageBox.information(
                self,
                "Merge Complete",
                f"Video merged successfully!\n\n"
                f"Saved to:\n{result.output_path}\n\n"
                f"Processing time: {result.duration:.1f}s"
            )
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
