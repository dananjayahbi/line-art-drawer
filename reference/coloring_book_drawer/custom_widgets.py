#!/usr/bin/env python3
"""
Custom Widgets for Coloring Book Drawer Control Panel
======================================================
Custom PySide6 widgets including toggle switches, image upload widgets,
and configuration dialogs.
"""

import shutil
from pathlib import Path

from PySide6.QtWidgets import (
    QLabel, QPushButton, QCheckBox, QFileDialog, QMessageBox, QFrame,
    QVBoxLayout, QHBoxLayout, QDialog
)
from PySide6.QtCore import Qt, Signal, QPoint, QSize
from PySide6.QtGui import QPixmap, QDragEnterEvent, QDropEvent, QPainter, QPen, QColor, QMouseEvent

from PIL import Image


def load_icon(icon_name):
    """Load an SVG icon from the icons folder and return a QIcon.
    
    Args:
        icon_name: Name of the icon file without extension (e.g., 'upload', 'save')
    
    Returns:
        QIcon object, or empty QIcon if file not found
    """
    from PySide6.QtGui import QIcon
    ICONS_FOLDER = Path(__file__).resolve().parent / "assets" / "icons"
    icon_path = ICONS_FOLDER / f"{icon_name}.svg"
    if icon_path.exists():
        return QIcon(str(icon_path))
    return QIcon()


class ClickableImageLabel(QLabel):
    """QLabel that emits click events and can show a crosshair."""
    
    clicked = Signal(QPoint)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.crosshair_pos = None
    
    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press events."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(event.position().toPoint())
    
    def set_crosshair(self, pos: QPoint):
        """Set crosshair position and trigger repaint."""
        self.crosshair_pos = pos
        self.update()
    
    def paintEvent(self, event):
        """Paint the label with optional crosshair."""
        super().paintEvent(event)
        
        if self.crosshair_pos:
            painter = QPainter(self)
            pen = QPen(QColor(139, 92, 246), 2)  # Purple color
            painter.setPen(pen)
            
            # Draw crosshair
            size = 15
            painter.drawLine(
                self.crosshair_pos.x() - size, self.crosshair_pos.y(),
                self.crosshair_pos.x() + size, self.crosshair_pos.y()
            )
            painter.drawLine(
                self.crosshair_pos.x(), self.crosshair_pos.y() - size,
                self.crosshair_pos.x(), self.crosshair_pos.y() + size
            )
            
            # Draw circle
            painter.drawEllipse(self.crosshair_pos, 5, 5)


class ToggleSwitch(QCheckBox):
    """Custom toggle switch widget with rounded design."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(QSize(50, 26))
        # Remove indicator styling since we'll use custom painting
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
        """Handle mouse press events to toggle the switch."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.setChecked(not self.isChecked())
            event.accept()
        else:
            super().mousePressEvent(event)
    
    def paintEvent(self, event):
        """Custom paint event to draw the toggle switch."""
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
    """Image upload widget with drag & drop support and preview."""
    
    imageUploaded = Signal(str)  # Emits filename
    imageCleared = Signal()
    
    def __init__(self, uploads_folder, parent=None):
        super().__init__(parent)
        self.uploads_folder = Path(uploads_folder)
        self.image_path = None
        self.setAcceptDrops(True)
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the UI."""
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
        self.preview_label.setText("📤\n\nUpload & Drop Here\n\nDrag and drop here")
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter event."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event: QDropEvent):
        """Handle drop event."""
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp')):
                self._load_image(file_path)
    
    def upload_image(self):
        """Handle image upload via file dialog."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Line Art Image",
            "",
            "Image files (*.png *.jpg *.jpeg *.bmp *.gif *.webp);;All files (*.*)"
        )
        
        if file_path:
            self._load_image(file_path)
    
    def _load_image(self, file_path):
        """Load and display image."""
        try:
            # Copy to uploads folder
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
            
            # Convert to QPixmap
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
        """Clear the uploaded image."""
        self.image_path = None
        self._set_placeholder_text()
        self.imageCleared.emit()
    
    def get_image_path(self):
        """Get the current image path."""
        return self.image_path


class PenTipConfigDialog(QDialog):
    """Dialog for configuring pen tip position by clicking on the image."""
    
    tipSelected = Signal(int, int)  # Emits x, y coordinates
    
    def __init__(self, pen_image_path, parent=None):
        super().__init__(parent)
        self.pen_image_path = pen_image_path
        self.tip_x = 0
        self.tip_y = 0
        self.pen_pixmap = None
        self.original_pen_pixmap = None  # Keep original size
        self.scale_factor = 1.0  # Track scale factor
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the dialog UI."""
        self.setWindowTitle("Configure Pen Tip")
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
            "Click on the pen image to mark the tip position.\n"
            "The tip should be the point that touches the paper when drawing."
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
        
        # Load and display image
        try:
            self.original_pen_pixmap = QPixmap(str(self.pen_image_path))
            self.pen_pixmap = self.original_pen_pixmap
            
            # Scale if too large
            if self.pen_pixmap.width() > 500 or self.pen_pixmap.height() > 500:
                self.pen_pixmap = self.pen_pixmap.scaled(
                    500, 500,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                # Calculate scale factor
                self.scale_factor = self.pen_pixmap.width() / self.original_pen_pixmap.width()
            
            self.image_label.setPixmap(self.pen_pixmap)
        except Exception as e:
            print(f"Error loading pen image: {e}")
        
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
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
    
    def _on_image_clicked(self, pos: QPoint):
        """Handle image click to set tip position."""
        if self.pen_pixmap:
            # Get the actual image position within the label
            label_rect = self.image_label.rect()
            pixmap_rect = self.pen_pixmap.rect()
            
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
            self.image_label.set_crosshair(QPoint(display_x + int(x_offset), display_y + int(y_offset)))
    
    def get_tip_position(self):
        """Return the selected tip position."""
        return self.tip_x, self.tip_y
