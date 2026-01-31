#!/usr/bin/env python3
"""
Greedy String Art - Control Panel Main Window (PySide6)
========================================================
Main control panel window implementation for the greedy string art simulation.
"""

import sys
import os
import json
import subprocess
import threading
import shutil
import time
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QSlider, QLineEdit, QCheckBox, QComboBox, QGroupBox,
    QFileDialog, QMessageBox, QScrollArea, QFrame, QSpinBox, QDialog, QInputDialog,
    QRadioButton
)
from PySide6.QtCore import Qt, Signal, QTimer, QThread, QUrl, QSize, QPoint
from PySide6.QtGui import QPixmap, QDragEnterEvent, QDropEvent, QIcon, QFont, QPainter, QPen, QColor, QMouseEvent

# Import modularized components
from settings_manager import SettingsManager
from custom_widgets import ToggleSwitch, ImageUploadWidget, load_icon
from video_thread import VideoGenerationThread

# Get paths
SIMULATION_DIR = Path(__file__).resolve().parent
BASE_DIR = SIMULATION_DIR.parent
FRAMES_FOLDER = SIMULATION_DIR / "frames"
UPLOADS_FOLDER = SIMULATION_DIR / "uploads"
ICONS_FOLDER = SIMULATION_DIR / "assets" / "icons"


class ControlPanel(QMainWindow):
    """Main control panel window."""
    
    def __init__(self):
        super().__init__()
        
        # Ensure folders exist
        UPLOADS_FOLDER.mkdir(parents=True, exist_ok=True)
        FRAMES_FOLDER.mkdir(parents=True, exist_ok=True)
        
        # Initialize settings manager
        self.settings_manager = SettingsManager(SIMULATION_DIR)
        
        # Process tracking
        self.simulation_process = None
        self.video_thread = None
        
        # Setup UI
        self._init_variables()
        self._load_settings()
        self._setup_ui()
        self._update_ui_from_settings()  # Update UI after setup
        self._update_frame_count()
        
        # Auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self._update_frame_count)
        self.refresh_timer.start(2000)  # 2 seconds
    
    def _init_variables(self):
        """Initialize all settings variables."""
        # Window settings
        self.width = 1080
        self.height = 1920
        self.fps = 60
        self.fullscreen = False
        
        # String Art Algorithm Settings
        self.nail_count = 250
        self.max_lines = 3000
        self.thread_opacity = 0.15
        self.brightness_reduction = 0.12
        self.min_distance = 20
        
        # Canvas Settings
        self.canvas_color = "#1a1410"
        self.thread_color = "#ffffff"
        self.nail_color = "#c0a080"
        self.nail_radius = 3
        
        # Optimization Settings
        self.use_gpu = True
        self.convergence_threshold = 0.001
        self.lookahead_nails = 0
        
        # Animation Settings
        self.use_manim = False
        self.show_thread_accumulation = True
        self.show_nail_numbers = False
        self.camera_follow_thread = True
        self.zoom_level = 1.2
        
        # Speed Control
        self.target_duration = 15.0
        self.animation_speed = 1.0
        
        # Recording Settings
        self.record = True
        self.record_format = "png"
        self.record_quality = 95
        
        # Visual Effects
        self.glow_effect = True
        self.motion_blur = True
        self.show_progress_bar = True
        self.theme = "dark_wood"
        
        # Border Settings
        self.show_border = True
        self.border_width = 40
        self.border_color = "#2d2416"
    
    def _load_settings(self):
        """Load all settings from file."""
        settings = self.settings_manager.load_settings()
        
        self.width = int(settings.get("width", "1080"))
        self.height = int(settings.get("height", "1920"))
        self.fps = 60  # Always 60
        self.fullscreen = settings.get("fullscreen", False)
        
        # Algorithm settings
        self.nail_count = int(settings.get("nail_count", "250"))
        self.max_lines = int(settings.get("max_lines", "3000"))
        self.thread_opacity = float(settings.get("thread_opacity", "0.15"))
        self.brightness_reduction = float(settings.get("brightness_reduction", "0.12"))
        self.min_distance = int(settings.get("min_distance", "20"))
        
        # Canvas settings
        self.canvas_color = settings.get("canvas_color", "#1a1410")
        self.thread_color = settings.get("thread_color", "#ffffff")
        self.nail_color = settings.get("nail_color", "#c0a080")
        self.nail_radius = int(settings.get("nail_radius", "3"))
        
        # Optimization settings
        self.use_gpu = settings.get("use_gpu", True)
        self.convergence_threshold = float(settings.get("convergence_threshold", "0.001"))
        self.lookahead_nails = int(settings.get("lookahead_nails", "0"))
        
        # Animation settings
        self.use_manim = settings.get("use_manim", False)
        self.show_thread_accumulation = settings.get("show_thread_accumulation", True)
        self.show_nail_numbers = settings.get("show_nail_numbers", False)
        self.camera_follow_thread = settings.get("camera_follow_thread", True)
        self.zoom_level = float(settings.get("zoom_level", "1.2"))
        
        # Speed control
        self.target_duration = float(settings.get("target_duration", "15.0"))
        self.animation_speed = float(settings.get("animation_speed", "1.0"))
        
        # Recording settings
        self.record = settings.get("record", True)
        self.record_format = settings.get("record_format", "png")
        self.record_quality = int(settings.get("record_quality", "95"))
        
        # Visual effects
        self.glow_effect = settings.get("glow_effect", True)
        self.motion_blur = settings.get("motion_blur", True)
        self.show_progress_bar = settings.get("show_progress_bar", True)
        self.theme = settings.get("theme", "dark_wood")
        
        # Border settings
        self.show_border = settings.get("show_border", True)
        self.border_width = int(settings.get("border_width", "40"))
        self.border_color = settings.get("border_color", "#2d2416")
    
    def _save_settings(self):
        """Save all settings to file."""
        # Read current values from UI
        try:
            width = int(self.width_input.text())
            height = int(self.height_input.text())
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Width and Height must be valid integers.")
            return
        
        # Get target duration
        try:
            target_duration = float(self.duration_input.text())
        except ValueError:
            target_duration = 15.0
        
        settings = {
            "width": str(width),
            "height": str(height),
            "fps": "60",  # Always 60
            "fullscreen": self.fullscreen_toggle.isChecked(),
            
            # Algorithm settings
            "nail_count": str(self.nail_count_spin.value()),
            "max_lines": str(self.max_lines_spin.value()),
            "thread_opacity": str(self.thread_opacity_slider.value() / 100.0),
            "brightness_reduction": str(self.brightness_slider.value() / 100.0),
            "min_distance": str(self.min_distance_spin.value()),
            
            # Canvas settings
            "canvas_color": self.canvas_color,
            "thread_color": self.thread_color,
            "nail_color": self.nail_color,
            "nail_radius": str(self.nail_radius_spin.value()),
            
            # Optimization settings
            "use_gpu": self.gpu_toggle.isChecked(),
            "convergence_threshold": str(self.convergence_slider.value() / 10000.0),
            "lookahead_nails": str(self.lookahead_spin.value()),
            
            # Animation settings
            "use_manim": self.manim_toggle.isChecked(),
            "show_thread_accumulation": self.thread_accum_toggle.isChecked(),
            "show_nail_numbers": self.nail_numbers_toggle.isChecked(),
            "camera_follow_thread": self.camera_follow_toggle.isChecked(),
            "zoom_level": str(self.zoom_slider.value() / 10.0),
            
            # Speed control
            "target_duration": str(target_duration),
            "animation_speed": str(self.speed_slider.value() / 10.0),
            
            # Recording settings
            "record": self.auto_record_toggle.isChecked(),
            "record_format": self.record_format_combo.currentText(),
            "record_quality": str(self.quality_slider.value()),
            
            # Visual effects
            "glow_effect": self.glow_toggle.isChecked(),
            "motion_blur": self.motion_blur_toggle.isChecked(),
            "show_progress_bar": self.progress_bar_toggle.isChecked(),
            "theme": self.theme_combo.currentText(),
            
            # Border settings
            "show_border": self.show_border_toggle.isChecked(),
            "border_width": str(self.border_width_slider.value()),
            "border_color": self.border_color
        }
        
        if self.settings_manager.save_settings(settings):
            self._update_status("Settings saved successfully!")
            QMessageBox.information(self, "Success", "Settings saved successfully!")
    
    def _reset_to_defaults(self):
        """Reset all settings to defaults."""
        reply = QMessageBox.question(
            self,
            "Reset Settings",
            "Are you sure you want to reset all settings to defaults?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.settings_manager.reset_to_defaults()
            self._load_settings()
            self._update_ui_from_settings()
            self._update_status("Settings reset to defaults")
            QMessageBox.information(self, "Reset Complete", "All settings have been reset to defaults.")
    
    def _setup_ui(self):
        """Setup the main UI."""
        self.setWindowTitle("Greedy String Art - Control Panel")
        self.setMinimumSize(1366, 768)
        self.setMaximumSize(1920, 1080)
        # Open as maximized window
        self.showMaximized()
        
        # Set warm terracotta theme
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5ebe0;
            }
            QWidget {
                background-color: #f5ebe0;
                color: #4a3428;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 11px;
            }
            QGroupBox {
                background-color: #faf7f2;
                border: 1px solid #d4c4b0;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 20px;
                font-weight: bold;
                color: #5c4033;
                font-size: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 5px 10px;
                color: #5c4033;
            }
            QLabel {
                color: #6b5444;
                background-color: transparent;
            }
            QLineEdit, QSpinBox {
                background-color: #ffffff;
                border: 1px solid #d4c4b0;
                border-radius: 4px;
                padding: 6px;
                color: #4a3428;
            }
            QLineEdit:focus, QSpinBox:focus {
                border: 1px solid #c2785a;
            }
            QSlider::groove:horizontal {
                height: 6px;
                background: #d4c4b0;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #c2785a;
                width: 16px;
                height: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }
            QSlider::handle:horizontal:hover {
                background: #a85d44;
            }
            QComboBox {
                background-color: #ffffff;
                border: 1px solid #d4c4b0;
                border-radius: 4px;
                padding: 6px;
                color: #4a3428;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid #6b5444;
                width: 0;
                height: 0;
            }
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                border: 1px solid #d4c4b0;
                selection-background-color: #c2785a;
                color: #4a3428;
            }
            QPushButton {
                background-color: #d4a88a;
                color: #4a3428;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 11px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #c2785a;
                color: white;
            }
            QPushButton:pressed {
                background-color: #a85d44;
            }
            QScrollArea {
                border: none;
            }
            QScrollBar:vertical {
                background-color: #e8ddd0;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #c2785a;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #a85d44;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        # Central widget with scroll area
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # Header
        self._create_header(main_layout)
        
        # Scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        scroll_content = QWidget()
        content_layout = QVBoxLayout(scroll_content)
        content_layout.setSpacing(15)
        
        # Main content - 3 columns
        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(15)
        
        # Left column
        left_column = QVBoxLayout()
        left_column.setSpacing(15)
        self._create_image_upload_section(left_column)
        self._create_window_settings(left_column)
        self._create_algorithm_settings(left_column)
        left_column.addStretch()
        columns_layout.addLayout(left_column, 1)
        
        # Middle column
        middle_column = QVBoxLayout()
        middle_column.setSpacing(15)
        self._create_canvas_settings(middle_column)
        self._create_optimization_settings(middle_column)
        self._create_animation_settings(middle_column)
        middle_column.addStretch()
        columns_layout.addLayout(middle_column, 1)
        
        # Right column
        right_column = QVBoxLayout()
        right_column.setSpacing(15)
        self._create_speed_settings(right_column)
        self._create_visual_settings(right_column)
        self._create_recording_settings(right_column)
        right_column.addStretch()
        columns_layout.addLayout(right_column, 1)
        
        content_layout.addLayout(columns_layout)
        
        # Frame management
        self._create_frame_management(content_layout)
        
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll, 1)
        
        # Launch button
        self._create_launch_button(main_layout)
        
        # Status bar
        self._create_status_bar(main_layout)
    
    def _create_header(self, layout):
        """Create header section."""
        header_layout = QHBoxLayout()
        
        # Title section
        title_layout = QVBoxLayout()
        title_label = QLabel("🧵 Greedy String Art")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #c2785a;
            }
        """)
        title_layout.addWidget(title_label)
        
        subtitle_label = QLabel("Algorithmic Portrait Thread Weaving")
        subtitle_label.setStyleSheet("""
            QLabel {
                font-size: 11px;
                color: #8b7355;
            }
        """)
        title_layout.addWidget(subtitle_label)
        
        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        
        # Save/Reset buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        save_btn = QPushButton("💾 Save Settings")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #c2785a;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                font-size: 12px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #a85d44;
            }
        """)
        save_btn.clicked.connect(self._save_settings)
        btn_layout.addWidget(save_btn)
        
        reset_btn = QPushButton("🔄 Reset to Defaults")
        reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #d4a88a;
                color: #4a3428;
                padding: 10px 20px;
                font-size: 12px;
                border-radius: 6px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #e8c5a8;
            }
        """)
        reset_btn.clicked.connect(self._reset_to_defaults)
        btn_layout.addWidget(reset_btn)
        
        header_layout.addLayout(btn_layout)
        
        layout.addLayout(header_layout)
    
    def _create_image_upload_section(self, layout):
        """Create image upload section."""
        group = QGroupBox("Target Portrait Image (Grayscale)")
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(10)
        
        info_label = QLabel("Upload a portrait image to recreate with string art")
        info_label.setStyleSheet("QLabel { color: #8b7355; font-size: 10px; }")
        group_layout.addWidget(info_label)
        
        self.image_upload_widget = ImageUploadWidget(UPLOADS_FOLDER)
        self.image_upload_widget.imageUploaded.connect(
            lambda filename: self._update_status(f"Loaded: {filename}")
        )
        self.image_upload_widget.imageCleared.connect(
            lambda: self._update_status("Image cleared")
        )
        group_layout.addWidget(self.image_upload_widget)
        
        layout.addWidget(group)
    
    def _create_window_settings(self, layout):
        """Create window settings section."""
        group = QGroupBox("Window Settings")
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(10)
        
        # Width and Height
        size_layout = QGridLayout()
        size_layout.setSpacing(10)
        
        size_layout.addWidget(QLabel("Width:"), 0, 0)
        self.width_input = QLineEdit(str(self.width))
        self.width_input.setMaximumWidth(100)
        size_layout.addWidget(self.width_input, 0, 1)
        
        size_layout.addWidget(QLabel("Height:"), 0, 2)
        self.height_input = QLineEdit(str(self.height))
        self.height_input.setMaximumWidth(100)
        size_layout.addWidget(self.height_input, 0, 3)
        
        # FPS is locked at 60
        size_layout.addWidget(QLabel("FPS:"), 1, 0)
        fps_label = QLabel("<b>60 FPS</b> (locked)")
        fps_label.setStyleSheet("QLabel { color: #c2785a; }")
        fps_label.setMaximumWidth(100)
        size_layout.addWidget(fps_label, 1, 1)
        
        group_layout.addLayout(size_layout)
        
        # Fullscreen toggle
        fullscreen_layout = QHBoxLayout()
        fullscreen_label = QLabel("Fullscreen Mode")
        self.fullscreen_toggle = ToggleSwitch()
        self.fullscreen_toggle.setChecked(self.fullscreen)
        fullscreen_layout.addWidget(fullscreen_label)
        fullscreen_layout.addStretch()
        fullscreen_layout.addWidget(self.fullscreen_toggle)
        group_layout.addLayout(fullscreen_layout)
        
        # Presets
        presets_layout = QHBoxLayout()
        presets_layout.setSpacing(8)
        
        preset_label = QLabel("Presets:")
        presets_layout.addWidget(preset_label)
        
        presets = [
            ("9:16 (1080x1920)", 1080, 1920),
            ("16:9 (1920x1080)", 1920, 1080),
            ("1:1 (1080x1080)", 1080, 1080)
        ]
        
        for name, w, h in presets:
            btn = QPushButton(name)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #4b5563;
                    padding: 5px 10px;
                    font-size: 10px;
                }
                QPushButton:hover {
                    background-color: #6b7280;
                }
            """)
            btn.clicked.connect(lambda checked, w=w, h=h: self._set_resolution(w, h))
            presets_layout.addWidget(btn)
        
        presets_layout.addStretch()
        group_layout.addLayout(presets_layout)
        
        layout.addWidget(group)
    
    def _create_algorithm_settings(self, layout):
        """Create string art algorithm settings section."""
        group = QGroupBox("String Art Algorithm Settings")
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(12)
        
        # Nail Count
        nail_layout = QHBoxLayout()
        nail_layout.addWidget(QLabel("Nail Count:"))
        self.nail_count_spin = QSpinBox()
        self.nail_count_spin.setMinimum(50)
        self.nail_count_spin.setMaximum(500)
        self.nail_count_spin.setValue(self.nail_count)
        self.nail_count_spin.setMaximumWidth(100)
        self.nail_count_spin.setToolTip("Number of nails around the circular perimeter")
        nail_layout.addWidget(self.nail_count_spin)
        nail_layout.addStretch()
        group_layout.addLayout(nail_layout)
        
        # Max Lines
        lines_layout = QHBoxLayout()
        lines_layout.addWidget(QLabel("Max Lines:"))
        self.max_lines_spin = QSpinBox()
        self.max_lines_spin.setMinimum(500)
        self.max_lines_spin.setMaximum(10000)
        self.max_lines_spin.setSingleStep(100)
        self.max_lines_spin.setValue(self.max_lines)
        self.max_lines_spin.setMaximumWidth(100)
        self.max_lines_spin.setToolTip("Maximum number of thread lines to draw")
        lines_layout.addWidget(self.max_lines_spin)
        lines_layout.addStretch()
        group_layout.addLayout(lines_layout)
        
        # Thread Opacity
        opacity_layout = QVBoxLayout()
        opacity_layout.setSpacing(5)
        
        opacity_header = QHBoxLayout()
        opacity_label = QLabel("Thread Opacity:")
        self.thread_opacity_value_label = QLabel(f"{self.thread_opacity:.2f}")
        self.thread_opacity_value_label.setStyleSheet("QLabel { color: #c2785a; font-weight: bold; }")
        opacity_header.addWidget(opacity_label)
        opacity_header.addStretch()
        opacity_header.addWidget(self.thread_opacity_value_label)
        opacity_layout.addLayout(opacity_header)
        
        self.thread_opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.thread_opacity_slider.setMinimum(5)
        self.thread_opacity_slider.setMaximum(50)
        self.thread_opacity_slider.setValue(int(self.thread_opacity * 100))
        self.thread_opacity_slider.valueChanged.connect(
            lambda v: self.thread_opacity_value_label.setText(f"{v/100:.2f}")
        )
        opacity_layout.addWidget(self.thread_opacity_slider)
        
        group_layout.addLayout(opacity_layout)
        
        # Brightness Reduction
        brightness_layout = QVBoxLayout()
        brightness_layout.setSpacing(5)
        
        brightness_header = QHBoxLayout()
        brightness_label = QLabel("Brightness Reduction:")
        self.brightness_value_label = QLabel(f"{self.brightness_reduction:.2f}")
        self.brightness_value_label.setStyleSheet("QLabel { color: #c2785a; font-weight: bold; }")
        brightness_header.addWidget(brightness_label)
        brightness_header.addStretch()
        brightness_header.addWidget(self.brightness_value_label)
        brightness_layout.addLayout(brightness_header)
        
        self.brightness_slider = QSlider(Qt.Orientation.Horizontal)
        self.brightness_slider.setMinimum(5)
        self.brightness_slider.setMaximum(30)
        self.brightness_slider.setValue(int(self.brightness_reduction * 100))
        self.brightness_slider.valueChanged.connect(
            lambda v: self.brightness_value_label.setText(f"{v/100:.2f}")
        )
        brightness_layout.addWidget(self.brightness_slider)
        
        group_layout.addLayout(brightness_layout)
        
        # Min Distance
        distance_layout = QHBoxLayout()
        distance_layout.addWidget(QLabel("Min Nail Distance:"))
        self.min_distance_spin = QSpinBox()
        self.min_distance_spin.setMinimum(1)
        self.min_distance_spin.setMaximum(50)
        self.min_distance_spin.setValue(self.min_distance)
        self.min_distance_spin.setMaximumWidth(100)
        self.min_distance_spin.setToolTip("Minimum distance between connected nails (prevents adjacent connections)")
        distance_layout.addWidget(self.min_distance_spin)
        distance_layout.addStretch()
        group_layout.addLayout(distance_layout)
        
        layout.addWidget(group)
    
    def _create_canvas_settings(self, layout):
        """Create canvas settings section."""
        group = QGroupBox("Canvas & Thread Settings")
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(12)
        
        # Canvas Color
        canvas_color_layout = QHBoxLayout()
        canvas_color_label = QLabel("Canvas Color:")
        canvas_color_layout.addWidget(canvas_color_label)
        
        self.canvas_color_btn = QPushButton(self.canvas_color)
        self.canvas_color_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.canvas_color};
                color: white;
                border: 1px solid #d4c4b0;
            }}
        """)
        self.canvas_color_btn.clicked.connect(lambda: self._choose_color('canvas'))
        canvas_color_layout.addWidget(self.canvas_color_btn)
        canvas_color_layout.addStretch()
        group_layout.addLayout(canvas_color_layout)
        
        # Thread Color
        thread_color_layout = QHBoxLayout()
        thread_color_label = QLabel("Thread Color:")
        thread_color_layout.addWidget(thread_color_label)
        
        self.thread_color_btn = QPushButton(self.thread_color)
        self.thread_color_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.thread_color};
                color: black;
                border: 1px solid #d4c4b0;
            }}
        """)
        self.thread_color_btn.clicked.connect(lambda: self._choose_color('thread'))
        thread_color_layout.addWidget(self.thread_color_btn)
        thread_color_layout.addStretch()
        group_layout.addLayout(thread_color_layout)
        
        # Nail Color
        nail_color_layout = QHBoxLayout()
        nail_color_label = QLabel("Nail Color:")
        nail_color_layout.addWidget(nail_color_label)
        
        self.nail_color_btn = QPushButton(self.nail_color)
        self.nail_color_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.nail_color};
                color: black;
                border: 1px solid #d4c4b0;
            }}
        """)
        self.nail_color_btn.clicked.connect(lambda: self._choose_color('nail'))
        nail_color_layout.addWidget(self.nail_color_btn)
        nail_color_layout.addStretch()
        group_layout.addLayout(nail_color_layout)
        
        # Nail Radius
        nail_radius_layout = QHBoxLayout()
        nail_radius_layout.addWidget(QLabel("Nail Radius:"))
        self.nail_radius_spin = QSpinBox()
        self.nail_radius_spin.setMinimum(1)
        self.nail_radius_spin.setMaximum(10)
        self.nail_radius_spin.setValue(self.nail_radius)
        self.nail_radius_spin.setMaximumWidth(100)
        nail_radius_layout.addWidget(self.nail_radius_spin)
        nail_radius_layout.addWidget(QLabel("pixels"))
        nail_radius_layout.addStretch()
        group_layout.addLayout(nail_radius_layout)
        
        layout.addWidget(group)
    
    def _create_optimization_settings(self, layout):
        """Create optimization settings section."""
        group = QGroupBox("Optimization Settings")
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(12)
        
        # GPU Acceleration
        gpu_layout = QHBoxLayout()
        gpu_label = QLabel("GPU Acceleration (if available)")
        self.gpu_toggle = ToggleSwitch()
        self.gpu_toggle.setChecked(self.use_gpu)
        gpu_layout.addWidget(gpu_label)
        gpu_layout.addStretch()
        gpu_layout.addWidget(self.gpu_toggle)
        group_layout.addLayout(gpu_layout)
        
        # Convergence Threshold
        convergence_layout = QVBoxLayout()
        convergence_layout.setSpacing(5)
        
        convergence_header = QHBoxLayout()
        convergence_label = QLabel("Convergence Threshold:")
        self.convergence_value_label = QLabel(f"{self.convergence_threshold:.4f}")
        self.convergence_value_label.setStyleSheet("QLabel { color: #c2785a; font-weight: bold; }")
        convergence_header.addWidget(convergence_label)
        convergence_header.addStretch()
        convergence_header.addWidget(self.convergence_value_label)
        convergence_layout.addLayout(convergence_header)
        
        self.convergence_slider = QSlider(Qt.Orientation.Horizontal)
        self.convergence_slider.setMinimum(1)
        self.convergence_slider.setMaximum(50)
        self.convergence_slider.setValue(int(self.convergence_threshold * 10000))
        self.convergence_slider.valueChanged.connect(
            lambda v: self.convergence_value_label.setText(f"{v/10000:.4f}")
        )
        convergence_layout.addWidget(self.convergence_slider)
        
        group_layout.addLayout(convergence_layout)
        
        # Lookahead Nails
        lookahead_layout = QHBoxLayout()
        lookahead_layout.addWidget(QLabel("Lookahead Nails:"))
        self.lookahead_spin = QSpinBox()
        self.lookahead_spin.setMinimum(0)
        self.lookahead_spin.setMaximum(100)
        self.lookahead_spin.setValue(self.lookahead_nails)
        self.lookahead_spin.setMaximumWidth(100)
        self.lookahead_spin.setToolTip("0 = check all nails, >0 = only check N closest nails for performance")
        lookahead_layout.addWidget(self.lookahead_spin)
        lookahead_layout.addStretch()
        group_layout.addLayout(lookahead_layout)
        
        layout.addWidget(group)
    
    def _create_animation_settings(self, layout):
        """Create animation settings section."""
        group = QGroupBox("Animation Settings")
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(12)
        
        # Use Manim
        manim_layout = QHBoxLayout()
        manim_label = QLabel("Use Manim Rendering")
        self.manim_toggle = ToggleSwitch()
        self.manim_toggle.setChecked(self.use_manim)
        manim_layout.addWidget(manim_label)
        manim_layout.addStretch()
        manim_layout.addWidget(self.manim_toggle)
        group_layout.addLayout(manim_layout)
        
        # Show Thread Accumulation
        thread_accum_layout = QHBoxLayout()
        thread_accum_label = QLabel("Show Thread Accumulation")
        self.thread_accum_toggle = ToggleSwitch()
        self.thread_accum_toggle.setChecked(self.show_thread_accumulation)
        thread_accum_layout.addWidget(thread_accum_label)
        thread_accum_layout.addStretch()
        thread_accum_layout.addWidget(self.thread_accum_toggle)
        group_layout.addLayout(thread_accum_layout)
        
        # Show Nail Numbers
        nail_numbers_layout = QHBoxLayout()
        nail_numbers_label = QLabel("Show Nail Numbers")
        self.nail_numbers_toggle = ToggleSwitch()
        self.nail_numbers_toggle.setChecked(self.show_nail_numbers)
        nail_numbers_layout.addWidget(nail_numbers_label)
        nail_numbers_layout.addStretch()
        nail_numbers_layout.addWidget(self.nail_numbers_toggle)
        group_layout.addLayout(nail_numbers_layout)
        
        # Camera Follow Thread
        camera_follow_layout = QHBoxLayout()
        camera_follow_label = QLabel("Camera Follow Thread")
        self.camera_follow_toggle = ToggleSwitch()
        self.camera_follow_toggle.setChecked(self.camera_follow_thread)
        camera_follow_layout.addWidget(camera_follow_label)
        camera_follow_layout.addStretch()
        camera_follow_layout.addWidget(self.camera_follow_toggle)
        group_layout.addLayout(camera_follow_layout)
        
        # Zoom Level
        zoom_layout = QVBoxLayout()
        zoom_layout.setSpacing(5)
        
        zoom_header = QHBoxLayout()
        zoom_label = QLabel("Zoom Level:")
        self.zoom_value_label = QLabel(f"{self.zoom_level:.1f}x")
        self.zoom_value_label.setStyleSheet("QLabel { color: #c2785a; font-weight: bold; }")
        zoom_header.addWidget(zoom_label)
        zoom_header.addStretch()
        zoom_header.addWidget(self.zoom_value_label)
        zoom_layout.addLayout(zoom_header)
        
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setMinimum(5)
        self.zoom_slider.setMaximum(30)
        self.zoom_slider.setValue(int(self.zoom_level * 10))
        self.zoom_slider.valueChanged.connect(
            lambda v: self.zoom_value_label.setText(f"{v/10:.1f}x")
        )
        zoom_layout.addWidget(self.zoom_slider)
        
        group_layout.addLayout(zoom_layout)
        
        layout.addWidget(group)
    
    def _create_speed_settings(self, layout):
        """Create speed settings section."""
        group = QGroupBox("Speed Settings")
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(12)
        
        # Target Duration
        duration_layout = QGridLayout()
        duration_layout.setSpacing(10)
        
        duration_label = QLabel("Target Duration:")
        duration_label.setToolTip("Set the exact duration for the animation")
        duration_layout.addWidget(duration_label, 0, 0)
        
        self.duration_input = QLineEdit(str(self.target_duration))
        self.duration_input.setMaximumWidth(100)
        self.duration_input.setPlaceholderText("seconds")
        duration_layout.addWidget(self.duration_input, 0, 1)
        
        duration_unit_label = QLabel("seconds")
        duration_layout.addWidget(duration_unit_label, 0, 2)
        
        duration_info = QLabel("ℹ️ Animation speed will auto-adjust to match this duration")
        duration_info.setStyleSheet("QLabel { color: #8b7355; font-size: 10px; }")
        duration_info.setWordWrap(True)
        duration_layout.addWidget(duration_info, 1, 0, 1, 3)
        
        group_layout.addLayout(duration_layout)
        
        # Manual Speed Multiplier
        speed_layout = QVBoxLayout()
        speed_layout.setSpacing(5)
        
        speed_header = QHBoxLayout()
        speed_label = QLabel("Speed Multiplier:")
        self.speed_value_label = QLabel(f"{self.animation_speed:.1f}x")
        self.speed_value_label.setStyleSheet("QLabel { color: #c2785a; font-weight: bold; }")
        speed_header.addWidget(speed_label)
        speed_header.addStretch()
        speed_header.addWidget(self.speed_value_label)
        speed_layout.addLayout(speed_header)
        
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setMinimum(1)
        self.speed_slider.setMaximum(50)
        self.speed_slider.setValue(int(self.animation_speed * 10))
        self.speed_slider.valueChanged.connect(
            lambda v: self.speed_value_label.setText(f"{v/10:.1f}x")
        )
        speed_layout.addWidget(self.speed_slider)
        
        group_layout.addLayout(speed_layout)
        
        layout.addWidget(group)
    
    def _create_visual_settings(self, layout):
        """Create visual settings section."""
        group = QGroupBox("Visual Effects")
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(12)
        
        # Glow Effect
        glow_layout = QHBoxLayout()
        glow_label = QLabel("Glow Effect")
        self.glow_toggle = ToggleSwitch()
        self.glow_toggle.setChecked(self.glow_effect)
        glow_layout.addWidget(glow_label)
        glow_layout.addStretch()
        glow_layout.addWidget(self.glow_toggle)
        group_layout.addLayout(glow_layout)
        
        # Motion Blur
        motion_blur_layout = QHBoxLayout()
        motion_blur_label = QLabel("Motion Blur")
        self.motion_blur_toggle = ToggleSwitch()
        self.motion_blur_toggle.setChecked(self.motion_blur)
        motion_blur_layout.addWidget(motion_blur_label)
        motion_blur_layout.addStretch()
        motion_blur_layout.addWidget(self.motion_blur_toggle)
        group_layout.addLayout(motion_blur_layout)
        
        # Show Progress Bar
        progress_bar_layout = QHBoxLayout()
        progress_bar_label = QLabel("Show Progress Bar")
        self.progress_bar_toggle = ToggleSwitch()
        self.progress_bar_toggle.setChecked(self.show_progress_bar)
        progress_bar_layout.addWidget(progress_bar_label)
        progress_bar_layout.addStretch()
        progress_bar_layout.addWidget(self.progress_bar_toggle)
        group_layout.addLayout(progress_bar_layout)
        
        # Theme
        theme_layout = QHBoxLayout()
        theme_layout.addWidget(QLabel("Theme:"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["dark_wood", "light_canvas", "modern_dark"])
        self.theme_combo.setCurrentText(self.theme)
        theme_layout.addWidget(self.theme_combo)
        theme_layout.addStretch()
        group_layout.addLayout(theme_layout)
        
        # Border Settings
        border_layout = QHBoxLayout()
        border_label = QLabel("Show Border")
        self.show_border_toggle = ToggleSwitch()
        self.show_border_toggle.setChecked(self.show_border)
        border_layout.addWidget(border_label)
        border_layout.addStretch()
        border_layout.addWidget(self.show_border_toggle)
        group_layout.addLayout(border_layout)
        
        # Border Width
        border_width_layout = QVBoxLayout()
        border_width_layout.setSpacing(5)
        
        border_width_header = QHBoxLayout()
        border_width_label = QLabel("Border Width:")
        self.border_width_value_label = QLabel(f"{self.border_width}px")
        self.border_width_value_label.setStyleSheet("QLabel { color: #c2785a; font-weight: bold; }")
        border_width_header.addWidget(border_width_label)
        border_width_header.addStretch()
        border_width_header.addWidget(self.border_width_value_label)
        border_width_layout.addLayout(border_width_header)
        
        self.border_width_slider = QSlider(Qt.Orientation.Horizontal)
        self.border_width_slider.setMinimum(10)
        self.border_width_slider.setMaximum(100)
        self.border_width_slider.setValue(self.border_width)
        self.border_width_slider.valueChanged.connect(
            lambda v: self.border_width_value_label.setText(f"{v}px")
        )
        border_width_layout.addWidget(self.border_width_slider)
        
        group_layout.addLayout(border_width_layout)
        
        layout.addWidget(group)
    
    def _create_recording_settings(self, layout):
        """Create recording settings section."""
        group = QGroupBox("Recording Settings")
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(12)
        
        # Auto-start Recording
        auto_layout = QHBoxLayout()
        auto_label = QLabel("Auto-start Recording")
        self.auto_record_toggle = ToggleSwitch()
        self.auto_record_toggle.setChecked(self.record)
        auto_layout.addWidget(auto_label)
        auto_layout.addStretch()
        auto_layout.addWidget(self.auto_record_toggle)
        group_layout.addLayout(auto_layout)
        
        # Format and Quality
        format_layout = QGridLayout()
        format_layout.setSpacing(10)
        
        format_layout.addWidget(QLabel("Format:"), 0, 0)
        self.record_format_combo = QComboBox()
        self.record_format_combo.addItems(["png", "jpg"])
        self.record_format_combo.setCurrentText(self.record_format)
        format_layout.addWidget(self.record_format_combo, 0, 1)
        
        group_layout.addLayout(format_layout)
        
        # Quality slider
        quality_layout = QVBoxLayout()
        quality_layout.setSpacing(5)
        
        quality_header = QHBoxLayout()
        quality_label = QLabel("Quality:")
        self.quality_value_label = QLabel(f"{self.record_quality}%")
        self.quality_value_label.setStyleSheet("QLabel { color: #c2785a; font-weight: bold; }")
        quality_header.addWidget(quality_label)
        quality_header.addStretch()
        quality_header.addWidget(self.quality_value_label)
        quality_layout.addLayout(quality_header)
        
        self.quality_slider = QSlider(Qt.Orientation.Horizontal)
        self.quality_slider.setMinimum(50)
        self.quality_slider.setMaximum(100)
        self.quality_slider.setValue(self.record_quality)
        self.quality_slider.valueChanged.connect(
            lambda v: self.quality_value_label.setText(f"{v}%")
        )
        quality_layout.addWidget(self.quality_slider)
        
        group_layout.addLayout(quality_layout)
        
        layout.addWidget(group)
    
    def _create_frame_management(self, layout):
        """Create frame management section."""
        group = QGroupBox("Frame Management")
        group_layout = QHBoxLayout(group)
        group_layout.setSpacing(15)
        
        # Frame count
        count_layout = QVBoxLayout()
        count_label = QLabel("Recorded Frames:")
        count_label.setStyleSheet("QLabel { color: #8b7355; font-size: 10px; }")
        count_layout.addWidget(count_label)
        
        self.frame_count_label = QLabel("0")
        self.frame_count_label.setStyleSheet("""
            QLabel {
                color: #c2785a;
                font-size: 20px;
                font-weight: bold;
            }
        """)
        count_layout.addWidget(self.frame_count_label)
        count_layout.addStretch()
        
        group_layout.addLayout(count_layout)
        
        # Buttons
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(8)
        
        btn_row1 = QHBoxLayout()
        btn_row1.setSpacing(8)
        
        clear_btn = QPushButton("🗑️ Clear Frames")
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #d97766;
                color: white;
                border-radius: 6px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #c85d4d;
            }
        """)
        clear_btn.clicked.connect(self._clear_frames)
        btn_row1.addWidget(clear_btn)
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setIcon(load_icon("refresh"))
        refresh_btn.clicked.connect(self._update_frame_count)
        btn_row1.addWidget(refresh_btn)
        
        btn_layout.addLayout(btn_row1)
        
        btn_row2 = QHBoxLayout()
        btn_row2.setSpacing(8)
        
        generate_btn = QPushButton("🎥 Generate Video")
        generate_btn.setStyleSheet("""
            QPushButton {
                background-color: #8fad88;
                color: white;
                border-radius: 6px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #7a9773;
            }
        """)
        generate_btn.clicked.connect(self._generate_video)
        btn_row2.addWidget(generate_btn)
        
        open_folder_btn = QPushButton("Open Frames Folder")
        open_folder_btn.setIcon(load_icon("folder"))
        open_folder_btn.clicked.connect(self._open_frames_folder)
        btn_row2.addWidget(open_folder_btn)
        
        btn_layout.addLayout(btn_row2)
        
        group_layout.addLayout(btn_layout, 1)
        
        layout.addWidget(group)
    
    def _create_launch_button(self, layout):
        """Create launch button."""
        launch_btn = QPushButton("🚀 LAUNCH SIMULATION")
        launch_btn.setStyleSheet("""
            QPushButton {
                background-color: #c2785a;
                color: white;
                font-size: 16px;
                font-weight: bold;
                padding: 15px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #a85d44;
            }
            QPushButton:pressed {
                background-color: #8f4e36;
            }
        """)
        launch_btn.clicked.connect(self._launch_simulation)
        layout.addWidget(launch_btn)
    
    def _create_status_bar(self, layout):
        """Create status bar."""
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #e8ddd0;
                color: #6b5444;
                padding: 8px 12px;
                border-radius: 4px;
                font-size: 10px;
            }
        """)
        layout.addWidget(self.status_label)
    
    def _update_status(self, message):
        """Update status bar message."""
        self.status_label.setText(message)
    
    def _set_resolution(self, width, height):
        """Set resolution preset."""
        self.width_input.setText(str(width))
        self.height_input.setText(str(height))
        self._update_status(f"Resolution set to {width}x{height}")
    
    def _choose_color(self, color_type):
        """Open color picker dialog."""
        from PySide6.QtWidgets import QColorDialog
        from PySide6.QtGui import QColor
        
        if color_type == 'canvas':
            current_color = QColor(self.canvas_color)
        elif color_type == 'thread':
            current_color = QColor(self.thread_color)
        else:  # nail
            current_color = QColor(self.nail_color)
        
        color = QColorDialog.getColor(current_color, self, f"Choose {color_type.title()} Color")
        
        if color.isValid():
            color_hex = color.name()
            if color_type == 'canvas':
                self.canvas_color = color_hex
                self.canvas_color_btn.setText(color_hex)
                self.canvas_color_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {color_hex};
                        color: white;
                        border: 1px solid #d4c4b0;
                    }}
                """)
            elif color_type == 'thread':
                self.thread_color = color_hex
                self.thread_color_btn.setText(color_hex)
                text_color = "black" if color.lightness() > 128 else "white"
                self.thread_color_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {color_hex};
                        color: {text_color};
                        border: 1px solid #d4c4b0;
                    }}
                """)
            else:  # nail
                self.nail_color = color_hex
                self.nail_color_btn.setText(color_hex)
                text_color = "black" if color.lightness() > 128 else "white"
                self.nail_color_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {color_hex};
                        color: {text_color};
                        border: 1px solid #d4c4b0;
                    }}
                """)
            
            self._update_status(f"{color_type.title()} color updated")
    
    def _update_frame_count(self):
        """Update frame count label."""
        try:
            frames = list(FRAMES_FOLDER.glob("frame_*.png"))
            count = len(frames)
            self.frame_count_label.setText(str(count))
        except Exception:
            self.frame_count_label.setText("0")
    
    def _clear_frames(self):
        """Clear all recorded frames."""
        reply = QMessageBox.question(
            self,
            "Clear Frames",
            "Are you sure you want to delete all recorded frames?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                for frame in FRAMES_FOLDER.glob("frame_*.png"):
                    frame.unlink()
                self._update_frame_count()
                self._update_status("All frames cleared")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to clear frames: {e}")
    
    def _open_frames_folder(self):
        """Open frames folder in file explorer."""
        try:
            if sys.platform == 'win32':
                os.startfile(str(FRAMES_FOLDER))
            elif sys.platform == 'darwin':
                subprocess.run(['open', str(FRAMES_FOLDER)])
            else:
                subprocess.run(['xdg-open', str(FRAMES_FOLDER)])
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open folder: {e}")
    
    def _generate_video(self):
        """Generate video from frames."""
        frames = list(FRAMES_FOLDER.glob("frame_*.png"))
        if not frames:
            QMessageBox.warning(
                self,
                "No Frames",
                "No frames found. Please run the simulation first."
            )
            return
        
        # FPS is always 60
        sim_fps = 60
        
        frame_count = len(frames)
        expected_duration = frame_count / sim_fps
        
        # Ask user for video generation confirmation
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle("Generate Video")
        msg.setText(
            f"<b>Video Generation Settings:</b><br><br>"
            f"• Captured frames: {frame_count}<br>"
            f"• Simulation FPS: <b>60 (locked)</b><br>"
            f"• Video duration: {expected_duration:.1f} seconds<br>"
            f"• Output FPS: <b>60 FPS</b> (smooth playback)<br><br>"
            f"<i>Note: Video will be 60 FPS while preserving the original<br>"
            f"{expected_duration:.1f}-second duration.</i>"
        )
        
        msg.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
        
        if msg.exec() != QMessageBox.StandardButton.Ok:
            return  # Cancelled
        
        # Get quality CRF value
        quality_map = {"low": 28, "medium": 23, "high": 18}
        quality_crf = quality_map.get(str(self.quality_slider.value()), 18)
        
        # Generate output filename in output/videos directory
        output_dir = BASE_DIR / "output" / "videos"
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_path = output_dir / f"string_art_{timestamp}_60fps.mp4"
        
        # Start video generation thread
        self.video_thread = VideoGenerationThread(
            FRAMES_FOLDER,
            output_path,
            sim_fps,  # Input framerate
            quality_crf,
            output_fps=60,  # Output framerate (always 60)
            motion_blur=self.motion_blur_toggle.isChecked()
        )
        self.video_thread.finished.connect(self._on_video_finished)
        self.video_thread.error.connect(self._on_video_error)
        self.video_thread.start()
        
        self._update_status("Generating 60 FPS video...")
    
    def _on_video_finished(self, output_path):
        """Handle video generation completion."""
        self._update_status(f"Video saved: {Path(output_path).name}")
        QMessageBox.information(
            self,
            "Video Generated",
            f"Video saved successfully:\n{output_path}"
        )
    
    def _on_video_error(self, error_msg):
        """Handle video generation error."""
        self._update_status("Video generation failed")
        QMessageBox.critical(self, "Video Generation Error", error_msg)
    
    def _update_ui_from_settings(self):
        """Update UI widgets from current settings."""
        self.width_input.setText(str(self.width))
        self.height_input.setText(str(self.height))
        self.fullscreen_toggle.setChecked(self.fullscreen)
        
        # Algorithm settings
        self.nail_count_spin.setValue(self.nail_count)
        self.max_lines_spin.setValue(self.max_lines)
        self.thread_opacity_slider.setValue(int(self.thread_opacity * 100))
        self.brightness_slider.setValue(int(self.brightness_reduction * 100))
        self.min_distance_spin.setValue(self.min_distance)
        
        # Canvas settings
        self.canvas_color_btn.setText(self.canvas_color)
        self.canvas_color_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.canvas_color};
                color: white;
                border: 1px solid #d4c4b0;
            }}
        """)
        
        self.thread_color_btn.setText(self.thread_color)
        self.thread_color_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.thread_color};
                color: black;
                border: 1px solid #d4c4b0;
            }}
        """)
        
        self.nail_color_btn.setText(self.nail_color)
        self.nail_color_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.nail_color};
                color: black;
                border: 1px solid #d4c4b0;
            }}
        """)
        self.nail_radius_spin.setValue(self.nail_radius)
        
        # Optimization settings
        self.gpu_toggle.setChecked(self.use_gpu)
        self.convergence_slider.setValue(int(self.convergence_threshold * 10000))
        self.lookahead_spin.setValue(self.lookahead_nails)
        
        # Animation settings
        self.manim_toggle.setChecked(self.use_manim)
        self.thread_accum_toggle.setChecked(self.show_thread_accumulation)
        self.nail_numbers_toggle.setChecked(self.show_nail_numbers)
        self.camera_follow_toggle.setChecked(self.camera_follow_thread)
        self.zoom_slider.setValue(int(self.zoom_level * 10))
        
        # Speed control
        self.duration_input.setText(str(self.target_duration))
        self.speed_slider.setValue(int(self.animation_speed * 10))
        
        # Recording settings
        self.auto_record_toggle.setChecked(self.record)
        self.record_format_combo.setCurrentText(self.record_format)
        self.quality_slider.setValue(self.record_quality)
        
        # Visual effects
        self.glow_toggle.setChecked(self.glow_effect)
        self.motion_blur_toggle.setChecked(self.motion_blur)
        self.progress_bar_toggle.setChecked(self.show_progress_bar)
        self.theme_combo.setCurrentText(self.theme)
        
        # Border settings
        self.show_border_toggle.setChecked(self.show_border)
        self.border_width_slider.setValue(self.border_width)
    
    def _launch_simulation(self):
        """Launch the simulation."""
        # Validate inputs
        image_path = self.image_upload_widget.get_image_path()
        if not image_path:
            QMessageBox.warning(
                self,
                "No Image",
                "Please upload a portrait image first."
            )
            return
        
        try:
            width = int(self.width_input.text())
            height = int(self.height_input.text())
            fps = 60  # Locked at 60
        except ValueError:
            QMessageBox.critical(
                self,
                "Invalid Input",
                "Width and Height must be valid integers."
            )
            return
        
        # Get target duration
        try:
            target_duration = float(self.duration_input.text())
            if target_duration <= 0:
                raise ValueError("Duration must be positive")
        except ValueError:
            QMessageBox.critical(
                self,
                "Invalid Duration",
                "Please enter a valid positive number for duration (in seconds)."
            )
            return
        
        # Build command
        cmd = [
            sys.executable,
            str(SIMULATION_DIR / "main.py"),
            "--width", str(width),
            "--height", str(height),
            "--image", image_path,
            "--nail-count", str(self.nail_count_spin.value()),
            "--max-lines", str(self.max_lines_spin.value()),
            "--thread-opacity", str(self.thread_opacity_slider.value() / 100.0),
            "--brightness-reduction", str(self.brightness_slider.value() / 100.0),
            "--min-distance", str(self.min_distance_spin.value()),
            "--canvas-color", self.canvas_color,
            "--thread-color", self.thread_color,
            "--nail-color", self.nail_color,
            "--nail-radius", str(self.nail_radius_spin.value()),
            "--convergence", str(self.convergence_slider.value() / 10000.0),
            "--lookahead", str(self.lookahead_spin.value()),
            "--zoom", str(self.zoom_slider.value() / 10.0),
            "--target-duration", str(target_duration),
            "--speed", str(self.speed_slider.value() / 10.0),
            "--quality", str(self.quality_slider.value()),
            "--theme", self.theme_combo.currentText(),
            "--border-width", str(self.border_width_slider.value())
        ]
        
        # Add conditional flags
        if self.fullscreen_toggle.isChecked():
            cmd.append("--fullscreen")
        
        if not self.auto_record_toggle.isChecked():
            cmd.append("--no-record")
        
        if not self.gpu_toggle.isChecked():
            cmd.append("--no-gpu")
        
        if self.manim_toggle.isChecked():
            cmd.append("--use-manim")
        
        if self.thread_accum_toggle.isChecked():
            cmd.append("--show-accumulation")
        
        if self.nail_numbers_toggle.isChecked():
            cmd.append("--show-nail-numbers")
        
        if self.camera_follow_toggle.isChecked():
            cmd.append("--camera-follow")
        
        if self.glow_toggle.isChecked():
            cmd.append("--glow")
        
        if self.motion_blur_toggle.isChecked():
            cmd.append("--motion-blur")
        
        if self.progress_bar_toggle.isChecked():
            cmd.append("--progress-bar")
        
        if self.show_border_toggle.isChecked():
            cmd.append("--show-border")
        
        # Launch in thread
        def run_simulation():
            try:
                self.simulation_process = subprocess.Popen(
                    cmd,
                    cwd=str(SIMULATION_DIR)
                )
                self.simulation_process.wait()
                self._update_status("Simulation completed")
                self._update_frame_count()
            except Exception as e:
                self._update_status(f"Simulation error: {str(e)}")
        
        thread = threading.Thread(target=run_simulation, daemon=True)
        thread.start()
        
        self._update_status("Simulation launched...")


def main():
    """Main entry point."""
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    window = ControlPanel()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
