#!/usr/bin/env python3
"""
Magnetic Iron Filings Art - Control Panel Main Window (PySide6)
================================================================
Main control panel window implementation for the magnetic iron filings
portrait formation simulation.
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
    QFileDialog, QMessageBox, QScrollArea, QFrame, QSpinBox, QDialog,
    QRadioButton
)
from PySide6.QtCore import Qt, Signal, QTimer, QThread, QUrl, QSize, QPoint
from PySide6.QtGui import QPixmap, QDragEnterEvent, QDropEvent, QIcon, QFont, QPainter, QPen, QColor, QMouseEvent

# Import modularized components
from settings_manager import SettingsManager
from custom_widgets import ToggleSwitch, ImageUploadWidget, MagnetConfigDialog, load_icon
from video_thread import VideoGenerationThread

# Get paths
SIMULATION_DIR = Path(__file__).resolve().parent
BASE_DIR = SIMULATION_DIR.parent
FRAMES_FOLDER = SIMULATION_DIR / "frames"
UPLOADS_FOLDER = SIMULATION_DIR / "uploads"
ICONS_FOLDER = SIMULATION_DIR / "assets" / "icons"


class ControlPanel(QMainWindow):
    """Main control panel window for Magnetic Iron Filings Art simulation."""
    
    def __init__(self):
        super().__init__()
        
        # Ensure folders exist
        UPLOADS_FOLDER.mkdir(parents=True, exist_ok=True)
        FRAMES_FOLDER.mkdir(parents=True, exist_ok=True)
        (SIMULATION_DIR / "assets").mkdir(parents=True, exist_ok=True)
        
        # Initialize settings manager
        self.settings_manager = SettingsManager(SIMULATION_DIR)
        
        # Process tracking
        self.simulation_process = None
        self.video_thread = None
        
        # Setup UI
        self._init_variables()
        self._load_settings()
        self._load_magnet_config()
        self._setup_ui()
        self._update_ui_from_settings()
        self._update_frame_count()
        
        # Auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self._update_frame_count)
        self.refresh_timer.start(2000)  # 2 seconds
    
    def _init_variables(self):
        """Initialize all settings variables with defaults."""
        # Window settings
        self.width = 540
        self.height = 960
        self.fps = 60  # Locked at 60
        
        # Simulation settings
        self.target_duration = 15.0
        self.particle_count = 10000
        self.magnetic_strength = 1.0
        
        # Physics settings
        self.particle_size = 2.0
        self.friction = 0.98
        self.inertia = 0.95
        
        # GPU settings
        self.use_gpu = True
        
        # Visual settings
        self.show_magnet = True
        self.show_field_lines = False
        self.motion_blur = True
        self.drop_shadows = True
        self.metallic_glints = True
        
        # Frame border settings
        self.frame_thickness = 4
        self.frame_speed = 1.0
        self.frame_margin = 15
        
        # Custom magnet settings
        self.use_custom_magnet = False
        self.custom_magnet_path = None
        self.magnet_tip_x = 0
        self.magnet_tip_y = 0
        self.magnet_scale = 0.5
        
        # Recording settings
        self.auto_record = True
        self.video_quality = "high"
    
    def _load_settings(self):
        """Load all settings from file."""
        settings = self.settings_manager.load_settings()
        
        # Window settings
        self.width = int(settings.get("width", "540"))
        self.height = int(settings.get("height", "960"))
        self.fps = 60  # Always 60
        
        # Simulation settings
        self.target_duration = float(settings.get("target_duration", "15.0"))
        self.particle_count = int(settings.get("particle_count", "10000"))
        self.magnetic_strength = float(settings.get("magnetic_strength", "1.0"))
        
        # Physics settings
        self.particle_size = float(settings.get("particle_size", "2.0"))
        self.friction = float(settings.get("friction", "0.98"))
        self.inertia = float(settings.get("inertia", "0.95"))
        
        # GPU settings
        self.use_gpu = settings.get("use_gpu", True)
        
        # Visual settings
        self.show_magnet = settings.get("show_magnet", True)
        self.show_field_lines = settings.get("show_field_lines", False)
        self.motion_blur = settings.get("motion_blur", True)
        self.drop_shadows = settings.get("drop_shadows", True)
        self.metallic_glints = settings.get("metallic_glints", True)
        
        # Frame border settings
        self.frame_thickness = int(settings.get("frame_thickness", "4"))
        self.frame_speed = float(settings.get("frame_speed", "1.0"))
        self.frame_margin = int(settings.get("frame_margin", "15"))
        
        # Custom magnet settings
        self.use_custom_magnet = settings.get("use_custom_magnet", False)
        self.custom_magnet_path = settings.get("custom_magnet_path", "")
        self.magnet_scale = float(settings.get("magnet_scale", "0.5"))
        
        # Check if custom magnet exists
        if self.custom_magnet_path and not Path(self.custom_magnet_path).exists():
            self.custom_magnet_path = ""
        
        # Try loading from default assets location if no path set
        if not self.custom_magnet_path:
            default_magnet = SIMULATION_DIR / "assets" / "custom_magnet.png"
            if default_magnet.exists():
                self.custom_magnet_path = str(default_magnet)
                self.use_custom_magnet = True
        
        # Recording settings
        self.auto_record = settings.get("auto_record", True)
        self.video_quality = settings.get("video_quality", "high")
    
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
        
        # Get particle count
        try:
            particle_count = int(self.particle_count_input.text())
        except ValueError:
            particle_count = 10000
        
        settings = {
            "width": str(width),
            "height": str(height),
            "fps": "60",  # Always 60
            "target_duration": str(target_duration),
            "particle_count": str(particle_count),
            "magnetic_strength": str(self.magnetic_strength_slider.value() / 10.0),
            "particle_size": str(self.particle_size_slider.value() / 10.0),
            "friction": str(self.friction_slider.value() / 100.0),
            "inertia": str(self.inertia_slider.value() / 100.0),
            "use_gpu": self.gpu_toggle.isChecked(),
            "show_magnet": self.show_magnet_toggle.isChecked(),
            "show_field_lines": self.show_field_lines_toggle.isChecked(),
            "motion_blur": self.motion_blur_toggle.isChecked(),
            "drop_shadows": self.drop_shadows_toggle.isChecked(),
            "metallic_glints": self.metallic_glints_toggle.isChecked(),
            "frame_thickness": str(self.frame_thickness_slider.value()),
            "frame_speed": str(self.frame_speed_slider.value() / 10.0),
            "frame_margin": str(self.frame_margin_slider.value()),
            "use_custom_magnet": self.use_custom_magnet,
            "custom_magnet_path": self.custom_magnet_path if self.custom_magnet_path else "",
            "magnet_scale": str(self.magnet_scale),
            "auto_record": self.auto_record_toggle.isChecked(),
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
    
    def _load_magnet_config(self):
        """Load custom magnet configuration."""
        magnet_config_file = SIMULATION_DIR / "assets" / "magnet_settings.json"
        if magnet_config_file.exists():
            try:
                with open(magnet_config_file, 'r') as f:
                    config = json.load(f)
                    self.magnet_tip_x = config.get("magnet_tip_x", 0)
                    self.magnet_tip_y = config.get("magnet_tip_y", 0)
            except Exception:
                pass
        else:
            self.magnet_tip_x = 0
            self.magnet_tip_y = 0
    
    def _setup_ui(self):
        """Setup the main UI."""
        self.setWindowTitle("Magnetic Iron Filings Art - Control Panel")
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
        left_column.addStretch()
        columns_layout.addLayout(left_column, 1)
        
        # Middle column
        middle_column = QVBoxLayout()
        middle_column.setSpacing(15)
        self._create_simulation_settings(middle_column)
        self._create_physics_settings(middle_column)
        middle_column.addStretch()
        columns_layout.addLayout(middle_column, 1)
        
        # Right column
        right_column = QVBoxLayout()
        right_column.setSpacing(15)
        self._create_visual_effects(right_column)
        self._create_frame_border_settings(right_column)
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
        """Create header section with title and buttons."""
        header_layout = QHBoxLayout()
        
        # Title section
        title_layout = QVBoxLayout()
        title_label = QLabel("🧲 Magnetic Iron Filings Art")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #c2785a;
            }
        """)
        title_layout.addWidget(title_label)
        
        subtitle_label = QLabel("Cinematic Portrait Formation Simulation")
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
        """Create portrait image upload section."""
        group = QGroupBox("Portrait Image (Target for Iron Filings Formation)")
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(10)
        
        info_label = QLabel("Upload a portrait or any image for iron filings to form")
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
        
        # Presets
        presets_layout = QHBoxLayout()
        presets_layout.setSpacing(8)
        
        preset_label = QLabel("Presets:")
        presets_layout.addWidget(preset_label)
        
        presets = [
            ("9:16 (540x960)", 540, 960),
            ("4:5 (800x1000)", 800, 1000),
            ("1:1 (800x800)", 800, 800)
        ]
        
        for name, w, h in presets:
            btn = QPushButton(name)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #4b5563;
                    color: white;
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
    
    def _create_simulation_settings(self, layout):
        """Create simulation settings section."""
        group = QGroupBox("Simulation Settings")
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(12)
        
        # Target Duration
        duration_layout = QGridLayout()
        duration_layout.setSpacing(10)
        
        duration_label = QLabel("Target Duration:")
        duration_label.setToolTip("Set the exact duration for the simulation to complete")
        duration_layout.addWidget(duration_label, 0, 0)
        
        self.duration_input = QLineEdit(str(self.target_duration))
        self.duration_input.setMaximumWidth(100)
        self.duration_input.setPlaceholderText("seconds")
        duration_layout.addWidget(self.duration_input, 0, 1)
        
        duration_unit_label = QLabel("seconds")
        duration_layout.addWidget(duration_unit_label, 0, 2)
        
        duration_info = QLabel("ℹ️ Particle movement speed will auto-adjust to match")
        duration_info.setStyleSheet("QLabel { color: #8b7355; font-size: 10px; }")
        duration_info.setWordWrap(True)
        duration_layout.addWidget(duration_info, 1, 0, 1, 3)
        
        group_layout.addLayout(duration_layout)
        
        # Separator
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.Shape.HLine)
        separator1.setStyleSheet("QFrame { background-color: #d4c4b0; }")
        separator1.setFixedHeight(1)
        group_layout.addWidget(separator1)
        
        # Particle Count
        particle_layout = QVBoxLayout()
        particle_layout.setSpacing(5)
        
        particle_header = QHBoxLayout()
        particle_label = QLabel("Particle Count:")
        self.particle_count_value_label = QLabel(str(self.particle_count))
        self.particle_count_value_label.setStyleSheet("QLabel { color: #c2785a; font-weight: bold; }")
        particle_header.addWidget(particle_label)
        particle_header.addStretch()
        particle_header.addWidget(self.particle_count_value_label)
        particle_layout.addLayout(particle_header)
        
        # Particle count input + slider
        particle_input_layout = QHBoxLayout()
        particle_input_layout.setSpacing(10)
        
        self.particle_count_input = QLineEdit(str(self.particle_count))
        self.particle_count_input.setMaximumWidth(80)
        self.particle_count_input.textChanged.connect(self._on_particle_count_input_changed)
        particle_input_layout.addWidget(self.particle_count_input)
        
        self.particle_count_slider = QSlider(Qt.Orientation.Horizontal)
        self.particle_count_slider.setMinimum(1000)
        self.particle_count_slider.setMaximum(50000)
        self.particle_count_slider.setValue(self.particle_count)
        self.particle_count_slider.valueChanged.connect(self._on_particle_slider_changed)
        particle_input_layout.addWidget(self.particle_count_slider, 1)
        
        particle_layout.addLayout(particle_input_layout)
        
        particle_info = QLabel("Range: 1,000 - 50,000 particles")
        particle_info.setStyleSheet("QLabel { color: #8b7355; font-size: 9px; }")
        particle_layout.addWidget(particle_info)
        
        group_layout.addLayout(particle_layout)
        
        # Magnetic Strength
        magnetic_layout = QVBoxLayout()
        magnetic_layout.setSpacing(5)
        
        magnetic_header = QHBoxLayout()
        magnetic_label = QLabel("Magnetic Strength:")
        self.magnetic_strength_value_label = QLabel(f"{self.magnetic_strength:.1f}")
        self.magnetic_strength_value_label.setStyleSheet("QLabel { color: #c2785a; font-weight: bold; }")
        magnetic_header.addWidget(magnetic_label)
        magnetic_header.addStretch()
        magnetic_header.addWidget(self.magnetic_strength_value_label)
        magnetic_layout.addLayout(magnetic_header)
        
        self.magnetic_strength_slider = QSlider(Qt.Orientation.Horizontal)
        self.magnetic_strength_slider.setMinimum(1)  # 0.1
        self.magnetic_strength_slider.setMaximum(30)  # 3.0
        self.magnetic_strength_slider.setValue(int(self.magnetic_strength * 10))
        self.magnetic_strength_slider.valueChanged.connect(
            lambda v: self.magnetic_strength_value_label.setText(f"{v/10:.1f}")
        )
        magnetic_layout.addWidget(self.magnetic_strength_slider)
        
        magnetic_info = QLabel("Range: 0.1 - 3.0")
        magnetic_info.setStyleSheet("QLabel { color: #8b7355; font-size: 9px; }")
        magnetic_layout.addWidget(magnetic_info)
        
        group_layout.addLayout(magnetic_layout)
        
        # Separator
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.Shape.HLine)
        separator2.setStyleSheet("QFrame { background-color: #d4c4b0; }")
        separator2.setFixedHeight(1)
        group_layout.addWidget(separator2)
        
        # GPU Acceleration
        gpu_layout = QHBoxLayout()
        gpu_label = QLabel("GPU Acceleration (CUDA if available)")
        self.gpu_toggle = ToggleSwitch()
        self.gpu_toggle.setChecked(self.use_gpu)
        gpu_layout.addWidget(gpu_label)
        gpu_layout.addStretch()
        gpu_layout.addWidget(self.gpu_toggle)
        group_layout.addLayout(gpu_layout)
        
        layout.addWidget(group)
    
    def _on_particle_count_input_changed(self, text):
        """Handle particle count input text change."""
        try:
            value = int(text)
            if 1000 <= value <= 50000:
                self.particle_count_slider.blockSignals(True)
                self.particle_count_slider.setValue(value)
                self.particle_count_slider.blockSignals(False)
                self.particle_count_value_label.setText(str(value))
        except ValueError:
            pass
    
    def _on_particle_slider_changed(self, value):
        """Handle particle count slider change."""
        self.particle_count_input.blockSignals(True)
        self.particle_count_input.setText(str(value))
        self.particle_count_input.blockSignals(False)
        self.particle_count_value_label.setText(str(value))
    
    def _create_physics_settings(self, layout):
        """Create physics settings section."""
        group = QGroupBox("Physics Settings")
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(12)
        
        # Friction
        friction_layout = QVBoxLayout()
        friction_layout.setSpacing(5)
        
        friction_header = QHBoxLayout()
        friction_label = QLabel("Friction:")
        friction_label.setToolTip("Air resistance - lower values = more sliding")
        self.friction_value_label = QLabel(f"{self.friction:.2f}")
        self.friction_value_label.setStyleSheet("QLabel { color: #c2785a; font-weight: bold; }")
        friction_header.addWidget(friction_label)
        friction_header.addStretch()
        friction_header.addWidget(self.friction_value_label)
        friction_layout.addLayout(friction_header)
        
        self.friction_slider = QSlider(Qt.Orientation.Horizontal)
        self.friction_slider.setMinimum(90)  # 0.90
        self.friction_slider.setMaximum(99)  # 0.99
        self.friction_slider.setValue(int(self.friction * 100))
        self.friction_slider.valueChanged.connect(
            lambda v: self.friction_value_label.setText(f"{v/100:.2f}")
        )
        friction_layout.addWidget(self.friction_slider)
        
        friction_info = QLabel("Range: 0.90 - 0.99 (higher = less resistance)")
        friction_info.setStyleSheet("QLabel { color: #8b7355; font-size: 9px; }")
        friction_layout.addWidget(friction_info)
        
        group_layout.addLayout(friction_layout)
        
        # Inertia
        inertia_layout = QVBoxLayout()
        inertia_layout.setSpacing(5)
        
        inertia_header = QHBoxLayout()
        inertia_label = QLabel("Inertia:")
        inertia_label.setToolTip("Momentum preservation - higher = smoother movement")
        self.inertia_value_label = QLabel(f"{self.inertia:.2f}")
        self.inertia_value_label.setStyleSheet("QLabel { color: #c2785a; font-weight: bold; }")
        inertia_header.addWidget(inertia_label)
        inertia_header.addStretch()
        inertia_header.addWidget(self.inertia_value_label)
        inertia_layout.addLayout(inertia_header)
        
        self.inertia_slider = QSlider(Qt.Orientation.Horizontal)
        self.inertia_slider.setMinimum(90)  # 0.90
        self.inertia_slider.setMaximum(99)  # 0.99
        self.inertia_slider.setValue(int(self.inertia * 100))
        self.inertia_slider.valueChanged.connect(
            lambda v: self.inertia_value_label.setText(f"{v/100:.2f}")
        )
        inertia_layout.addWidget(self.inertia_slider)
        
        inertia_info = QLabel("Range: 0.90 - 0.99 (higher = more momentum)")
        inertia_info.setStyleSheet("QLabel { color: #8b7355; font-size: 9px; }")
        inertia_layout.addWidget(inertia_info)
        
        group_layout.addLayout(inertia_layout)
        
        # Particle Size
        size_layout = QVBoxLayout()
        size_layout.setSpacing(5)
        
        size_header = QHBoxLayout()
        size_label = QLabel("Particle Size:")
        self.particle_size_value_label = QLabel(f"{self.particle_size:.1f}px")
        self.particle_size_value_label.setStyleSheet("QLabel { color: #c2785a; font-weight: bold; }")
        size_header.addWidget(size_label)
        size_header.addStretch()
        size_header.addWidget(self.particle_size_value_label)
        size_layout.addLayout(size_header)
        
        self.particle_size_slider = QSlider(Qt.Orientation.Horizontal)
        self.particle_size_slider.setMinimum(10)  # 1.0
        self.particle_size_slider.setMaximum(50)  # 5.0
        self.particle_size_slider.setValue(int(self.particle_size * 10))
        self.particle_size_slider.valueChanged.connect(
            lambda v: self.particle_size_value_label.setText(f"{v/10:.1f}px")
        )
        size_layout.addWidget(self.particle_size_slider)
        
        size_info = QLabel("Range: 1.0 - 5.0 pixels")
        size_info.setStyleSheet("QLabel { color: #8b7355; font-size: 9px; }")
        size_layout.addWidget(size_info)
        
        group_layout.addLayout(size_layout)
        
        layout.addWidget(group)
    
    def _create_visual_effects(self, layout):
        """Create visual effects section."""
        group = QGroupBox("Visual Effects")
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(10)
        
        # Show Magnet
        magnet_layout = QHBoxLayout()
        magnet_label = QLabel("Show Magnet")
        self.show_magnet_toggle = ToggleSwitch()
        self.show_magnet_toggle.setChecked(self.show_magnet)
        magnet_layout.addWidget(magnet_label)
        magnet_layout.addStretch()
        magnet_layout.addWidget(self.show_magnet_toggle)
        group_layout.addLayout(magnet_layout)
        
        # Motion Blur
        blur_layout = QHBoxLayout()
        blur_label = QLabel("Motion Blur")
        self.motion_blur_toggle = ToggleSwitch()
        self.motion_blur_toggle.setChecked(self.motion_blur)
        blur_layout.addWidget(blur_label)
        blur_layout.addStretch()
        blur_layout.addWidget(self.motion_blur_toggle)
        group_layout.addLayout(blur_layout)
        
        # Drop Shadows
        shadow_layout = QHBoxLayout()
        shadow_label = QLabel("Drop Shadows")
        self.drop_shadows_toggle = ToggleSwitch()
        self.drop_shadows_toggle.setChecked(self.drop_shadows)
        shadow_layout.addWidget(shadow_label)
        shadow_layout.addStretch()
        shadow_layout.addWidget(self.drop_shadows_toggle)
        group_layout.addLayout(shadow_layout)
        
        # Metallic Glints
        glints_layout = QHBoxLayout()
        glints_label = QLabel("Metallic Glints")
        self.metallic_glints_toggle = ToggleSwitch()
        self.metallic_glints_toggle.setChecked(self.metallic_glints)
        glints_layout.addWidget(glints_label)
        glints_layout.addStretch()
        glints_layout.addWidget(self.metallic_glints_toggle)
        group_layout.addLayout(glints_layout)
        
        # Show Field Lines
        field_layout = QHBoxLayout()
        field_label = QLabel("Show Field Lines")
        self.show_field_lines_toggle = ToggleSwitch()
        self.show_field_lines_toggle.setChecked(self.show_field_lines)
        field_layout.addWidget(field_label)
        field_layout.addStretch()
        field_layout.addWidget(self.show_field_lines_toggle)
        group_layout.addLayout(field_layout)
        
        layout.addWidget(group)
    
    def _create_frame_border_settings(self, layout):
        """Create frame border settings section."""
        group = QGroupBox("Frame Border Settings")
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(12)
        
        # Border Thickness
        thickness_layout = QVBoxLayout()
        thickness_layout.setSpacing(5)
        
        thickness_header = QHBoxLayout()
        thickness_label = QLabel("Border Thickness:")
        self.frame_thickness_value_label = QLabel(f"{self.frame_thickness}")
        self.frame_thickness_value_label.setStyleSheet("QLabel { color: #c2785a; font-weight: bold; }")
        thickness_header.addWidget(thickness_label)
        thickness_header.addStretch()
        thickness_header.addWidget(self.frame_thickness_value_label)
        thickness_layout.addLayout(thickness_header)
        
        self.frame_thickness_slider = QSlider(Qt.Orientation.Horizontal)
        self.frame_thickness_slider.setMinimum(1)
        self.frame_thickness_slider.setMaximum(10)
        self.frame_thickness_slider.setValue(self.frame_thickness)
        self.frame_thickness_slider.valueChanged.connect(
            lambda v: self.frame_thickness_value_label.setText(str(v))
        )
        thickness_layout.addWidget(self.frame_thickness_slider)
        
        thickness_info = QLabel("Range: 1 - 10 pixels")
        thickness_info.setStyleSheet("QLabel { color: #8b7355; font-size: 9px; }")
        thickness_layout.addWidget(thickness_info)
        
        group_layout.addLayout(thickness_layout)
        
        # Border Draw Speed
        speed_layout = QVBoxLayout()
        speed_layout.setSpacing(5)
        
        speed_header = QHBoxLayout()
        speed_label = QLabel("Border Draw Speed:")
        self.frame_speed_value_label = QLabel(f"{self.frame_speed:.1f}x")
        self.frame_speed_value_label.setStyleSheet("QLabel { color: #c2785a; font-weight: bold; }")
        speed_header.addWidget(speed_label)
        speed_header.addStretch()
        speed_header.addWidget(self.frame_speed_value_label)
        speed_layout.addLayout(speed_header)
        
        self.frame_speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.frame_speed_slider.setMinimum(5)  # 0.5
        self.frame_speed_slider.setMaximum(30)  # 3.0
        self.frame_speed_slider.setValue(int(self.frame_speed * 10))
        self.frame_speed_slider.valueChanged.connect(
            lambda v: self.frame_speed_value_label.setText(f"{v/10:.1f}x")
        )
        speed_layout.addWidget(self.frame_speed_slider)
        
        speed_info = QLabel("Range: 0.5x - 3.0x")
        speed_info.setStyleSheet("QLabel { color: #8b7355; font-size: 9px; }")
        speed_layout.addWidget(speed_info)
        
        group_layout.addLayout(speed_layout)
        
        # Border Margin
        margin_layout = QVBoxLayout()
        margin_layout.setSpacing(5)
        
        margin_header = QHBoxLayout()
        margin_label = QLabel("Border Margin:")
        self.frame_margin_value_label = QLabel(f"{self.frame_margin}px")
        self.frame_margin_value_label.setStyleSheet("QLabel { color: #c2785a; font-weight: bold; }")
        margin_header.addWidget(margin_label)
        margin_header.addStretch()
        margin_header.addWidget(self.frame_margin_value_label)
        margin_layout.addLayout(margin_header)
        
        self.frame_margin_slider = QSlider(Qt.Orientation.Horizontal)
        self.frame_margin_slider.setMinimum(5)
        self.frame_margin_slider.setMaximum(50)
        self.frame_margin_slider.setValue(self.frame_margin)
        self.frame_margin_slider.valueChanged.connect(
            lambda v: self.frame_margin_value_label.setText(f"{v}px")
        )
        margin_layout.addWidget(self.frame_margin_slider)
        
        margin_info = QLabel("Range: 5 - 50 pixels")
        margin_info.setStyleSheet("QLabel { color: #8b7355; font-size: 9px; }")
        margin_layout.addWidget(margin_info)
        
        group_layout.addLayout(margin_layout)
        
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
        self.auto_record_toggle.setChecked(self.auto_record)
        auto_layout.addWidget(auto_label)
        auto_layout.addStretch()
        auto_layout.addWidget(self.auto_record_toggle)
        group_layout.addLayout(auto_layout)
        
        # Video Quality settings
        video_settings_layout = QGridLayout()
        video_settings_layout.setSpacing(10)
        
        video_settings_layout.addWidget(QLabel("Output FPS:"), 0, 0)
        fps_info = QLabel("<b>60 FPS</b> (always smooth)")
        fps_info.setStyleSheet("QLabel { color: #c2785a; }")
        video_settings_layout.addWidget(fps_info, 0, 1)
        
        video_settings_layout.addWidget(QLabel("Quality:"), 1, 0)
        self.video_quality_combo = QComboBox()
        self.video_quality_combo.addItems(["low", "medium", "high"])
        self.video_quality_combo.setCurrentText(self.video_quality)
        video_settings_layout.addWidget(self.video_quality_combo, 1, 1)
        
        group_layout.addLayout(video_settings_layout)
        
        # Quality info
        quality_info = QLabel("ℹ️ High quality recommended for final renders")
        quality_info.setStyleSheet("QLabel { color: #8b7355; font-size: 10px; }")
        quality_info.setWordWrap(True)
        group_layout.addWidget(quality_info)
        
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
        
        refresh_btn = QPushButton("🔄 Refresh")
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
        
        open_folder_btn = QPushButton("📁 Open Folder")
        open_folder_btn.setIcon(load_icon("folder"))
        open_folder_btn.clicked.connect(self._open_frames_folder)
        btn_row2.addWidget(open_folder_btn)
        
        btn_layout.addLayout(btn_row2)
        
        group_layout.addLayout(btn_layout, 1)
        
        layout.addWidget(group)
    
    def _create_launch_button(self, layout):
        """Create launch simulation button."""
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
    
    def _set_resolution(self, width, height):
        """Set resolution preset."""
        self.width_input.setText(str(width))
        self.height_input.setText(str(height))
        self._update_status(f"Resolution set to {width}x{height}")
    
    def _update_status(self, message):
        """Update status bar message."""
        self.status_label.setText(message)
    
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
        quality_crf = quality_map.get(self.video_quality_combo.currentText(), 23)
        
        # Generate output filename in output/videos directory
        output_dir = BASE_DIR / "output" / "videos"
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_path = output_dir / f"magnetic_iron_{timestamp}_60fps.mp4"
        
        # Start video generation thread
        self.video_thread = VideoGenerationThread(
            FRAMES_FOLDER,
            output_path,
            sim_fps,  # Input framerate
            quality_crf,
            output_fps=60  # Output framerate
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
        # Window settings
        self.width_input.setText(str(self.width))
        self.height_input.setText(str(self.height))
        
        # Simulation settings
        self.duration_input.setText(str(self.target_duration))
        self.particle_count_input.setText(str(self.particle_count))
        self.particle_count_slider.setValue(self.particle_count)
        self.magnetic_strength_slider.setValue(int(self.magnetic_strength * 10))
        self.gpu_toggle.setChecked(self.use_gpu)
        
        # Physics settings
        self.friction_slider.setValue(int(self.friction * 100))
        self.inertia_slider.setValue(int(self.inertia * 100))
        self.particle_size_slider.setValue(int(self.particle_size * 10))
        
        # Visual effects
        self.show_magnet_toggle.setChecked(self.show_magnet)
        self.motion_blur_toggle.setChecked(self.motion_blur)
        self.drop_shadows_toggle.setChecked(self.drop_shadows)
        self.metallic_glints_toggle.setChecked(self.metallic_glints)
        self.show_field_lines_toggle.setChecked(self.show_field_lines)
        
        # Frame border settings
        self.frame_thickness_slider.setValue(self.frame_thickness)
        self.frame_speed_slider.setValue(int(self.frame_speed * 10))
        self.frame_margin_slider.setValue(self.frame_margin)
        
        # Recording settings
        self.auto_record_toggle.setChecked(self.auto_record)
        self.video_quality_combo.setCurrentText(self.video_quality)
        
        # Update value labels
        self.particle_count_value_label.setText(str(self.particle_count))
        self.magnetic_strength_value_label.setText(f"{self.magnetic_strength:.1f}")
        self.friction_value_label.setText(f"{self.friction:.2f}")
        self.inertia_value_label.setText(f"{self.inertia:.2f}")
        self.particle_size_value_label.setText(f"{self.particle_size:.1f}px")
        self.frame_thickness_value_label.setText(str(self.frame_thickness))
        self.frame_speed_value_label.setText(f"{self.frame_speed:.1f}x")
        self.frame_margin_value_label.setText(f"{self.frame_margin}px")
    
    def _launch_simulation(self):
        """Launch the magnetic iron filings simulation."""
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
        
        # Get particle count
        try:
            particle_count = int(self.particle_count_input.text())
            if particle_count < 1000 or particle_count > 50000:
                raise ValueError("Particle count out of range")
        except ValueError:
            QMessageBox.critical(
                self,
                "Invalid Particle Count",
                "Particle count must be between 1,000 and 50,000."
            )
            return
        
        # Get values from sliders
        magnetic_strength = self.magnetic_strength_slider.value() / 10.0
        particle_size = self.particle_size_slider.value() / 10.0
        friction = self.friction_slider.value() / 100.0
        inertia = self.inertia_slider.value() / 100.0
        frame_thickness = self.frame_thickness_slider.value()
        frame_speed = self.frame_speed_slider.value() / 10.0
        frame_margin = self.frame_margin_slider.value()
        
        # Build command
        cmd = [
            sys.executable,
            str(SIMULATION_DIR / "main.py"),
            "--width", str(width),
            "--height", str(height),
            "--image", image_path,
            "--target-duration", str(target_duration),
            "--particle-count", str(particle_count),
            "--magnetic-strength", str(magnetic_strength),
            "--particle-size", str(particle_size),
            "--friction", str(friction),
            "--inertia", str(inertia),
            "--frame-thickness", str(frame_thickness),
            "--frame-speed", str(frame_speed),
            "--frame-margin", str(frame_margin)
        ]
        
        # Add conditional flags
        if not self.show_magnet_toggle.isChecked():
            cmd.append("--no-magnet")
        
        if self.show_field_lines_toggle.isChecked():
            cmd.append("--show-field-lines")
        
        if self.motion_blur_toggle.isChecked():
            cmd.append("--motion-blur")
        
        if self.drop_shadows_toggle.isChecked():
            cmd.append("--drop-shadows")
        
        if self.metallic_glints_toggle.isChecked():
            cmd.append("--metallic-glints")
        
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
