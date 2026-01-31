#!/usr/bin/env python3
"""
Settings Manager for Magnetic Iron Filings Art
================================================
Handles loading, saving, and resetting of simulation settings.
"""

import json
from pathlib import Path


class SettingsManager:
    """Manages simulation settings with JSON persistence."""
    
    DEFAULTS = {
        "width": "540",
        "height": "960",
        "fps": "60",
        "target_duration": "15.0",
        "particle_count": "10000",
        "magnetic_strength": "1.0",
        "particle_size": "2.0",
        "friction": "0.98",
        "inertia": "0.95",
        "use_gpu": True,
        "show_magnet": True,
        "show_field_lines": False,
        "particle_color": "#3d3d3d",
        "background_color": "#f5f0e6",
        "frame_thickness": "4",
        "frame_speed": "1.0",
        "frame_margin": "15",
        "use_custom_magnet": False,
        "custom_magnet_path": "",
        "magnet_scale": "0.5",
        "auto_record": True,
        "video_fps": "60",
        "video_quality": "high",
        "motion_blur": True,
        "drop_shadows": True,
        "metallic_glints": True
    }
    
    def __init__(self, simulation_dir):
        """Initialize with path to simulation directory."""
        self.simulation_dir = Path(simulation_dir)
        self.settings_file = self.simulation_dir / "control_settings.json"
    
    def load_settings(self):
        """Load settings from file, returning defaults if file doesn't exist."""
        if self.settings_file.exists():
            try:
                with open(self.settings_file, 'r') as f:
                    saved = json.load(f)
                    # Merge with defaults to handle new settings
                    settings = self.DEFAULTS.copy()
                    settings.update(saved)
                    return settings
            except Exception as e:
                print(f"Error loading settings: {e}")
        return self.DEFAULTS.copy()
    
    def save_settings(self, settings):
        """Save settings to file."""
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f, indent=4)
            return True
        except Exception as e:
            print(f"Error saving settings: {e}")
            return False
    
    def reset_to_defaults(self):
        """Reset settings to default values."""
        return self.save_settings(self.DEFAULTS.copy())
    
    def get_default(self, key):
        """Get a default value for a key."""
        return self.DEFAULTS.get(key)
