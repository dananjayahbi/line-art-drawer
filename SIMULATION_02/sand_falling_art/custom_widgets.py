#!/usr/bin/env python3
"""
Custom Widgets for Sand Falling Art Control Panel
==================================================
Custom PySide6 widgets including toggle switches and image upload widgets.
"""

import shutil
from pathlib import Path

from PySide6.QtWidgets import (
    QLabel, QPushButton, QFileDialog, QMessageBox, QFrame,
    QVBoxLayout, QHBoxLayout, QCheckBox
)
from PySide6.QtCore import Qt, Signal, QSize
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


class ToggleSwitch(QCheckBox):
    """Custom toggle switch widget with rounded design."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(QSize(50, 26))
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
            circle_color = QColor(255, 255, 255)
        else:
            circle_x = 3
            circle_color = QColor(156, 163, 175)
        
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
        self.preview_label.setText("📤\n\nUpload Target Image\n\nDrag and drop here")
    
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
            "Select Target Image",
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
