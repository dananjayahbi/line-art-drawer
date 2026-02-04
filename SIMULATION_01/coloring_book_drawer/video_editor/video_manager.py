"""
Video Manager Module
====================
Handles video file discovery, thumbnail generation, and video metadata.
"""

import os
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import json


@dataclass
class VideoInfo:
    """Information about a video file."""
    path: Path
    filename: str
    duration: float  # seconds
    width: int
    height: int
    fps: float
    thumbnail_path: Optional[Path] = None
    
    def to_dict(self) -> dict:
        return {
            'path': str(self.path),
            'filename': self.filename,
            'duration': self.duration,
            'width': self.width,
            'height': self.height,
            'fps': self.fps,
            'thumbnail_path': str(self.thumbnail_path) if self.thumbnail_path else None
        }


class VideoManager:
    """Manages video files and thumbnail generation."""
    
    def __init__(self, videos_dir: Path, thumbnails_dir: Path):
        """
        Initialize the video manager.
        
        Args:
            videos_dir: Directory containing video files
            thumbnails_dir: Directory for storing thumbnails
        """
        self.videos_dir = Path(videos_dir)
        self.thumbnails_dir = Path(thumbnails_dir)
        self.videos_dir.mkdir(parents=True, exist_ok=True)
        self.thumbnails_dir.mkdir(parents=True, exist_ok=True)
        self._video_cache: Dict[str, VideoInfo] = {}
        
    def get_ffprobe_path(self) -> str:
        """Get the path to ffprobe executable."""
        # Try to find ffprobe in PATH
        import shutil
        ffprobe = shutil.which('ffprobe')
        if ffprobe:
            return ffprobe
        
        # Try common Windows locations
        common_paths = [
            r"C:\ffmpeg\bin\ffprobe.exe",
            r"C:\Program Files\ffmpeg\bin\ffprobe.exe",
            r"C:\Program Files (x86)\ffmpeg\bin\ffprobe.exe",
        ]
        for path in common_paths:
            if os.path.exists(path):
                return path
        
        return 'ffprobe'  # Hope it's in PATH
    
    def get_ffmpeg_path(self) -> str:
        """Get the path to ffmpeg executable."""
        import shutil
        ffmpeg = shutil.which('ffmpeg')
        if ffmpeg:
            return ffmpeg
        
        common_paths = [
            r"C:\ffmpeg\bin\ffmpeg.exe",
            r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
            r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe",
        ]
        for path in common_paths:
            if os.path.exists(path):
                return path
        
        return 'ffmpeg'
    
    def get_video_info(self, video_path: Path) -> Optional[VideoInfo]:
        """
        Get information about a video file using ffprobe.
        
        Args:
            video_path: Path to the video file
            
        Returns:
            VideoInfo object or None if failed
        """
        video_path = Path(video_path)
        
        # Check cache
        cache_key = str(video_path)
        if cache_key in self._video_cache:
            return self._video_cache[cache_key]
        
        try:
            ffprobe = self.get_ffprobe_path()
            cmd = [
                ffprobe,
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                str(video_path)
            ]
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            if result.returncode != 0:
                print(f"ffprobe error for {video_path}: {result.stderr}")
                return None
            
            data = json.loads(result.stdout)
            
            # Find video stream
            video_stream = None
            for stream in data.get('streams', []):
                if stream.get('codec_type') == 'video':
                    video_stream = stream
                    break
            
            if not video_stream:
                return None
            
            # Parse frame rate (can be "30/1" or "29.97")
            fps_str = video_stream.get('avg_frame_rate', '30/1')
            if '/' in fps_str:
                num, den = fps_str.split('/')
                fps = float(num) / float(den) if float(den) != 0 else 30.0
            else:
                fps = float(fps_str)
            
            # Get duration from format or stream
            duration = float(data.get('format', {}).get('duration', 0))
            if duration == 0:
                duration = float(video_stream.get('duration', 0))
            
            # Check for thumbnail
            thumbnail_path = self._get_thumbnail_path(video_path)
            
            info = VideoInfo(
                path=video_path,
                filename=video_path.name,
                duration=duration,
                width=int(video_stream.get('width', 0)),
                height=int(video_stream.get('height', 0)),
                fps=fps,
                thumbnail_path=thumbnail_path if thumbnail_path.exists() else None
            )
            
            self._video_cache[cache_key] = info
            return info
            
        except Exception as e:
            print(f"Error getting video info for {video_path}: {e}")
            return None
    
    def _get_thumbnail_path(self, video_path: Path) -> Path:
        """Get the expected thumbnail path for a video."""
        return self.thumbnails_dir / f"{video_path.stem}_thumb.jpg"
    
    def generate_thumbnail(self, video_path: Path, force: bool = False) -> Optional[Path]:
        """
        Generate a thumbnail for a video file using the LAST frame.
        
        Args:
            video_path: Path to the video file
            force: If True, regenerate even if thumbnail exists
            
        Returns:
            Path to thumbnail or None if failed
        """
        video_path = Path(video_path)
        thumbnail_path = self._get_thumbnail_path(video_path)
        
        # Skip if already exists and not forcing
        if thumbnail_path.exists() and not force:
            return thumbnail_path
        
        try:
            ffmpeg = self.get_ffmpeg_path()
            
            # Get video info to calculate last frame position
            info = self.get_video_info(video_path)
            if info and info.duration > 0:
                # Seek to 2 seconds before the end (or 90% if short video)
                seek_time = max(0, info.duration - 2.0)
                if info.duration < 5:
                    seek_time = info.duration * 0.9
            else:
                seek_time = 0
            
            cmd = [
                ffmpeg,
                '-y',  # Overwrite
                '-sseof', '-1',  # Seek from end (last 1 second)
                '-i', str(video_path),
                '-vframes', '1',  # One frame
                '-vf', 'scale=200:-1',  # Scale to 200px width
                '-q:v', '3',  # Quality
                str(thumbnail_path)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            if result.returncode == 0 and thumbnail_path.exists():
                # Update cache
                cache_key = str(video_path)
                if cache_key in self._video_cache:
                    self._video_cache[cache_key].thumbnail_path = thumbnail_path
                return thumbnail_path
            else:
                print(f"ffmpeg thumbnail error: {result.stderr.decode()}")
                return None
                
        except Exception as e:
            print(f"Error generating thumbnail for {video_path}: {e}")
            return None
    
    def list_videos(self, generate_thumbnails: bool = True) -> List[VideoInfo]:
        """
        List all videos in the videos directory.
        
        Args:
            generate_thumbnails: If True, generate missing thumbnails
            
        Returns:
            List of VideoInfo objects
        """
        videos = []
        extensions = {'.mp4', '.avi', '.mov', '.mkv', '.webm'}
        
        if not self.videos_dir.exists():
            return videos
        
        for file_path in self.videos_dir.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in extensions:
                info = self.get_video_info(file_path)
                if info:
                    # Generate thumbnail if needed
                    if generate_thumbnails and not info.thumbnail_path:
                        thumb = self.generate_thumbnail(file_path)
                        if thumb:
                            info.thumbnail_path = thumb
                    videos.append(info)
        
        # Sort by modification time (newest first)
        videos.sort(key=lambda v: v.path.stat().st_mtime, reverse=True)
        return videos
    
    def delete_video(self, video_path: Path) -> bool:
        """Delete a video and its thumbnail."""
        video_path = Path(video_path)
        try:
            # Delete thumbnail
            thumb_path = self._get_thumbnail_path(video_path)
            if thumb_path.exists():
                thumb_path.unlink()
            
            # Delete video
            if video_path.exists():
                video_path.unlink()
            
            # Clear from cache
            cache_key = str(video_path)
            if cache_key in self._video_cache:
                del self._video_cache[cache_key]
            
            return True
        except Exception as e:
            print(f"Error deleting video {video_path}: {e}")
            return False
    
    def format_duration(self, seconds: float) -> str:
        """Format duration in seconds to MM:SS format."""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"
