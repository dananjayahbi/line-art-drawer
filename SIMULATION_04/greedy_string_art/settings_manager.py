"""
Settings Manager for Greedy String Art Simulation
Handles loading, saving, and validation of user settings
"""

import json
from pathlib import Path
from typing import Dict, Any


class SettingsManager:
    """Manages simulation settings with persistence"""
    
    def __init__(self, simulation_dir: Path):
        """
        Initialize the settings manager
        
        Args:
            simulation_dir: Path to the greedy_string_art directory
        """
        self.settings_file = simulation_dir / "control_settings.json"
        self.default_settings = self._get_default_settings()
    
    def _get_default_settings(self) -> Dict[str, Any]:
        """
        Get default settings for the simulation
        
        Returns:
            Dictionary of default settings
        """
        return {
            # Window Settings
            "width": "1080",
            "height": "1920",
            "fps": "60",
            "fullscreen": False,
            
            # String Art Algorithm Settings
            "nail_count": "250",
            "max_lines": "3000",
            "thread_opacity": "0.15",
            "brightness_reduction": "0.12",
            "min_distance": "20",  # Minimum nail distance to avoid adjacent connections
            
            # Canvas Settings
            "canvas_color": "#1a1410",  # Dark wooden brown
            "thread_color": "#ffffff",  # White thread
            "nail_color": "#c0a080",  # Brass/gold nail heads
            "nail_radius": "3",
            
            # Optimization Settings
            "use_gpu": True,
            "convergence_threshold": "0.001",
            "lookahead_nails": "0",  # 0 = check all nails, >0 = only check N closest
            
            # Animation Settings
            "use_manim": False,
            "show_thread_accumulation": True,
            "show_nail_numbers": False,
            "camera_follow_thread": True,
            "zoom_level": "1.2",
            
            # Speed Control
            "target_duration": "15.0",  # Auto-calculate speed for 15-second video
            "animation_speed": "1.0",
            
            # Recording Settings
            "record": True,
            "record_format": "png",
            "record_quality": "95",
            
            # Visual Effects
            "glow_effect": True,
            "motion_blur": True,
            "show_progress_bar": True,
            "theme": "dark_wood",
            
            # Border Settings
            "show_border": True,
            "border_width": "40",
            "border_color": "#2d2416",
            
            # Image Upload
            "last_image_path": "",
            "image_preprocessing": "auto_contrast",  # auto_contrast, grayscale, none
            
            # Advanced
            "debug_mode": False,
            "log_level": "INFO",
            "save_intermediate_frames": False
        }
    
    def load_settings(self) -> Dict[str, Any]:
        """
        Load settings from JSON file
        
        Returns:
            Dictionary of settings (merged with defaults)
        """
        # Start with defaults
        settings = self.default_settings.copy()
        
        # Try to load saved settings
        if self.settings_file.exists():
            try:
                with open(self.settings_file, 'r') as f:
                    saved_settings = json.load(f)
                    # Merge saved settings with defaults (adds new fields)
                    settings.update(saved_settings)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load settings from {self.settings_file}: {e}")
                print("Using default settings")
        
        return settings
    
    def save_settings(self, settings: Dict[str, Any]) -> bool:
        """
        Save settings to JSON file
        
        Args:
            settings: Dictionary of settings to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure directory exists
            self.settings_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Write settings with pretty formatting
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f, indent=2)
            
            return True
        except (IOError, TypeError) as e:
            print(f"Error: Could not save settings to {self.settings_file}: {e}")
            return False
    
    def reset_to_defaults(self) -> Dict[str, Any]:
        """
        Reset settings to defaults and save
        
        Returns:
            Dictionary of default settings
        """
        default_settings = self.default_settings.copy()
        self.save_settings(default_settings)
        return default_settings
    
    def validate_settings(self, settings: Dict[str, Any]) -> tuple[bool, list[str]]:
        """
        Validate settings values
        
        Args:
            settings: Dictionary of settings to validate
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Validate numeric ranges
        try:
            width = int(settings.get("width", 0))
            if width < 100 or width > 7680:
                errors.append("Width must be between 100 and 7680 pixels")
        except ValueError:
            errors.append("Width must be a valid integer")
        
        try:
            height = int(settings.get("height", 0))
            if height < 100 or height > 4320:
                errors.append("Height must be between 100 and 4320 pixels")
        except ValueError:
            errors.append("Height must be a valid integer")
        
        try:
            nail_count = int(settings.get("nail_count", 0))
            if nail_count < 50 or nail_count > 500:
                errors.append("Nail count must be between 50 and 500")
        except ValueError:
            errors.append("Nail count must be a valid integer")
        
        try:
            max_lines = int(settings.get("max_lines", 0))
            if max_lines < 100 or max_lines > 20000:
                errors.append("Max lines must be between 100 and 20,000")
        except ValueError:
            errors.append("Max lines must be a valid integer")
        
        try:
            thread_opacity = float(settings.get("thread_opacity", 0))
            if thread_opacity < 0.01 or thread_opacity > 1.0:
                errors.append("Thread opacity must be between 0.01 and 1.0")
        except ValueError:
            errors.append("Thread opacity must be a valid number")
        
        try:
            brightness_reduction = float(settings.get("brightness_reduction", 0))
            if brightness_reduction < 0.01 or brightness_reduction > 1.0:
                errors.append("Brightness reduction must be between 0.01 and 1.0")
        except ValueError:
            errors.append("Brightness reduction must be a valid number")
        
        # Validate image path if provided
        image_path = settings.get("last_image_path", "")
        if image_path and not Path(image_path).exists():
            errors.append(f"Image file not found: {image_path}")
        
        return len(errors) == 0, errors
    
    def get_cli_args(self, settings: Dict[str, Any]) -> list[str]:
        """
        Convert settings to CLI arguments for main.py
        
        Args:
            settings: Dictionary of settings
            
        Returns:
            List of command-line arguments
        """
        args = []
        
        # Required arguments
        if settings.get("last_image_path"):
            args.extend(["--image", settings["last_image_path"]])
        
        # Window settings
        args.extend(["--width", str(settings["width"])])
        args.extend(["--height", str(settings["height"])])
        
        if settings.get("fullscreen"):
            args.append("--fullscreen")
        
        # Algorithm settings
        args.extend(["--nail-count", str(settings["nail_count"])])
        args.extend(["--max-lines", str(settings["max_lines"])])
        args.extend(["--thread-opacity", str(settings["thread_opacity"])])
        args.extend(["--brightness-reduction", str(settings["brightness_reduction"])])
        args.extend(["--min-distance", str(settings["min_distance"])])
        
        # Canvas color settings
        args.extend(["--canvas-color", str(settings.get("canvas_color", "#1a1410"))])
        args.extend(["--thread-color", str(settings.get("thread_color", "#ffffff"))])
        args.extend(["--nail-color", str(settings.get("nail_color", "#c0a080"))])
        args.extend(["--nail-radius", str(settings.get("nail_radius", "3"))])
        
        # Optimization settings
        args.extend(["--convergence", str(settings.get("convergence_threshold", "0.001"))])
        args.extend(["--lookahead", str(settings.get("lookahead_nails", "0"))])
        
        # Camera settings
        args.extend(["--zoom", str(settings.get("zoom_level", "1.2"))])
        
        # GPU settings
        if settings.get("use_gpu"):
            args.append("--use-gpu")
        
        # Animation settings
        if settings.get("use_manim"):
            args.append("--use-manim")
        
        if settings.get("camera_follow_thread"):
            args.append("--camera-follow")
        
        # Visual effects
        if settings.get("show_thread_accumulation", True):
            args.append("--show-accumulation")
        
        if settings.get("glow_effect", True):
            args.append("--glow")
        
        if settings.get("motion_blur", True):
            args.append("--motion-blur")
        
        if settings.get("show_progress_bar", True):
            args.append("--progress-bar")
        
        # Border settings
        if settings.get("show_border", True):
            args.append("--show-border")
        
        args.extend(["--border-width", str(settings.get("border_width", "40"))])
        
        # Speed settings
        if settings.get("target_duration"):
            args.extend(["--target-duration", str(settings["target_duration"])])
        else:
            args.extend(["--speed", str(settings.get("animation_speed", "1.0"))])
        
        # Recording settings
        if settings.get("record"):
            args.append("--record")
        
        args.extend(["--quality", str(settings.get("record_quality", "95"))])
        
        # Theme
        if settings.get("theme"):
            args.extend(["--theme", settings["theme"]])
        
        return args

