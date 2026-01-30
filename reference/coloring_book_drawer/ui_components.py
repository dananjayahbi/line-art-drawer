#!/usr/bin/env python3
"""
UI Components for Coloring Book Drawer Control Panel
=====================================================
Reusable UI widgets and sections for the control panel.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import shutil
from pathlib import Path
from PIL import Image, ImageTk


class ImageUploadSection:
    """Image upload section with preview."""
    
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
        preview_frame = tk.Frame(self.parent, bg='#16213e', relief='solid', borderwidth=1)
        preview_frame.pack(pady=10, padx=10, fill='x')
        
        self.preview_label = tk.Label(
            preview_frame,
            text="No image selected\n\nClick 'Upload Image' below",
            bg='#16213e',
            fg='#94a3b8',
            font=('Segoe UI', 11),
            width=25,
            height=12,
            anchor='center'
        )
        self.preview_label.pack(pady=10, padx=10)
        
        # Buttons
        btn_frame = tk.Frame(self.parent, bg='#1a1a2e')
        btn_frame.pack(pady=5)
        
        upload_btn = tk.Button(
            btn_frame,
            text="📁 Upload Image",
            command=self.upload_image,
            bg='#8b5cf6',
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
            bg='#ef4444',
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
            title="Select Line Art Image",
            filetypes=filetypes
        )
        
        if filepath:
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
    """A labeled slider with value display."""
    
    def __init__(self, parent, label_text, variable, from_, to, resolution=0.1, 
                 format_func=None, on_change_callback=None):
        """
        Initialize labeled slider.
        
        Args:
            parent: Parent widget
            label_text: Label text
            variable: tk Variable to bind to
            from_: Minimum value
            to: Maximum value
            resolution: Step size
            format_func: Function to format the value display
            on_change_callback: Callback when value changes
        """
        self.parent = parent
        self.label_text = label_text
        self.variable = variable
        self.from_ = from_
        self.to = to
        self.resolution = resolution
        self.format_func = format_func or (lambda x: f"{x:.1f}")
        self.on_change_callback = on_change_callback
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Create the slider widgets."""
        frame = tk.Frame(self.parent, bg='#1a1a2e')
        frame.pack(fill='x', pady=5, padx=10)
        
        # Label with value
        self.value_label = tk.Label(
            frame,
            text=f"{self.label_text}: {self.format_func(self.variable.get())}",
            bg='#1a1a2e',
            fg='#e2e8f0',
            font=('Segoe UI', 10)
        )
        self.value_label.pack(anchor='w')
        
        # Slider
        slider = ttk.Scale(
            frame,
            from_=self.from_,
            to=self.to,
            variable=self.variable,
            orient='horizontal'
        )
        slider.pack(fill='x', pady=2)
        
        # Bind update
        self.variable.trace_add('write', self._update_label)
    
    def _update_label(self, *args):
        """Update the label text."""
        self.value_label.config(text=f"{self.label_text}: {self.format_func(self.variable.get())}")
        if self.on_change_callback:
            self.on_change_callback()


class ResolutionPresets:
    """Resolution preset buttons."""
    
    def __init__(self, parent, on_preset_callback):
        """
        Initialize resolution presets.
        
        Args:
            parent: Parent widget
            on_preset_callback: Callback(width, height) when preset is clicked
        """
        self.parent = parent
        self.on_preset_callback = on_preset_callback
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Create preset buttons."""
        presets_frame = tk.Frame(self.parent, bg='#1a1a2e')
        presets_frame.pack(fill='x', padx=10, pady=5)
        
        tk.Label(
            presets_frame,
            text="Quick Presets:",
            bg='#1a1a2e',
            fg='#94a3b8',
            font=('Segoe UI', 9)
        ).pack(anchor='w')
        
        btn_frame = tk.Frame(presets_frame, bg='#1a1a2e')
        btn_frame.pack(fill='x', pady=2)
        
        presets = [
            ("4:5 (800x1000)", 800, 1000),
            ("1:1 (800x800)", 800, 800),
            ("16:9 (1280x720)", 1280, 720),
            ("9:16 (720x1280)", 720, 1280),
        ]
        
        for text, w, h in presets:
            btn = tk.Button(
                btn_frame,
                text=text,
                command=lambda w=w, h=h: self.on_preset_callback(w, h),
                bg='#334155',
                fg='white',
                font=('Segoe UI', 8),
                relief='flat',
                cursor='hand2',
                padx=8,
                pady=4
            )
            btn.pack(side='left', padx=2)


class StatusBar:
    """Status bar at the bottom of the window."""
    
    def __init__(self, parent):
        """
        Initialize status bar.
        
        Args:
            parent: Parent widget
        """
        self.parent = parent
        self._create_widgets()
    
    def _create_widgets(self):
        """Create status bar."""
        self.status_label = tk.Label(
            self.parent,
            text="Ready",
            bg='#0f1419',
            fg='#94a3b8',
            font=('Segoe UI', 9),
            anchor='w',
            padx=10,
            pady=5
        )
        self.status_label.pack(side='bottom', fill='x')
    
    def set_text(self, text):
        """Update status text."""
        self.status_label.configure(text=text)
    
    def get_label(self):
        """Get the label widget."""
        return self.status_label
