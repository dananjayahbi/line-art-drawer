"""
Video Player Widget Module
===========================
Custom video player widget using PySide6 and OpenCV for video playback.
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Optional, Callable

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QSlider, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer, Signal, QSize
from PySide6.QtGui import QImage, QPixmap, QIcon


# Get icons path
ICONS_DIR = Path(__file__).resolve().parent.parent / "assets" / "icons"


def load_icon(name: str) -> QIcon:
    """Load an icon from the icons folder."""
    icon_path = ICONS_DIR / f"{name}.svg"
    if icon_path.exists():
        return QIcon(str(icon_path))
    return QIcon()


class VideoPlayerWidget(QWidget):
    """Custom video player widget with playback controls."""
    
    # Signals
    playback_started = Signal()
    playback_paused = Signal()
    playback_stopped = Signal()
    playback_finished = Signal()
    position_changed = Signal(float)  # Current position in seconds
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.video_path: Optional[Path] = None
        self.cap: Optional[cv2.VideoCapture] = None
        self.is_playing = False
        self.current_frame = 0
        self.total_frames = 0
        self.fps = 30.0
        self.duration = 0.0
        
        self._setup_ui()
        
        # Playback timer
        self.playback_timer = QTimer()
        self.playback_timer.timeout.connect(self._update_frame)
        
    def _setup_ui(self):
        """Setup the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Video display area
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("""
            QLabel {
                background-color: #1a1a1a;
                border-radius: 8px;
            }
        """)
        self.video_label.setMinimumSize(400, 300)
        self.video_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.video_label, stretch=1)
        
        # Controls container
        controls_frame = QFrame()
        controls_frame.setStyleSheet("""
            QFrame {
                background-color: #2d2d2d;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        controls_layout = QVBoxLayout(controls_frame)
        controls_layout.setContentsMargins(10, 8, 10, 8)
        controls_layout.setSpacing(6)
        
        # Progress slider row
        progress_row = QHBoxLayout()
        progress_row.setSpacing(10)
        
        self.time_label = QLabel("00:00")
        self.time_label.setStyleSheet("color: #b0b0b0; font-size: 12px; min-width: 45px;")
        progress_row.addWidget(self.time_label)
        
        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setMinimum(0)
        self.progress_slider.setMaximum(1000)
        self.progress_slider.setValue(0)
        self.progress_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                background: #404040;
                height: 6px;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #8fad88;
                width: 14px;
                margin: -4px 0;
                border-radius: 7px;
            }
            QSlider::sub-page:horizontal {
                background: #8fad88;
                border-radius: 3px;
            }
        """)
        self.progress_slider.sliderPressed.connect(self._on_slider_pressed)
        self.progress_slider.sliderReleased.connect(self._on_slider_released)
        self.progress_slider.sliderMoved.connect(self._on_slider_moved)
        progress_row.addWidget(self.progress_slider, stretch=1)
        
        self.duration_label = QLabel("00:00")
        self.duration_label.setStyleSheet("color: #b0b0b0; font-size: 12px; min-width: 45px;")
        progress_row.addWidget(self.duration_label)
        
        controls_layout.addLayout(progress_row)
        
        # Playback buttons row
        button_row = QHBoxLayout()
        button_row.setSpacing(10)
        button_row.addStretch()
        
        # Rewind button
        self.rewind_btn = QPushButton()
        self.rewind_btn.setIcon(load_icon("rewind"))
        self.rewind_btn.setIconSize(QSize(18, 18))
        self.rewind_btn.setFixedSize(36, 36)
        self.rewind_btn.setStyleSheet(self._get_button_style())
        self.rewind_btn.clicked.connect(self.rewind)
        button_row.addWidget(self.rewind_btn)
        
        # Play/Pause button
        self.play_btn = QPushButton()
        self.play_btn.setIcon(load_icon("play"))
        self.play_btn.setIconSize(QSize(22, 22))
        self.play_btn.setFixedSize(44, 44)
        self.play_btn.setStyleSheet(self._get_button_style(primary=True))
        self.play_btn.clicked.connect(self.toggle_play)
        button_row.addWidget(self.play_btn)
        
        # Stop button
        self.stop_btn = QPushButton()
        self.stop_btn.setIcon(load_icon("stop"))
        self.stop_btn.setIconSize(QSize(18, 18))
        self.stop_btn.setFixedSize(36, 36)
        self.stop_btn.setStyleSheet(self._get_button_style())
        self.stop_btn.clicked.connect(self.stop)
        button_row.addWidget(self.stop_btn)
        
        button_row.addStretch()
        controls_layout.addLayout(button_row)
        
        layout.addWidget(controls_frame)
        
        # Show placeholder
        self._show_placeholder()
    
    def _get_button_style(self, primary=False) -> str:
        """Get button stylesheet."""
        bg_color = "#8fad88" if primary else "#404040"
        hover_color = "#7a9773" if primary else "#505050"
        return f"""
            QPushButton {{
                background-color: {bg_color};
                color: white;
                border: none;
                border-radius: 18px;
                font-size: 16px;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
            QPushButton:disabled {{
                background-color: #303030;
                color: #606060;
            }}
        """
    
    def _show_placeholder(self):
        """Show placeholder when no video is loaded."""
        self.video_label.setText("No video loaded\n\nSelect a video from the list")
        self.video_label.setStyleSheet("""
            QLabel {
                background-color: #1a1a1a;
                border-radius: 8px;
                color: #606060;
                font-size: 14px;
            }
        """)
    
    def load_video(self, video_path: Path) -> bool:
        """
        Load a video file for playback.
        
        Args:
            video_path: Path to the video file
            
        Returns:
            True if loaded successfully
        """
        # Stop current playback
        self.stop()
        
        # Release previous capture
        if self.cap is not None:
            self.cap.release()
        
        try:
            self.cap = cv2.VideoCapture(str(video_path))
            if not self.cap.isOpened():
                self._show_placeholder()
                return False
            
            self.video_path = Path(video_path)
            self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
            self.duration = self.total_frames / self.fps
            self.current_frame = 0
            
            # Update duration label
            self.duration_label.setText(self._format_time(self.duration))
            self.time_label.setText("00:00")
            self.progress_slider.setValue(0)
            
            # Show first frame
            self._show_frame(0)
            
            # Reset style
            self.video_label.setStyleSheet("""
                QLabel {
                    background-color: #1a1a1a;
                    border-radius: 8px;
                }
            """)
            
            return True
            
        except Exception as e:
            print(f"Error loading video: {e}")
            self._show_placeholder()
            return False
    
    def _show_frame(self, frame_num: int):
        """Display a specific frame."""
        if self.cap is None:
            return
        
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = self.cap.read()
        
        if ret:
            self._display_frame(frame)
            self.current_frame = frame_num
            
            # Update time label
            current_time = frame_num / self.fps
            self.time_label.setText(self._format_time(current_time))
            
            # Update slider (only if not being dragged)
            if not self.progress_slider.isSliderDown():
                progress = int((frame_num / max(1, self.total_frames - 1)) * 1000)
                self.progress_slider.setValue(progress)
    
    def _display_frame(self, frame):
        """Convert and display a frame in the label."""
        # Convert BGR to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Get label size
        label_size = self.video_label.size()
        
        # Calculate aspect-ratio preserving size
        frame_h, frame_w = rgb_frame.shape[:2]
        aspect = frame_w / frame_h
        
        if label_size.width() / label_size.height() > aspect:
            # Height limited
            new_h = label_size.height() - 20
            new_w = int(new_h * aspect)
        else:
            # Width limited
            new_w = label_size.width() - 20
            new_h = int(new_w / aspect)
        
        new_w = max(1, new_w)
        new_h = max(1, new_h)
        
        # Resize frame
        resized = cv2.resize(rgb_frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
        
        # Convert to QImage
        h, w, ch = resized.shape
        bytes_per_line = ch * w
        q_image = QImage(resized.data, w, h, bytes_per_line, QImage.Format_RGB888)
        
        # Display
        self.video_label.setPixmap(QPixmap.fromImage(q_image))
    
    def _update_frame(self):
        """Timer callback to update frame during playback."""
        if self.cap is None or not self.is_playing:
            return
        
        ret, frame = self.cap.read()
        
        if ret:
            self._display_frame(frame)
            self.current_frame = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
            
            # Update UI
            current_time = self.current_frame / self.fps
            self.time_label.setText(self._format_time(current_time))
            self.position_changed.emit(current_time)
            
            if not self.progress_slider.isSliderDown():
                progress = int((self.current_frame / max(1, self.total_frames - 1)) * 1000)
                self.progress_slider.setValue(progress)
        else:
            # End of video
            self.stop()
            self.playback_finished.emit()
    
    def play(self):
        """Start playback."""
        if self.cap is None:
            return
        
        self.is_playing = True
        self.play_btn.setIcon(load_icon("pause"))
        
        # Calculate timer interval from fps
        interval = int(1000 / self.fps)
        self.playback_timer.start(interval)
        self.playback_started.emit()
    
    def pause(self):
        """Pause playback."""
        self.is_playing = False
        self.play_btn.setIcon(load_icon("play"))
        self.playback_timer.stop()
        self.playback_paused.emit()
    
    def toggle_play(self):
        """Toggle between play and pause."""
        if self.is_playing:
            self.pause()
        else:
            self.play()
    
    def stop(self):
        """Stop playback and reset to beginning."""
        self.pause()
        if self.cap is not None:
            self._show_frame(0)
        self.playback_stopped.emit()
    
    def rewind(self):
        """Rewind 5 seconds."""
        if self.cap is None:
            return
        
        new_frame = max(0, self.current_frame - int(5 * self.fps))
        self._show_frame(new_frame)
    
    def seek(self, seconds: float):
        """
        Seek to a specific position.
        
        Args:
            seconds: Position in seconds
        """
        if self.cap is None:
            return
        
        frame_num = int(seconds * self.fps)
        frame_num = max(0, min(frame_num, self.total_frames - 1))
        self._show_frame(frame_num)
    
    def _on_slider_pressed(self):
        """Handle slider press."""
        # Pause playback while dragging
        if self.is_playing:
            self.playback_timer.stop()
    
    def _on_slider_released(self):
        """Handle slider release."""
        # Resume playback if was playing
        if self.is_playing:
            interval = int(1000 / self.fps)
            self.playback_timer.start(interval)
    
    def _on_slider_moved(self, value: int):
        """Handle slider movement."""
        if self.cap is None:
            return
        
        # Calculate frame from slider position
        frame_num = int((value / 1000) * (self.total_frames - 1))
        self._show_frame(frame_num)
    
    def _format_time(self, seconds: float) -> str:
        """Format seconds as MM:SS."""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"
    
    def get_video_path(self) -> Optional[Path]:
        """Get the currently loaded video path."""
        return self.video_path
    
    def get_duration(self) -> float:
        """Get video duration in seconds."""
        return self.duration
    
    def cleanup(self):
        """Clean up resources."""
        self.stop()
        if self.cap is not None:
            self.cap.release()
            self.cap = None
    
    def resizeEvent(self, event):
        """Handle resize to update displayed frame."""
        super().resizeEvent(event)
        if self.cap is not None and not self.is_playing:
            # Redraw current frame at new size
            self._show_frame(self.current_frame)
