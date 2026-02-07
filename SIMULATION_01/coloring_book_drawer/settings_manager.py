#!/usr/bin/env python3
"""
Settings Manager for Coloring Book Drawer
==========================================
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
            # Window settings
            "width": "800",
            "height": "1000",
            "fps": "60",
            
            # Drawing settings
            "speed": 5.0,
            "thickness": 1.0,
            "show_pen": True,
            "use_gpu": True,
            
            # Visual settings
            "theme": "Classic",
            
            # Engine selection (auto / pixel_reveal / pencil_shading / advanced_gradient)
            "engine_type": "auto",
            
            # Frame border settings
            "frame_thickness": 6.0,
            "frame_speed": 1.0,
            "frame_margin": 20.0,
            
            # Custom pen settings
            "use_custom_pen": False,
            "custom_pen_path": "",
            "pen_scale": 1.0,
            "pen_rotation": True,
            
            # Recording settings
            "auto_record": False,
            "video_fps": "60",
            "video_quality": "high",
            
            # Engine 2: Pencil Shading settings
            "force_shading_engine": False,
            "shading_sensitivity": 0.5,
            "hatching_angle": 45.0,
            "stroke_spacing": 3,
            "edge_phases_first": 1,
            "shading_order": "top_to_bottom",
            
            # Engine 3: Advanced Gradient settings
            "contour_sensitivity": 0.5,
            "gradient_smoothness": 0.7,
            "texture_detection_strength": 0.6,
            "shadow_passes": 3,
            "shadow_angle_variation": 30.0,
            "brush_softness_contour": 0.3,
            "brush_softness_shading": 0.7,
            "pressure_variation": 0.5,
            "phase_1_weight": 1.0,
            "phase_2_weight": 0.8,
            "phase_3_weight": 1.0,
            "merge_shading_phases": False,
            "auto_analyze": False,
            
            # Engine 3D: Zone Progressive settings
            "zp_num_zones": 10,
            "zp_saliency_threshold": 0.3,
            "zp_max_focal_points": 5,
            "zp_animation_mode": "multi_focal",
            "zp_transition_width": 0.1,
            "zp_stroke_density": 0.8,
            "zp_enable_portrait": True,
            
            # Engine 3E: Adaptive Brush settings
            "ab_tip_shape": "round",
            "ab_pencil_hardness": 0.5,
            "ab_pencil_sharpness": 0.7,
            "ab_paper_type": "cold_press",
            "ab_paper_texture_strength": 0.5,
            "ab_pressure_variation": 0.5,
            "ab_graphite_buildup": 0.7,
            
            # Engine 3F: Hybrid Multi-Strategy settings
            "hm_num_segments": 100,
            "hm_min_region_area": 500,
            "hm_transition_width": 10,
            "hm_blend_smoothness": 0.7,
            "hm_strategy_mode": "auto",
            "hm_focal_detection": True,
            # Engine 2V2: Pencil Shading V2 settings
            "ps2_auto_tune": False
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
