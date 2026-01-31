#!/usr/bin/env python3
"""
Custom Widgets for Pixel Sorting Art Control Panel
===================================================
Custom PySide6 widgets including toggle switches, image upload widgets,
and configuration dialogs with vaporwave/cyberpunk theme.
"""

import shutil
from pathlib import Path

from PySide6.QtWidgets import (
    QLabel, QPushButton, QCheckBox, QFileDialog, QMessageBox, QFrame,
    QVBoxLayout, QHBoxLayout, QDialog, QComboBox
)
from PySide6.QtCore import Qt, Signal, QPoint, QSize
from PySide6.QtGui import QPixmap, QDragEnterEvent, QDropEvent, QPainter, QPen, QColor, QMouseEvent

from PIL import Image


# Theme colors for vaporwave/cyberpunk
THEME = {
    "accent_primary": "#ff00ff",     # Magenta
    "accent_secondary": "#00ffff",   # Cyan
    "background": "#1a1a2e",
    "surface": "#16213e",
    "surface_light": "#0f3460",
    "text": "#e8e8e8",
    "text_muted": "#94a3b8",
    "success": "#00ff88",
    "warning": "#ffaa00",
    "error": "#ff4466",
}


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
            pen = QPen(QColor(255, 0, 255), 2)  # Magenta color for vaporwave
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
    """Custom toggle switch widget with modern rounded design."""
    
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
            bg_color = QColor(255, 0, 255)  # #ff00ff - Magenta accent
            border_color = QColor(200, 0, 200)
        else:
            bg_color = QColor(22, 33, 62)  # #16213e - Surface
            border_color = QColor(15, 52, 96)  # #0f3460
        
        painter.setPen(QPen(border_color, 2))
        painter.setBrush(bg_color)
        painter.drawRoundedRect(0, 0, 50, 26, 13, 13)
        
        # Draw toggle circle
        if self.isChecked():
            circle_x = 26
            circle_color = QColor(255, 255, 255)  # white
        else:
            circle_x = 3
            circle_color = QColor(148, 163, 184)  # #94a3b8
        
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
        self.setStyleSheet(f"""
            #imageUploadWidget {{
                background-color: {THEME['surface']};
                border: 2px dashed {THEME['accent_primary']};
                border-radius: 8px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Preview area
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumSize(300, 300)
        self.preview_label.setStyleSheet(f"""
            QLabel {{
                color: {THEME['text_muted']};
                font-size: 14px;
                background-color: transparent;
            }}
        """)
        self._set_placeholder_text()
        layout.addWidget(self.preview_label)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        self.upload_btn = QPushButton("Upload Image")
        self.upload_btn.setIcon(load_icon("upload"))
        self.upload_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {THEME['accent_primary']};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #cc00cc;
            }}
            QPushButton:pressed {{
                background-color: #990099;
            }}
        """)
        self.upload_btn.clicked.connect(self.upload_image)
        btn_layout.addWidget(self.upload_btn)
        
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setIcon(load_icon("clear"))
        self.clear_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {THEME['surface_light']};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: #1a4a7a;
            }}
            QPushButton:pressed {{
                background-color: {THEME['surface']};
            }}
        """)
        self.clear_btn.clicked.connect(self.clear_image)
        btn_layout.addWidget(self.clear_btn)
        
        layout.addLayout(btn_layout)
    
    def _set_placeholder_text(self):
        """Set placeholder text when no image is loaded."""
        self.preview_label.setPixmap(QPixmap())
        self.preview_label.setText("📤\n\nDrop Image Here\n\nor click Upload")
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter event."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet(f"""
                #imageUploadWidget {{
                    background-color: {THEME['surface']};
                    border: 2px solid {THEME['accent_secondary']};
                    border-radius: 8px;
                }}
            """)
    
    def dragLeaveEvent(self, event):
        """Handle drag leave event."""
        self.setStyleSheet(f"""
            #imageUploadWidget {{
                background-color: {THEME['surface']};
                border: 2px dashed {THEME['accent_primary']};
                border-radius: 8px;
            }}
        """)
    
    def dropEvent(self, event: QDropEvent):
        """Handle drop event."""
        self.setStyleSheet(f"""
            #imageUploadWidget {{
                background-color: {THEME['surface']};
                border: 2px dashed {THEME['accent_primary']};
                border-radius: 8px;
            }}
        """)
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp')):
                self._load_image(file_path)
    
    def upload_image(self):
        """Handle image upload via file dialog."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Image for Pixel Sorting",
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


class ColorStyleSelector(QComboBox):
    """Dropdown selector for vaporwave/cyberpunk color styles."""
    
    styleChanged = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the combo box UI."""
        self.addItems([
            "Vaporwave",
            "Cyberpunk",
            "Neon Sunset",
            "Synthwave",
            "Outrun",
            "Miami Vice",
            "Retrowave",
            "Custom"
        ])
        
        self.setStyleSheet(f"""
            QComboBox {{
                background-color: {THEME['surface']};
                border: 1px solid {THEME['surface_light']};
                border-radius: 4px;
                padding: 8px 12px;
                color: {THEME['text']};
                font-size: 12px;
                min-width: 150px;
            }}
            QComboBox::drop-down {{
                border: none;
                padding-right: 10px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
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
        """)
        
        self.currentTextChanged.connect(self._on_style_changed)
    
    def _on_style_changed(self, style: str):
        """Handle style change."""
        self.styleChanged.emit(style.lower().replace(" ", "_"))
    
    def get_style(self) -> str:
        """Get current selected style."""
        return self.currentText().lower().replace(" ", "_")
    
    def set_style(self, style: str):
        """Set current style by name."""
        # Convert from snake_case to Title Case
        display_style = style.replace("_", " ").title()
        index = self.findText(display_style)
        if index >= 0:
            self.setCurrentIndex(index)


class SortingAlgorithmSelector(QComboBox):
    """Dropdown selector for sorting algorithms."""
    
    algorithmChanged = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the combo box UI."""
        self.addItems([
            "Quick Sort",
            "Shell Sort",
            "Bubble Sort",
            "Insertion Sort",
            "Merge Sort",
            "Heap Sort",
            "Selection Sort"
        ])
        
        self.setStyleSheet(f"""
            QComboBox {{
                background-color: {THEME['surface']};
                border: 1px solid {THEME['surface_light']};
                border-radius: 4px;
                padding: 8px 12px;
                color: {THEME['text']};
                font-size: 12px;
                min-width: 150px;
            }}
            QComboBox::drop-down {{
                border: none;
                padding-right: 10px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid {THEME['accent_secondary']};
                width: 0;
                height: 0;
            }}
            QComboBox QAbstractItemView {{
                background-color: {THEME['surface']};
                border: 1px solid {THEME['surface_light']};
                selection-background-color: {THEME['accent_secondary']};
                color: {THEME['text']};
            }}
        """)
        
        self.currentTextChanged.connect(self._on_algorithm_changed)
    
    def _on_algorithm_changed(self, algorithm: str):
        """Handle algorithm change."""
        self.algorithmChanged.emit(algorithm.lower().replace(" ", "_"))
    
    def get_algorithm(self) -> str:
        """Get current selected algorithm."""
        return self.currentText().lower().replace(" ", "_")
    
    def set_algorithm(self, algorithm: str):
        """Set current algorithm by name."""
        display_name = algorithm.replace("_", " ").title()
        index = self.findText(display_name)
        if index >= 0:
            self.setCurrentIndex(index)


class SortDirectionSelector(QComboBox):
    """Dropdown selector for sorting direction."""
    
    directionChanged = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the combo box UI."""
        self.addItems([
            "Horizontal",
            "Vertical",
            "Both",
            "Diagonal Left",
            "Diagonal Right",
            "Radial"
        ])
        
        self.setStyleSheet(f"""
            QComboBox {{
                background-color: {THEME['surface']};
                border: 1px solid {THEME['surface_light']};
                border-radius: 4px;
                padding: 8px 12px;
                color: {THEME['text']};
                font-size: 12px;
                min-width: 150px;
            }}
            QComboBox::drop-down {{
                border: none;
                padding-right: 10px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
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
        """)
        
        self.currentTextChanged.connect(self._on_direction_changed)
    
    def _on_direction_changed(self, direction: str):
        """Handle direction change."""
        self.directionChanged.emit(direction.lower().replace(" ", "_"))
    
    def get_direction(self) -> str:
        """Get current selected direction."""
        return self.currentText().lower().replace(" ", "_")
    
    def set_direction(self, direction: str):
        """Set current direction by name."""
        display_name = direction.replace("_", " ").title()
        index = self.findText(display_name)
        if index >= 0:
            self.setCurrentIndex(index)


class SortCriteriaSelector(QComboBox):
    """Dropdown selector for sorting criteria."""
    
    criteriaChanged = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the combo box UI."""
        self.addItems([
            "Brightness",
            "Hue",
            "Saturation",
            "Luminance",
            "Red Channel",
            "Green Channel",
            "Blue Channel"
        ])
        
        self.setStyleSheet(f"""
            QComboBox {{
                background-color: {THEME['surface']};
                border: 1px solid {THEME['surface_light']};
                border-radius: 4px;
                padding: 8px 12px;
                color: {THEME['text']};
                font-size: 12px;
                min-width: 150px;
            }}
            QComboBox::drop-down {{
                border: none;
                padding-right: 10px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid {THEME['accent_secondary']};
                width: 0;
                height: 0;
            }}
            QComboBox QAbstractItemView {{
                background-color: {THEME['surface']};
                border: 1px solid {THEME['surface_light']};
                selection-background-color: {THEME['accent_secondary']};
                color: {THEME['text']};
            }}
        """)
        
        self.currentTextChanged.connect(self._on_criteria_changed)
    
    def _on_criteria_changed(self, criteria: str):
        """Handle criteria change."""
        self.criteriaChanged.emit(criteria.lower().replace(" ", "_"))
    
    def get_criteria(self) -> str:
        """Get current selected criteria."""
        return self.currentText().lower().replace(" ", "_")
    
    def set_criteria(self, criteria: str):
        """Set current criteria by name."""
        display_name = criteria.replace("_", " ").title()
        index = self.findText(display_name)
        if index >= 0:
            self.setCurrentIndex(index)
