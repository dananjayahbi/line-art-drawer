"""
Video Merger Module
===================
Handles merging video files with background music using FFmpeg.
"""

import os
import subprocess
from pathlib import Path
from typing import Optional, Callable
from dataclasses import dataclass
import threading
import shutil


@dataclass
class MergeResult:
    """Result of a merge operation."""
    success: bool
    output_path: Optional[Path]
    error_message: Optional[str] = None
    duration: float = 0.0  # Processing time in seconds


class VideoMerger:
    """Handles video and audio merging operations."""
    
    def __init__(self, output_dir: Path):
        """
        Initialize the video merger.
        
        Args:
            output_dir: Directory for saving merged videos
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._current_process: Optional[subprocess.Popen] = None
        self._cancel_requested = False
        
    def get_ffmpeg_path(self) -> str:
        """Get the path to ffmpeg executable."""
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
    
    def get_ffprobe_path(self) -> str:
        """Get the path to ffprobe executable."""
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
    
    def _get_video_duration(self, video_path: Path) -> float:
        """Get video duration in seconds."""
        try:
            cmd = [
                self.get_ffprobe_path(),
                '-v', 'quiet',
                '-show_entries', 'format=duration',
                '-of', 'csv=p=0',
                str(video_path)
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            return float(result.stdout.strip())
        except:
            return 0.0
    
    def _generate_output_filename(self, video_path: Path, music_path: Path) -> str:
        """Generate output filename from video and music names."""
        video_stem = video_path.stem
        music_stem = music_path.stem[:20]  # Limit music name length
        return f"{video_stem}_with_{music_stem}.mp4"
    
    def merge(
        self, 
        video_path: Path, 
        music_path: Path,
        output_name: Optional[str] = None,
        fade_audio: bool = True,
        fade_duration: float = 2.0,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> MergeResult:
        """
        Merge video with background music.
        
        The music will be cropped from the END to match the video length.
        This means we use the ending portion of the music track.
        
        Args:
            video_path: Path to the video file
            music_path: Path to the music file
            output_name: Optional custom output filename
            fade_audio: Whether to fade audio in/out
            fade_duration: Duration of fade in seconds
            progress_callback: Callback for progress updates (0.0 to 1.0)
            
        Returns:
            MergeResult object
        """
        import time
        start_time = time.time()
        
        video_path = Path(video_path)
        music_path = Path(music_path)
        
        # Validate inputs
        if not video_path.exists():
            return MergeResult(False, None, f"Video file not found: {video_path}")
        if not music_path.exists():
            return MergeResult(False, None, f"Music file not found: {music_path}")
        
        # Get video duration
        video_duration = self._get_video_duration(video_path)
        if video_duration <= 0:
            return MergeResult(False, None, "Could not determine video duration")
        
        # Generate output path
        if output_name:
            output_filename = output_name if output_name.endswith('.mp4') else f"{output_name}.mp4"
        else:
            output_filename = self._generate_output_filename(video_path, music_path)
        
        output_path = self.output_dir / output_filename
        
        # Handle existing file
        counter = 1
        while output_path.exists():
            stem = output_path.stem
            if stem.endswith(f"_{counter-1}"):
                stem = stem[:-len(f"_{counter-1}")]
            output_path = self.output_dir / f"{stem}_{counter}.mp4"
            counter += 1
        
        try:
            ffmpeg = self.get_ffmpeg_path()
            
            # Build audio filter for cropping from end and optional fading
            # We want the LAST video_duration seconds of the music
            audio_filters = []
            
            # Crop from end: use atrim to get last N seconds
            # This uses a negative start time relative to the end
            # We'll use a different approach: get music duration and calculate offset
            music_duration = self._get_audio_duration(music_path)
            
            if music_duration > video_duration:
                # Crop from the end: start = music_duration - video_duration
                start_offset = music_duration - video_duration
                audio_filters.append(f"atrim=start={start_offset}")
                audio_filters.append("asetpts=PTS-STARTPTS")  # Reset timestamps
            
            # Add fade effects
            if fade_audio:
                # Fade in at start
                audio_filters.append(f"afade=t=in:st=0:d={fade_duration}")
                # Fade out at end
                fade_out_start = video_duration - fade_duration
                if fade_out_start > 0:
                    audio_filters.append(f"afade=t=out:st={fade_out_start}:d={fade_duration}")
            
            # Build the filter string
            audio_filter_str = ",".join(audio_filters) if audio_filters else None
            
            # Build FFmpeg command
            cmd = [
                ffmpeg,
                '-y',  # Overwrite output
                '-i', str(video_path),  # Input video
                '-i', str(music_path),  # Input audio
                '-map', '0:v',  # Use video from first input
                '-map', '1:a',  # Use audio from second input
            ]
            
            if audio_filter_str:
                cmd.extend(['-af', audio_filter_str])
            
            cmd.extend([
                '-c:v', 'copy',  # Copy video codec (fast, no re-encoding)
                '-c:a', 'aac',  # Encode audio as AAC
                '-b:a', '192k',  # Audio bitrate
                '-shortest',  # End when shortest stream ends
                str(output_path)
            ])
            
            # Run FFmpeg
            self._cancel_requested = False
            self._current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            # Wait for completion
            stdout, stderr = self._current_process.communicate()
            
            if self._cancel_requested:
                # Clean up partial file
                if output_path.exists():
                    output_path.unlink()
                return MergeResult(False, None, "Merge cancelled")
            
            if self._current_process.returncode != 0:
                error_msg = stderr.decode('utf-8', errors='ignore')
                return MergeResult(False, None, f"FFmpeg error: {error_msg[:500]}")
            
            if not output_path.exists():
                return MergeResult(False, None, "Output file was not created")
            
            elapsed = time.time() - start_time
            return MergeResult(True, output_path, duration=elapsed)
            
        except Exception as e:
            return MergeResult(False, None, f"Merge failed: {str(e)}")
        finally:
            self._current_process = None
    
    def _get_audio_duration(self, audio_path: Path) -> float:
        """Get audio duration in seconds."""
        try:
            cmd = [
                self.get_ffprobe_path(),
                '-v', 'quiet',
                '-show_entries', 'format=duration',
                '-of', 'csv=p=0',
                str(audio_path)
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            return float(result.stdout.strip())
        except:
            return 0.0
    
    def cancel(self):
        """Cancel the current merge operation."""
        self._cancel_requested = True
        if self._current_process:
            try:
                self._current_process.terminate()
            except:
                pass
    
    def merge_async(
        self,
        video_path: Path,
        music_path: Path,
        output_name: Optional[str] = None,
        fade_audio: bool = True,
        fade_duration: float = 2.0,
        on_complete: Optional[Callable[[MergeResult], None]] = None,
        on_progress: Optional[Callable[[float], None]] = None
    ) -> threading.Thread:
        """
        Merge video with background music asynchronously.
        
        Args:
            video_path: Path to the video file
            music_path: Path to the music file
            output_name: Optional custom output filename
            fade_audio: Whether to fade audio in/out
            fade_duration: Duration of fade in seconds
            on_complete: Callback when merge is complete
            on_progress: Callback for progress updates
            
        Returns:
            Thread object for the async operation
        """
        def run():
            result = self.merge(
                video_path, 
                music_path, 
                output_name, 
                fade_audio, 
                fade_duration,
                on_progress
            )
            if on_complete:
                on_complete(result)
        
        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        return thread
