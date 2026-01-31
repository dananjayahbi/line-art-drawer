#!/usr/bin/env python3
"""
Settings Manager for Pixel Sorting Art
=======================================
Handles saving and loading control panel settings to/from JSON.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from tkinter import messagebox


class SettingsManager:
    """Manages saving/loading control panel settings."""
    
    def __init__(self, simulation_dir: Optional[str] = None):
        """
        Initialize settings manager.
        
        Args:
            simulation_dir: Path to the simulation directory
        """
        if simulation_dir:
            self.simulation_dir = Path(simulation_dir)
        else:
            self.simulation_dir = Path(__file__).resolve().parent
        
        self.settings_file = self.simulation_dir / "control_settings.json"
        self.default_settings = self._get_default_settings()
    
    def _get_default_settings(self) -> Dict[str, Any]:
        """Get default settings dictionary."""
        return {
            # Window/Canvas settings (9:16 vertical ratio)
            "width": "1080",
            "height": "1920",
            "fps": "60",
            "target_duration": "30.0",
            
            # Sorting algorithm settings
            "sorting_algorithm": "quick_sort",  # quick_sort, shell_sort
            "sort_direction": "horizontal",     # horizontal, vertical, both
            "sort_criteria": "brightness",      # brightness, hue
            "threshold": 0.3,                   # Scramble intensity (0-1)
            
            # Visual style settings
            "color_style": "vaporwave",         # vaporwave, cyberpunk
            "neon_glow_intensity": 0.8,         # Glow effect intensity (0-1)
            "motion_blur_strength": 0.3,        # Motion blur strength (0-1)
            
            # Animation settings
            "beat_drop_time": 15.0,             # Time in seconds for beat drop
            "beat_drop_multiplier": 5.0,        # Speed multiplier during beat drop
            "zoom_intensity": 0.1,              # Camera zoom intensity (0-1)
            "wave_speed": 0.5,                  # Cascading wave speed (lag ratio)
            
            # Pixel rendering settings
            "pixel_scale": 1.0,                 # Scale factor for pixel size
            "steps_per_frame": 10,              # Sorting steps per animation frame
            
            # Recording settings
            "auto_record": False,
            "video_fps": "60",
            "video_quality": "high",            # low, medium, high, ultra
            "video_codec": "libx264",           # Video codec
            "video_bitrate": "8000k",           # Video bitrate
            
            # Advanced settings
            "use_gpu": True,                    # Use GPU acceleration if available
            "preview_scale": 0.5,               # Preview window scale factor
            "show_progress": True,              # Show progress overlay
            "show_debug": False,                # Show debug information
        }
    
    def save_settings(self, settings_dict: Dict[str, Any]) -> bool:
        """
        Save settings to JSON file.
        
        Args:
            settings_dict: Dictionary of settings to save
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings_dict, f, indent=2)
            return True
        except Exception as e:
            try:
                messagebox.showerror("Save Error", f"Failed to save settings: {str(e)}")
            except Exception:
                print(f"Error saving settings: {e}")
            return False
    
    def load_settings(self) -> Dict[str, Any]:
        """
        Load settings from JSON file.
        
        Returns:
            dict: Settings dictionary, or default settings if file doesn't exist
        """
        if not self.settings_file.exists():
            return self.default_settings.copy()
        
        try:
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                settings = json.load(f)
            
            # Merge with defaults to handle new settings in updates
            merged = self.default_settings.copy()
            merged.update(settings)
            return merged
            
        except Exception as e:
            try:
                messagebox.showerror("Load Error", f"Failed to load settings: {str(e)}")
            except Exception:
                print(f"Error loading settings: {e}")
            return self.default_settings.copy()
    
    def reset_to_defaults(self) -> Dict[str, Any]:
        """
        Reset settings to defaults and save.
        
        Returns:
            dict: Default settings dictionary
        """
        defaults = self.default_settings.copy()
        self.save_settings(defaults)
        return defaults
    
    def get_defaults(self) -> Dict[str, Any]:
        """Get a copy of the default settings."""
        return self.default_settings.copy()
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """
        Get a specific setting value.
        
        Args:
            key: Setting key name
            default: Default value if key not found
            
        Returns:
            Setting value or default
        """
        settings = self.load_settings()
        return settings.get(key, default)
    
    def set_setting(self, key: str, value: Any) -> bool:
        """
        Set a specific setting value.
        
        Args:
            key: Setting key name
            value: Value to set
            
        Returns:
            bool: True if successful
        """
        settings = self.load_settings()
        settings[key] = value
        return self.save_settings(settings)
    
    def validate_settings(self, settings: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate settings values.
        
        Args:
            settings: Settings dictionary to validate
            
        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []
        
        # Validate numeric values
        try:
            width = int(settings.get("width", 1080))
            if width < 100 or width > 7680:
                errors.append("Width must be between 100 and 7680")
        except ValueError:
            errors.append("Width must be a valid integer")
        
        try:
            height = int(settings.get("height", 1920))
            if height < 100 or height > 7680:
                errors.append("Height must be between 100 and 7680")
        except ValueError:
            errors.append("Height must be a valid integer")
        
        try:
            fps = int(settings.get("fps", 60))
            if fps < 1 or fps > 120:
                errors.append("FPS must be between 1 and 120")
        except ValueError:
            errors.append("FPS must be a valid integer")
        
        try:
            duration = float(settings.get("target_duration", 30.0))
            if duration < 1.0 or duration > 600.0:
                errors.append("Target duration must be between 1 and 600 seconds")
        except ValueError:
            errors.append("Target duration must be a valid number")
        
        # Validate enum values
        valid_algorithms = ["quick_sort", "shell_sort"]
        if settings.get("sorting_algorithm") not in valid_algorithms:
            errors.append(f"Sorting algorithm must be one of: {valid_algorithms}")
        
        valid_directions = ["horizontal", "vertical", "both"]
        if settings.get("sort_direction") not in valid_directions:
            errors.append(f"Sort direction must be one of: {valid_directions}")
        
        valid_criteria = ["brightness", "hue"]
        if settings.get("sort_criteria") not in valid_criteria:
            errors.append(f"Sort criteria must be one of: {valid_criteria}")
        
        valid_styles = ["vaporwave", "cyberpunk"]
        if settings.get("color_style") not in valid_styles:
            errors.append(f"Color style must be one of: {valid_styles}")
        
        valid_quality = ["low", "medium", "high", "ultra"]
        if settings.get("video_quality") not in valid_quality:
            errors.append(f"Video quality must be one of: {valid_quality}")
        
        # Validate range values (0-1)
        for key in ["threshold", "neon_glow_intensity", "motion_blur_strength", 
                    "zoom_intensity", "wave_speed", "preview_scale"]:
            try:
                value = float(settings.get(key, 0.5))
                if value < 0.0 or value > 1.0:
                    errors.append(f"{key} must be between 0.0 and 1.0")
            except (ValueError, TypeError):
                errors.append(f"{key} must be a valid number")
        
        return len(errors) == 0, errors
    
    def get_resolution_presets(self) -> Dict[str, Tuple[int, int]]:
        """
        Get common resolution presets.
        
        Returns:
            Dictionary of preset names to (width, height) tuples
        """
        return {
            "TikTok/Reels (1080x1920)": (1080, 1920),
            "TikTok/Reels HD (1080x1920)": (1080, 1920),
            "YouTube Shorts (1080x1920)": (1080, 1920),
            "Instagram Story (1080x1920)": (1080, 1920),
            "Instagram Square (1080x1080)": (1080, 1080),
            "YouTube 1080p (1920x1080)": (1920, 1080),
            "YouTube 4K (3840x2160)": (3840, 2160),
            "Twitter Video (1280x720)": (1280, 720),
            "Custom": (0, 0),
        }
    
    def get_algorithm_descriptions(self) -> Dict[str, str]:
        """
        Get descriptions for sorting algorithms.
        
        Returns:
            Dictionary of algorithm names to descriptions
        """
        return {
            "quick_sort": "Quick Sort - Fast divide-and-conquer algorithm with dramatic pivot movements",
            "shell_sort": "Shell Sort - Gap-based insertion sort with wave-like patterns"
        }
    
    def get_style_descriptions(self) -> Dict[str, str]:
        """
        Get descriptions for color styles.
        
        Returns:
            Dictionary of style names to descriptions
        """
        return {
            "vaporwave": "Vaporwave - Pink, magenta, and cyan neon aesthetics with retro vibes",
            "cyberpunk": "Cyberpunk - Neon green and red with high contrast futuristic look"
        }
