"""
Music Manager Module
====================
Handles background music file discovery, playback, and metadata.
"""

import os
import subprocess
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass
import json

# Try to import pygame for audio playback
try:
    import pygame
    pygame.mixer.init()
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    print("Warning: pygame not available, music preview will be disabled")


@dataclass
class MusicInfo:
    """Information about a music file."""
    path: Path
    filename: str
    display_name: str  # Cleaned up name for display
    duration: float  # seconds
    
    def to_dict(self) -> dict:
        return {
            'path': str(self.path),
            'filename': self.filename,
            'display_name': self.display_name,
            'duration': self.duration
        }


class MusicManager:
    """Manages background music files and playback."""
    
    def __init__(self, music_dir: Path):
        """
        Initialize the music manager.
        
        Args:
            music_dir: Directory containing music files
        """
        self.music_dir = Path(music_dir)
        self._music_cache: Dict[str, MusicInfo] = {}
        self._current_playing: Optional[Path] = None
        
    def get_ffprobe_path(self) -> str:
        """Get the path to ffprobe executable."""
        import shutil
        ffprobe = shutil.which('ffprobe')
        if ffprobe:
            return ffprobe
        
        common_paths = [
            r"C:\ffmpeg\bin\ffprobe.exe",
            r"C:\Program Files\ffmpeg\bin\ffprobe.exe",
            r"C:\Program Files (x86)\ffmpeg\bin\ffprobe.exe",
        ]
        for path in common_paths:
            if os.path.exists(path):
                return path
        
        return 'ffprobe'
    
    def _clean_display_name(self, filename: str) -> str:
        """
        Clean up filename for display.
        
        Args:
            filename: Original filename
            
        Returns:
            Cleaned display name
        """
        # Remove extension
        name = Path(filename).stem
        
        # Replace hyphens and underscores with spaces
        name = name.replace('-', ' ').replace('_', ' ')
        
        # Title case
        name = ' '.join(word.capitalize() for word in name.split())
        
        # Truncate if too long
        if len(name) > 50:
            name = name[:47] + "..."
        
        return name
    
    def get_music_info(self, music_path: Path) -> Optional[MusicInfo]:
        """
        Get information about a music file using ffprobe.
        
        Args:
            music_path: Path to the music file
            
        Returns:
            MusicInfo object or None if failed
        """
        music_path = Path(music_path)
        
        # Check cache
        cache_key = str(music_path)
        if cache_key in self._music_cache:
            return self._music_cache[cache_key]
        
        try:
            ffprobe = self.get_ffprobe_path()
            cmd = [
                ffprobe,
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                str(music_path)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            if result.returncode != 0:
                # Fallback: estimate duration from file size
                duration = 180.0  # Default 3 minutes
            else:
                data = json.loads(result.stdout)
                duration = float(data.get('format', {}).get('duration', 180.0))
            
            info = MusicInfo(
                path=music_path,
                filename=music_path.name,
                display_name=self._clean_display_name(music_path.name),
                duration=duration
            )
            
            self._music_cache[cache_key] = info
            return info
            
        except Exception as e:
            print(f"Error getting music info for {music_path}: {e}")
            # Return basic info without duration
            return MusicInfo(
                path=music_path,
                filename=music_path.name,
                display_name=self._clean_display_name(music_path.name),
                duration=180.0
            )
    
    def list_music(self) -> List[MusicInfo]:
        """
        List all music files in the music directory.
        
        Returns:
            List of MusicInfo objects
        """
        music_files = []
        extensions = {'.mp3', '.wav', '.ogg', '.m4a', '.flac'}
        
        if not self.music_dir.exists():
            return music_files
        
        for file_path in self.music_dir.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in extensions:
                info = self.get_music_info(file_path)
                if info:
                    music_files.append(info)
        
        # Sort alphabetically by display name
        music_files.sort(key=lambda m: m.display_name.lower())
        return music_files
    
    def play(self, music_path: Path) -> bool:
        """
        Start playing a music file.
        
        Args:
            music_path: Path to the music file
            
        Returns:
            True if playback started successfully
        """
        if not PYGAME_AVAILABLE:
            print("pygame not available for music playback")
            return False
        
        try:
            # Stop current playback
            self.stop()
            
            # Load and play
            pygame.mixer.music.load(str(music_path))
            pygame.mixer.music.play()
            self._current_playing = music_path
            return True
            
        except Exception as e:
            print(f"Error playing music {music_path}: {e}")
            return False
    
    def stop(self):
        """Stop current playback."""
        if PYGAME_AVAILABLE:
            try:
                pygame.mixer.music.stop()
                self._current_playing = None
            except:
                pass
    
    def pause(self):
        """Pause current playback."""
        if PYGAME_AVAILABLE:
            try:
                pygame.mixer.music.pause()
            except:
                pass
    
    def unpause(self):
        """Resume paused playback."""
        if PYGAME_AVAILABLE:
            try:
                pygame.mixer.music.unpause()
            except:
                pass
    
    def is_playing(self) -> bool:
        """Check if music is currently playing."""
        if PYGAME_AVAILABLE:
            return pygame.mixer.music.get_busy()
        return False
    
    def get_current_playing(self) -> Optional[Path]:
        """Get the path of currently playing music."""
        return self._current_playing
    
    def get_position(self) -> float:
        """Get current playback position in seconds."""
        if PYGAME_AVAILABLE:
            try:
                # pygame.mixer.music.get_pos() returns time in milliseconds
                pos_ms = pygame.mixer.music.get_pos()
                if pos_ms >= 0:
                    return pos_ms / 1000.0
            except:
                pass
        return 0.0
    
    def set_position(self, position: float) -> bool:
        """
        Set playback position in seconds.
        
        Note: This only works reliably for MP3 files.
        For other formats, playback will restart from the beginning.
        
        Args:
            position: Position in seconds from start
            
        Returns:
            True if successful
        """
        if PYGAME_AVAILABLE and self._current_playing:
            try:
                # pygame.mixer.music.set_pos() sets position in seconds for MP3
                pygame.mixer.music.set_pos(position)
                return True
            except Exception as e:
                print(f"Error seeking music: {e}")
                # Fallback: reload and play from position
                try:
                    pygame.mixer.music.load(str(self._current_playing))
                    pygame.mixer.music.play(start=position)
                    return True
                except:
                    pass
        return False
    
    def set_volume(self, volume: float):
        """
        Set playback volume.
        
        Args:
            volume: Volume level (0.0 to 1.0)
        """
        if PYGAME_AVAILABLE:
            pygame.mixer.music.set_volume(max(0.0, min(1.0, volume)))
    
    def format_duration(self, seconds: float) -> str:
        """Format duration in seconds to MM:SS format."""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"
    
    def cleanup(self):
        """Clean up resources."""
        self.stop()
        if PYGAME_AVAILABLE:
            try:
                pygame.mixer.quit()
            except:
                pass
