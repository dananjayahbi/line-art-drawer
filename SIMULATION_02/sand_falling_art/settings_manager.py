#!/usr/bin/env python3
"""
Settings Manager for Sand Falling Art
======================================
Handles saving and loading control panel settings to/from JSON.
"""

import json
from pathlib import Path
from tkinter import messagebox


class SettingsManager:
    """Manages saving/loading control panel settings."""
    
    def __init__(self, simulation_dir):
        """
        Initialize settings manager.
        
        Args:
            simulation_dir: Path to the simulation directory
        """
        self.simulation_dir = Path(simulation_dir)
        self.settings_file = self.simulation_dir / "control_settings.json"
        self.default_settings = self._get_default_settings()
    
    def _get_default_settings(self):
        """Get default settings dictionary."""
        return {
            # Window settings (4:3 aspect ratio)
            "width": "1600",
            "height": "1200",
            "fps": "60",
            
            # Sand particle settings
            "particle_size": 2.0,
            "spawn_rate": 10,
            "gravity": 980.0,
            
            # Physics settings
            "particle_friction": 0.7,
            "particle_elasticity": 0.1,
            
            # Visual settings
            "particle_glow": True,
            "show_target_outline": False,
            "antialiasing": True,
            "use_gpu": True,  # GPU acceleration
            
            # Recording settings
            "auto_record": False,
            "video_fps": "60",
            "video_quality": "high"
        }
    
    def save_settings(self, settings_dict):
        """
        Save settings to JSON file.
        
        Args:
            settings_dict: Dictionary of settings to save
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(settings_dict, f, indent=2)
            return True
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save settings: {str(e)}")
            return False
    
    def load_settings(self):
        """
        Load settings from JSON file.
        
        Returns:
            dict: Settings dictionary, or default settings if file doesn't exist
        """
        if not self.settings_file.exists():
            return self.default_settings.copy()
        
        try:
            with open(self.settings_file, 'r') as f:
                settings = json.load(f)
            
            # Merge with defaults to handle new settings in updates
            merged = self.default_settings.copy()
            merged.update(settings)
            return merged
            
        except Exception as e:
            messagebox.showerror("Load Error", f"Failed to load settings: {str(e)}")
            return self.default_settings.copy()
    
    def reset_to_defaults(self):
        """
        Reset settings to defaults.
        
        Returns:
            dict: Default settings dictionary
        """
        self.save_settings(self.default_settings)
        return self.default_settings.copy()
