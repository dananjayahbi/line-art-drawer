#!/usr/bin/env python3
"""
Coloring Book Drawer - Control Panel Main Window (PySide6)
===========================================================
Main control panel window implementation for the coloring book drawer simulation.
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
from custom_widgets import ToggleSwitch, ImageUploadWidget, PenTipConfigDialog, load_icon
from video_thread import VideoGenerationThread
from video_editor.video_editor_panel import VideoEditorPanel

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
        self._load_pen_config()
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
        self.width = 1920
        self.height = 1080
        self.fps = 60
        
        # Drawing settings (fixed duration mode)
        self.target_duration = 10.0
        self.thickness = 1.0
        self.use_gpu = True
        
        # Visual settings
        self.show_pen = True
        
        # Shading engine settings (for complex artwork)
        self.force_shading_engine = False
        self.shading_sensitivity = 0.5
        self.hatching_angle = 45.0
        self.stroke_spacing = 3
        self.edge_phases_first = 1  # Number of edge layers to complete before shading (1-3)
        self.shading_order = "top_to_bottom"  # "top_to_bottom", "natural", "random"
        
        # Frame border settings
        self.frame_thickness = 6.0
        self.frame_speed = 1.0
        self.frame_margin = 20.0
        
        # Custom pen settings
        self.use_custom_pen = False
        self.custom_pen_path = None
        self.pen_tip_x = 0
        self.pen_tip_y = 0
        self.pen_scale = 1.0
        
        # Recording settings
        self.auto_record = False
        self.video_fps = 60
        self.video_quality = "high"
    
    def _load_settings(self):
        """Load all settings from file."""
        settings = self.settings_manager.load_settings()
        
        self.width = int(settings.get("width", "1920"))
        self.height = int(settings.get("height", "1080"))
        self.fps = 60  # Always 60
        self.target_duration = float(settings.get("target_duration", "10.0"))
        self.thickness = float(settings.get("thickness", 1.0))
        self.use_gpu = settings.get("use_gpu", True)
        self.show_pen = settings.get("show_pen", True)
        self.frame_thickness = float(settings.get("frame_thickness", 3.0))
        self.frame_speed = float(settings.get("frame_speed", 1.0))
        self.frame_margin = float(settings.get("frame_margin", 100.0))
        self.use_custom_pen = settings.get("use_custom_pen", False)
        self.custom_pen_path = settings.get("custom_pen_path", "")
        
        print(f"DEBUG: Loaded custom_pen_path from settings: '{self.custom_pen_path}'")
        print(f"DEBUG: use_custom_pen: {self.use_custom_pen}")
        
        # Check if custom pen exists, if not try default location
        if self.custom_pen_path and not Path(self.custom_pen_path).exists():
            print(f"DEBUG: Saved path doesn't exist, clearing: {self.custom_pen_path}")
            self.custom_pen_path = ""
        
        # Try loading from default assets location if no path set
        if not self.custom_pen_path:
            default_pen = SIMULATION_DIR / "assets" / "custom_pen.png"
            print(f"DEBUG: Checking default pen location: {default_pen}")
            if default_pen.exists():
                self.custom_pen_path = str(default_pen)
                self.use_custom_pen = True
                print(f"DEBUG: Found default pen, set path to: {self.custom_pen_path}")
            else:
                print("DEBUG: Default pen not found")
        
        self.pen_scale = float(settings.get("pen_scale", 0.3))
        self.auto_record = settings.get("auto_record", False)
        self.video_fps = 60  # Always 60
        self.video_quality = settings.get("video_quality", "high")
        
        # Shading engine settings
        self.force_shading_engine = settings.get("force_shading_engine", False)
        self.shading_sensitivity = float(settings.get("shading_sensitivity", 0.5))
        self.hatching_angle = float(settings.get("hatching_angle", 45.0))
        self.stroke_spacing = int(settings.get("stroke_spacing", 3))
        self.edge_phases_first = int(settings.get("edge_phases_first", 1))
        self.shading_order = settings.get("shading_order", "top_to_bottom")
    
    def _get_shading_order_display(self) -> str:
        """Convert internal shading order value to display text."""
        order_map = {
            "top_to_bottom": "Top to Bottom",
            "natural": "Natural",
            "random": "Random"
        }
        return order_map.get(self.shading_order, "Top to Bottom")
    
    def _get_shading_order_value(self, display_text: str) -> str:
        """Convert display text to internal shading order value."""
        order_map = {
            "Top to Bottom": "top_to_bottom",
            "Natural": "natural",
            "Random": "random"
        }
        return order_map.get(display_text, "top_to_bottom")
    
    def _save_settings(self):
        """Save all settings to file."""
        # Read current values from UI
        try:
            width = int(self.width_input.text())
            height = int(self.height_input.text())
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Width and Height must be valid integers.")
            return
        
        # Get target duration (fixed duration mode)
        try:
            target_duration = float(self.duration_input.text())
        except ValueError:
            target_duration = 10.0
        
        settings = {
            "width": str(width),
            "height": str(height),
            "fps": "60",  # Always 60
            "target_duration": str(target_duration),
            "thickness": str(self.thickness_slider.value() / 10.0),
            "use_gpu": self.gpu_toggle.isChecked(),
            "show_pen": self.show_pen_toggle.isChecked(),
            "frame_thickness": str(self.frame_thickness_slider.value()),
            "frame_speed": str(self.frame_speed_slider.value() / 10.0),
            "frame_margin": str(self.frame_margin_slider.value()),
            "use_custom_pen": self.custom_pen_toggle.isChecked(),
            "custom_pen_path": self.custom_pen_path if self.custom_pen_path else "",
            "pen_scale": str(self.pen_scale_slider.value() / 10.0),
            "auto_record": self.auto_record_toggle.isChecked(),
            "video_fps": "60",  # Always 60
            "video_quality": self.video_quality_combo.currentText(),
            # Shading engine settings
            "force_shading_engine": self.force_shading_toggle.isChecked(),
            "shading_sensitivity": str(self.shading_sensitivity_slider.value() / 10.0),
            "hatching_angle": str(self.hatching_angle_slider.value()),
            "stroke_spacing": str(self.stroke_spacing_slider.value()),
            "edge_phases_first": str(self.edge_phases_slider.value()),
            "shading_order": self._get_shading_order_value(self.shading_order_combo.currentText())
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
    
    def _load_pen_config(self):
        """Load custom pen configuration."""
        pen_config_file = SIMULATION_DIR / "assets" / "pen_settings.json"
        if pen_config_file.exists():
            try:
                with open(pen_config_file, 'r') as f:
                    config = json.load(f)
                    self.pen_tip_x = config.get("pen_tip_x", 0)
                    self.pen_tip_y = config.get("pen_tip_y", 0)
            except Exception:
                pass
        else:
            # Default pen tip values
            self.pen_tip_x = 0
            self.pen_tip_y = 0
    
    def _load_pen_preview(self):
        """Load and display the pen preview image."""
        if not hasattr(self, 'pen_preview_label'):
            print("Warning: pen_preview_label not yet created")
            return
            
        if self.custom_pen_path and Path(self.custom_pen_path).exists():
            try:
                print(f"Loading pen preview from: {self.custom_pen_path}")
                pixmap = QPixmap(self.custom_pen_path)
                if not pixmap.isNull():
                    scaled_pixmap = pixmap.scaled(
                        100, 100,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    self.pen_preview_label.setPixmap(scaled_pixmap)
                    print("Pen preview loaded successfully")
                else:
                    print("Failed to load pen preview: pixmap is null")
            except Exception as e:
                print(f"Failed to load pen preview: {e}")
        else:
            print(f"No valid pen path: {self.custom_pen_path}")
    
    def _setup_ui(self):
        """Setup the main UI."""
        self.setWindowTitle("Coloring Book Drawer - Control Panel")
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
        self._create_drawing_settings(middle_column)
        self._create_visual_settings(middle_column)
        middle_column.addStretch()
        columns_layout.addLayout(middle_column, 1)
        
        # Right column
        right_column = QVBoxLayout()
        right_column.setSpacing(15)
        self._create_custom_pen_settings(right_column)
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
        """Create header section."""
        header_layout = QHBoxLayout()
        
        # Title section
        title_layout = QVBoxLayout()
        title_label = QLabel("🎨 Coloring Book Drawer")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #c2785a;
            }
        """)
        title_layout.addWidget(title_label)
        
        subtitle_label = QLabel("GPU-Accelerated Line Art Animation")
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
        group = QGroupBox("Line Art Image (Black lines on White background)")
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(10)
        
        info_label = QLabel("Upload a line art image (like coloring book pages)")
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
        
        # FPS is now locked at 60 - show as fixed label instead of input
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
            ("4:5 (800x1000)", 800, 1000),
            ("1:1 (800x800)", 800, 800),
            ("9:16 (540x960)", 540, 960)
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
    
    def _create_drawing_settings(self, layout):
        """Create drawing settings section."""
        group = QGroupBox("Drawing Settings")
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(12)
        
        # Mode Selector: Fixed Duration only
        mode_layout = QHBoxLayout()
        mode_label = QLabel("Control Mode:")
        mode_layout.addWidget(mode_label)
        
        mode_value_label = QLabel("Fixed Duration")
        mode_value_label.setStyleSheet("QLabel { color: #c2785a; font-weight: bold; }")
        mode_layout.addWidget(mode_value_label)
        
        mode_layout.addStretch()
        group_layout.addLayout(mode_layout)
        
        # Fixed Duration Control
        duration_layout = QGridLayout()
        duration_layout.setContentsMargins(0, 10, 0, 0)
        duration_layout.setSpacing(10)
        
        duration_label = QLabel("Target Duration:")
        duration_label.setToolTip("Set the exact duration for the full animation to complete")
        duration_layout.addWidget(duration_label, 0, 0)
        
        self.duration_input = QLineEdit("10")
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
        
        # Thickness Scale
        thickness_layout = QVBoxLayout()
        thickness_layout.setSpacing(5)
        
        thickness_header = QHBoxLayout()
        thickness_label = QLabel("Thickness Scale:")
        self.thickness_value_label = QLabel(f"{self.thickness:.1f}")
        self.thickness_value_label.setStyleSheet("QLabel { color: #c2785a; font-weight: bold; }")
        thickness_header.addWidget(thickness_label)
        thickness_header.addStretch()
        thickness_header.addWidget(self.thickness_value_label)
        thickness_layout.addLayout(thickness_header)
        
        self.thickness_slider = QSlider(Qt.Orientation.Horizontal)
        self.thickness_slider.setMinimum(5)
        self.thickness_slider.setMaximum(30)
        self.thickness_slider.setValue(int(self.thickness * 10))
        self.thickness_slider.valueChanged.connect(
            lambda v: self.thickness_value_label.setText(f"{v/10:.1f}")
        )
        thickness_layout.addWidget(self.thickness_slider)
        
        group_layout.addLayout(thickness_layout)
        
        # GPU Acceleration
        gpu_layout = QHBoxLayout()
        gpu_label = QLabel("GPU Acceleration (if available)")
        self.gpu_toggle = ToggleSwitch()
        self.gpu_toggle.setChecked(self.use_gpu)
        gpu_layout.addWidget(gpu_label)
        gpu_layout.addStretch()
        gpu_layout.addWidget(self.gpu_toggle)
        group_layout.addLayout(gpu_layout)
        
        layout.addWidget(group)
    
    def _create_visual_settings(self, layout):
        """Create visual settings section."""
        group = QGroupBox("Visual Settings")
        group_layout = QVBoxLayout(group)
        
        # Show Pen Animation
        pen_layout = QHBoxLayout()
        pen_label = QLabel("Show Pen Animation")
        self.show_pen_toggle = ToggleSwitch()
        self.show_pen_toggle.setChecked(self.show_pen)
        pen_layout.addWidget(pen_label)
        pen_layout.addStretch()
        pen_layout.addWidget(self.show_pen_toggle)
        group_layout.addLayout(pen_layout)
        
        layout.addWidget(group)
        
        # Add Shading Engine Settings section
        self._create_shading_settings(layout)
    
    def _create_shading_settings(self, layout):
        """Create shading engine settings section for complex artwork."""
        group = QGroupBox("🎨 Shading Engine (For Complex Artwork)")
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(12)
        
        # Info label
        info_label = QLabel("For images with textures, shadows, and gradients (not just line art)")
        info_label.setStyleSheet("QLabel { color: #8b7355; font-size: 10px; font-style: italic; }")
        info_label.setWordWrap(True)
        group_layout.addWidget(info_label)
        
        # Force Shading Engine toggle
        force_layout = QHBoxLayout()
        force_label = QLabel("Force Shading Engine")
        force_label.setToolTip("Always use advanced shading engine even for simple line art")
        self.force_shading_toggle = ToggleSwitch()
        self.force_shading_toggle.setChecked(self.force_shading_engine)
        force_layout.addWidget(force_label)
        force_layout.addStretch()
        force_layout.addWidget(self.force_shading_toggle)
        group_layout.addLayout(force_layout)
        
        # Shading Sensitivity
        sensitivity_layout = QVBoxLayout()
        sensitivity_layout.setSpacing(5)
        
        sensitivity_header = QHBoxLayout()
        sensitivity_label = QLabel("Shading Sensitivity:")
        sensitivity_label.setToolTip("How sensitive to detect shading regions (higher = more sensitive)")
        self.shading_sensitivity_value_label = QLabel(f"{self.shading_sensitivity:.1f}")
        self.shading_sensitivity_value_label.setStyleSheet("QLabel { color: #c2785a; font-weight: bold; }")
        sensitivity_header.addWidget(sensitivity_label)
        sensitivity_header.addStretch()
        sensitivity_header.addWidget(self.shading_sensitivity_value_label)
        sensitivity_layout.addLayout(sensitivity_header)
        
        self.shading_sensitivity_slider = QSlider(Qt.Orientation.Horizontal)
        self.shading_sensitivity_slider.setMinimum(1)
        self.shading_sensitivity_slider.setMaximum(10)
        self.shading_sensitivity_slider.setValue(int(self.shading_sensitivity * 10))
        self.shading_sensitivity_slider.valueChanged.connect(
            lambda v: self.shading_sensitivity_value_label.setText(f"{v/10:.1f}")
        )
        sensitivity_layout.addWidget(self.shading_sensitivity_slider)
        group_layout.addLayout(sensitivity_layout)
        
        # Hatching Angle
        angle_layout = QVBoxLayout()
        angle_layout.setSpacing(5)
        
        angle_header = QHBoxLayout()
        angle_label = QLabel("Hatching Angle:")
        angle_label.setToolTip("Primary angle for shading strokes (in degrees)")
        self.hatching_angle_value_label = QLabel(f"{int(self.hatching_angle)}°")
        self.hatching_angle_value_label.setStyleSheet("QLabel { color: #c2785a; font-weight: bold; }")
        angle_header.addWidget(angle_label)
        angle_header.addStretch()
        angle_header.addWidget(self.hatching_angle_value_label)
        angle_layout.addLayout(angle_header)
        
        self.hatching_angle_slider = QSlider(Qt.Orientation.Horizontal)
        self.hatching_angle_slider.setMinimum(0)
        self.hatching_angle_slider.setMaximum(90)
        self.hatching_angle_slider.setValue(int(self.hatching_angle))
        self.hatching_angle_slider.valueChanged.connect(
            lambda v: self.hatching_angle_value_label.setText(f"{v}°")
        )
        angle_layout.addWidget(self.hatching_angle_slider)
        group_layout.addLayout(angle_layout)
        
        # Stroke Spacing
        spacing_layout = QVBoxLayout()
        spacing_layout.setSpacing(5)
        
        spacing_header = QHBoxLayout()
        spacing_label = QLabel("Stroke Spacing:")
        spacing_label.setToolTip("Spacing between hatching strokes in pixels (smaller = denser)")
        self.stroke_spacing_value_label = QLabel(f"{self.stroke_spacing}px")
        self.stroke_spacing_value_label.setStyleSheet("QLabel { color: #c2785a; font-weight: bold; }")
        spacing_header.addWidget(spacing_label)
        spacing_header.addStretch()
        spacing_header.addWidget(self.stroke_spacing_value_label)
        spacing_layout.addLayout(spacing_header)
        
        self.stroke_spacing_slider = QSlider(Qt.Orientation.Horizontal)
        self.stroke_spacing_slider.setMinimum(1)
        self.stroke_spacing_slider.setMaximum(10)
        self.stroke_spacing_slider.setValue(self.stroke_spacing)
        self.stroke_spacing_slider.valueChanged.connect(
            lambda v: self.stroke_spacing_value_label.setText(f"{v}px")
        )
        spacing_layout.addWidget(self.stroke_spacing_slider)
        group_layout.addLayout(spacing_layout)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("QFrame { color: #3d3d3d; }")
        group_layout.addWidget(separator)
        
        # Edge Phases First (number of edge layers to complete before shading)
        edge_phases_layout = QVBoxLayout()
        edge_phases_layout.setSpacing(5)
        
        edge_phases_header = QHBoxLayout()
        edge_phases_label = QLabel("Edge Phases First:")
        edge_phases_label.setToolTip(
            "Number of edge/outline layers to complete before shading:\n"
            "1 = Draw main outlines first, then shading\n"
            "2 = Draw outlines + hatching first, then remaining\n"
            "3 = Draw outlines + hatching + cross-hatching first"
        )
        self.edge_phases_value_label = QLabel(f"{self.edge_phases_first}")
        self.edge_phases_value_label.setStyleSheet("QLabel { color: #c2785a; font-weight: bold; }")
        edge_phases_header.addWidget(edge_phases_label)
        edge_phases_header.addStretch()
        edge_phases_header.addWidget(self.edge_phases_value_label)
        edge_phases_layout.addLayout(edge_phases_header)
        
        self.edge_phases_slider = QSlider(Qt.Orientation.Horizontal)
        self.edge_phases_slider.setMinimum(1)
        self.edge_phases_slider.setMaximum(3)
        self.edge_phases_slider.setValue(self.edge_phases_first)
        self.edge_phases_slider.valueChanged.connect(
            lambda v: self.edge_phases_value_label.setText(f"{v}")
        )
        edge_phases_layout.addWidget(self.edge_phases_slider)
        group_layout.addLayout(edge_phases_layout)
        
        # Shading Order dropdown
        shading_order_layout = QHBoxLayout()
        shading_order_label = QLabel("Shading Order:")
        shading_order_label.setToolTip(
            "How shading strokes are ordered after edges:\n"
            "• Top to Bottom: Shade from top of image to bottom\n"
            "• Natural: Keep stroke paths as generated\n"
            "• Random: Randomize shading order"
        )
        self.shading_order_combo = QComboBox()
        self.shading_order_combo.addItems(["Top to Bottom", "Natural", "Random"])
        self.shading_order_combo.setCurrentText(self._get_shading_order_display())
        self.shading_order_combo.setMinimumWidth(120)
        shading_order_layout.addWidget(shading_order_label)
        shading_order_layout.addStretch()
        shading_order_layout.addWidget(self.shading_order_combo)
        group_layout.addLayout(shading_order_layout)
        
        layout.addWidget(group)
    
    def _create_custom_pen_settings(self, layout):
        """Create custom pen settings section."""
        group = QGroupBox("Custom Pen Settings")
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(12)
        
        # Use Custom Pen
        custom_pen_layout = QHBoxLayout()
        custom_pen_label = QLabel("Use Custom Pen Image")
        self.custom_pen_toggle = ToggleSwitch()
        self.custom_pen_toggle.setChecked(self.use_custom_pen)
        custom_pen_layout.addWidget(custom_pen_label)
        custom_pen_layout.addStretch()
        custom_pen_layout.addWidget(self.custom_pen_toggle)
        group_layout.addLayout(custom_pen_layout)
        
        # Upload Pen
        upload_layout = QHBoxLayout()
        upload_btn = QPushButton("Upload Pen PNG")
        upload_btn.setStyleSheet("""
            QPushButton {
                background-color: #c2785a;
                color: white;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #a85d44;
            }
        """)
        upload_btn.clicked.connect(self._upload_pen_image)
        upload_layout.addWidget(upload_btn)
        
        self.pen_status_label = QLabel("Custom pen loaded" if self.custom_pen_path else "No custom pen")
        self.pen_status_label.setStyleSheet("QLabel { color: #8b7355; font-size: 10px; }")
        upload_layout.addWidget(self.pen_status_label)
        
        # Add pen preview
        self.pen_preview_label = QLabel()
        self.pen_preview_label.setFixedSize(100, 100)
        self.pen_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pen_preview_label.setStyleSheet("""
            QLabel {
                background-color: #ffffff;
                border: 1px solid #d4c4b0;
                border-radius: 4px;
            }
        """)
        upload_layout.addWidget(self.pen_preview_label)
        upload_layout.addStretch()
        
        group_layout.addLayout(upload_layout)
        
        # Configure Tip
        configure_btn = QPushButton("Configure Pen Tip")
        configure_btn.setStyleSheet("""
            QPushButton {
                background-color: #c2785a;
                color: white;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #a85d44;
            }
        """)
        configure_btn.clicked.connect(self._configure_pen_tip)
        group_layout.addWidget(configure_btn)
        
        # Pen Scale
        scale_layout = QVBoxLayout()
        scale_layout.setSpacing(5)
        
        scale_header = QHBoxLayout()
        scale_label = QLabel("Pen Scale:")
        self.pen_scale_value_label = QLabel(f"{self.pen_scale:.1f}x")
        self.pen_scale_value_label.setStyleSheet("QLabel { color: #c2785a; font-weight: bold; }")
        scale_header.addWidget(scale_label)
        scale_header.addStretch()
        scale_header.addWidget(self.pen_scale_value_label)
        scale_layout.addLayout(scale_header)
        
        self.pen_scale_slider = QSlider(Qt.Orientation.Horizontal)
        self.pen_scale_slider.setMinimum(3)
        self.pen_scale_slider.setMaximum(30)
        self.pen_scale_slider.setValue(int(self.pen_scale * 10))
        self.pen_scale_slider.valueChanged.connect(
            lambda v: self.pen_scale_value_label.setText(f"{v/10:.1f}x")
        )
        scale_layout.addWidget(self.pen_scale_slider)
        
        group_layout.addLayout(scale_layout)
        
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
        self.frame_thickness_value_label = QLabel(f"{int(self.frame_thickness)}")
        self.frame_thickness_value_label.setStyleSheet("QLabel { color: #c2785a; font-weight: bold; }")
        thickness_header.addWidget(thickness_label)
        thickness_header.addStretch()
        thickness_header.addWidget(self.frame_thickness_value_label)
        thickness_layout.addLayout(thickness_header)
        
        self.frame_thickness_slider = QSlider(Qt.Orientation.Horizontal)
        self.frame_thickness_slider.setMinimum(2)
        self.frame_thickness_slider.setMaximum(15)
        self.frame_thickness_slider.setValue(int(self.frame_thickness))
        self.frame_thickness_slider.valueChanged.connect(
            lambda v: self.frame_thickness_value_label.setText(str(v))
        )
        thickness_layout.addWidget(self.frame_thickness_slider)
        
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
        self.frame_speed_slider.setMinimum(5)
        self.frame_speed_slider.setMaximum(50)
        self.frame_speed_slider.setValue(int(self.frame_speed * 10))
        self.frame_speed_slider.valueChanged.connect(
            lambda v: self.frame_speed_value_label.setText(f"{v/10:.1f}x")
        )
        speed_layout.addWidget(self.frame_speed_slider)
        
        group_layout.addLayout(speed_layout)
        
        # Border Margin
        margin_layout = QVBoxLayout()
        margin_layout.setSpacing(5)
        
        margin_header = QHBoxLayout()
        margin_label = QLabel("Border Margin:")
        self.frame_margin_value_label = QLabel(f"{int(self.frame_margin)}px")
        self.frame_margin_value_label.setStyleSheet("QLabel { color: #c2785a; font-weight: bold; }")
        margin_header.addWidget(margin_label)
        margin_header.addStretch()
        margin_header.addWidget(self.frame_margin_value_label)
        margin_layout.addLayout(margin_header)
        
        self.frame_margin_slider = QSlider(Qt.Orientation.Horizontal)
        self.frame_margin_slider.setMinimum(10)
        self.frame_margin_slider.setMaximum(100)
        self.frame_margin_slider.setValue(int(self.frame_margin))
        self.frame_margin_slider.valueChanged.connect(
            lambda v: self.frame_margin_value_label.setText(f"{v}px")
        )
        margin_layout.addWidget(self.frame_margin_slider)
        
        # Adjust Frame button - opens interactive preview window
        adjust_frame_btn = QPushButton("🖼️ Adjust Frame Interactively...")
        adjust_frame_btn.setToolTip("Open a preview window to adjust frame margin with UP/DOWN arrow keys")
        adjust_frame_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a6572;
                color: white;
                border: none;
                padding: 8px 12px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5a7582;
            }
            QPushButton:pressed {
                background-color: #3a5562;
            }
        """)
        adjust_frame_btn.clicked.connect(self._open_frame_adjuster)
        margin_layout.addWidget(adjust_frame_btn)
        
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
        
        # Video Quality setting (FPS is always 60)
        video_settings_layout = QGridLayout()
        video_settings_layout.setSpacing(10)
        
        video_settings_layout.addWidget(QLabel("Output FPS:"), 0, 0)
        fps_info = QLabel("<b>60 FPS</b> (always smooth)")
        fps_info.setStyleSheet("QLabel { color: #c2785a; }")
        video_settings_layout.addWidget(fps_info, 0, 1)
        
        video_settings_layout.addWidget(QLabel("Quality:"), 0, 2)
        self.video_quality_combo = QComboBox()
        self.video_quality_combo.addItems(["low", "medium", "high"])
        self.video_quality_combo.setCurrentText(self.video_quality)
        video_settings_layout.addWidget(self.video_quality_combo, 0, 3)
        
        group_layout.addLayout(video_settings_layout)
        
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
        
        # Row 3: Manage Videos button
        btn_row3 = QHBoxLayout()
        btn_row3.setSpacing(8)
        
        manage_videos_btn = QPushButton("🎬 Manage Videos")
        manage_videos_btn.setStyleSheet("""
            QPushButton {
                background-color: #6b8fa8;
                color: white;
                border-radius: 6px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #5a7d94;
            }
        """)
        manage_videos_btn.clicked.connect(self._open_video_editor)
        btn_row3.addWidget(manage_videos_btn)
        
        btn_layout.addLayout(btn_row3)
        
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
    
    def _upload_pen_image(self):
        """Handle pen image upload."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Custom Pen Image (PNG)",
            "",
            "PNG files (*.png);;All files (*.*)"
        )
        
        if file_path:
            try:
                assets_folder = SIMULATION_DIR / "assets"
                assets_folder.mkdir(parents=True, exist_ok=True)
                
                dest_path = assets_folder / "custom_pen.png"
                shutil.copy(file_path, dest_path)
                
                self.custom_pen_path = str(dest_path)
                self.pen_status_label.setText("Custom pen loaded")
                
                # Update preview
                pixmap = QPixmap(str(dest_path))
                if not pixmap.isNull():
                    scaled_pixmap = pixmap.scaled(
                        100, 100,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    self.pen_preview_label.setPixmap(scaled_pixmap)
                
                self._update_status("Custom pen uploaded successfully")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to upload pen image: {e}")
    
    def _configure_pen_tip(self):
        """Configure pen tip position."""
        if not self.custom_pen_path or not Path(self.custom_pen_path).exists():
            QMessageBox.warning(
                self,
                "No Custom Pen",
                "Please upload a custom pen image first."
            )
            return
        
        # Open pen tip configuration dialog
        dialog = PenTipConfigDialog(self.custom_pen_path, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Get the tip position from the dialog
            self.pen_tip_x, self.pen_tip_y = dialog.get_tip_position()
            
            # Save to pen_settings.json
            pen_config_file = SIMULATION_DIR / "assets" / "pen_settings.json"
            pen_config_file.parent.mkdir(parents=True, exist_ok=True)
            
            try:
                with open(pen_config_file, 'w') as f:
                    json.dump({
                        "pen_tip_x": self.pen_tip_x,
                        "pen_tip_y": self.pen_tip_y
                    }, f, indent=2)
                
                self._update_status(f"Pen tip configured: ({self.pen_tip_x}, {self.pen_tip_y})")
                QMessageBox.information(
                    self,
                    "Success",
                    f"Pen tip position saved:\nX: {self.pen_tip_x}\nY: {self.pen_tip_y}"
                )
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save pen tip configuration: {e}")
    
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
    
    def _open_video_editor(self):
        """Open the video editor panel for adding background music."""
        try:
            self.video_editor_window = VideoEditorPanel(self)
            self.video_editor_window.show()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open video editor: {e}")
    
    def _open_frame_adjuster(self):
        """Open interactive frame adjuster window."""
        # Get current image path from the upload widget
        image_path = self.image_upload_widget.get_image_path()
        if not image_path:
            QMessageBox.warning(
                self,
                "No Image",
                "Please upload an image first before adjusting the frame."
            )
            return
        
        try:
            # Import the frame adjuster
            from frame_adjuster import adjust_frame_margin
            
            # Get current margin value
            current_margin = self.frame_margin_slider.value()
            
            # Get window dimensions from the input fields
            try:
                width = int(self.width_input.text())
                height = int(self.height_input.text())
            except (ValueError, AttributeError):
                width = self.width
                height = self.height
            
            # Open the adjuster window (blocks until user confirms or cancels)
            self._update_status("Opening frame adjuster... Use UP/DOWN to adjust, Enter to confirm")
            
            new_margin = adjust_frame_margin(
                image_path=image_path,
                width=width,
                height=height,
                initial_margin=current_margin
            )
            
            if new_margin is not None:
                # User confirmed - update the slider
                self.frame_margin_slider.setValue(int(new_margin))
                self.frame_margin_value_label.setText(f"{int(new_margin)}px")
                self._update_status(f"Frame margin set to {int(new_margin)}px")
            else:
                # User cancelled
                self._update_status("Frame adjustment cancelled")
                
        except ImportError as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Could not import frame adjuster module: {e}"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to open frame adjuster: {e}"
            )

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
        
        # FPS is always 60 now
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
            f"{expected_duration:.1f}-second duration by duplicating frames.</i>"
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
        output_path = output_dir / f"output_{timestamp}_60fps.mp4"
        
        # Start video generation thread
        self.video_thread = VideoGenerationThread(
            FRAMES_FOLDER,
            output_path,
            sim_fps,  # Input framerate (how frames were captured)
            quality_crf,
            output_fps=60  # Output framerate (always 60 for smoothness)
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
        # FPS is locked at 60, no UI control
        self.duration_input.setText(str(self.target_duration))
        self.thickness_slider.setValue(int(self.thickness * 10))
        self.gpu_toggle.setChecked(self.use_gpu)
        self.show_pen_toggle.setChecked(self.show_pen)
        self.frame_thickness_slider.setValue(int(self.frame_thickness))
        self.frame_speed_slider.setValue(int(self.frame_speed * 10))
        self.frame_margin_slider.setValue(int(self.frame_margin))
        self.custom_pen_toggle.setChecked(self.use_custom_pen)
        self.pen_scale_slider.setValue(int(self.pen_scale * 10))
        self.auto_record_toggle.setChecked(self.auto_record)
        # Note: video_fps is always 60, no UI control needed
        self.video_quality_combo.setCurrentText(self.video_quality)
        
        # Shading engine settings
        self.force_shading_toggle.setChecked(self.force_shading_engine)
        self.shading_sensitivity_slider.setValue(int(self.shading_sensitivity * 10))
        self.hatching_angle_slider.setValue(int(self.hatching_angle))
        self.stroke_spacing_slider.setValue(self.stroke_spacing)
        self.edge_phases_slider.setValue(self.edge_phases_first)
        self.shading_order_combo.setCurrentText(self._get_shading_order_display())
        
        # Update pen status label and preview
        print(f"DEBUG _update_ui_from_settings: use_custom_pen={self.use_custom_pen}, custom_pen_path='{self.custom_pen_path}'")
        if self.use_custom_pen and self.custom_pen_path:
            self.pen_status_label.setText("Custom pen loaded")
            # Load pen preview immediately (no timer needed, UI is already created)
            print("DEBUG: Calling _load_pen_preview()")
            self._load_pen_preview()
        else:
            self.pen_status_label.setText("No custom pen")
            # Clear preview
            self.pen_preview_label.clear()
            print("DEBUG: No custom pen, cleared preview")
    
    def _launch_simulation(self):
        """Launch the simulation."""
        # Validate inputs
        image_path = self.image_upload_widget.get_image_path()
        if not image_path:
            QMessageBox.warning(
                self,
                "No Image",
                "Please upload a line art image first."
            )
            return
        
        try:
            width = int(self.width_input.text())
            height = int(self.height_input.text())
            # FPS is locked at 60
            fps = 60
        except ValueError:
            QMessageBox.critical(
                self,
                "Invalid Input",
                "Width and Height must be valid integers."
            )
            return
        
        # Get current values from UI
        # Fixed Duration mode only
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
        
        # Speed will be auto-calculated by simulation
        speed = None
        
        thickness = self.thickness_slider.value() / 10.0
        frame_thickness = int(self.frame_thickness_slider.value())
        frame_speed = int(self.frame_speed_slider.value() / 10.0)
        frame_margin = int(self.frame_margin_slider.value())
        pen_scale = self.pen_scale_slider.value() / 10.0
        
        # Build command (no --fps argument, it's always 60)
        cmd = [
            sys.executable,
            str(SIMULATION_DIR / "main.py"),
            "--width", str(width),
            "--height", str(height),
            # --fps removed, always 60
            "--image", image_path,
            "--thickness", str(thickness),
            "--frame-thickness", str(frame_thickness),
            "--frame-speed", str(frame_speed),
            "--frame-margin", str(frame_margin)
        ]
        
        # Add duration parameter (fixed duration mode only)
        cmd.extend(["--target-duration", str(target_duration)])
        
        # Add conditional flags
        if not self.show_pen_toggle.isChecked():
            cmd.append("--no-pen")
        
        if not self.auto_record_toggle.isChecked():
            cmd.append("--no-record")
        
        if not self.gpu_toggle.isChecked():
            cmd.append("--no-gpu")
        
        # Custom pen settings
        if self.custom_pen_toggle.isChecked() and self.custom_pen_path and Path(self.custom_pen_path).exists():
            cmd.extend([
                "--custom-pen", self.custom_pen_path,
                "--pen-tip-x", str(self.pen_tip_x),
                "--pen-tip-y", str(self.pen_tip_y),
                "--pen-scale", str(pen_scale),
                "--pen-rotation"  # Always enable pen rotation
            ])
        
        # Shading engine settings
        if self.force_shading_toggle.isChecked():
            cmd.append("--force-shading")
        
        shading_sensitivity = self.shading_sensitivity_slider.value() / 10.0
        hatching_angle = self.hatching_angle_slider.value()
        stroke_spacing = self.stroke_spacing_slider.value()
        edge_phases_first = self.edge_phases_slider.value()
        shading_order = self._get_shading_order_value(self.shading_order_combo.currentText())
        
        cmd.extend([
            "--shading-sensitivity", str(shading_sensitivity),
            "--hatching-angle", str(hatching_angle),
            "--stroke-spacing", str(stroke_spacing),
            "--edge-phases-first", str(edge_phases_first),
            "--shading-order", shading_order
        ])
        
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
