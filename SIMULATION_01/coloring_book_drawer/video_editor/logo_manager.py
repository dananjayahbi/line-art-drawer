"""
Logo Manager Module
===================
Handles logo file management, settings, and overlay configuration.
"""

import os
import json
import shutil
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict


# Paths
SIMULATION_DIR = Path(__file__).resolve().parent.parent
LOGOS_DIR = SIMULATION_DIR / "assets" / "logos"
SETTINGS_FILE = LOGOS_DIR / "logo_settings.json"


@dataclass
class LogoInfo:
    """Information about a logo file."""
    path: Path
    filename: str
    display_name: str
    width: int = 0
    height: int = 0
    
    def to_dict(self) -> dict:
        return {
            'path': str(self.path),
            'filename': self.filename,
            'display_name': self.display_name,
            'width': self.width,
            'height': self.height
        }


@dataclass
class LogoSettings:
    """Settings for logo overlay."""
    default_logo: Optional[str] = None  # Filename of default logo
    position_x: int = 50  # X position as percentage (0-100)
    position_y: int = 90  # Y position as percentage (0-100)
    scale: float = 0.15  # Logo scale relative to video width
    opacity: float = 0.85  # Logo opacity (0.0-1.0)
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'LogoSettings':
        return cls(
            default_logo=data.get('default_logo'),
            position_x=data.get('position_x', 50),
            position_y=data.get('position_y', 90),
            scale=data.get('scale', 0.15),
            opacity=data.get('opacity', 0.85)
        )


class LogoManager:
    """Manages logo files and overlay settings."""
    
    def __init__(self):
        """Initialize the logo manager."""
        self.logos_dir = LOGOS_DIR
        self.logos_dir.mkdir(parents=True, exist_ok=True)
        self._logo_cache: Dict[str, LogoInfo] = {}
        self.settings = self._load_settings()
    
    def _load_settings(self) -> LogoSettings:
        """Load settings from file."""
        try:
            if SETTINGS_FILE.exists():
                with open(SETTINGS_FILE, 'r') as f:
                    data = json.load(f)
                    return LogoSettings.from_dict(data)
        except Exception as e:
            print(f"Error loading logo settings: {e}")
        
        return LogoSettings()
    
    def get_settings(self) -> LogoSettings:
        """Get current settings."""
        return self.settings
    
    def save_settings(self):
        """Save settings to file."""
        try:
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(self.settings.to_dict(), f, indent=2)
        except Exception as e:
            print(f"Error saving logo settings: {e}")
    
    def get_logo_info(self, logo_path: Path) -> Optional[LogoInfo]:
        """
        Get information about a logo file.
        
        Args:
            logo_path: Path to the logo file
            
        Returns:
            LogoInfo object or None if failed
        """
        logo_path = Path(logo_path)
        
        # Check cache
        cache_key = str(logo_path)
        if cache_key in self._logo_cache:
            return self._logo_cache[cache_key]
        
        try:
            from PIL import Image
            
            with Image.open(logo_path) as img:
                width, height = img.size
            
            # Clean up display name
            name = logo_path.stem
            name = name.replace('-', ' ').replace('_', ' ')
            name = ' '.join(word.capitalize() for word in name.split())
            
            info = LogoInfo(
                path=logo_path,
                filename=logo_path.name,
                display_name=name,
                width=width,
                height=height
            )
            
            self._logo_cache[cache_key] = info
            return info
            
        except ImportError:
            # PIL not available, create basic info
            name = logo_path.stem.replace('-', ' ').replace('_', ' ')
            name = ' '.join(word.capitalize() for word in name.split())
            
            info = LogoInfo(
                path=logo_path,
                filename=logo_path.name,
                display_name=name
            )
            self._logo_cache[cache_key] = info
            return info
            
        except Exception as e:
            print(f"Error getting logo info for {logo_path}: {e}")
            return None
    
    def list_logos(self) -> List[LogoInfo]:
        """
        List all logos in the logos directory.
        
        Returns:
            List of LogoInfo objects
        """
        logos = []
        extensions = {'.png', '.jpg', '.jpeg', '.svg', '.webp', '.gif'}
        
        if not self.logos_dir.exists():
            return logos
        
        for file_path in self.logos_dir.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in extensions:
                if file_path.name == 'logo_settings.json':
                    continue
                info = self.get_logo_info(file_path)
                if info:
                    logos.append(info)
        
        # Sort alphabetically
        logos.sort(key=lambda l: l.display_name.lower())
        return logos
    
    def add_logo(self, source_path: Path) -> Optional[LogoInfo]:
        """
        Add a logo from an external path to the logos directory.
        
        Args:
            source_path: Path to the source logo file
            
        Returns:
            LogoInfo for the added logo, or None if failed
        """
        source_path = Path(source_path)
        
        if not source_path.exists():
            return None
        
        try:
            # Copy to logos directory
            dest_path = self.logos_dir / source_path.name
            
            # Handle filename collision
            counter = 1
            while dest_path.exists():
                stem = source_path.stem
                suffix = source_path.suffix
                dest_path = self.logos_dir / f"{stem}_{counter}{suffix}"
                counter += 1
            
            shutil.copy2(source_path, dest_path)
            
            # Clear cache and get info
            return self.get_logo_info(dest_path)
            
        except Exception as e:
            print(f"Error adding logo: {e}")
            return None
    
    def delete_logo(self, logo_path: Path) -> bool:
        """
        Delete a logo from the logos directory.
        
        Args:
            logo_path: Path to the logo to delete
            
        Returns:
            True if deleted successfully
        """
        logo_path = Path(logo_path)
        
        try:
            if logo_path.exists():
                logo_path.unlink()
            
            # Clear from cache
            cache_key = str(logo_path)
            if cache_key in self._logo_cache:
                del self._logo_cache[cache_key]
            
            # Clear default if this was the default
            if self.settings.default_logo == logo_path.name:
                self.settings.default_logo = None
                self.save_settings()
            
            return True
            
        except Exception as e:
            print(f"Error deleting logo: {e}")
            return False
    
    def set_default_logo(self, filename: Optional[str]):
        """Set the default logo filename."""
        self.settings.default_logo = filename
        self.save_settings()
    
    def get_default_logo(self) -> Optional[LogoInfo]:
        """Get the default logo info."""
        if not self.settings.default_logo:
            return None
        
        logo_path = self.logos_dir / self.settings.default_logo
        if logo_path.exists():
            return self.get_logo_info(logo_path)
        return None
    
    def set_position(self, x_percent: int, y_percent: int):
        """
        Set the logo position as percentage of video dimensions.
        
        Args:
            x_percent: X position (0-100, left to right)
            y_percent: Y position (0-100, top to bottom)
        """
        self.settings.position_x = max(0, min(100, x_percent))
        self.settings.position_y = max(0, min(100, y_percent))
        self.save_settings()
    
    def set_scale(self, scale: float):
        """Set logo scale (0.05 to 0.5)."""
        self.settings.scale = max(0.05, min(0.5, scale))
        self.save_settings()
    
    def set_opacity(self, opacity: float):
        """Set logo opacity (0.0 to 1.0)."""
        self.settings.opacity = max(0.0, min(1.0, opacity))
        self.save_settings()
    
    def get_ffmpeg_overlay_filter(
        self, 
        logo_path: Path, 
        video_width: int, 
        video_height: int
    ) -> str:
        """
        Generate FFmpeg filter for logo overlay.
        
        Args:
            logo_path: Path to logo file
            video_width: Video width in pixels
            video_height: Video height in pixels
            
        Returns:
            FFmpeg filter string
        """
        # Calculate logo size
        logo_width = int(video_width * self.settings.scale)
        
        # Calculate position
        x_pos = int((self.settings.position_x / 100) * video_width - logo_width / 2)
        y_pos = int((self.settings.position_y / 100) * video_height - logo_width / 2)
        
        # Clamp position
        x_pos = max(0, min(x_pos, video_width - logo_width))
        y_pos = max(0, min(y_pos, video_height - logo_width))
        
        # Build filter with alpha for opacity
        # Scale the logo, then overlay with transparency
        filter_str = (
            f"[1:v]scale={logo_width}:-1,format=rgba,"
            f"colorchannelmixer=aa={self.settings.opacity}[logo];"
            f"[0:v][logo]overlay={x_pos}:{y_pos}"
        )
        
        return filter_str
