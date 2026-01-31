#!/usr/bin/env python3
"""
Pendulum Paint Art - Control Panel Main Window (PySide6)
==========================================================
Main control panel window implementation for the pendulum paint art simulation.
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
    QFileDialog, QMessageBox, QScrollArea, QFrame, QSpinBox, QDialog, QDoubleSpinBox
)
from PySide6.QtCore import Qt, Signal, QTimer, QThread, QUrl, QSize, QPoint
from PySide6.QtGui import QPixmap, QDragEnterEvent, QDropEvent, QIcon, QFont, QPainter, QPen, QColor, QMouseEvent

# Import modularized components
from settings_manager import SettingsManager
from custom_widgets import ToggleSwitch, ImageUploadWidget, ColorPickerButton, load_icon
from video_thread import VideoGenerationThread

# Get paths
SIMULATION_DIR = Path(__file__).resolve().parent
BASE_DIR = SIMULATION_DIR.parent
FRAMES_FOLDER = SIMULATION_DIR / "frames"
UPLOADS_FOLDER = SIMULATION_DIR / "uploads"
ICONS_FOLDER = SIMULATION_DIR / "assets" / "icons"
OUTPUT_FOLDER = BASE_DIR / "output" / "videos"


class ControlPanel(QMainWindow):
    """Main control panel window."""
    
    def __init__(self):
        super().__init__()
        
        # Ensure folders exist
        UPLOADS_FOLDER.mkdir(parents=True, exist_ok=True)
        FRAMES_FOLDER.mkdir(parents=True, exist_ok=True)
        OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
        
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
        self.refresh_timer.start(2000)
    
    def _init_variables(self):
        """Initialize all settings variables."""
        # Window settings
        self.width = 800
        self.height = 1000
        self.fps = 60
        
        # Animation settings
        self.target_duration = 30.0
        
        # Pendulum settings
        self.pendulum_length = 300
        self.initial_angle_x = 45.0
        self.initial_angle_y = 30.0
        self.damping_x = 0.02
        self.damping_y = 0.02
        self.gravity = 9.8
        
        # Paint settings
        self.drip_rate = 0.15
        self.paint_thickness = 8
        self.viscosity = 0.7
        self.paint_color = "#2c1810"
        
        # Visual settings
        self.show_pendulum = True
        self.show_trails = True
        
        # Recording settings
        self.auto_record = False
        self.video_fps = 60
        self.video_quality = "high"
    
    def _load_settings(self):
        """Load all settings from file."""
        settings = self.settings_manager.load_settings()
        
        self.width = int(settings.get("width", "800"))
        self.height = int(settings.get("height", "1000"))
        self.fps = 60
        self.target_duration = float(settings.get("target_duration", "30.0"))
        
        self.pendulum_length = int(settings.get("pendulum_length", "300"))
        self.initial_angle_x = float(settings.get("initial_angle_x", "45.0"))
        self.initial_angle_y = float(settings.get("initial_angle_y", "30.0"))
        self.damping_x = float(settings.get("damping_x", "0.02"))
        self.damping_y = float(settings.get("damping_y", "0.02"))
        self.gravity = float(settings.get("gravity", "9.8"))
        
        self.drip_rate = float(settings.get("drip_rate", "0.15"))
        self.paint_thickness = int(settings.get("paint_thickness", "8"))
        self.viscosity = float(settings.get("viscosity", "0.7"))
        self.paint_color = settings.get("paint_color", "#2c1810")
        
        self.show_pendulum = settings.get("show_pendulum", True)
        self.show_trails = settings.get("show_trails", True)
        
        self.auto_record = settings.get("auto_record", False)
        self.video_fps = 60
        self.video_quality = settings.get("video_quality", "high")
    
    def _save_settings(self):
        """Save all settings to file."""
        try:
            width = int(self.width_input.text())
            height = int(self.height_input.text())
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Width and Height must be valid integers.")
            return
        
        try:
            target_duration = float(self.duration_input.text())
        except ValueError:
            target_duration = 30.0
        
        settings = {
            "width": str(width),
            "height": str(height),
            "fps": "60",
            "target_duration": str(target_duration),
            "pendulum_length": str(self.length_slider.value()),
            "initial_angle_x": str(self.angle_x_slider.value()),
            "initial_angle_y": str(self.angle_y_slider.value()),
            "damping_x": str(self.damping_x_slider.value() / 1000.0),
            "damping_y": str(self.damping_y_slider.value() / 1000.0),
            "gravity": str(self.gravity_slider.value() / 10.0),
            "drip_rate": str(self.drip_rate_slider.value() / 100.0),
            "paint_thickness": str(self.thickness_slider.value()),
            "viscosity": str(self.viscosity_slider.value() / 100.0),
            "paint_color": self.color_picker.get_color(),
            "show_pendulum": self.show_pendulum_toggle.isChecked(),
            "show_trails": self.show_trails_toggle.isChecked(),
            "auto_record": self.auto_record_toggle.isChecked(),
            "video_fps": "60",
            "video_quality": self.video_quality_combo.currentText()
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
        self.setWindowTitle("Pendulum Paint Art - Control Panel")
        self.setMinimumSize(1366, 768)
        self.setMaximumSize(1920, 1080)
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
            QLineEdit, QSpinBox, QDoubleSpinBox {
                background-color: #ffffff;
                border: 1px solid #d4c4b0;
                border-radius: 4px;
                padding: 6px;
                color: #4a3428;
            }
            QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
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
        self._create_canvas_settings(left_column)
        left_column.addStretch()
        columns_layout.addLayout(left_column, 1)
        
        # Middle column
        middle_column = QVBoxLayout()
        middle_column.setSpacing(15)
        self._create_pendulum_settings(middle_column)
        self._create_paint_settings(middle_column)
        middle_column.addStretch()
        columns_layout.addLayout(middle_column, 1)
        
        # Right column
        right_column = QVBoxLayout()
        right_column.setSpacing(15)
        self._create_visual_settings(right_column)
        self._create_recording_settings(right_column)
        self._create_frame_management(right_column)
        right_column.addStretch()
        columns_layout.addLayout(right_column, 1)
        
        content_layout.addLayout(columns_layout)
        
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
        title_label = QLabel("🎨 Pendulum Paint Art")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #c2785a;
            }
        """)
        title_layout.addWidget(title_label)
        
        subtitle_label = QLabel("Physics-Based Pendulum Paint Simulation")
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
        group = QGroupBox("Target Image (Paint will follow dark areas)")
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(10)
        
        info_label = QLabel("Upload an image - paint drips more over dark pixels")
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
    
    def _create_canvas_settings(self, layout):
        """Create canvas settings section."""
        group = QGroupBox("Canvas Settings")
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
        
        size_layout.addWidget(QLabel("FPS:"), 1, 0)
        fps_label = QLabel("<b>60 FPS</b> (locked)")
        fps_label.setStyleSheet("QLabel { color: #c2785a; }")
        size_layout.addWidget(fps_label, 1, 1)
        
        group_layout.addLayout(size_layout)
        
        # Duration
        duration_layout = QHBoxLayout()
        duration_layout.addWidget(QLabel("Duration:"))
        self.duration_input = QLineEdit(str(self.target_duration))
        self.duration_input.setMaximumWidth(80)
        duration_layout.addWidget(self.duration_input)
        duration_layout.addWidget(QLabel("seconds"))
        duration_layout.addStretch()
        group_layout.addLayout(duration_layout)
        
        # Presets
        presets_layout = QHBoxLayout()
        presets_layout.setSpacing(8)
        
        preset_label = QLabel("Presets:")
        presets_layout.addWidget(preset_label)
        
        presets = [
            ("4:5 (800x1000)", 800, 1000),
            ("1:1 (800x800)", 800, 800),
            ("9:16 (540x960)", 540, 960)
        ]
        
        for name, w, h in presets:
            btn = QPushButton(name)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #d4c4b0;
                    padding: 5px 10px;
                    font-size: 10px;
                }
                QPushButton:hover {
                    background-color: #c4b4a0;
                }
            """)
            btn.clicked.connect(lambda checked, w=w, h=h: self._set_resolution(w, h))
            presets_layout.addWidget(btn)
        
        presets_layout.addStretch()
        group_layout.addLayout(presets_layout)
        
        layout.addWidget(group)
    
    def _create_pendulum_settings(self, layout):
        """Create pendulum physics settings section."""
        group = QGroupBox("Pendulum Physics")
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(12)
        
        # Pendulum Length
        self._create_slider_setting(
            group_layout, "Pendulum Length:", "length",
            100, 500, self.pendulum_length, "px"
        )
        
        # Initial Angle X
        self._create_slider_setting(
            group_layout, "Initial Angle X:", "angle_x",
            0, 90, int(self.initial_angle_x), "°"
        )
        
        # Initial Angle Y
        self._create_slider_setting(
            group_layout, "Initial Angle Y:", "angle_y",
            0, 90, int(self.initial_angle_y), "°"
        )
        
        # Damping X
        self._create_slider_setting(
            group_layout, "Damping X:", "damping_x",
            1, 100, int(self.damping_x * 1000), "/1000",
            divisor=1000
        )
        
        # Damping Y
        self._create_slider_setting(
            group_layout, "Damping Y:", "damping_y",
            1, 100, int(self.damping_y * 1000), "/1000",
            divisor=1000
        )
        
        # Gravity
        self._create_slider_setting(
            group_layout, "Gravity:", "gravity",
            10, 200, int(self.gravity * 10), "m/s²",
            divisor=10
        )
        
        layout.addWidget(group)
    
    def _create_paint_settings(self, layout):
        """Create paint settings section."""
        group = QGroupBox("Paint Settings")
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(12)
        
        # Drip Rate
        self._create_slider_setting(
            group_layout, "Drip Rate:", "drip_rate",
            1, 50, int(self.drip_rate * 100), "%",
            divisor=100
        )
        
        # Paint Thickness
        self._create_slider_setting(
            group_layout, "Paint Thickness:", "thickness",
            2, 20, self.paint_thickness, "px"
        )
        
        # Viscosity
        self._create_slider_setting(
            group_layout, "Viscosity:", "viscosity",
            10, 100, int(self.viscosity * 100), "%",
            divisor=100
        )
        
        # Paint Color
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("Paint Color:"))
        self.color_picker = ColorPickerButton(self.paint_color)
        color_layout.addWidget(self.color_picker)
        color_layout.addStretch()
        group_layout.addLayout(color_layout)
        
        layout.addWidget(group)
    
    def _create_slider_setting(self, layout, label_text, name, min_val, max_val, 
                               initial_val, suffix="", divisor=1):
        """Create a slider setting with label and value display."""
        setting_layout = QVBoxLayout()
        setting_layout.setSpacing(5)
        
        header = QHBoxLayout()
        label = QLabel(label_text)
        
        if divisor > 1:
            display_val = f"{initial_val / divisor:.2f}"
        else:
            display_val = str(initial_val)
        
        value_label = QLabel(f"{display_val}{suffix}")
        value_label.setStyleSheet("QLabel { color: #c2785a; font-weight: bold; }")
        value_label.setObjectName(f"{name}_value")
        
        header.addWidget(label)
        header.addStretch()
        header.addWidget(value_label)
        setting_layout.addLayout(header)
        
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setMinimum(min_val)
        slider.setMaximum(max_val)
        slider.setValue(initial_val)
        slider.setObjectName(f"{name}_slider")
        
        # Store reference
        setattr(self, f"{name}_slider", slider)
        setattr(self, f"{name}_value_label", value_label)
        
        # Connect value change
        def on_change(v, lbl=value_label, sfx=suffix, div=divisor):
            if div > 1:
                lbl.setText(f"{v / div:.2f}{sfx}")
            else:
                lbl.setText(f"{v}{sfx}")
        
        slider.valueChanged.connect(on_change)
        setting_layout.addWidget(slider)
        
        layout.addLayout(setting_layout)
    
    def _create_visual_settings(self, layout):
        """Create visual settings section."""
        group = QGroupBox("Visual Settings")
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(12)
        
        # Show Pendulum
        pendulum_layout = QHBoxLayout()
        pendulum_layout.addWidget(QLabel("Show Pendulum"))
        self.show_pendulum_toggle = ToggleSwitch()
        self.show_pendulum_toggle.setChecked(self.show_pendulum)
        pendulum_layout.addStretch()
        pendulum_layout.addWidget(self.show_pendulum_toggle)
        group_layout.addLayout(pendulum_layout)
        
        # Show Trails
        trails_layout = QHBoxLayout()
        trails_layout.addWidget(QLabel("Show Paint Trails"))
        self.show_trails_toggle = ToggleSwitch()
        self.show_trails_toggle.setChecked(self.show_trails)
        trails_layout.addStretch()
        trails_layout.addWidget(self.show_trails_toggle)
        group_layout.addLayout(trails_layout)
        
        layout.addWidget(group)
    
    def _create_recording_settings(self, layout):
        """Create recording settings section."""
        group = QGroupBox("Recording Settings")
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(12)
        
        # Auto Record
        record_layout = QHBoxLayout()
        record_layout.addWidget(QLabel("Auto-Record"))
        self.auto_record_toggle = ToggleSwitch()
        self.auto_record_toggle.setChecked(self.auto_record)
        record_layout.addStretch()
        record_layout.addWidget(self.auto_record_toggle)
        group_layout.addLayout(record_layout)
        
        # Video Quality
        quality_layout = QHBoxLayout()
        quality_layout.addWidget(QLabel("Video Quality:"))
        self.video_quality_combo = QComboBox()
        self.video_quality_combo.addItems(["high", "medium", "low"])
        self.video_quality_combo.setCurrentText(self.video_quality)
        quality_layout.addWidget(self.video_quality_combo)
        quality_layout.addStretch()
        group_layout.addLayout(quality_layout)
        
        layout.addWidget(group)
    
    def _create_frame_management(self, layout):
        """Create frame management section."""
        group = QGroupBox("Frame Management")
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(10)
        
        # Frame count
        self.frame_count_label = QLabel("Frames: 0")
        self.frame_count_label.setStyleSheet("QLabel { font-weight: bold; color: #c2785a; }")
        group_layout.addWidget(self.frame_count_label)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        clear_btn = QPushButton("Clear Frames")
        clear_btn.clicked.connect(self._clear_frames)
        btn_layout.addWidget(clear_btn)
        
        generate_btn = QPushButton("Generate Video")
        generate_btn.setStyleSheet("""
            QPushButton {
                background-color: #c2785a;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #a85d44;
            }
        """)
        generate_btn.clicked.connect(self._generate_video)
        btn_layout.addWidget(generate_btn)
        
        group_layout.addLayout(btn_layout)
        
        layout.addWidget(group)
    
    def _create_launch_button(self, layout):
        """Create the main launch button."""
        launch_btn = QPushButton("🚀 Launch Simulation")
        launch_btn.setStyleSheet("""
            QPushButton {
                background-color: #c2785a;
                color: white;
                font-size: 16px;
                font-weight: bold;
                padding: 15px 40px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #a85d44;
            }
            QPushButton:pressed {
                background-color: #8a4a35;
            }
        """)
        launch_btn.clicked.connect(self._launch_simulation)
        layout.addWidget(launch_btn, alignment=Qt.AlignmentFlag.AlignCenter)
    
    def _create_status_bar(self, layout):
        """Create status bar."""
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #8b7355;
                font-size: 11px;
                padding: 5px;
            }
        """)
        layout.addWidget(self.status_label)
    
    def _update_status(self, message):
        """Update status bar message."""
        self.status_label.setText(message)
    
    def _update_ui_from_settings(self):
        """Update UI elements from loaded settings."""
        self.width_input.setText(str(self.width))
        self.height_input.setText(str(self.height))
        self.duration_input.setText(str(self.target_duration))
        
        self.length_slider.setValue(self.pendulum_length)
        self.angle_x_slider.setValue(int(self.initial_angle_x))
        self.angle_y_slider.setValue(int(self.initial_angle_y))
        self.damping_x_slider.setValue(int(self.damping_x * 1000))
        self.damping_y_slider.setValue(int(self.damping_y * 1000))
        self.gravity_slider.setValue(int(self.gravity * 10))
        
        self.drip_rate_slider.setValue(int(self.drip_rate * 100))
        self.thickness_slider.setValue(self.paint_thickness)
        self.viscosity_slider.setValue(int(self.viscosity * 100))
        self.color_picker.set_color(self.paint_color)
        
        self.show_pendulum_toggle.setChecked(self.show_pendulum)
        self.show_trails_toggle.setChecked(self.show_trails)
        self.auto_record_toggle.setChecked(self.auto_record)
        self.video_quality_combo.setCurrentText(self.video_quality)
    
    def _set_resolution(self, width, height):
        """Set resolution from preset."""
        self.width_input.setText(str(width))
        self.height_input.setText(str(height))
    
    def _update_frame_count(self):
        """Update frame count display."""
        if FRAMES_FOLDER.exists():
            frames = list(FRAMES_FOLDER.glob("frame_*.png"))
            self.frame_count_label.setText(f"Frames: {len(frames)}")
    
    def _clear_frames(self):
        """Clear all captured frames."""
        reply = QMessageBox.question(
            self,
            "Clear Frames",
            "Delete all captured frames?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if FRAMES_FOLDER.exists():
                for f in FRAMES_FOLDER.glob("frame_*.png"):
                    f.unlink()
            self._update_frame_count()
            self._update_status("Frames cleared")
    
    def _generate_video(self):
        """Generate video from frames."""
        frames = list(FRAMES_FOLDER.glob("frame_*.png"))
        if not frames:
            QMessageBox.warning(self, "No Frames", "No frames found to generate video.")
            return
        
        # Output path
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_path = OUTPUT_FOLDER / f"pendulum_paint_{timestamp}.mp4"
        
        # Quality settings
        quality_map = {"high": 18, "medium": 23, "low": 28}
        crf = quality_map.get(self.video_quality_combo.currentText(), 23)
        
        # Start video generation thread
        self.video_thread = VideoGenerationThread(
            FRAMES_FOLDER, output_path, 60, crf, 60
        )
        self.video_thread.finished.connect(self._on_video_finished)
        self.video_thread.error.connect(self._on_video_error)
        self.video_thread.start()
        
        self._update_status("Generating video...")
    
    def _on_video_finished(self, output_path):
        """Handle video generation completion."""
        self._update_status(f"Video saved: {output_path}")
        QMessageBox.information(self, "Video Generated", f"Video saved to:\n{output_path}")
    
    def _on_video_error(self, error_msg):
        """Handle video generation error."""
        self._update_status("Video generation failed")
        QMessageBox.critical(self, "Error", error_msg)
    
    def _launch_simulation(self):
        """Launch the simulation."""
        # Save current settings first
        self._save_settings()
        
        # Build command
        cmd = [sys.executable, str(SIMULATION_DIR / "main.py")]
        
        # Add image path if set
        image_path = self.image_upload_widget.get_image_path()
        if image_path:
            cmd.extend(["--image", image_path])
        
        # Add settings
        cmd.extend(["--width", self.width_input.text()])
        cmd.extend(["--height", self.height_input.text()])
        cmd.extend(["--duration", self.duration_input.text()])
        cmd.extend(["--length", str(self.length_slider.value())])
        cmd.extend(["--angle-x", str(self.angle_x_slider.value())])
        cmd.extend(["--angle-y", str(self.angle_y_slider.value())])
        cmd.extend(["--damping-x", str(self.damping_x_slider.value() / 1000.0)])
        cmd.extend(["--damping-y", str(self.damping_y_slider.value() / 1000.0)])
        cmd.extend(["--gravity", str(self.gravity_slider.value() / 10.0)])
        cmd.extend(["--drip-rate", str(self.drip_rate_slider.value() / 100.0)])
        cmd.extend(["--thickness", str(self.thickness_slider.value())])
        cmd.extend(["--viscosity", str(self.viscosity_slider.value() / 100.0)])
        cmd.extend(["--color", self.color_picker.get_color()])
        
        if not self.show_pendulum_toggle.isChecked():
            cmd.append("--no-pendulum")
        if not self.show_trails_toggle.isChecked():
            cmd.append("--no-trails")
        if not self.auto_record_toggle.isChecked():
            cmd.append("--no-record")
        
        # Launch
        try:
            self.simulation_process = subprocess.Popen(cmd)
            self._update_status("Simulation launched!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to launch simulation:\n{e}")
    
    def closeEvent(self, event):
        """Handle window close event."""
        if self.simulation_process and self.simulation_process.poll() is None:
            self.simulation_process.terminate()
        event.accept()


def main():
    """Main entry point."""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    window = ControlPanel()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
