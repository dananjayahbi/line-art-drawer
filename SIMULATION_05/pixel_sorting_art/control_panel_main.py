#!/usr/bin/env python3
"""
Pixel Sorting Art - Control Panel Main Window (PySide6)
========================================================
Main control panel window implementation for the pixel sorting art simulation.
Features vaporwave/cyberpunk dark theme with magenta and cyan accents.
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
    QRadioButton, QProgressBar, QDoubleSpinBox
)
from PySide6.QtCore import Qt, Signal, QTimer, QThread, QUrl, QSize, QPoint
from PySide6.QtGui import QPixmap, QDragEnterEvent, QDropEvent, QIcon, QFont, QPainter, QPen, QColor, QMouseEvent

# Import modularized components
from settings_manager import SettingsManager
from custom_widgets import (
    ToggleSwitch, ImageUploadWidget, ColorStyleSelector,
    SortingAlgorithmSelector, SortDirectionSelector, SortCriteriaSelector,
    load_icon, THEME
)
from video_thread import VideoGenerationThread, get_quality_crf

# Get paths
SIMULATION_DIR = Path(__file__).resolve().parent
BASE_DIR = SIMULATION_DIR.parent
FRAMES_FOLDER = SIMULATION_DIR / "frames"
UPLOADS_FOLDER = SIMULATION_DIR / "uploads"
ICONS_FOLDER = SIMULATION_DIR / "assets" / "icons"


class ControlPanel(QMainWindow):
    """Main control panel window with vaporwave/cyberpunk theme."""
    
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
        self._update_ui_from_settings()
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
        
        # Sorting settings
        self.sorting_algorithm = "quick_sort"
        self.sort_direction = "horizontal"
        self.sort_criteria = "brightness"
        self.threshold = 0.3
        
        # Duration settings
        self.target_duration = 30.0
        
        # Visual settings
        self.color_style = "vaporwave"
        self.neon_glow_intensity = 0.8
        self.motion_blur_strength = 0.3
        self.beat_drop_time = 15.0
        self.zoom_intensity = 0.1
        
        # Recording settings
        self.auto_record = False
        self.video_fps = 60
        self.video_quality = "high"
        
        # GPU settings
        self.use_gpu = True
    
    def _load_settings(self):
        """Load all settings from file."""
        settings = self.settings_manager.load_settings()
        
        self.width = int(settings.get("width", "1080"))
        self.height = int(settings.get("height", "1920"))
        self.fps = 60  # Always 60
        self.target_duration = float(settings.get("target_duration", "30.0"))
        
        # Sorting settings
        self.sorting_algorithm = settings.get("sorting_algorithm", "quick_sort")
        self.sort_direction = settings.get("sort_direction", "horizontal")
        self.sort_criteria = settings.get("sort_criteria", "brightness")
        self.threshold = float(settings.get("threshold", 0.3))
        
        # Visual settings
        self.color_style = settings.get("color_style", "vaporwave")
        self.neon_glow_intensity = float(settings.get("neon_glow_intensity", 0.8))
        self.motion_blur_strength = float(settings.get("motion_blur_strength", 0.3))
        self.beat_drop_time = float(settings.get("beat_drop_time", 15.0))
        self.zoom_intensity = float(settings.get("zoom_intensity", 0.1))
        
        # Recording settings
        self.auto_record = settings.get("auto_record", False)
        self.video_fps = 60  # Always 60
        self.video_quality = settings.get("video_quality", "high")
        
        # GPU settings
        self.use_gpu = settings.get("use_gpu", True)
    
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
            target_duration = 30.0
        
        settings = {
            "width": str(width),
            "height": str(height),
            "fps": "60",
            "target_duration": str(target_duration),
            
            # Sorting settings
            "sorting_algorithm": self.algorithm_selector.get_algorithm(),
            "sort_direction": self.direction_selector.get_direction(),
            "sort_criteria": self.criteria_selector.get_criteria(),
            "threshold": str(self.threshold_slider.value() / 100.0),
            
            # Visual settings
            "color_style": self.color_style_selector.get_style(),
            "neon_glow_intensity": str(self.glow_slider.value() / 100.0),
            "motion_blur_strength": str(self.blur_slider.value() / 100.0),
            "beat_drop_time": str(self.beat_drop_input.value()),
            "zoom_intensity": str(self.zoom_slider.value() / 100.0),
            
            # Recording settings
            "auto_record": self.auto_record_toggle.isChecked(),
            "video_fps": "60",
            "video_quality": self.video_quality_combo.currentText().lower(),
            
            # GPU settings
            "use_gpu": self.gpu_toggle.isChecked(),
        }
        
        if self.settings_manager.save_settings(settings):
            self._update_status("✨ Settings saved successfully!")
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
            self._update_status("🔄 Settings reset to defaults")
            QMessageBox.information(self, "Reset Complete", "All settings have been reset to defaults.")
    
    def _setup_ui(self):
        """Setup the main UI."""
        self.setWindowTitle("Pixel Sorting Art - Control Panel")
        self.setMinimumSize(1366, 768)
        self.setMaximumSize(1920, 1080)
        # Open as maximized window
        self.showMaximized()
        
        # Set vaporwave/cyberpunk dark theme
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {THEME['background']};
            }}
            QWidget {{
                background-color: {THEME['background']};
                color: {THEME['text']};
                font-family: 'Segoe UI', 'Consolas', Arial, sans-serif;
                font-size: 11px;
            }}
            QGroupBox {{
                background-color: {THEME['surface']};
                border: 1px solid {THEME['surface_light']};
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 20px;
                font-weight: bold;
                color: {THEME['accent_primary']};
                font-size: 12px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 5px 10px;
                color: {THEME['accent_primary']};
            }}
            QLabel {{
                color: {THEME['text']};
                background-color: transparent;
            }}
            QLineEdit, QSpinBox, QDoubleSpinBox {{
                background-color: {THEME['surface']};
                border: 1px solid {THEME['surface_light']};
                border-radius: 4px;
                padding: 6px;
                color: {THEME['text']};
            }}
            QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
                border: 1px solid {THEME['accent_primary']};
            }}
            QSlider::groove:horizontal {{
                height: 6px;
                background: {THEME['surface_light']};
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background: {THEME['accent_primary']};
                width: 16px;
                height: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }}
            QSlider::handle:horizontal:hover {{
                background: {THEME['accent_secondary']};
            }}
            QSlider::sub-page:horizontal {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {THEME['accent_primary']}, stop:1 {THEME['accent_secondary']});
                border-radius: 3px;
            }}
            QComboBox {{
                background-color: {THEME['surface']};
                border: 1px solid {THEME['surface_light']};
                border-radius: 4px;
                padding: 6px;
                color: {THEME['text']};
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid {THEME['accent_primary']};
                width: 0;
                height: 0;
            }}
            QComboBox QAbstractItemView {{
                background-color: {THEME['surface']};
                border: 1px solid {THEME['surface_light']};
                selection-background-color: {THEME['accent_primary']};
                color: {THEME['text']};
            }}
            QPushButton {{
                background-color: {THEME['surface_light']};
                color: {THEME['text']};
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 11px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {THEME['accent_primary']};
                color: white;
            }}
            QPushButton:pressed {{
                background-color: #990099;
            }}
            QScrollArea {{
                border: none;
            }}
            QScrollBar:vertical {{
                background-color: {THEME['surface']};
                width: 12px;
                border-radius: 6px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {THEME['accent_primary']};
                border-radius: 6px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {THEME['accent_secondary']};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QProgressBar {{
                background-color: {THEME['surface']};
                border: 1px solid {THEME['surface_light']};
                border-radius: 4px;
                text-align: center;
                color: {THEME['text']};
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {THEME['accent_primary']}, stop:1 {THEME['accent_secondary']});
                border-radius: 3px;
            }}
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
        left_column.addStretch()
        columns_layout.addLayout(left_column, 1)
        
        # Middle column
        middle_column = QVBoxLayout()
        middle_column.setSpacing(15)
        self._create_sorting_settings(middle_column)
        self._create_animation_settings(middle_column)
        middle_column.addStretch()
        columns_layout.addLayout(middle_column, 1)
        
        # Right column
        right_column = QVBoxLayout()
        right_column.setSpacing(15)
        self._create_visual_effects(right_column)
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
        title_label = QLabel("🌆 Pixel Sorting Art")
        title_label.setStyleSheet(f"""
            QLabel {{
                font-size: 28px;
                font-weight: bold;
                color: {THEME['accent_primary']};
            }}
        """)
        title_layout.addWidget(title_label)
        
        subtitle_label = QLabel("Vaporwave • Cyberpunk • Glitch Art Generator")
        subtitle_label.setStyleSheet(f"""
            QLabel {{
                font-size: 12px;
                color: {THEME['accent_secondary']};
            }}
        """)
        title_layout.addWidget(subtitle_label)
        
        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        
        # Save/Reset buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        save_btn = QPushButton("💾 Save Settings")
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {THEME['accent_primary']}, stop:1 #cc00cc);
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                font-size: 12px;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #cc00cc, stop:1 {THEME['accent_secondary']});
            }}
        """)
        save_btn.clicked.connect(self._save_settings)
        btn_layout.addWidget(save_btn)
        
        reset_btn = QPushButton("🔄 Reset to Defaults")
        reset_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {THEME['surface_light']};
                color: {THEME['text']};
                padding: 10px 20px;
                font-size: 12px;
                border-radius: 6px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {THEME['accent_secondary']};
                color: {THEME['background']};
            }}
        """)
        reset_btn.clicked.connect(self._reset_to_defaults)
        btn_layout.addWidget(reset_btn)
        
        header_layout.addLayout(btn_layout)
        
        layout.addLayout(header_layout)
    
    def _create_image_upload_section(self, layout):
        """Create image upload section."""
        group = QGroupBox("📷 Source Image")
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(10)
        
        info_label = QLabel("Upload an image for pixel sorting effect")
        info_label.setStyleSheet(f"QLabel {{ color: {THEME['text_muted']}; font-size: 10px; }}")
        group_layout.addWidget(info_label)
        
        self.image_upload_widget = ImageUploadWidget(UPLOADS_FOLDER)
        self.image_upload_widget.imageUploaded.connect(
            lambda filename: self._update_status(f"📷 Loaded: {filename}")
        )
        self.image_upload_widget.imageCleared.connect(
            lambda: self._update_status("🗑️ Image cleared")
        )
        group_layout.addWidget(self.image_upload_widget)
        
        layout.addWidget(group)
    
    def _create_window_settings(self, layout):
        """Create window settings section."""
        group = QGroupBox("🖥️ Window Settings")
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
        fps_label.setStyleSheet(f"QLabel {{ color: {THEME['accent_secondary']}; }}")
        fps_label.setMaximumWidth(120)
        size_layout.addWidget(fps_label, 1, 1, 1, 2)
        
        group_layout.addLayout(size_layout)
        
        # Presets for 9:16 vertical
        presets_layout = QHBoxLayout()
        presets_layout.setSpacing(8)
        
        preset_label = QLabel("Presets:")
        presets_layout.addWidget(preset_label)
        
        presets = [
            ("9:16 (1080x1920)", 1080, 1920),
            ("9:16 (720x1280)", 720, 1280),
            ("1:1 (1080x1080)", 1080, 1080),
            ("16:9 (1920x1080)", 1920, 1080),
        ]
        
        for name, w, h in presets:
            btn = QPushButton(name)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {THEME['surface_light']};
                    padding: 5px 8px;
                    font-size: 9px;
                }}
                QPushButton:hover {{
                    background-color: {THEME['accent_primary']};
                }}
            """)
            btn.clicked.connect(lambda checked, w=w, h=h: self._set_resolution(w, h))
            presets_layout.addWidget(btn)
        
        presets_layout.addStretch()
        group_layout.addLayout(presets_layout)
        
        layout.addWidget(group)
    
    def _create_sorting_settings(self, layout):
        """Create sorting algorithm settings section."""
        group = QGroupBox("⚡ Sorting Settings")
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(12)
        
        # Algorithm selector
        algo_layout = QHBoxLayout()
        algo_label = QLabel("Algorithm:")
        self.algorithm_selector = SortingAlgorithmSelector()
        algo_layout.addWidget(algo_label)
        algo_layout.addStretch()
        algo_layout.addWidget(self.algorithm_selector)
        group_layout.addLayout(algo_layout)
        
        # Direction selector
        dir_layout = QHBoxLayout()
        dir_label = QLabel("Direction:")
        self.direction_selector = SortDirectionSelector()
        dir_layout.addWidget(dir_label)
        dir_layout.addStretch()
        dir_layout.addWidget(self.direction_selector)
        group_layout.addLayout(dir_layout)
        
        # Criteria selector
        crit_layout = QHBoxLayout()
        crit_label = QLabel("Sort By:")
        self.criteria_selector = SortCriteriaSelector()
        crit_layout.addWidget(crit_label)
        crit_layout.addStretch()
        crit_layout.addWidget(self.criteria_selector)
        group_layout.addLayout(crit_layout)
        
        # Threshold slider
        threshold_layout = QVBoxLayout()
        threshold_layout.setSpacing(5)
        
        threshold_header = QHBoxLayout()
        threshold_label = QLabel("Threshold / Intensity:")
        self.threshold_value_label = QLabel(f"{int(self.threshold * 100)}%")
        self.threshold_value_label.setStyleSheet(f"QLabel {{ color: {THEME['accent_primary']}; font-weight: bold; }}")
        threshold_header.addWidget(threshold_label)
        threshold_header.addStretch()
        threshold_header.addWidget(self.threshold_value_label)
        threshold_layout.addLayout(threshold_header)
        
        self.threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.threshold_slider.setMinimum(0)
        self.threshold_slider.setMaximum(100)
        self.threshold_slider.setValue(int(self.threshold * 100))
        self.threshold_slider.valueChanged.connect(
            lambda v: self.threshold_value_label.setText(f"{v}%")
        )
        threshold_layout.addWidget(self.threshold_slider)
        
        group_layout.addLayout(threshold_layout)
        
        layout.addWidget(group)
    
    def _create_animation_settings(self, layout):
        """Create animation timing settings section."""
        group = QGroupBox("⏱️ Animation Settings")
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(12)
        
        # Target Duration
        duration_layout = QGridLayout()
        duration_layout.setSpacing(10)
        
        duration_label = QLabel("Target Duration:")
        duration_label.setToolTip("Set the total duration for the animation")
        duration_layout.addWidget(duration_label, 0, 0)
        
        self.duration_input = QLineEdit(str(self.target_duration))
        self.duration_input.setMaximumWidth(80)
        self.duration_input.setPlaceholderText("seconds")
        duration_layout.addWidget(self.duration_input, 0, 1)
        
        duration_unit_label = QLabel("seconds")
        duration_layout.addWidget(duration_unit_label, 0, 2)
        
        duration_info = QLabel("ℹ️ Animation speed auto-adjusts to match this duration")
        duration_info.setStyleSheet(f"QLabel {{ color: {THEME['text_muted']}; font-size: 10px; }}")
        duration_info.setWordWrap(True)
        duration_layout.addWidget(duration_info, 1, 0, 1, 3)
        
        group_layout.addLayout(duration_layout)
        
        # GPU Acceleration
        gpu_layout = QHBoxLayout()
        gpu_label = QLabel("GPU Acceleration")
        self.gpu_toggle = ToggleSwitch()
        self.gpu_toggle.setChecked(self.use_gpu)
        gpu_layout.addWidget(gpu_label)
        gpu_layout.addStretch()
        gpu_layout.addWidget(self.gpu_toggle)
        group_layout.addLayout(gpu_layout)
        
        layout.addWidget(group)
    
    def _create_visual_effects(self, layout):
        """Create visual effects settings section."""
        group = QGroupBox("🎨 Visual Effects")
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(12)
        
        # Color Style selector
        style_layout = QHBoxLayout()
        style_label = QLabel("Color Style:")
        self.color_style_selector = ColorStyleSelector()
        style_layout.addWidget(style_label)
        style_layout.addStretch()
        style_layout.addWidget(self.color_style_selector)
        group_layout.addLayout(style_layout)
        
        # Glow Intensity
        glow_layout = QVBoxLayout()
        glow_layout.setSpacing(5)
        
        glow_header = QHBoxLayout()
        glow_label = QLabel("Neon Glow Intensity:")
        self.glow_value_label = QLabel(f"{int(self.neon_glow_intensity * 100)}%")
        self.glow_value_label.setStyleSheet(f"QLabel {{ color: {THEME['accent_secondary']}; font-weight: bold; }}")
        glow_header.addWidget(glow_label)
        glow_header.addStretch()
        glow_header.addWidget(self.glow_value_label)
        glow_layout.addLayout(glow_header)
        
        self.glow_slider = QSlider(Qt.Orientation.Horizontal)
        self.glow_slider.setMinimum(0)
        self.glow_slider.setMaximum(100)
        self.glow_slider.setValue(int(self.neon_glow_intensity * 100))
        self.glow_slider.valueChanged.connect(
            lambda v: self.glow_value_label.setText(f"{v}%")
        )
        glow_layout.addWidget(self.glow_slider)
        
        group_layout.addLayout(glow_layout)
        
        # Beat Drop Time
        beat_layout = QHBoxLayout()
        beat_label = QLabel("Beat Drop Time:")
        self.beat_drop_input = QDoubleSpinBox()
        self.beat_drop_input.setRange(0.0, 120.0)
        self.beat_drop_input.setValue(self.beat_drop_time)
        self.beat_drop_input.setSuffix(" sec")
        self.beat_drop_input.setMaximumWidth(100)
        beat_layout.addWidget(beat_label)
        beat_layout.addStretch()
        beat_layout.addWidget(self.beat_drop_input)
        group_layout.addLayout(beat_layout)
        
        # Zoom Intensity
        zoom_layout = QVBoxLayout()
        zoom_layout.setSpacing(5)
        
        zoom_header = QHBoxLayout()
        zoom_label = QLabel("Zoom Intensity:")
        self.zoom_value_label = QLabel(f"{int(self.zoom_intensity * 100)}%")
        self.zoom_value_label.setStyleSheet(f"QLabel {{ color: {THEME['accent_primary']}; font-weight: bold; }}")
        zoom_header.addWidget(zoom_label)
        zoom_header.addStretch()
        zoom_header.addWidget(self.zoom_value_label)
        zoom_layout.addLayout(zoom_header)
        
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setMinimum(0)
        self.zoom_slider.setMaximum(100)
        self.zoom_slider.setValue(int(self.zoom_intensity * 100))
        self.zoom_slider.valueChanged.connect(
            lambda v: self.zoom_value_label.setText(f"{v}%")
        )
        zoom_layout.addWidget(self.zoom_slider)
        
        group_layout.addLayout(zoom_layout)
        
        # Motion Blur
        blur_layout = QVBoxLayout()
        blur_layout.setSpacing(5)
        
        blur_header = QHBoxLayout()
        blur_label = QLabel("Motion Blur:")
        self.blur_value_label = QLabel(f"{int(self.motion_blur_strength * 100)}%")
        self.blur_value_label.setStyleSheet(f"QLabel {{ color: {THEME['accent_secondary']}; font-weight: bold; }}")
        blur_header.addWidget(blur_label)
        blur_header.addStretch()
        blur_header.addWidget(self.blur_value_label)
        blur_layout.addLayout(blur_header)
        
        self.blur_slider = QSlider(Qt.Orientation.Horizontal)
        self.blur_slider.setMinimum(0)
        self.blur_slider.setMaximum(100)
        self.blur_slider.setValue(int(self.motion_blur_strength * 100))
        self.blur_slider.valueChanged.connect(
            lambda v: self.blur_value_label.setText(f"{v}%")
        )
        blur_layout.addWidget(self.blur_slider)
        
        group_layout.addLayout(blur_layout)
        
        layout.addWidget(group)
    
    def _create_recording_settings(self, layout):
        """Create recording settings section."""
        group = QGroupBox("🎥 Recording Settings")
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(12)
        
        # Auto-start Recording
        auto_layout = QHBoxLayout()
        auto_label = QLabel("Auto-start Recording")
        self.auto_record_toggle = ToggleSwitch()
        self.auto_record_toggle.setChecked(self.auto_record)
        auto_layout.addWidget(auto_label)
        auto_layout.addStretch()
        auto_layout.addWidget(self.auto_record_toggle)
        group_layout.addLayout(auto_layout)
        
        # Video Quality setting
        video_settings_layout = QGridLayout()
        video_settings_layout.setSpacing(10)
        
        video_settings_layout.addWidget(QLabel("Output FPS:"), 0, 0)
        fps_info = QLabel("<b>60 FPS</b> (smooth)")
        fps_info.setStyleSheet(f"QLabel {{ color: {THEME['accent_secondary']}; }}")
        video_settings_layout.addWidget(fps_info, 0, 1)
        
        video_settings_layout.addWidget(QLabel("Quality:"), 1, 0)
        self.video_quality_combo = QComboBox()
        self.video_quality_combo.addItems(["Low", "Medium", "High", "Ultra"])
        self.video_quality_combo.setCurrentText(self.video_quality.title())
        video_settings_layout.addWidget(self.video_quality_combo, 1, 1)
        
        group_layout.addLayout(video_settings_layout)
        
        layout.addWidget(group)
    
    def _create_frame_management(self, layout):
        """Create frame management section."""
        group = QGroupBox("🎞️ Frame Management")
        group_layout = QHBoxLayout(group)
        group_layout.setSpacing(15)
        
        # Frame count
        count_layout = QVBoxLayout()
        count_label = QLabel("Recorded Frames:")
        count_label.setStyleSheet(f"QLabel {{ color: {THEME['text_muted']}; font-size: 10px; }}")
        count_layout.addWidget(count_label)
        
        self.frame_count_label = QLabel("0")
        self.frame_count_label.setStyleSheet(f"""
            QLabel {{
                color: {THEME['accent_primary']};
                font-size: 24px;
                font-weight: bold;
            }}
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
        clear_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {THEME['error']};
                color: white;
                border-radius: 6px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: #ff2244;
            }}
        """)
        clear_btn.clicked.connect(self._clear_frames)
        btn_row1.addWidget(clear_btn)
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setIcon(load_icon("refresh"))
        refresh_btn.clicked.connect(self._update_frame_count)
        btn_row1.addWidget(refresh_btn)
        
        btn_layout.addLayout(btn_row1)
        
        btn_row2 = QHBoxLayout()
        btn_row2.setSpacing(8)
        
        generate_btn = QPushButton("🎥 Generate Video")
        generate_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {THEME['success']};
                color: {THEME['background']};
                border-radius: 6px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: #00cc66;
            }}
        """)
        generate_btn.clicked.connect(self._generate_video)
        btn_row2.addWidget(generate_btn)
        
        open_folder_btn = QPushButton("📂 Open Folder")
        open_folder_btn.setIcon(load_icon("folder"))
        open_folder_btn.clicked.connect(self._open_frames_folder)
        btn_row2.addWidget(open_folder_btn)
        
        btn_layout.addLayout(btn_row2)
        
        group_layout.addLayout(btn_layout, 1)
        
        layout.addWidget(group)
    
    def _create_launch_button(self, layout):
        """Create launch button."""
        launch_btn = QPushButton("🚀 LAUNCH SIMULATION")
        launch_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {THEME['accent_primary']}, stop:1 {THEME['accent_secondary']});
                color: white;
                font-size: 18px;
                font-weight: bold;
                padding: 18px;
                border-radius: 10px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {THEME['accent_secondary']}, stop:1 {THEME['accent_primary']});
            }}
            QPushButton:pressed {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #990099, stop:1 #009999);
            }}
        """)
        launch_btn.clicked.connect(self._launch_simulation)
        layout.addWidget(launch_btn)
    
    def _create_status_bar(self, layout):
        """Create status bar."""
        status_layout = QHBoxLayout()
        
        self.status_label = QLabel("✨ Ready")
        self.status_label.setStyleSheet(f"""
            QLabel {{
                background-color: {THEME['surface']};
                color: {THEME['text']};
                padding: 8px 12px;
                border-radius: 4px;
                font-size: 11px;
            }}
        """)
        status_layout.addWidget(self.status_label, 1)
        
        # Progress bar (hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumWidth(200)
        status_layout.addWidget(self.progress_bar)
        
        layout.addLayout(status_layout)
    
    def _update_status(self, message):
        """Update status bar message."""
        self.status_label.setText(message)
    
    def _set_resolution(self, width, height):
        """Set resolution preset."""
        self.width_input.setText(str(width))
        self.height_input.setText(str(height))
        self._update_status(f"📐 Resolution set to {width}x{height}")
    
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
                self._update_status("🗑️ All frames cleared")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to clear frames: {e}")
    
    def _open_frames_folder(self):
        """Open frames folder in file explorer."""
        try:
            FRAMES_FOLDER.mkdir(parents=True, exist_ok=True)
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
        
        sim_fps = 60  # Always 60
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
            f"<i>Note: Video will maintain smooth 60 FPS playback.</i>"
        )
        
        msg.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
        
        if msg.exec() != QMessageBox.StandardButton.Ok:
            return
        
        # Get quality CRF value
        quality_crf = get_quality_crf(self.video_quality_combo.currentText())
        
        # Generate output filename in output/videos directory
        output_dir = BASE_DIR / "output" / "videos"
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_path = output_dir / f"pixel_sort_{timestamp}_60fps.mp4"
        
        # Start video generation thread
        self.video_thread = VideoGenerationThread(
            FRAMES_FOLDER,
            output_path,
            sim_fps,
            quality_crf,
            output_fps=60
        )
        self.video_thread.finished.connect(self._on_video_finished)
        self.video_thread.error.connect(self._on_video_error)
        self.video_thread.start()
        
        self._update_status("🎬 Generating 60 FPS video...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
    
    def _on_video_finished(self, output_path):
        """Handle video generation completion."""
        self.progress_bar.setVisible(False)
        self._update_status(f"✅ Video saved: {Path(output_path).name}")
        QMessageBox.information(
            self,
            "Video Generated",
            f"Video saved successfully:\n{output_path}"
        )
    
    def _on_video_error(self, error_msg):
        """Handle video generation error."""
        self.progress_bar.setVisible(False)
        self._update_status("❌ Video generation failed")
        QMessageBox.critical(self, "Video Generation Error", error_msg)
    
    def _update_ui_from_settings(self):
        """Update UI widgets from current settings."""
        self.width_input.setText(str(self.width))
        self.height_input.setText(str(self.height))
        self.duration_input.setText(str(self.target_duration))
        
        # Sorting settings
        self.algorithm_selector.set_algorithm(self.sorting_algorithm)
        self.direction_selector.set_direction(self.sort_direction)
        self.criteria_selector.set_criteria(self.sort_criteria)
        self.threshold_slider.setValue(int(self.threshold * 100))
        
        # Visual settings
        self.color_style_selector.set_style(self.color_style)
        self.glow_slider.setValue(int(self.neon_glow_intensity * 100))
        self.blur_slider.setValue(int(self.motion_blur_strength * 100))
        self.beat_drop_input.setValue(self.beat_drop_time)
        self.zoom_slider.setValue(int(self.zoom_intensity * 100))
        
        # Recording settings
        self.auto_record_toggle.setChecked(self.auto_record)
        self.video_quality_combo.setCurrentText(self.video_quality.title())
        
        # GPU settings
        self.gpu_toggle.setChecked(self.use_gpu)
    
    def _launch_simulation(self):
        """Launch the simulation."""
        # Validate inputs
        image_path = self.image_upload_widget.get_image_path()
        if not image_path:
            QMessageBox.warning(
                self,
                "No Image",
                "Please upload an image first."
            )
            return
        
        try:
            width = int(self.width_input.text())
            height = int(self.height_input.text())
            fps = 60  # Always 60
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
            "--target-duration", str(target_duration),
            "--algorithm", self.algorithm_selector.get_algorithm(),
            "--direction", self.direction_selector.get_direction(),
            "--criteria", self.criteria_selector.get_criteria(),
            "--threshold", str(self.threshold_slider.value() / 100.0),
            "--color-style", self.color_style_selector.get_style(),
            "--glow-intensity", str(self.glow_slider.value() / 100.0),
            "--blur-strength", str(self.blur_slider.value() / 100.0),
            "--beat-drop-time", str(self.beat_drop_input.value()),
            "--zoom-intensity", str(self.zoom_slider.value() / 100.0),
        ]
        
        # Add conditional flags
        if not self.auto_record_toggle.isChecked():
            cmd.append("--no-record")
        
        if not self.gpu_toggle.isChecked():
            cmd.append("--no-gpu")
        
        # Launch in thread
        def run_simulation():
            try:
                self.simulation_process = subprocess.Popen(
                    cmd,
                    cwd=str(SIMULATION_DIR)
                )
                self.simulation_process.wait()
                self._update_status("✅ Simulation completed")
                self._update_frame_count()
            except Exception as e:
                self._update_status(f"❌ Simulation error: {str(e)}")
        
        thread = threading.Thread(target=run_simulation, daemon=True)
        thread.start()
        
        self._update_status("🚀 Simulation launched...")
    
    def closeEvent(self, event):
        """Handle window close event."""
        # Stop refresh timer
        if hasattr(self, 'refresh_timer'):
            self.refresh_timer.stop()
        
        # Terminate simulation process if running
        if self.simulation_process and self.simulation_process.poll() is None:
            self.simulation_process.terminate()
        
        event.accept()


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
