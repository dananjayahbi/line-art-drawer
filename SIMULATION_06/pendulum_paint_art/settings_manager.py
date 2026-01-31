#!/usr/bin/env python3
"""
Settings Manager for Pendulum Paint Art
=========================================
Handles saving and loading control panel settings to/from JSON.
"""

import json
from pathlib import Path


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
            # Window settings
            "width": "800",
            "height": "1000",
            "fps": "60",
            
            # Animation settings
            "target_duration": "30.0",
            
            # Pendulum settings
            "pendulum_length": "300",
            "initial_angle_x": "45.0",
            "initial_angle_y": "30.0",
            "damping_x": "0.02",
            "damping_y": "0.02",
            "gravity": "9.8",
            
            # Paint settings
            "drip_rate": "0.15",
            "paint_thickness": "8",
            "viscosity": "0.7",
            "paint_color": "#2c1810",
            
            # Visual settings
            "show_pendulum": True,
            "show_trails": True,
            
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
            print(f"Failed to save settings: {str(e)}")
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
            print(f"Failed to load settings: {str(e)}")
            return self.default_settings.copy()
    
    def reset_to_defaults(self):
        """
        Reset settings to defaults and save.
        
        Returns:
            dict: Default settings dictionary
        """
        defaults = self.default_settings.copy()
        self.save_settings(defaults)
        return defaults
    
    def get_defaults(self):
        """Get a copy of the default settings."""
        return self.default_settings.copy()
