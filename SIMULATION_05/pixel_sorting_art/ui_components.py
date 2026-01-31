#!/usr/bin/env python3
"""
UI Components for Pixel Sorting Art Control Panel
==================================================
Reusable UI widgets and sections for the control panel.
Includes both PySide6 components and legacy Tkinter compatibility layer.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import shutil
from pathlib import Path

try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


# ============================================================================
# Theme Constants (Vaporwave/Cyberpunk)
# ============================================================================

THEME_COLORS = {
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


# ============================================================================
# Legacy Tkinter Components (for backward compatibility)
# ============================================================================

class ImageUploadSection:
    """Image upload section with preview (Tkinter version)."""
    
    def __init__(self, parent, uploads_folder, on_upload_callback=None, on_clear_callback=None):
        """
        Initialize image upload section.
        
        Args:
            parent: Parent widget
            uploads_folder: Path to uploads folder
            on_upload_callback: Callback when image is uploaded
            on_clear_callback: Callback when image is cleared
        """
        self.parent = parent
        self.uploads_folder = Path(uploads_folder)
        self.on_upload_callback = on_upload_callback
        self.on_clear_callback = on_clear_callback
        
        self.image_path = None
        self.preview_image = None
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Create the UI widgets."""
        # Preview area
        preview_frame = tk.Frame(
            self.parent, 
            bg=THEME_COLORS['surface'], 
            relief='solid', 
            borderwidth=1
        )
        preview_frame.pack(pady=10, padx=10, fill='x')
        
        self.preview_label = tk.Label(
            preview_frame,
            text="No image selected\n\nClick 'Upload Image' below",
            bg=THEME_COLORS['surface'],
            fg=THEME_COLORS['text_muted'],
            font=('Segoe UI', 11),
            width=25,
            height=12,
            anchor='center'
        )
        self.preview_label.pack(pady=10, padx=10)
        
        # Buttons
        btn_frame = tk.Frame(self.parent, bg=THEME_COLORS['background'])
        btn_frame.pack(pady=5)
        
        upload_btn = tk.Button(
            btn_frame,
            text="📁 Upload Image",
            command=self.upload_image,
            bg=THEME_COLORS['accent_primary'],
            fg='white',
            font=('Segoe UI', 10, 'bold'),
            cursor='hand2',
            relief='flat',
            padx=15,
            pady=8
        )
        upload_btn.pack(side='left', padx=5)
        
        clear_btn = tk.Button(
            btn_frame,
            text="✖ Clear",
            command=self.clear_image,
            bg=THEME_COLORS['error'],
            fg='white',
            font=('Segoe UI', 10),
            cursor='hand2',
            relief='flat',
            padx=15,
            pady=8
        )
        clear_btn.pack(side='left', padx=5)
    
    def upload_image(self):
        """Handle image upload."""
        filetypes = [
            ("Image files", "*.png *.jpg *.jpeg *.bmp *.gif *.webp"),
            ("All files", "*.*")
        ]
        
        filepath = filedialog.askopenfilename(
            title="Select Image for Pixel Sorting",
            filetypes=filetypes
        )
        
        if filepath and HAS_PIL:
            try:
                # Copy to uploads folder
                self.uploads_folder.mkdir(parents=True, exist_ok=True)
                filename = Path(filepath).name
                dest_path = self.uploads_folder / filename
                shutil.copy(filepath, dest_path)
                
                self.image_path = str(dest_path)
                
                # Load and display preview
                img = Image.open(filepath)
                
                # Resize for preview (maintain aspect ratio)
                max_size = (240, 200)
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
                
                self.preview_image = ImageTk.PhotoImage(img)
                self.preview_label.configure(image=self.preview_image, text='')
                
                if self.on_upload_callback:
                    self.on_upload_callback(filename)
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load image: {e}")
    
    def clear_image(self):
        """Clear the uploaded image."""
        self.image_path = None
        self.preview_image = None
        self.preview_label.configure(
            image='',
            text="No image selected\n\nClick 'Upload Image' below"
        )
        if self.on_clear_callback:
            self.on_clear_callback()
    
    def get_image_path(self):
        """Get the current image path."""
        return self.image_path


class LabeledSlider:
    """A labeled slider with value display (Tkinter version)."""
    
    def __init__(self, parent, label_text, variable, from_, to, resolution=0.1, 
                 format_func=None, on_change_callback=None):
        """
        Initialize labeled slider.
        
        Args:
            parent: Parent widget
            label_text: Label text
            variable: Tkinter variable to bind to
            from_: Minimum value
            to: Maximum value
            resolution: Step resolution
            format_func: Function to format display value
            on_change_callback: Callback on value change
        """
        self.parent = parent
        self.variable = variable
        self.format_func = format_func or (lambda x: f"{x:.1f}")
        self.on_change_callback = on_change_callback
        
        self._create_widgets(label_text, from_, to, resolution)
    
    def _create_widgets(self, label_text, from_, to, resolution):
        """Create the UI widgets."""
        # Container frame
        self.frame = tk.Frame(self.parent, bg=THEME_COLORS['background'])
        
        # Header with label and value
        header_frame = tk.Frame(self.frame, bg=THEME_COLORS['background'])
        header_frame.pack(fill='x')
        
        label = tk.Label(
            header_frame,
            text=label_text,
            bg=THEME_COLORS['background'],
            fg=THEME_COLORS['text'],
            font=('Segoe UI', 10)
        )
        label.pack(side='left')
        
        self.value_label = tk.Label(
            header_frame,
            text=self.format_func(self.variable.get()),
            bg=THEME_COLORS['background'],
            fg=THEME_COLORS['accent_primary'],
            font=('Segoe UI', 10, 'bold')
        )
        self.value_label.pack(side='right')
        
        # Slider
        self.slider = ttk.Scale(
            self.frame,
            from_=from_,
            to=to,
            variable=self.variable,
            orient='horizontal',
            command=self._on_value_changed
        )
        self.slider.pack(fill='x', pady=(5, 0))
    
    def _on_value_changed(self, value):
        """Handle value change."""
        display_value = self.format_func(float(value))
        self.value_label.configure(text=display_value)
        
        if self.on_change_callback:
            self.on_change_callback(float(value))
    
    def pack(self, **kwargs):
        """Pack the frame."""
        self.frame.pack(**kwargs)
    
    def grid(self, **kwargs):
        """Grid the frame."""
        self.frame.grid(**kwargs)


class ToggleSwitchTk(tk.Canvas):
    """Custom toggle switch widget (Tkinter version)."""
    
    def __init__(self, parent, variable=None, command=None, **kwargs):
        """
        Initialize toggle switch.
        
        Args:
            parent: Parent widget
            variable: BooleanVar to bind to
            command: Callback on toggle
        """
        super().__init__(
            parent, 
            width=50, 
            height=26, 
            bg=THEME_COLORS['background'],
            highlightthickness=0,
            **kwargs
        )
        
        self.variable = variable or tk.BooleanVar(value=False)
        self.command = command
        
        self.bind('<Button-1>', self._toggle)
        self._draw()
        
        # Trace variable changes
        self.variable.trace_add('write', lambda *args: self._draw())
    
    def _toggle(self, event=None):
        """Toggle the switch."""
        self.variable.set(not self.variable.get())
        if self.command:
            self.command()
    
    def _draw(self):
        """Draw the toggle switch."""
        self.delete('all')
        
        is_on = self.variable.get()
        
        # Background track
        if is_on:
            bg_color = THEME_COLORS['accent_primary']
        else:
            bg_color = THEME_COLORS['surface']
        
        # Draw rounded rectangle (track)
        self.create_oval(0, 0, 26, 26, fill=bg_color, outline='')
        self.create_oval(24, 0, 50, 26, fill=bg_color, outline='')
        self.create_rectangle(13, 0, 37, 26, fill=bg_color, outline='')
        
        # Draw toggle circle
        if is_on:
            circle_x = 27
            circle_color = 'white'
        else:
            circle_x = 3
            circle_color = THEME_COLORS['text_muted']
        
        self.create_oval(
            circle_x, 3, 
            circle_x + 20, 23, 
            fill=circle_color, 
            outline=''
        )
    
    def get(self):
        """Get current value."""
        return self.variable.get()
    
    def set(self, value):
        """Set current value."""
        self.variable.set(value)


class ColorStyleDropdown:
    """Dropdown for color style selection (Tkinter version)."""
    
    STYLES = [
        "Vaporwave",
        "Cyberpunk",
        "Neon Sunset",
        "Synthwave",
        "Outrun",
        "Miami Vice",
        "Retrowave",
        "Custom"
    ]
    
    def __init__(self, parent, variable=None, command=None):
        """
        Initialize dropdown.
        
        Args:
            parent: Parent widget
            variable: StringVar to bind to
            command: Callback on selection change
        """
        self.parent = parent
        self.variable = variable or tk.StringVar(value=self.STYLES[0])
        self.command = command
        
        self._create_widget()
    
    def _create_widget(self):
        """Create the combo box."""
        self.combo = ttk.Combobox(
            self.parent,
            textvariable=self.variable,
            values=self.STYLES,
            state='readonly',
            width=20
        )
        
        if self.command:
            self.combo.bind('<<ComboboxSelected>>', lambda e: self.command())
    
    def pack(self, **kwargs):
        """Pack the widget."""
        self.combo.pack(**kwargs)
    
    def grid(self, **kwargs):
        """Grid the widget."""
        self.combo.grid(**kwargs)
    
    def get(self):
        """Get current value."""
        return self.variable.get().lower().replace(' ', '_')
    
    def set(self, value):
        """Set current value."""
        display_value = value.replace('_', ' ').title()
        self.variable.set(display_value)


class SortingAlgorithmDropdown:
    """Dropdown for sorting algorithm selection (Tkinter version)."""
    
    ALGORITHMS = [
        "Quick Sort",
        "Shell Sort",
        "Bubble Sort",
        "Insertion Sort",
        "Merge Sort",
        "Heap Sort",
        "Selection Sort"
    ]
    
    def __init__(self, parent, variable=None, command=None):
        """
        Initialize dropdown.
        
        Args:
            parent: Parent widget
            variable: StringVar to bind to
            command: Callback on selection change
        """
        self.parent = parent
        self.variable = variable or tk.StringVar(value=self.ALGORITHMS[0])
        self.command = command
        
        self._create_widget()
    
    def _create_widget(self):
        """Create the combo box."""
        self.combo = ttk.Combobox(
            self.parent,
            textvariable=self.variable,
            values=self.ALGORITHMS,
            state='readonly',
            width=20
        )
        
        if self.command:
            self.combo.bind('<<ComboboxSelected>>', lambda e: self.command())
    
    def pack(self, **kwargs):
        """Pack the widget."""
        self.combo.pack(**kwargs)
    
    def grid(self, **kwargs):
        """Grid the widget."""
        self.combo.grid(**kwargs)
    
    def get(self):
        """Get current value."""
        return self.variable.get().lower().replace(' ', '_')
    
    def set(self, value):
        """Set current value."""
        display_value = value.replace('_', ' ').title()
        self.variable.set(display_value)


# ============================================================================
# PySide6 Utility Components
# ============================================================================

def create_styled_button(text, color=None, icon=None, parent=None):
    """
    Create a styled PySide6 button.
    
    Args:
        text: Button text
        color: Background color (hex string)
        icon: Icon name (for load_icon)
        parent: Parent widget
        
    Returns:
        QPushButton instance
    """
    try:
        from PySide6.QtWidgets import QPushButton
        from custom_widgets import load_icon
        
        btn = QPushButton(text, parent)
        
        if icon:
            btn.setIcon(load_icon(icon))
        
        bg_color = color or THEME_COLORS['surface_light']
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_color};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 11px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {THEME_COLORS['accent_primary']};
            }}
            QPushButton:pressed {{
                background-color: #990099;
            }}
        """)
        
        return btn
    except ImportError:
        return None


def create_gradient_button(text, parent=None):
    """
    Create a gradient PySide6 button with vaporwave colors.
    
    Args:
        text: Button text
        parent: Parent widget
        
    Returns:
        QPushButton instance
    """
    try:
        from PySide6.QtWidgets import QPushButton
        
        btn = QPushButton(text, parent)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {THEME_COLORS['accent_primary']}, 
                    stop:1 {THEME_COLORS['accent_secondary']});
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {THEME_COLORS['accent_secondary']}, 
                    stop:1 {THEME_COLORS['accent_primary']});
            }}
        """)
        
        return btn
    except ImportError:
        return None


def create_section_header(text, parent=None):
    """
    Create a styled section header label.
    
    Args:
        text: Header text
        parent: Parent widget
        
    Returns:
        QLabel instance
    """
    try:
        from PySide6.QtWidgets import QLabel
        
        label = QLabel(text, parent)
        label.setStyleSheet(f"""
            QLabel {{
                font-size: 14px;
                font-weight: bold;
                color: {THEME_COLORS['accent_primary']};
                padding: 5px 0;
            }}
        """)
        
        return label
    except ImportError:
        return None


# ============================================================================
# Export all components
# ============================================================================

__all__ = [
    # Theme
    'THEME_COLORS',
    # Tkinter components
    'ImageUploadSection',
    'LabeledSlider',
    'ToggleSwitchTk',
    'ColorStyleDropdown',
    'SortingAlgorithmDropdown',
    # PySide6 utilities
    'create_styled_button',
    'create_gradient_button',
    'create_section_header',
]
