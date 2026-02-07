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
        
        # Engine selection
        self.engine_type = "auto"  # "auto", "pixel_reveal", "pencil_shading", "pencil_shading_v2", "advanced_gradient", "hybrid_multi"
        
        # Pencil Shading V2 Engine settings (Engine 2V2)
        self.ps2_auto_tune = False
        
        # Advanced Gradient Engine settings (Engine 3)
        self.contour_sensitivity = 0.5
        self.gradient_smoothness = 0.7
        self.texture_detection_strength = 0.6
        self.shadow_passes = 3
        self.shadow_angle_variation = 30.0
        self.brush_softness_contour = 0.3
        self.brush_softness_shading = 0.7
        self.pressure_variation = 0.5
        self.phase_1_weight = 1.0
        self.phase_2_weight = 0.8
        self.phase_3_weight = 1.0
        self.merge_shading_phases = False
        self.auto_analyze = False
        
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
        
        # Engine selection
        self.engine_type = settings.get("engine_type", "auto")
        
        # Advanced Gradient Engine settings (Engine 3)
        self.contour_sensitivity = float(settings.get("contour_sensitivity", 0.5))
        self.gradient_smoothness = float(settings.get("gradient_smoothness", 0.7))
        self.texture_detection_strength = float(settings.get("texture_detection_strength", 0.6))
        self.shadow_passes = int(settings.get("shadow_passes", 3))
        self.shadow_angle_variation = float(settings.get("shadow_angle_variation", 30.0))
        self.brush_softness_contour = float(settings.get("brush_softness_contour", 0.3))
        self.brush_softness_shading = float(settings.get("brush_softness_shading", 0.7))
        self.pressure_variation = float(settings.get("pressure_variation", 0.5))
        self.phase_1_weight = float(settings.get("phase_1_weight", 1.0))
        self.phase_2_weight = float(settings.get("phase_2_weight", 0.8))
        self.phase_3_weight = float(settings.get("phase_3_weight", 1.0))
        self.merge_shading_phases = str(settings.get("merge_shading_phases", "false")).lower() == "true"
        self.auto_analyze = str(settings.get("auto_analyze", "false")).lower() == "true"
        
        # Zone Progressive Engine settings (Engine 3D)
        self.zp_num_zones = int(settings.get("zp_num_zones", 10))
        self.zp_saliency_threshold = float(settings.get("zp_saliency_threshold", 0.3))
        self.zp_max_focal_points = int(settings.get("zp_max_focal_points", 5))
        self.zp_animation_mode = settings.get("zp_animation_mode", "multi_focal")
        self.zp_transition_width = float(settings.get("zp_transition_width", 0.1))
        self.zp_stroke_density = float(settings.get("zp_stroke_density", 0.8))
        self.zp_enable_portrait = settings.get("zp_enable_portrait", True)
        
        # Adaptive Brush Engine settings (Engine 3E)
        self.ab_tip_shape = settings.get("ab_tip_shape", "round")
        self.ab_pencil_hardness = float(settings.get("ab_pencil_hardness", 0.5))
        self.ab_pencil_sharpness = float(settings.get("ab_pencil_sharpness", 0.7))
        self.ab_paper_type = settings.get("ab_paper_type", "cold_press")
        self.ab_paper_texture_strength = float(settings.get("ab_paper_texture_strength", 0.5))
        self.ab_pressure_variation = float(settings.get("ab_pressure_variation", 0.5))
        self.ab_graphite_buildup = float(settings.get("ab_graphite_buildup", 0.7))
        
        # Hybrid Multi-Strategy Engine settings (Engine 3F)
        self.hm_num_segments = int(settings.get("hm_num_segments", 100))
        self.hm_min_region_area = int(settings.get("hm_min_region_area", 500))
        self.hm_transition_width = int(settings.get("hm_transition_width", 10))
        self.hm_blend_smoothness = float(settings.get("hm_blend_smoothness", 0.7))
        self.hm_strategy_mode = settings.get("hm_strategy_mode", "auto")
        self.hm_focal_detection = settings.get("hm_focal_detection", True)
        
        # Pencil Shading V2 Engine settings (Engine 2V2)
        self.ps2_auto_tune = str(settings.get("ps2_auto_tune", "false")).lower() == "true"
    
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
    
    def _get_engine_type_value(self, index: int) -> str:
        """Convert combo box index to engine type string."""
        engine_map = {
            0: "auto",
            1: "pixel_reveal",
            2: "pencil_shading",
            3: "advanced_gradient",
            4: "zone_progressive",
            5: "adaptive_brush",
            6: "hybrid_multi",
            7: "pencil_shading_v2"
        }
        return engine_map.get(index, "auto")
    
    def _get_engine_type_index(self, engine_type: str) -> int:
        """Convert engine type string to combo box index."""
        index_map = {
            "auto": 0,
            "pixel_reveal": 1,
            "pencil_shading": 2,
            "advanced_gradient": 3,
            "zone_progressive": 4,
            "adaptive_brush": 5,
            "hybrid_multi": 6,
            "pencil_shading_v2": 7
        }
        return index_map.get(engine_type, 0)
    
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
            "shading_order": self._get_shading_order_value(self.shading_order_combo.currentText()),
            # Engine selection
            "engine_type": self._get_engine_type_value(self.engine_type_combo.currentIndex()),
            # Advanced Gradient Engine settings (Engine 3)
            "contour_sensitivity": str(self.ag_contour_sensitivity_slider.value() / 10.0),
            "gradient_smoothness": str(self.ag_gradient_smoothness_slider.value() / 10.0),
            "texture_detection_strength": str(self.ag_texture_strength_slider.value() / 10.0),
            "shadow_passes": str(self.ag_shadow_passes_slider.value()),
            "shadow_angle_variation": str(self.ag_shadow_angle_slider.value()),
            "brush_softness_contour": str(self.ag_brush_contour_slider.value() / 10.0),
            "brush_softness_shading": str(self.ag_brush_shading_slider.value() / 10.0),
            "pressure_variation": str(self.ag_pressure_slider.value() / 10.0),
            "phase_1_weight": str(self.ag_phase_1_weight_slider.value() / 10.0),
            "phase_2_weight": str(self.ag_phase_2_weight_slider.value() / 10.0),
            "phase_3_weight": str(self.ag_phase_3_weight_slider.value() / 10.0),
            "merge_shading_phases": str(self.ag_merge_shading_checkbox.isChecked()),
            "auto_analyze": str(self.ag_auto_analyze_checkbox.isChecked()),
            # Zone Progressive Engine settings (Engine 3D)
            "zp_num_zones": str(self.zp_num_zones_slider.value()),
            "zp_saliency_threshold": str(self.zp_saliency_slider.value() / 10.0),
            "zp_max_focal_points": str(self.zp_focal_points_slider.value()),
            "zp_animation_mode": self._get_zp_animation_mode_value(self.zp_animation_mode_combo.currentText()),
            "zp_transition_width": str(self.zp_transition_slider.value() / 10.0),
            "zp_stroke_density": str(self.zp_stroke_density_slider.value() / 10.0),
            "zp_enable_portrait": self.zp_portrait_toggle.isChecked(),
            # Adaptive Brush Engine settings (Engine 3E)
            "ab_tip_shape": self._get_ab_tip_shape_value(self.ab_tip_shape_combo.currentText()),
            "ab_pencil_hardness": str(self.ab_hardness_slider.value() / 10.0),
            "ab_pencil_sharpness": str(self.ab_sharpness_slider.value() / 10.0),
            "ab_paper_type": self._get_ab_paper_type_value(self.ab_paper_type_combo.currentText()),
            "ab_paper_texture_strength": str(self.ab_texture_strength_slider.value() / 10.0),
            "ab_pressure_variation": str(self.ab_pressure_variation_slider.value() / 10.0),
            "ab_graphite_buildup": str(self.ab_graphite_buildup_slider.value() / 10.0),
            # Hybrid Multi-Strategy Engine settings (Engine 3F)
            "hm_num_segments": str(self.hm_num_segments_slider.value()),
            "hm_min_region_area": str(self.hm_min_area_slider.value()),
            "hm_transition_width": str(self.hm_transition_width_slider.value()),
            "hm_blend_smoothness": str(self.hm_blend_smoothness_slider.value() / 20.0),
            "hm_strategy_mode": self._get_hm_strategy_mode_value(self.hm_strategy_mode_combo.currentText()),
            "hm_focal_detection": self.hm_focal_detection_checkbox.isChecked(),
            # Pencil Shading V2 Engine settings (Engine 2V2)
            "ps2_auto_tune": self.ps2_auto_tune_checkbox.isChecked() if hasattr(self, 'ps2_auto_tune_checkbox') else False
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
        """Create visual settings section with engine selection."""
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
        
        # Engine Selection section
        self._create_engine_selection(layout)
        
        # Engine-specific settings sections (will be shown/hidden based on selection)
        self._create_shading_settings(layout)
        self._create_advanced_gradient_settings(layout)
        self._create_zone_progressive_settings(layout)
        self._create_pencil_shading_v2_settings(layout)
        
        # Set initial visibility based on current engine_type
        self._on_engine_type_changed(self._get_engine_type_index(self.engine_type))
    
    def _create_engine_selection(self, layout):
        """Create engine selection dropdown."""
        group = QGroupBox("🔧 Engine Selection")
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(10)
        
        # Info label
        info_label = QLabel(
            "Select the rendering engine for the simulation. "
            "Auto-detect analyzes the image and picks the best engine."
        )
        info_label.setStyleSheet("QLabel { color: #8b7355; font-size: 10px; font-style: italic; }")
        info_label.setWordWrap(True)
        group_layout.addWidget(info_label)
        
        # Engine type dropdown
        engine_layout = QHBoxLayout()
        engine_label = QLabel("Engine:")
        engine_label.setToolTip(
            "Choose the rendering engine:\n"
            "• Auto-detect: Analyzes image complexity automatically\n"
            "• Engine 1 - Pixel Reveal: Fast, skeleton-based line art\n"
            "• Engine 2 - Pencil Shading: Hatching-based shading\n"
            "• Engine 3 - Advanced Gradient: Direction-aware gradient shading\n"
            "• Engine 3D - Zone Progressive: Focal-point-first dramatic reveal\n"
            "• Engine 3E - Adaptive Brush: Physics-based pencil simulation\n"
            "• Engine 3F - Hybrid Multi-Strategy: Multi-strategy region-based rendering\n"
            "• Engine 2V2 - Pencil Shading V2: Enhanced shading with auto-tune & organic strokes"
        )
        self.engine_type_combo = QComboBox()
        self.engine_type_combo.addItems([
            "🔍 Auto-detect",
            "✏️ Engine 1: Pixel Reveal (Line Art)",
            "🎨 Engine 2: Pencil Shading",
            "🌈 Engine 3: Advanced Gradient",
            "🎯 Engine 3D: Zone Progressive",
            "🖊️ Engine 3E: Adaptive Brush",
            "🔀 Engine 3F: Hybrid Multi-Strategy",
            "🎨 Engine 2V2: Pencil Shading V2"
        ])
        self.engine_type_combo.setCurrentIndex(self._get_engine_type_index(self.engine_type))
        self.engine_type_combo.setMinimumWidth(200)
        self.engine_type_combo.currentIndexChanged.connect(self._on_engine_type_changed)
        engine_layout.addWidget(engine_label)
        engine_layout.addStretch()
        engine_layout.addWidget(self.engine_type_combo)
        group_layout.addLayout(engine_layout)
        
        # Engine description label (updates when selection changes)
        self.engine_description_label = QLabel("")
        self.engine_description_label.setStyleSheet("QLabel { color: #6b8fa8; font-size: 10px; }")
        self.engine_description_label.setWordWrap(True)
        group_layout.addWidget(self.engine_description_label)
        self._update_engine_description(self._get_engine_type_index(self.engine_type))
        
        layout.addWidget(group)
    
    def _create_shading_settings(self, layout):
        """Create shading engine settings section for complex artwork."""
        self.shading_settings_group = QGroupBox("🎨 Shading Engine (For Complex Artwork)")
        group_layout = QVBoxLayout(self.shading_settings_group)
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
        
        layout.addWidget(self.shading_settings_group)
    
    def _create_advanced_gradient_settings(self, layout):
        """Create Advanced Gradient Engine (Engine 3) settings section."""
        self.advanced_gradient_settings_group = QGroupBox("🌈 Advanced Gradient Engine Settings")
        group_layout = QVBoxLayout(self.advanced_gradient_settings_group)
        group_layout.setSpacing(10)
        
        # Info label
        info_label = QLabel(
            "Engine 3 uses structure tensor analysis for direction-aware strokes, "
            "progressive gradient reveal, and multi-pass shadow accumulation."
        )
        info_label.setStyleSheet("QLabel { color: #8b7355; font-size: 10px; font-style: italic; }")
        info_label.setWordWrap(True)
        group_layout.addWidget(info_label)
        
        # --- Contour Sensitivity ---
        self._add_ag_slider(group_layout, "Contour Sensitivity:",
                           "How sensitive edge/contour detection is (higher = more detail)",
                           "ag_contour_sensitivity", self.contour_sensitivity,
                           min_val=1, max_val=10, divisor=10.0, suffix="")
        
        # --- Gradient Smoothness ---
        self._add_ag_slider(group_layout, "Gradient Smoothness:",
                           "Smoothness of tonal gradient transitions (higher = smoother)",
                           "ag_gradient_smoothness", self.gradient_smoothness,
                           min_val=1, max_val=10, divisor=10.0, suffix="")
        
        # --- Texture Detection Strength ---
        self._add_ag_slider(group_layout, "Texture Detection:",
                           "Strength of texture/hatching pattern detection",
                           "ag_texture_strength", self.texture_detection_strength,
                           min_val=1, max_val=10, divisor=10.0, suffix="")
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("QFrame { color: #d4c4b0; }")
        group_layout.addWidget(separator)
        
        # --- Shadow Passes ---
        shadow_passes_layout = QVBoxLayout()
        shadow_passes_layout.setSpacing(5)
        
        sp_header = QHBoxLayout()
        sp_label = QLabel("Shadow Passes:")
        sp_label.setToolTip("Number of shadow accumulation passes (more = richer darks)")
        self.ag_shadow_passes_value_label = QLabel(f"{self.shadow_passes}")
        self.ag_shadow_passes_value_label.setStyleSheet("QLabel { color: #c2785a; font-weight: bold; }")
        sp_header.addWidget(sp_label)
        sp_header.addStretch()
        sp_header.addWidget(self.ag_shadow_passes_value_label)
        shadow_passes_layout.addLayout(sp_header)
        
        self.ag_shadow_passes_slider = QSlider(Qt.Orientation.Horizontal)
        self.ag_shadow_passes_slider.setMinimum(1)
        self.ag_shadow_passes_slider.setMaximum(6)
        self.ag_shadow_passes_slider.setValue(self.shadow_passes)
        self.ag_shadow_passes_slider.valueChanged.connect(
            lambda v: self.ag_shadow_passes_value_label.setText(f"{v}")
        )
        shadow_passes_layout.addWidget(self.ag_shadow_passes_slider)
        group_layout.addLayout(shadow_passes_layout)
        
        # --- Shadow Angle Variation ---
        sa_layout = QVBoxLayout()
        sa_layout.setSpacing(5)
        
        sa_header = QHBoxLayout()
        sa_label = QLabel("Shadow Angle Variation:")
        sa_label.setToolTip("Angle variation between shadow passes (degrees)")
        self.ag_shadow_angle_value_label = QLabel(f"{int(self.shadow_angle_variation)}°")
        self.ag_shadow_angle_value_label.setStyleSheet("QLabel { color: #c2785a; font-weight: bold; }")
        sa_header.addWidget(sa_label)
        sa_header.addStretch()
        sa_header.addWidget(self.ag_shadow_angle_value_label)
        sa_layout.addLayout(sa_header)
        
        self.ag_shadow_angle_slider = QSlider(Qt.Orientation.Horizontal)
        self.ag_shadow_angle_slider.setMinimum(5)
        self.ag_shadow_angle_slider.setMaximum(90)
        self.ag_shadow_angle_slider.setValue(int(self.shadow_angle_variation))
        self.ag_shadow_angle_slider.valueChanged.connect(
            lambda v: self.ag_shadow_angle_value_label.setText(f"{v}°")
        )
        sa_layout.addWidget(self.ag_shadow_angle_slider)
        group_layout.addLayout(sa_layout)
        
        # Separator
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.Shape.HLine)
        separator2.setStyleSheet("QFrame { color: #d4c4b0; }")
        group_layout.addWidget(separator2)
        
        # --- Brush Softness (Contour) ---
        self._add_ag_slider(group_layout, "Brush Softness (Contour):",
                           "Softness of brush for contour/edge strokes (0=hard, 1=soft)",
                           "ag_brush_contour", self.brush_softness_contour,
                           min_val=0, max_val=10, divisor=10.0, suffix="")
        
        # --- Brush Softness (Shading) ---
        self._add_ag_slider(group_layout, "Brush Softness (Shading):",
                           "Softness of brush for shading/shadow strokes (0=hard, 1=soft)",
                           "ag_brush_shading", self.brush_softness_shading,
                           min_val=0, max_val=10, divisor=10.0, suffix="")
        
        # --- Pressure Variation ---
        self._add_ag_slider(group_layout, "Pressure Variation:",
                           "How much stroke pressure varies (0=uniform, 1=high variation)",
                           "ag_pressure", self.pressure_variation,
                           min_val=0, max_val=10, divisor=10.0, suffix="")
        
        # --- Separator ---
        from PySide6.QtWidgets import QFrame as QFrameSep
        separator = QFrameSep()
        separator.setFrameShape(QFrameSep.Shape.HLine)
        separator.setFrameShadow(QFrameSep.Shadow.Sunken)
        group_layout.addWidget(separator)
        
        phase_label = QLabel("Phase Weight Controls")
        phase_label.setStyleSheet("font-weight: bold; font-size: 13px; margin-top: 5px;")
        group_layout.addWidget(phase_label)

        # --- Phase 1 Weight (Lines) ---
        self._add_ag_slider(group_layout, "Phase 1 Weight (Lines):",
                           "How strongly line-drawing strokes reveal pixels (contours + edges)",
                           "ag_phase_1_weight", self.phase_1_weight,
                           min_val=0, max_val=10, divisor=10.0, suffix="")

        # --- Phase 2 Weight (Shading) ---
        self._add_ag_slider(group_layout, "Phase 2 Weight (Shading):",
                           "How strongly shading strokes reveal pixels (gradients + textures)",
                           "ag_phase_2_weight", self.phase_2_weight,
                           min_val=0, max_val=10, divisor=10.0, suffix="")

        # --- Phase 3 Weight (Dark Areas) ---
        self._add_ag_slider(group_layout, "Phase 3 Weight (Dark Areas):",
                           "How strongly dark area strokes reveal pixels (shadows + finishing)",
                           "ag_phase_3_weight", self.phase_3_weight,
                           min_val=0, max_val=10, divisor=10.0, suffix="")

        # --- Merge Shading Phases ---
        self.ag_merge_shading_checkbox = QCheckBox("Merge Shading Phases (combine phases 2+3 for medium-level images)")
        self.ag_merge_shading_checkbox.setChecked(self.merge_shading_phases)
        group_layout.addWidget(self.ag_merge_shading_checkbox)

        # --- Auto-Analyze ---
        self.ag_auto_analyze_checkbox = QCheckBox("Auto-Analyze Image (automatically set optimal phase weights)")
        self.ag_auto_analyze_checkbox.setChecked(self.auto_analyze)
        group_layout.addWidget(self.ag_auto_analyze_checkbox)
        
        layout.addWidget(self.advanced_gradient_settings_group)
    
    def _add_ag_slider(self, parent_layout, label_text: str, tooltip: str,
                      attr_prefix: str, initial_value: float,
                      min_val: int, max_val: int, divisor: float, suffix: str):
        """Helper to add a labeled slider for Advanced Gradient settings."""
        slider_layout = QVBoxLayout()
        slider_layout.setSpacing(5)
        
        header = QHBoxLayout()
        label = QLabel(label_text)
        label.setToolTip(tooltip)
        value_label = QLabel(f"{initial_value:.1f}{suffix}")
        value_label.setStyleSheet("QLabel { color: #c2785a; font-weight: bold; }")
        header.addWidget(label)
        header.addStretch()
        header.addWidget(value_label)
        slider_layout.addLayout(header)
        
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setMinimum(min_val)
        slider.setMaximum(max_val)
        slider.setValue(int(initial_value * divisor))
        slider.valueChanged.connect(
            lambda v: value_label.setText(f"{v/divisor:.1f}{suffix}")
        )
        slider_layout.addWidget(slider)
        
        # Store references as instance attributes
        setattr(self, f"{attr_prefix}_slider", slider)
        setattr(self, f"{attr_prefix}_value_label", value_label)
        
        parent_layout.addLayout(slider_layout)
    
    def _create_zone_progressive_settings(self, layout):
        """Create Zone Progressive Engine (Engine 3D) settings section."""
        self.zone_progressive_settings_group = QGroupBox("🎯 Zone Progressive Engine Settings")
        group_layout = QVBoxLayout(self.zone_progressive_settings_group)
        group_layout.setSpacing(10)
        
        # Info label
        info_label = QLabel(
            "Engine 3D reveals artwork from visually important focal points outward. "
            "It detects saliency, faces, and eyes to create dramatic unveiling animations."
        )
        info_label.setStyleSheet("QLabel { color: #8b7355; font-size: 10px; font-style: italic; }")
        info_label.setWordWrap(True)
        group_layout.addWidget(info_label)
        
        # --- Number of Zones ---
        zones_layout = QVBoxLayout()
        zones_layout.setSpacing(5)
        zones_header = QHBoxLayout()
        zones_label = QLabel("Number of Zones:")
        zones_label.setToolTip("Number of concentric reveal zones (more = finer progression)")
        self.zp_num_zones_value_label = QLabel(f"{self.zp_num_zones}")
        self.zp_num_zones_value_label.setStyleSheet("QLabel { color: #5a8f7b; font-weight: bold; }")
        zones_header.addWidget(zones_label)
        zones_header.addStretch()
        zones_header.addWidget(self.zp_num_zones_value_label)
        zones_layout.addLayout(zones_header)
        
        self.zp_num_zones_slider = QSlider(Qt.Orientation.Horizontal)
        self.zp_num_zones_slider.setMinimum(3)
        self.zp_num_zones_slider.setMaximum(25)
        self.zp_num_zones_slider.setValue(self.zp_num_zones)
        self.zp_num_zones_slider.valueChanged.connect(
            lambda v: self.zp_num_zones_value_label.setText(f"{v}")
        )
        zones_layout.addWidget(self.zp_num_zones_slider)
        group_layout.addLayout(zones_layout)
        
        # --- Saliency Threshold ---
        self._add_ag_slider(group_layout, "Saliency Threshold:",
                           "Minimum saliency for focal point detection (lower = more focal points)",
                           "zp_saliency", self.zp_saliency_threshold,
                           min_val=1, max_val=9, divisor=10.0, suffix="")
        
        # --- Max Focal Points ---
        focal_layout = QVBoxLayout()
        focal_layout.setSpacing(5)
        focal_header = QHBoxLayout()
        focal_label = QLabel("Max Focal Points:")
        focal_label.setToolTip("Maximum number of focal centers to detect")
        self.zp_focal_points_value_label = QLabel(f"{self.zp_max_focal_points}")
        self.zp_focal_points_value_label.setStyleSheet("QLabel { color: #5a8f7b; font-weight: bold; }")
        focal_header.addWidget(focal_label)
        focal_header.addStretch()
        focal_header.addWidget(self.zp_focal_points_value_label)
        focal_layout.addLayout(focal_header)
        
        self.zp_focal_points_slider = QSlider(Qt.Orientation.Horizontal)
        self.zp_focal_points_slider.setMinimum(1)
        self.zp_focal_points_slider.setMaximum(10)
        self.zp_focal_points_slider.setValue(self.zp_max_focal_points)
        self.zp_focal_points_slider.valueChanged.connect(
            lambda v: self.zp_focal_points_value_label.setText(f"{v}")
        )
        focal_layout.addWidget(self.zp_focal_points_slider)
        group_layout.addLayout(focal_layout)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("QFrame { color: #d4c4b0; }")
        group_layout.addWidget(separator)
        
        # --- Animation Mode ---
        mode_layout = QHBoxLayout()
        mode_label = QLabel("Animation Mode:")
        mode_label.setToolTip(
            "How the reveal animation plays:\n"
            "• Multi Focal: Multiple points reveal simultaneously\n"
            "• Single Focal: One center point, radial reveal\n"
            "• Spiral: Focal to edge in spiral pattern\n"
            "• Burst: Quick focal reveal, slow background"
        )
        self.zp_animation_mode_combo = QComboBox()
        self.zp_animation_mode_combo.addItems([
            "Multi Focal",
            "Single Focal",
            "Spiral",
            "Burst"
        ])
        self.zp_animation_mode_combo.setCurrentText(
            self._get_zp_animation_mode_display(self.zp_animation_mode)
        )
        mode_layout.addWidget(mode_label)
        mode_layout.addStretch()
        mode_layout.addWidget(self.zp_animation_mode_combo)
        group_layout.addLayout(mode_layout)
        
        # --- Transition Width ---
        self._add_ag_slider(group_layout, "Transition Width:",
                           "Width of smooth transition between zones (0=sharp, 1=wide)",
                           "zp_transition", self.zp_transition_width,
                           min_val=0, max_val=10, divisor=10.0, suffix="")
        
        # --- Stroke Density ---
        self._add_ag_slider(group_layout, "Stroke Density:",
                           "Density of reveal strokes within zones (0=sparse, 1=dense)",
                           "zp_stroke_density", self.zp_stroke_density,
                           min_val=1, max_val=10, divisor=10.0, suffix="")
        
        # Separator
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.Shape.HLine)
        separator2.setStyleSheet("QFrame { color: #d4c4b0; }")
        group_layout.addWidget(separator2)
        
        # --- Enable Portrait Detection ---
        portrait_layout = QHBoxLayout()
        portrait_label = QLabel("Portrait Detection:")
        portrait_label.setToolTip(
            "Enable face/eye detection for portraits. "
            "Eyes and faces are given highest priority as focal points."
        )
        self.zp_portrait_toggle = QCheckBox()
        self.zp_portrait_toggle.setChecked(self.zp_enable_portrait)
        portrait_layout.addWidget(portrait_label)
        portrait_layout.addStretch()
        portrait_layout.addWidget(self.zp_portrait_toggle)
        group_layout.addLayout(portrait_layout)
        
        layout.addWidget(self.zone_progressive_settings_group)
        
        # Engine 3E: Adaptive Brush settings
        self._create_adaptive_brush_settings(layout)
    
    def _create_adaptive_brush_settings(self, layout):
        """Create Engine 3E: Adaptive Brush settings controls."""
        
        self.adaptive_brush_settings_group = QGroupBox("🖊️ Adaptive Brush Engine Settings")
        group_layout = QVBoxLayout(self.adaptive_brush_settings_group)
        group_layout.setSpacing(8)
        
        # Tip Shape combo
        tip_layout = QHBoxLayout()
        tip_label = QLabel("Tip Shape:")
        self.ab_tip_shape_combo = QComboBox()
        self.ab_tip_shape_combo.addItems(["Round", "Chisel", "Blunt"])
        self.ab_tip_shape_combo.setCurrentText(self._get_ab_tip_shape_display(self.ab_tip_shape))
        tip_layout.addWidget(tip_label)
        tip_layout.addStretch()
        tip_layout.addWidget(self.ab_tip_shape_combo)
        group_layout.addLayout(tip_layout)
        
        # Pencil Hardness slider (0=soft 6B, 10=hard 4H)
        hardness_layout = QHBoxLayout()
        hardness_label = QLabel("Pencil Hardness (Soft 6B ↔ Hard 4H):")
        self.ab_hardness_slider = QSlider(Qt.Orientation.Horizontal)
        self.ab_hardness_slider.setRange(0, 10)
        self.ab_hardness_slider.setValue(int(self.ab_pencil_hardness * 10))
        self.ab_hardness_value = QLabel(f"{self.ab_pencil_hardness:.1f}")
        self.ab_hardness_slider.valueChanged.connect(
            lambda v: self.ab_hardness_value.setText(f"{v / 10.0:.1f}"))
        hardness_layout.addWidget(hardness_label)
        hardness_layout.addWidget(self.ab_hardness_slider)
        hardness_layout.addWidget(self.ab_hardness_value)
        group_layout.addLayout(hardness_layout)
        
        # Pencil Sharpness slider
        sharpness_layout = QHBoxLayout()
        sharpness_label = QLabel("Pencil Sharpness:")
        self.ab_sharpness_slider = QSlider(Qt.Orientation.Horizontal)
        self.ab_sharpness_slider.setRange(1, 10)
        self.ab_sharpness_slider.setValue(int(self.ab_pencil_sharpness * 10))
        self.ab_sharpness_value = QLabel(f"{self.ab_pencil_sharpness:.1f}")
        self.ab_sharpness_slider.valueChanged.connect(
            lambda v: self.ab_sharpness_value.setText(f"{v / 10.0:.1f}"))
        sharpness_layout.addWidget(sharpness_label)
        sharpness_layout.addWidget(self.ab_sharpness_slider)
        sharpness_layout.addWidget(self.ab_sharpness_value)
        group_layout.addLayout(sharpness_layout)
        
        # Paper Type combo
        paper_layout = QHBoxLayout()
        paper_label = QLabel("Paper Type:")
        self.ab_paper_type_combo = QComboBox()
        self.ab_paper_type_combo.addItems(["Smooth", "Cold Press", "Rough"])
        self.ab_paper_type_combo.setCurrentText(self._get_ab_paper_type_display(self.ab_paper_type))
        paper_layout.addWidget(paper_label)
        paper_layout.addStretch()
        paper_layout.addWidget(self.ab_paper_type_combo)
        group_layout.addLayout(paper_layout)
        
        # Paper Texture Strength slider
        tex_layout = QHBoxLayout()
        tex_label = QLabel("Paper Texture Strength:")
        self.ab_texture_strength_slider = QSlider(Qt.Orientation.Horizontal)
        self.ab_texture_strength_slider.setRange(0, 10)
        self.ab_texture_strength_slider.setValue(int(self.ab_paper_texture_strength * 10))
        self.ab_tex_value = QLabel(f"{self.ab_paper_texture_strength:.1f}")
        self.ab_texture_strength_slider.valueChanged.connect(
            lambda v: self.ab_tex_value.setText(f"{v / 10.0:.1f}"))
        tex_layout.addWidget(tex_label)
        tex_layout.addWidget(self.ab_texture_strength_slider)
        tex_layout.addWidget(self.ab_tex_value)
        group_layout.addLayout(tex_layout)
        
        # Pressure Variation slider
        press_layout = QHBoxLayout()
        press_label = QLabel("Pressure Variation:")
        self.ab_pressure_variation_slider = QSlider(Qt.Orientation.Horizontal)
        self.ab_pressure_variation_slider.setRange(0, 10)
        self.ab_pressure_variation_slider.setValue(int(self.ab_pressure_variation * 10))
        self.ab_press_value = QLabel(f"{self.ab_pressure_variation:.1f}")
        self.ab_pressure_variation_slider.valueChanged.connect(
            lambda v: self.ab_press_value.setText(f"{v / 10.0:.1f}"))
        press_layout.addWidget(press_label)
        press_layout.addWidget(self.ab_pressure_variation_slider)
        press_layout.addWidget(self.ab_press_value)
        group_layout.addLayout(press_layout)
        
        # Graphite Buildup slider
        buildup_layout = QHBoxLayout()
        buildup_label = QLabel("Graphite Buildup:")
        self.ab_graphite_buildup_slider = QSlider(Qt.Orientation.Horizontal)
        self.ab_graphite_buildup_slider.setRange(1, 10)
        self.ab_graphite_buildup_slider.setValue(int(self.ab_graphite_buildup * 10))
        self.ab_buildup_value = QLabel(f"{self.ab_graphite_buildup:.1f}")
        self.ab_graphite_buildup_slider.valueChanged.connect(
            lambda v: self.ab_buildup_value.setText(f"{v / 10.0:.1f}"))
        buildup_layout.addWidget(buildup_label)
        buildup_layout.addWidget(self.ab_graphite_buildup_slider)
        buildup_layout.addWidget(self.ab_buildup_value)
        group_layout.addLayout(buildup_layout)
        
        layout.addWidget(self.adaptive_brush_settings_group)
        
        # Engine 3F: Hybrid Multi-Strategy settings
        self._create_hybrid_multi_settings(layout)
    
    def _create_hybrid_multi_settings(self, layout):
        """Create Engine 3F: Hybrid Multi-Strategy settings controls."""
        
        self.hybrid_multi_settings_group = QGroupBox("🔀 Hybrid Multi-Strategy Engine Settings")
        group_layout = QVBoxLayout(self.hybrid_multi_settings_group)
        group_layout.setSpacing(8)
        
        # Segments slider (int, 20-500, default 100)
        seg_layout = QHBoxLayout()
        seg_label = QLabel("Segments:")
        self.hm_num_segments_slider = QSlider(Qt.Orientation.Horizontal)
        self.hm_num_segments_slider.setRange(20, 500)
        self.hm_num_segments_slider.setValue(self.hm_num_segments)
        self.hm_num_segments_value = QLabel(str(self.hm_num_segments))
        self.hm_num_segments_slider.valueChanged.connect(
            lambda v: self.hm_num_segments_value.setText(str(v)))
        seg_layout.addWidget(seg_label)
        seg_layout.addWidget(self.hm_num_segments_slider)
        seg_layout.addWidget(self.hm_num_segments_value)
        group_layout.addLayout(seg_layout)
        
        # Min Region Area slider (int, 100-5000, default 500)
        area_layout = QHBoxLayout()
        area_label = QLabel("Min Region Area:")
        self.hm_min_area_slider = QSlider(Qt.Orientation.Horizontal)
        self.hm_min_area_slider.setRange(100, 5000)
        self.hm_min_area_slider.setValue(self.hm_min_region_area)
        self.hm_min_area_value = QLabel(str(self.hm_min_region_area))
        self.hm_min_area_slider.valueChanged.connect(
            lambda v: self.hm_min_area_value.setText(str(v)))
        area_layout.addWidget(area_label)
        area_layout.addWidget(self.hm_min_area_slider)
        area_layout.addWidget(self.hm_min_area_value)
        group_layout.addLayout(area_layout)
        
        # Transition Width slider (int, 1-50, default 10)
        tw_layout = QHBoxLayout()
        tw_label = QLabel("Transition Width:")
        self.hm_transition_width_slider = QSlider(Qt.Orientation.Horizontal)
        self.hm_transition_width_slider.setRange(1, 50)
        self.hm_transition_width_slider.setValue(self.hm_transition_width)
        self.hm_transition_width_value = QLabel(str(self.hm_transition_width))
        self.hm_transition_width_slider.valueChanged.connect(
            lambda v: self.hm_transition_width_value.setText(str(v)))
        tw_layout.addWidget(tw_label)
        tw_layout.addWidget(self.hm_transition_width_slider)
        tw_layout.addWidget(self.hm_transition_width_value)
        group_layout.addLayout(tw_layout)
        
        # Blend Smoothness slider (float, 0.0-1.0, step 0.05, default 0.7)
        bs_layout = QHBoxLayout()
        bs_label = QLabel("Blend Smoothness:")
        self.hm_blend_smoothness_slider = QSlider(Qt.Orientation.Horizontal)
        self.hm_blend_smoothness_slider.setRange(0, 20)  # 0.0 to 1.0 in steps of 0.05
        self.hm_blend_smoothness_slider.setValue(int(self.hm_blend_smoothness * 20))
        self.hm_blend_smoothness_value = QLabel(f"{self.hm_blend_smoothness:.2f}")
        self.hm_blend_smoothness_slider.valueChanged.connect(
            lambda v: self.hm_blend_smoothness_value.setText(f"{v / 20.0:.2f}"))
        bs_layout.addWidget(bs_label)
        bs_layout.addWidget(self.hm_blend_smoothness_slider)
        bs_layout.addWidget(self.hm_blend_smoothness_value)
        group_layout.addLayout(bs_layout)
        
        # Strategy Mode combo
        mode_layout = QHBoxLayout()
        mode_label = QLabel("Strategy Mode:")
        self.hm_strategy_mode_combo = QComboBox()
        self.hm_strategy_mode_combo.addItems(["Auto", "Gradient Only", "Brush Only", "Full"])
        self.hm_strategy_mode_combo.setCurrentText(self._get_hm_strategy_mode_display(self.hm_strategy_mode))
        mode_layout.addWidget(mode_label)
        mode_layout.addStretch()
        mode_layout.addWidget(self.hm_strategy_mode_combo)
        group_layout.addLayout(mode_layout)
        
        # Focal Detection checkbox
        focal_layout = QHBoxLayout()
        focal_label = QLabel("Focal Detection:")
        self.hm_focal_detection_checkbox = QCheckBox()
        self.hm_focal_detection_checkbox.setChecked(self.hm_focal_detection)
        focal_layout.addWidget(focal_label)
        focal_layout.addStretch()
        focal_layout.addWidget(self.hm_focal_detection_checkbox)
        group_layout.addLayout(focal_layout)
        
        layout.addWidget(self.hybrid_multi_settings_group)
    
    def _get_hm_strategy_mode_value(self, display_text: str) -> str:
        """Convert display text to internal strategy mode value."""
        mode_map = {"Auto": "auto", "Gradient Only": "gradient_only", "Brush Only": "brush_only", "Full": "full"}
        return mode_map.get(display_text, "auto")
    
    def _get_hm_strategy_mode_display(self, mode: str) -> str:
        """Convert internal strategy mode to display text."""
        display_map = {"auto": "Auto", "gradient_only": "Gradient Only", "brush_only": "Brush Only", "full": "Full"}
        return display_map.get(mode, "Auto")
    
    def _get_ab_tip_shape_value(self, display_text: str) -> str:
        """Convert display text to internal tip shape value."""
        shape_map = {"Round": "round", "Chisel": "chisel", "Blunt": "blunt"}
        return shape_map.get(display_text, "round")
    
    def _get_ab_tip_shape_display(self, shape: str) -> str:
        """Convert internal tip shape to display text."""
        display_map = {"round": "Round", "chisel": "Chisel", "blunt": "Blunt"}
        return display_map.get(shape, "Round")
    
    def _get_ab_paper_type_value(self, display_text: str) -> str:
        """Convert display text to internal paper type value."""
        paper_map = {"Smooth": "smooth", "Cold Press": "cold_press", "Rough": "rough"}
        return paper_map.get(display_text, "cold_press")
    
    def _get_ab_paper_type_display(self, paper_type: str) -> str:
        """Convert internal paper type to display text."""
        display_map = {"smooth": "Smooth", "cold_press": "Cold Press", "rough": "Rough"}
        return display_map.get(paper_type, "Cold Press")
    
    def _get_zp_animation_mode_value(self, display_text: str) -> str:
        """Convert display text to internal animation mode value."""
        mode_map = {
            "Multi Focal": "multi_focal",
            "Single Focal": "single_focal",
            "Spiral": "spiral",
            "Burst": "burst"
        }
        return mode_map.get(display_text, "multi_focal")
    
    def _get_zp_animation_mode_display(self, mode: str) -> str:
        """Convert internal animation mode to display text."""
        display_map = {
            "multi_focal": "Multi Focal",
            "single_focal": "Single Focal",
            "spiral": "Spiral",
            "burst": "Burst"
        }
        return display_map.get(mode, "Multi Focal")
    
    def _create_pencil_shading_v2_settings(self, layout):
        """Create Pencil Shading V2 engine-specific settings section."""
        group = QGroupBox("🎨 Engine 2V2: Pencil Shading V2 Settings")
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(8)
        
        # Info label
        info_label = QLabel(
            "V2 enhancements: feathered edges, tapered strokes, smoothed sampling, "
            "natural hand wobble, soft phase thresholds, zone-interleaved drawing, "
            "resolution-aware scaling, and auto-tuning.\n"
            "Note: V2 also uses the Engine 2 shading controls above (hatching angle, stroke spacing, etc.)"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #888; font-size: 11px; margin-bottom: 4px;")
        group_layout.addWidget(info_label)
        
        # Auto-Tune checkbox
        auto_tune_layout = QHBoxLayout()
        auto_tune_label = QLabel("Auto-Tune Parameters")
        auto_tune_label.setToolTip(
            "When enabled, the engine automatically analyzes the image and sets:\n"
            "• White threshold (paper detection)\n"
            "• Edge detection sensitivity\n"
            "• Stroke spacing based on content density\n"
            "• Hatching angle perpendicular to dominant gradients\n"
            "• Cross-hatch and detail phase thresholds\n\n"
            "This eliminates the need for manual per-image tuning."
        )
        self.ps2_auto_tune_checkbox = QCheckBox()
        self.ps2_auto_tune_checkbox.setChecked(self.ps2_auto_tune)
        auto_tune_layout.addWidget(auto_tune_label)
        auto_tune_layout.addStretch()
        auto_tune_layout.addWidget(self.ps2_auto_tune_checkbox)
        group_layout.addLayout(auto_tune_layout)
        
        self.pencil_shading_v2_settings_group = group
        layout.addWidget(group)
    
    def _on_engine_type_changed(self, index: int):
        """Handle engine type selection change. Show/hide engine-specific settings."""
        self._update_engine_description(index)
        
        # Show/hide engine-specific settings groups
        # Engine 2 (Pencil Shading) settings — also visible for V2 since it shares shading controls
        if hasattr(self, 'shading_settings_group'):
            # Show for Auto-detect (0), Engine 2 (2), or Engine 2V2 (7)
            self.shading_settings_group.setVisible(index in (0, 2, 7))
        
        # Engine 3 (Advanced Gradient) settings
        if hasattr(self, 'advanced_gradient_settings_group'):
            # Show for Auto-detect (0), or Engine 3 (3)
            self.advanced_gradient_settings_group.setVisible(index in (0, 3))
        
        # Engine 3D (Zone Progressive) settings
        if hasattr(self, 'zone_progressive_settings_group'):
            # Show for Auto-detect (0), or Engine 3D (4)
            self.zone_progressive_settings_group.setVisible(index in (0, 4))
        
        # Engine 3E (Adaptive Brush) settings
        if hasattr(self, 'adaptive_brush_settings_group'):
            # Show for Auto-detect (0), or Engine 3E (5)
            self.adaptive_brush_settings_group.setVisible(index in (0, 5))
        
        # Engine 3F (Hybrid Multi-Strategy) settings
        if hasattr(self, 'hybrid_multi_settings_group'):
            # Show for Auto-detect (0), or Engine 3F (6)
            self.hybrid_multi_settings_group.setVisible(index in (0, 6))
        
        # Engine 2V2 (Pencil Shading V2) settings
        if hasattr(self, 'pencil_shading_v2_settings_group'):
            # Show for Auto-detect (0), or Engine 2V2 (7)
            self.pencil_shading_v2_settings_group.setVisible(index in (0, 7))
    
    def _update_engine_description(self, index: int):
        """Update the engine description label based on selection."""
        descriptions = {
            0: "ℹ️ Auto-detect analyzes your image and picks the best engine. "
               "Engine-specific settings below will be used if that engine is selected.",
            1: "✏️ Engine 1 (Pixel Reveal): Fast skeleton-based tracing for clean line art. "
               "Best for simple coloring book pages with no shading.",
            2: "🎨 Engine 2 (Pencil Shading): Hatching-based rendering for complex artwork. "
               "Best for images with textures and shadows.",
            3: "🌈 Engine 3 (Advanced Gradient): Direction-aware gradient shading with "
               "structure tensor analysis. Best for high-contrast pencil art with rich shadows.",
            4: "🎯 Engine 3D (Zone Progressive): Reveals artwork from visually important regions "
               "outward. Best for portraits, centered compositions, and dramatic reveals.",
            5: "🖊️ Engine 3E (Adaptive Brush): Physics-based pencil simulation with realistic tip, "
               "paper texture, and pressure dynamics. Best for organic, hand-drawn appearance.",
            6: "🔀 Engine 3F (Hybrid Multi-Strategy): Multi-strategy region-based rendering that "
               "segments the image and applies the best engine per region. Best for complex mixed-content artwork.",
            7: "🎨 Engine 2V2 (Pencil Shading V2): Enhanced pencil shading with auto-tune parameter "
               "optimization, feathered edges, organic strokes, and zone-interleaved drawing. "
               "Uses the same shading controls as Engine 2 plus auto-tuning."
        }
        if hasattr(self, 'engine_description_label'):
            self.engine_description_label.setText(descriptions.get(index, ""))
    
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
        self.pen_scale_slider.setMinimum(1)  # Minimum 0.1x scale
        self.pen_scale_slider.setMaximum(30)  # Maximum 3.0x scale
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
        
        # Engine selection
        self.engine_type_combo.setCurrentIndex(self._get_engine_type_index(self.engine_type))
        
        # Advanced Gradient Engine settings (Engine 3)
        self.ag_contour_sensitivity_slider.setValue(int(self.contour_sensitivity * 10))
        self.ag_gradient_smoothness_slider.setValue(int(self.gradient_smoothness * 10))
        self.ag_texture_strength_slider.setValue(int(self.texture_detection_strength * 10))
        self.ag_shadow_passes_slider.setValue(self.shadow_passes)
        self.ag_shadow_angle_slider.setValue(int(self.shadow_angle_variation))
        self.ag_brush_contour_slider.setValue(int(self.brush_softness_contour * 10))
        self.ag_brush_shading_slider.setValue(int(self.brush_softness_shading * 10))
        self.ag_pressure_slider.setValue(int(self.pressure_variation * 10))
        
        # Zone Progressive Engine settings (Engine 3D)
        self.zp_num_zones_slider.setValue(self.zp_num_zones)
        self.zp_saliency_slider.setValue(int(self.zp_saliency_threshold * 10))
        self.zp_focal_points_slider.setValue(self.zp_max_focal_points)
        self.zp_animation_mode_combo.setCurrentText(self._get_zp_animation_mode_display(self.zp_animation_mode))
        self.zp_transition_slider.setValue(int(self.zp_transition_width * 10))
        self.zp_stroke_density_slider.setValue(int(self.zp_stroke_density * 10))
        self.zp_portrait_toggle.setChecked(self.zp_enable_portrait)
        
        # Adaptive Brush Engine settings (Engine 3E)
        self.ab_tip_shape_combo.setCurrentText(self._get_ab_tip_shape_display(self.ab_tip_shape))
        self.ab_hardness_slider.setValue(int(self.ab_pencil_hardness * 10))
        self.ab_sharpness_slider.setValue(int(self.ab_pencil_sharpness * 10))
        self.ab_paper_type_combo.setCurrentText(self._get_ab_paper_type_display(self.ab_paper_type))
        self.ab_texture_strength_slider.setValue(int(self.ab_paper_texture_strength * 10))
        self.ab_pressure_variation_slider.setValue(int(self.ab_pressure_variation * 10))
        self.ab_graphite_buildup_slider.setValue(int(self.ab_graphite_buildup * 10))
        
        # Hybrid Multi-Strategy Engine settings (Engine 3F)
        self.hm_num_segments_slider.setValue(self.hm_num_segments)
        self.hm_min_area_slider.setValue(self.hm_min_region_area)
        self.hm_transition_width_slider.setValue(self.hm_transition_width)
        self.hm_blend_smoothness_slider.setValue(int(self.hm_blend_smoothness * 20))
        self.hm_strategy_mode_combo.setCurrentText(self._get_hm_strategy_mode_display(self.hm_strategy_mode))
        self.hm_focal_detection_checkbox.setChecked(self.hm_focal_detection)
        
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
                "--pen-scale", str(pen_scale)
                # Note: --pen-rotation removed to keep pen orientation fixed
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
        
        # Engine selection
        engine_type = self._get_engine_type_value(self.engine_type_combo.currentIndex())
        cmd.extend(["--engine-type", engine_type])
        
        # Advanced Gradient Engine settings (Engine 3)
        cmd.extend([
            "--contour-sensitivity", str(self.ag_contour_sensitivity_slider.value() / 10.0),
            "--gradient-smoothness", str(self.ag_gradient_smoothness_slider.value() / 10.0),
            "--texture-detection-strength", str(self.ag_texture_strength_slider.value() / 10.0),
            "--shadow-passes", str(self.ag_shadow_passes_slider.value()),
            "--shadow-angle-variation", str(self.ag_shadow_angle_slider.value()),
            "--brush-softness-contour", str(self.ag_brush_contour_slider.value() / 10.0),
            "--brush-softness-shading", str(self.ag_brush_shading_slider.value() / 10.0),
            "--pressure-variation", str(self.ag_pressure_slider.value() / 10.0),
            "--phase-1-weight", str(self.ag_phase_1_weight_slider.value() / 10.0),
            "--phase-2-weight", str(self.ag_phase_2_weight_slider.value() / 10.0),
            "--phase-3-weight", str(self.ag_phase_3_weight_slider.value() / 10.0),
            "--merge-shading-phases", str(self.ag_merge_shading_checkbox.isChecked()),
            "--auto-analyze", str(self.ag_auto_analyze_checkbox.isChecked()),
        ])
        
        # Zone Progressive Engine settings (Engine 3D)
        cmd.extend([
            "--zp-num-zones", str(self.zp_num_zones_slider.value()),
            "--zp-saliency-threshold", str(self.zp_saliency_slider.value() / 10.0),
            "--zp-max-focal-points", str(self.zp_focal_points_slider.value()),
            "--zp-animation-mode", self._get_zp_animation_mode_value(self.zp_animation_mode_combo.currentText()),
            "--zp-transition-width", str(self.zp_transition_slider.value() / 10.0),
            "--zp-stroke-density", str(self.zp_stroke_density_slider.value() / 10.0),
            "--zp-enable-portrait", str(self.zp_portrait_toggle.isChecked())
        ])
        
        # Adaptive Brush Engine settings (Engine 3E)
        cmd.extend([
            "--ab-tip-shape", self._get_ab_tip_shape_value(self.ab_tip_shape_combo.currentText()),
            "--ab-pencil-hardness", str(self.ab_hardness_slider.value() / 10.0),
            "--ab-pencil-sharpness", str(self.ab_sharpness_slider.value() / 10.0),
            "--ab-paper-type", self._get_ab_paper_type_value(self.ab_paper_type_combo.currentText()),
            "--ab-paper-texture-strength", str(self.ab_texture_strength_slider.value() / 10.0),
            "--ab-pressure-variation", str(self.ab_pressure_variation_slider.value() / 10.0),
            "--ab-graphite-buildup", str(self.ab_graphite_buildup_slider.value() / 10.0)
        ])
        
        # Hybrid Multi-Strategy Engine settings (Engine 3F)
        cmd.extend([
            "--hm-num-segments", str(self.hm_num_segments_slider.value()),
            "--hm-min-region-area", str(self.hm_min_area_slider.value()),
            "--hm-transition-width", str(self.hm_transition_width_slider.value()),
            "--hm-blend-smoothness", str(self.hm_blend_smoothness_slider.value() / 20.0),
            "--hm-strategy-mode", self._get_hm_strategy_mode_value(self.hm_strategy_mode_combo.currentText()),
            "--hm-focal-detection", str(self.hm_focal_detection_checkbox.isChecked())
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
