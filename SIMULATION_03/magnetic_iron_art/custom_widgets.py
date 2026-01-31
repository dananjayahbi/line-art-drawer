#!/usr/bin/env python3
"""
Custom Widgets for Magnetic Iron Art Control Panel
===================================================
Custom PySide6 widgets including toggle switches, image upload widgets,
and magnet configuration dialogs.
"""

import shutil
from pathlib import Path

from PySide6.QtWidgets import (
    QLabel, QPushButton, QCheckBox, QFileDialog, QMessageBox, QFrame,
    QVBoxLayout, QHBoxLayout, QDialog
)
from PySide6.QtCore import Qt, Signal, QPoint, QSize
from PySide6.QtGui import (
    QPixmap, QDragEnterEvent, QDropEvent, QPainter, QPen, QColor, 
    QMouseEvent, QIcon
)

from PIL import Image


def load_icon(icon_name: str) -> QIcon:
    """Load an SVG icon from the assets/icons folder and return a QIcon.
    
    Args:
        icon_name: Name of the icon file without extension (e.g., 'upload', 'save')
    
    Returns:
        QIcon object, or empty QIcon if file not found
    """
    ICONS_FOLDER = Path(__file__).resolve().parent / "assets" / "icons"
    icon_path = ICONS_FOLDER / f"{icon_name}.svg"
    if icon_path.exists():
        return QIcon(str(icon_path))
    return QIcon()


class ClickableImageLabel(QLabel):
    """QLabel that emits click events and can show a crosshair overlay.
    
    This widget extends QLabel to provide click detection and optional
    crosshair drawing capabilities, useful for position selection on images.
    
    Signals:
        clicked(QPoint): Emitted when the label is clicked, contains click position.
    """
    
    clicked = Signal(QPoint)
    
    def __init__(self, parent=None):
        """Initialize the clickable image label.
        
        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self.crosshair_pos = None
    
    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press events to emit click signal.
        
        Args:
            event: The mouse event containing click information.
        """
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(event.position().toPoint())
    
    def set_crosshair(self, pos: QPoint):
        """Set crosshair position and trigger repaint.
        
        Args:
            pos: The position where the crosshair should be drawn.
        """
        self.crosshair_pos = pos
        self.update()
    
    def clear_crosshair(self):
        """Clear the crosshair from the display."""
        self.crosshair_pos = None
        self.update()
    
    def paintEvent(self, event):
        """Paint the label with optional crosshair overlay.
        
        Args:
            event: The paint event.
        """
        super().paintEvent(event)
        
        if self.crosshair_pos:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Purple crosshair color
            pen = QPen(QColor(139, 92, 246), 2)  # #8b5cf6
            painter.setPen(pen)
            
            # Draw crosshair lines
            size = 15
            painter.drawLine(
                self.crosshair_pos.x() - size, self.crosshair_pos.y(),
                self.crosshair_pos.x() + size, self.crosshair_pos.y()
            )
            painter.drawLine(
                self.crosshair_pos.x(), self.crosshair_pos.y() - size,
                self.crosshair_pos.x(), self.crosshair_pos.y() + size
            )
            
            # Draw circle around crosshair center
            painter.drawEllipse(self.crosshair_pos, 5, 5)


class ToggleSwitch(QCheckBox):
    """Custom toggle switch widget with rounded design.
    
    A modern toggle switch that replaces the standard checkbox appearance
    with a sliding pill-shaped toggle. Uses purple accent color when checked.
    
    Size: Fixed at 50x26 pixels.
    Colors:
        - Checked: Purple (#8b5cf6) background with white circle
        - Unchecked: Gray (#374151) background with gray circle
    """
    
    def __init__(self, parent=None):
        """Initialize the toggle switch.
        
        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self.setFixedSize(QSize(50, 26))
        # Remove default indicator styling for custom painting
        self.setStyleSheet("""
            QCheckBox {
                spacing: 0px;
            }
            QCheckBox::indicator {
                width: 0px;
                height: 0px;
            }
        """)
    
    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press events to toggle the switch.
        
        Args:
            event: The mouse event.
        """
        if event.button() == Qt.MouseButton.LeftButton:
            self.setChecked(not self.isChecked())
            event.accept()
        else:
            super().mousePressEvent(event)
    
    def paintEvent(self, event):
        """Custom paint event to draw the toggle switch.
        
        Args:
            event: The paint event.
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw background track
        if self.isChecked():
            bg_color = QColor(139, 92, 246)  # #8b5cf6
            border_color = QColor(124, 58, 237)  # #7c3aed
        else:
            bg_color = QColor(55, 65, 81)  # #374151
            border_color = QColor(75, 85, 99)  # #4b5563
        
        painter.setPen(QPen(border_color, 2))
        painter.setBrush(bg_color)
        painter.drawRoundedRect(0, 0, 50, 26, 13, 13)
        
        # Draw toggle circle
        if self.isChecked():
            circle_x = 26
            circle_color = QColor(255, 255, 255)  # white
        else:
            circle_x = 3
            circle_color = QColor(156, 163, 175)  # #9ca3af
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(circle_color)
        painter.drawEllipse(circle_x, 3, 20, 20)


class ImageUploadWidget(QFrame):
    """Image upload widget with drag & drop support and preview.
    
    Provides a drag-and-drop area for uploading images with visual preview.
    Uploaded images are copied to a designated uploads folder.
    
    Signals:
        imageUploaded(str): Emitted when an image is uploaded, contains filename.
        imageCleared(): Emitted when the image is cleared.
    
    Styling:
        - Dark background (#1f2937)
        - Dashed border (#4b5563)
        - Purple upload button
    """
    
    imageUploaded = Signal(str)  # Emits filename
    imageCleared = Signal()
    
    def __init__(self, uploads_folder: str, parent=None):
        """Initialize the image upload widget.
        
        Args:
            uploads_folder: Path to the folder where uploaded images will be copied.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self.uploads_folder = Path(uploads_folder)
        self.image_path = None
        self.setAcceptDrops(True)
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the widget UI components."""
        self.setObjectName("imageUploadWidget")
        self.setStyleSheet("""
            #imageUploadWidget {
                background-color: #1f2937;
                border: 2px dashed #4b5563;
                border-radius: 8px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Preview area
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumSize(300, 300)
        self.preview_label.setStyleSheet("""
            QLabel {
                color: #9ca3af;
                font-size: 14px;
                background-color: transparent;
            }
        """)
        self._set_placeholder_text()
        layout.addWidget(self.preview_label)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        self.upload_btn = QPushButton("Upload Image")
        self.upload_btn.setIcon(load_icon("upload"))
        self.upload_btn.setStyleSheet("""
            QPushButton {
                background-color: #8b5cf6;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7c3aed;
            }
            QPushButton:pressed {
                background-color: #6d28d9;
            }
        """)
        self.upload_btn.clicked.connect(self.upload_image)
        btn_layout.addWidget(self.upload_btn)
        
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setIcon(load_icon("clear"))
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #374151;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #4b5563;
            }
            QPushButton:pressed {
                background-color: #1f2937;
            }
        """)
        self.clear_btn.clicked.connect(self.clear_image)
        btn_layout.addWidget(self.clear_btn)
        
        layout.addLayout(btn_layout)
    
    def _set_placeholder_text(self):
        """Set placeholder text when no image is loaded."""
        self.preview_label.setPixmap(QPixmap())
        self.preview_label.setText("📤\n\nUpload Image\n\nDrag and drop here")
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter event for drag & drop support.
        
        Args:
            event: The drag enter event.
        """
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event: QDropEvent):
        """Handle drop event to load dropped image.
        
        Args:
            event: The drop event containing file URLs.
        """
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp')):
                self._load_image(file_path)
    
    def upload_image(self):
        """Handle image upload via file dialog."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Target Image",
            "",
            "Image files (*.png *.jpg *.jpeg *.bmp *.gif *.webp);;All files (*.*)"
        )
        
        if file_path:
            self._load_image(file_path)
    
    def _load_image(self, file_path: str):
        """Load and display an image from the given file path.
        
        Args:
            file_path: Path to the image file to load.
        """
        try:
            # Create uploads folder if it doesn't exist
            self.uploads_folder.mkdir(parents=True, exist_ok=True)
            filename = Path(file_path).name
            dest_path = self.uploads_folder / filename
            shutil.copy(file_path, dest_path)
            
            self.image_path = str(dest_path)
            
            # Load and display preview
            img = Image.open(file_path)
            
            # Resize for preview (maintain aspect ratio)
            max_size = (280, 280)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Convert to QPixmap via temporary file
            img_path_temp = self.uploads_folder / f"_preview_{filename}"
            img.save(img_path_temp)
            pixmap = QPixmap(str(img_path_temp))
            img_path_temp.unlink()  # Clean up temp file
            
            self.preview_label.setPixmap(pixmap)
            self.preview_label.setText("")
            
            self.imageUploaded.emit(filename)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load image: {e}")
    
    def clear_image(self):
        """Clear the uploaded image and reset to placeholder."""
        self.image_path = None
        self._set_placeholder_text()
        self.imageCleared.emit()
    
    def get_image_path(self) -> str:
        """Get the current uploaded image path.
        
        Returns:
            The path to the uploaded image, or None if no image is uploaded.
        """
        return self.image_path


class MagnetConfigDialog(QDialog):
    """Dialog for configuring magnet tip position by clicking on the image.
    
    Allows users to click on a magnet image to define the tip position
    (the point that creates the magnetic field center). The tip position
    is used to accurately position the magnetic field origin during rendering.
    
    Signals:
        tipSelected(int, int): Emitted when tip position is selected, contains x, y coordinates.
    """
    
    tipSelected = Signal(int, int)  # Emits x, y coordinates
    
    def __init__(self, magnet_image_path: str, parent=None):
        """Initialize the magnet configuration dialog.
        
        Args:
            magnet_image_path: Path to the magnet image file.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self.magnet_image_path = magnet_image_path
        self.tip_x = 0
        self.tip_y = 0
        self.magnet_pixmap = None
        self.original_magnet_pixmap = None
        self.scale_factor = 1.0
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the dialog UI components."""
        self.setWindowTitle("Configure Magnet Tip")
        self.setModal(True)
        self.setMinimumSize(600, 600)
        
        self.setStyleSheet("""
            QDialog {
                background-color: #111827;
            }
            QLabel {
                color: #d1d5db;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Instructions
        instructions = QLabel(
            "Click on the magnet image to mark the tip position.\n"
            "The tip is the point where the magnetic field is centered."
        )
        instructions.setStyleSheet("""
            QLabel {
                background-color: #1f2937;
                padding: 15px;
                border-radius: 8px;
                color: #f3f4f6;
                font-size: 12px;
            }
        """)
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Image display with click detection
        self.image_label = ClickableImageLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.clicked.connect(self._on_image_clicked)
        
        # Load and display magnet image
        try:
            self.original_magnet_pixmap = QPixmap(str(self.magnet_image_path))
            self.magnet_pixmap = self.original_magnet_pixmap
            
            # Scale if too large
            if self.magnet_pixmap.width() > 500 or self.magnet_pixmap.height() > 500:
                self.magnet_pixmap = self.magnet_pixmap.scaled(
                    500, 500,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                # Calculate scale factor for coordinate mapping
                self.scale_factor = self.magnet_pixmap.width() / self.original_magnet_pixmap.width()
            
            self.image_label.setPixmap(self.magnet_pixmap)
        except Exception as e:
            print(f"Error loading magnet image: {e}")
        
        layout.addWidget(self.image_label, 1)
        
        # Coordinates display
        self.coords_label = QLabel("Tip position: Not set")
        self.coords_label.setStyleSheet("""
            QLabel {
                color: #8b5cf6;
                font-weight: bold;
                font-size: 12px;
            }
        """)
        self.coords_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.coords_label)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        save_btn = QPushButton("Save Tip Position")
        save_btn.setIcon(load_icon("save"))
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #22c55e;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #16a34a;
            }
            QPushButton:pressed {
                background-color: #15803d;
            }
        """)
        save_btn.clicked.connect(self.accept)
        btn_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #374151;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #4b5563;
            }
            QPushButton:pressed {
                background-color: #1f2937;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
    
    def _on_image_clicked(self, pos: QPoint):
        """Handle image click to set tip position.
        
        Args:
            pos: The click position relative to the image label.
        """
        if self.magnet_pixmap:
            # Get the actual image position within the label
            label_rect = self.image_label.rect()
            pixmap_rect = self.magnet_pixmap.rect()
            
            # Calculate offset to center the pixmap in the label
            x_offset = (label_rect.width() - pixmap_rect.width()) / 2
            y_offset = (label_rect.height() - pixmap_rect.height()) / 2
            
            # Calculate position relative to the displayed pixmap
            display_x = int(pos.x() - x_offset)
            display_y = int(pos.y() - y_offset)
            
            # Clamp to displayed image bounds
            display_x = max(0, min(display_x, pixmap_rect.width()))
            display_y = max(0, min(display_y, pixmap_rect.height()))
            
            # Scale back to original image coordinates
            self.tip_x = int(display_x / self.scale_factor)
            self.tip_y = int(display_y / self.scale_factor)
            
            self.coords_label.setText(f"Tip position: ({self.tip_x}, {self.tip_y})")
            
            # Redraw with crosshair at display coordinates
            self.image_label.set_crosshair(
                QPoint(display_x + int(x_offset), display_y + int(y_offset))
            )
    
    def get_tip_position(self) -> tuple:
        """Return the selected tip position.
        
        Returns:
            Tuple of (x, y) coordinates for the magnet tip position.
        """
        return self.tip_x, self.tip_y
    
    def set_initial_tip_position(self, x: int, y: int):
        """Set an initial tip position (for editing existing configuration).
        
        Args:
            x: The x coordinate of the tip.
            y: The y coordinate of the tip.
        """
        self.tip_x = x
        self.tip_y = y
        self.coords_label.setText(f"Tip position: ({self.tip_x}, {self.tip_y})")
        
        # Calculate display coordinates and show crosshair
        if self.magnet_pixmap:
            label_rect = self.image_label.rect()
            pixmap_rect = self.magnet_pixmap.rect()
            
            x_offset = (label_rect.width() - pixmap_rect.width()) / 2
            y_offset = (label_rect.height() - pixmap_rect.height()) / 2
            
            display_x = int(x * self.scale_factor)
            display_y = int(y * self.scale_factor)
            
            self.image_label.set_crosshair(
                QPoint(display_x + int(x_offset), display_y + int(y_offset))
            )
