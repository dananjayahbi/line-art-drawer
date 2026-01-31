#!/usr/bin/env python3
"""
Sand Falling Art - Control Panel Main Window (PySide6)
=======================================================
Main control panel window implementation for the sand falling art simulation.
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
    QFileDialog, QMessageBox, QScrollArea, QFrame, QSpinBox
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont

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
        self._update_ui_from_settings()
        self._update_frame_count()
        
        # Auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self._update_frame_count)
        self.refresh_timer.start(2000)
    
    def _init_variables(self):
        """Initialize all settings variables."""
        self.width = 1600  # 4:3 aspect ratio
        self.height = 1200
        self.fps = 60
        self.particle_size = 2.0
        self.spawn_rate = 10
        self.gravity = 980.0
        self.particle_glow = True
        self.show_target_outline = False
        self.antialiasing = True
        self.use_gpu = True  # GPU acceleration
        self.auto_record = False
        self.video_fps = 60
        self.video_quality = "high"
    
    def _load_settings(self):
        """Load all settings from file."""
        settings = self.settings_manager.load_settings()
        
        self.width = int(settings.get("width", "1600"))
        self.height = int(settings.get("height", "1200"))
        self.fps = 60
        self.particle_size = float(settings.get("particle_size", 2.0))
        self.spawn_rate = int(settings.get("spawn_rate", 10))
        self.gravity = float(settings.get("gravity", 980.0))
        self.particle_glow = settings.get("particle_glow", True)
        self.show_target_outline = settings.get("show_target_outline", False)
        self.antialiasing = settings.get("antialiasing", True)
        self.use_gpu = settings.get("use_gpu", True)
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
        
        settings = {
            "width": str(width),
            "height": str(height),
            "fps": "60",
            "particle_size": str(self.particle_size_slider.value() / 10.0),
            "spawn_rate": str(self.spawn_rate_slider.value()),
            "gravity": str(self.gravity_slider.value()),
            "use_gpu": self.gpu_toggle.isChecked(),
            "particle_glow": self.particle_glow_toggle.isChecked(),
            "show_target_outline": self.target_outline_toggle.isChecked(),
            "antialiasing": self.antialiasing_toggle.isChecked(),
            "auto_record": self.auto_record_toggle.isChecked(),
            "video_fps": "60",
            "video_quality": self.video_quality_combo.currentText()
        }
        
        if self.settings_manager.save_settings(settings):
            self._update_status("Settings saved successfully!")
            QMessageBox.information(self, "Success", "Settings saved successfully!")
    
    def _setup_ui(self):
        """Setup the main UI."""
        self.setWindowTitle("Sand Falling Art - Control Panel")
        self.setMinimumSize(1366, 768)
        self.showMaximized()
        
        # Set theme
        self.setStyleSheet("""
            QMainWindow { background-color: #f5ebe0; }
            QWidget { background-color: #f5ebe0; color: #4a3428; font-family: 'Segoe UI', Arial; font-size: 11px; }
            QGroupBox { background-color: #faf7f2; border: 1px solid #d4c4b0; border-radius: 8px; 
                       margin-top: 12px; padding-top: 20px; font-weight: bold; color: #5c4033; }
            QLabel { color: #6b5444; background-color: transparent; }
            QLineEdit, QSpinBox { background-color: #ffffff; border: 1px solid #d4c4b0; border-radius: 4px; padding: 6px; }
            QSlider::groove:horizontal { height: 6px; background: #d4c4b0; border-radius: 3px; }
            QSlider::handle:horizontal { background: #c2785a; width: 16px; height: 16px; margin: -5px 0; border-radius: 8px; }
            QPushButton { background-color: #d4a88a; color: #4a3428; border: none; border-radius: 6px; 
                         padding: 8px 16px; font-weight: 500; }
            QPushButton:hover { background-color: #c2785a; color: white; }
        """)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # Header
        self._create_header(main_layout)
        
        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        content_layout = QVBoxLayout(scroll_content)
        
        # 3 columns
        columns_layout = QHBoxLayout()
        
        # Left column
        left_column = QVBoxLayout()
        self._create_image_upload_section(left_column)
        self._create_window_settings(left_column)
        left_column.addStretch()
        
        # Middle column
        middle_column = QVBoxLayout()
        self._create_physics_settings(middle_column)
        self._create_visual_settings(middle_column)
        middle_column.addStretch()
        
        # Right column
        right_column = QVBoxLayout()
        self._create_recording_settings(right_column)
        self._create_frame_management(right_column)
        right_column.addStretch()
        
        columns_layout.addLayout(left_column, 1)
        columns_layout.addLayout(middle_column, 1)
        columns_layout.addLayout(right_column, 1)
        
        content_layout.addLayout(columns_layout)
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll, 1)
        
        # Footer
        self._create_footer(main_layout)
    
    def _create_header(self, layout):
        """Create header section."""
        header = QLabel("⏳ Sand Falling Art Simulation")
        font = QFont('Segoe UI', 24)
        font.setBold(True)
        header.setFont(font)
        header.setStyleSheet("color: #5c4033; padding: 10px;")
        layout.addWidget(header)
    
    def _create_image_upload_section(self, layout):
        """Create image upload section."""
        group = QGroupBox("Target Image")
        group_layout = QVBoxLayout()
        
        self.image_upload = ImageUploadWidget(UPLOADS_FOLDER)
        self.image_upload.imageUploaded.connect(self._on_image_uploaded)
        group_layout.addWidget(self.image_upload)
        
        group.setLayout(group_layout)
        layout.addWidget(group)
    
    def _create_window_settings(self, layout):
        """Create window settings section."""
        group = QGroupBox("Window Settings")
        grid = QGridLayout()
        
        grid.addWidget(QLabel("Width:"), 0, 0)
        self.width_input = QLineEdit(str(self.width))
        grid.addWidget(self.width_input, 0, 1)
        
        grid.addWidget(QLabel("Height:"), 1, 0)
        self.height_input = QLineEdit(str(self.height))
        grid.addWidget(self.height_input, 1, 1)
        
        grid.addWidget(QLabel("FPS:"), 2, 0)
        fps_label = QLabel("60 (Fixed)")
        fps_label.setStyleSheet("color: #8b5cf6; font-weight: bold;")
        grid.addWidget(fps_label, 2, 1)
        
        group.setLayout(grid)
        layout.addWidget(group)
    
    def _create_physics_settings(self, layout):
        """Create physics settings section."""
        group = QGroupBox("Physics Settings")
        grid = QGridLayout()
        
        # Particle size
        grid.addWidget(QLabel("Particle Size:"), 0, 0)
        self.particle_size_slider = QSlider(Qt.Orientation.Horizontal)
        self.particle_size_slider.setRange(10, 50)
        self.particle_size_slider.setValue(int(self.particle_size * 10))
        self.particle_size_value_label = QLabel(f"{self.particle_size:.1f}px")
        self.particle_size_slider.valueChanged.connect(
            lambda v: self.particle_size_value_label.setText(f"{v/10:.1f}px")
        )
        grid.addWidget(self.particle_size_slider, 0, 1)
        grid.addWidget(self.particle_size_value_label, 0, 2)
        
        # Spawn rate
        grid.addWidget(QLabel("Spawn Rate:"), 1, 0)
        self.spawn_rate_slider = QSlider(Qt.Orientation.Horizontal)
        self.spawn_rate_slider.setRange(1, 50)
        self.spawn_rate_slider.setValue(self.spawn_rate)
        self.spawn_rate_value_label = QLabel(f"{self.spawn_rate} /frame")
        self.spawn_rate_slider.valueChanged.connect(
            lambda v: self.spawn_rate_value_label.setText(f"{v} /frame")
        )
        grid.addWidget(self.spawn_rate_slider, 1, 1)
        grid.addWidget(self.spawn_rate_value_label, 1, 2)
        
        # Gravity
        grid.addWidget(QLabel("Gravity:"), 2, 0)
        self.gravity_slider = QSlider(Qt.Orientation.Horizontal)
        self.gravity_slider.setRange(100, 2000)
        self.gravity_slider.setValue(int(self.gravity))
        self.gravity_value_label = QLabel(f"{self.gravity:.0f}")
        self.gravity_slider.valueChanged.connect(
            lambda v: self.gravity_value_label.setText(f"{v:.0f}")
        )
        grid.addWidget(self.gravity_slider, 2, 1)
        grid.addWidget(self.gravity_value_label, 2, 2)
        
        group.setLayout(grid)
        layout.addWidget(group)
    
    def _create_visual_settings(self, layout):
        """Create visual settings section."""
        group = QGroupBox("Visual Settings")
        grid = QGridLayout()
        
        grid.addWidget(QLabel("GPU Acceleration:"), 0, 0)
        self.gpu_toggle = ToggleSwitch()
        self.gpu_toggle.setChecked(self.use_gpu)
        grid.addWidget(self.gpu_toggle, 0, 1)
        
        grid.addWidget(QLabel("Particle Glow:"), 1, 0)
        self.particle_glow_toggle = ToggleSwitch()
        self.particle_glow_toggle.setChecked(self.particle_glow)
        grid.addWidget(self.particle_glow_toggle, 1, 1)
        
        grid.addWidget(QLabel("Target Outline:"), 2, 0)
        self.target_outline_toggle = ToggleSwitch()
        self.target_outline_toggle.setChecked(self.show_target_outline)
        grid.addWidget(self.target_outline_toggle, 2, 1)
        
        grid.addWidget(QLabel("Anti-aliasing:"), 3, 0)
        self.antialiasing_toggle = ToggleSwitch()
        self.antialiasing_toggle.setChecked(self.antialiasing)
        grid.addWidget(self.antialiasing_toggle, 3, 1)
        
        group.setLayout(grid)
        layout.addWidget(group)
    
    def _create_recording_settings(self, layout):
        """Create recording settings section."""
        group = QGroupBox("Recording Settings")
        grid = QGridLayout()
        
        grid.addWidget(QLabel("Auto Record:"), 0, 0)
        self.auto_record_toggle = ToggleSwitch()
        self.auto_record_toggle.setChecked(self.auto_record)
        grid.addWidget(self.auto_record_toggle, 0, 1)
        
        grid.addWidget(QLabel("Video Quality:"), 1, 0)
        self.video_quality_combo = QComboBox()
        self.video_quality_combo.addItems(["low", "medium", "high", "ultra"])
        self.video_quality_combo.setCurrentText(self.video_quality)
        grid.addWidget(self.video_quality_combo, 1, 1)
        
        group.setLayout(grid)
        layout.addWidget(group)
    
    def _create_frame_management(self, layout):
        """Create frame management section."""
        group = QGroupBox("Frame Management")
        group_layout = QVBoxLayout()
        
        self.frame_count_label = QLabel("Frames: 0")
        self.frame_count_label.setStyleSheet("font-weight: bold; color: #8b5cf6;")
        group_layout.addWidget(self.frame_count_label)
        
        clear_frames_btn = QPushButton("Clear Frames")
        clear_frames_btn.clicked.connect(self._clear_frames)
        group_layout.addWidget(clear_frames_btn)
        
        generate_video_btn = QPushButton("Generate Video")
        generate_video_btn.clicked.connect(self._generate_video)
        group_layout.addWidget(generate_video_btn)
        
        group.setLayout(group_layout)
        layout.addWidget(group)
    
    def _create_footer(self, layout):
        """Create footer with action buttons."""
        footer = QHBoxLayout()
        
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #6b5444;")
        footer.addWidget(self.status_label)
        
        footer.addStretch()
        
        save_btn = QPushButton("💾 Save Settings")
        save_btn.clicked.connect(self._save_settings)
        footer.addWidget(save_btn)
        
        run_btn = QPushButton("▶️ Run Simulation")
        run_btn.setStyleSheet("background-color: #22c55e; color: white; padding: 10px 30px; font-size: 12px;")
        run_btn.clicked.connect(self._run_simulation)
        footer.addWidget(run_btn)
        
        layout.addLayout(footer)
    
    def _update_ui_from_settings(self):
        """Update UI elements from loaded settings."""
        self.width_input.setText(str(self.width))
        self.height_input.setText(str(self.height))
        self.particle_size_slider.setValue(int(self.particle_size * 10))
        self.spawn_rate_slider.setValue(self.spawn_rate)
        self.gpu_toggle.setChecked(self.use_gpu)
        self.gravity_slider.setValue(int(self.gravity))
        self.particle_glow_toggle.setChecked(self.particle_glow)
        self.target_outline_toggle.setChecked(self.show_target_outline)
        self.antialiasing_toggle.setChecked(self.antialiasing)
        self.auto_record_toggle.setChecked(self.auto_record)
        self.video_quality_combo.setCurrentText(self.video_quality)
    
    def _update_status(self, message):
        """Update status label."""
        self.status_label.setText(message)
    
    def _update_frame_count(self):
        """Update frame count display."""
        if FRAMES_FOLDER.exists():
            frames = list(FRAMES_FOLDER.glob("frame_*.png"))
            self.frame_count_label.setText(f"Frames: {len(frames)}")
    
    def _on_image_uploaded(self, filename):
        """Handle image upload."""
        self._update_status(f"Image uploaded: {filename}")
    
    def _run_simulation(self):
        """Run the simulation."""
        image_path = self.image_upload.get_image_path()
        if not image_path:
            QMessageBox.warning(self, "No Image", "Please upload a target image first!")
            return
        
        self._save_settings()
        
        # Build command
        cmd = [
            sys.executable,
            str(SIMULATION_DIR / "main.py"),
            "--image", image_path,
            "--width", self.width_input.text(),
            "--height", self.height_input.text(),
            "--particle-size", str(self.particle_size_slider.value() / 10.0),
            "--spawn-rate", str(self.spawn_rate_slider.value()),
            "--gravity", str(self.gravity_slider.value())
        ]
        
        if self.auto_record_toggle.isChecked():
            cmd.append("--record")
        
        self._update_status("Starting simulation...")
        
        try:
            self.simulation_process = subprocess.Popen(cmd)
            QMessageBox.information(self, "Simulation Started", "Sand falling art simulation is now running!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start simulation: {e}")
    
    def _clear_frames(self):
        """Clear all frames."""
        reply = QMessageBox.question(
            self, "Clear Frames",
            "Are you sure you want to delete all frames?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                for frame in FRAMES_FOLDER.glob("frame_*.png"):
                    frame.unlink()
                self._update_frame_count()
                self._update_status("Frames cleared")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to clear frames: {e}")
    
    def _generate_video(self):
        """Generate video from frames."""
        frames = list(FRAMES_FOLDER.glob("frame_*.png"))
        if not frames:
            QMessageBox.warning(self, "No Frames", "No frames available for video generation!")
            return
        
        output_dir = BASE_DIR / "output" / "videos"
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_path = output_dir / f"sand_art_{timestamp}.mp4"
        
        quality_map = {"low": 28, "medium": 23, "high": 18, "ultra": 15}
        crf = quality_map[self.video_quality_combo.currentText()]
        
        self.video_thread = VideoGenerationThread(FRAMES_FOLDER, output_path, 60, crf, 60)
        self.video_thread.finished.connect(self._on_video_finished)
        self.video_thread.error.connect(self._on_video_error)
        self.video_thread.start()
        
        self._update_status("Generating video...")
    
    def _on_video_finished(self, output_path):
        """Handle video generation completion."""
        self._update_status("Video generated successfully!")
        QMessageBox.information(self, "Success", f"Video saved to:\n{output_path}")
    
    def _on_video_error(self, error_msg):
        """Handle video generation error."""
        self._update_status("Video generation failed")
        QMessageBox.critical(self, "Error", error_msg)


def main():
    """Main entry point."""
    app = QApplication(sys.argv)
    window = ControlPanel()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
