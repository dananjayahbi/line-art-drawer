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
        logo_path: Optional[Path] = None,
        logo_x_percent: int = 50,
        logo_y_percent: int = 90,
        logo_scale: float = 0.15,
        logo_opacity: float = 0.85,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> MergeResult:
        """
        Merge video with background music and optional logo overlay.
        
        Audio handling:
        - Music always starts from the beginning.
        - If music is LONGER than video → trim the excess from the END.
        - If music is SHORTER than video → loop the music and trim the excess from the END.
        
        Args:
            video_path: Path to the video file
            music_path: Path to the music file
            output_name: Optional custom output filename
            fade_audio: Whether to fade audio in/out
            fade_duration: Duration of fade in seconds
            logo_path: Optional path to logo image for overlay
            logo_x_percent: Logo X position (0-100)
            logo_y_percent: Logo Y position (0-100)
            logo_scale: Logo scale relative to video width
            logo_opacity: Logo opacity (0-1)
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
            
            # ── Audio handling ──────────────────────────────────────
            # Rule 1: Music ALWAYS starts from the beginning (no offset).
            # Rule 2: If music is LONGER than video  → trim from the END.
            # Rule 3: If music is SHORTER than video → loop it, then trim the extra from the END.
            audio_filters = []
            music_duration = self._get_audio_duration(music_path)
            
            # We need to loop when the music is shorter than the video
            need_loop = music_duration > 0 and music_duration < video_duration
            
            # Always trim audio to exactly the video duration
            # atrim=end=<seconds> keeps only the first <seconds> of the audio
            audio_filters.append(f"atrim=start=0:end={video_duration:.3f}")
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
            
            # Build video filter for logo overlay
            video_filter_str = None
            has_logo = logo_path is not None and logo_path.exists()
            
            if has_logo:
                # Get video dimensions
                video_info = self._get_video_dimensions(video_path)
                if video_info:
                    video_width, video_height = video_info
                    
                    # Calculate logo size
                    logo_width = int(video_width * logo_scale)
                    
                    # Calculate position
                    x_pos = int((logo_x_percent / 100) * video_width - logo_width / 2)
                    y_pos = int((logo_y_percent / 100) * video_height - logo_width / 2)
                    
                    # Clamp position
                    x_pos = max(0, x_pos)
                    y_pos = max(0, y_pos)
                    
                    # Build filter with alpha for opacity
                    # Output is named [outv] for mapping
                    opacity_str = f"{logo_opacity:.2f}"
                    video_filter_str = (
                        f"[1:v]scale={logo_width}:-1,format=rgba,"
                        f"colorchannelmixer=aa={opacity_str}[logo];"
                        f"[0:v][logo]overlay={x_pos}:{y_pos}[outv]"
                    )

            
            # Build FFmpeg command
            cmd = [
                ffmpeg,
                '-y',  # Overwrite output
                '-i', str(video_path),  # Input video (0)
            ]
            
            # Add logo input if needed
            if has_logo:
                cmd.extend(['-i', str(logo_path)])  # Input logo (1)
            
            # Add music input — loop infinitely if music is shorter than video
            # -stream_loop -1 MUST come BEFORE the -i for the audio file
            if need_loop:
                cmd.extend(['-stream_loop', '-1'])
            cmd.extend(['-i', str(music_path)])  # Input audio (1 or 2)
            
            # Map streams based on whether we have a logo
            if has_logo:
                # With logo: use filter_complex for video
                if video_filter_str:
                    cmd.extend(['-filter_complex', video_filter_str])
                    cmd.extend(['-map', '[outv]'])  # Use filtered video output (overlay result)
                cmd.extend(['-map', '2:a'])  # Audio is input 2
            else:
                cmd.extend(['-map', '0:v'])  # Use video from first input
                cmd.extend(['-map', '1:a'])  # Audio is input 1
            
            if audio_filter_str:
                cmd.extend(['-af', audio_filter_str])
            
            # Video codec: copy if no logo, encode if logo
            if has_logo:
                cmd.extend([
                    '-c:v', 'libx264',  # Re-encode with H.264
                    '-preset', 'medium',
                    '-crf', '23',
                ])
            else:
                cmd.extend(['-c:v', 'copy'])  # Copy video codec (fast)
            
            cmd.extend([
                '-c:a', 'aac',  # Encode audio as AAC
                '-b:a', '192k',  # Audio bitrate
                '-shortest',  # End when shortest stream ends
                str(output_path)
            ])
            
            # Log the command for debugging
            print(f"[VideoMerger] Video duration: {video_duration:.2f}s")
            print(f"[VideoMerger] Music duration: {music_duration:.2f}s")
            print(f"[VideoMerger] Music looped: {need_loop}")
            print(f"[VideoMerger] Logo path: {logo_path}")
            print(f"[VideoMerger] Has logo: {has_logo}")
            print(f"[VideoMerger] Video filter: {video_filter_str}")
            print(f"[VideoMerger] Audio filter: {audio_filter_str}")
            print(f"[VideoMerger] FFmpeg command: {' '.join(cmd)}")
            
            # Add -progress and -nostats for machine-readable progress on stdout
            cmd.insert(-1, '-progress')
            cmd.insert(-1, 'pipe:1')
            cmd.insert(-1, '-nostats')
            
            # Run FFmpeg
            self._cancel_requested = False
            self._current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            # Drain stderr in a background thread to prevent pipe deadlock.
            # FFmpeg writes encoding info to stderr; if the pipe buffer fills
            # up (~64KB), FFmpeg blocks and our stdout reading stalls.
            stderr_lines = []
            stderr_drain = threading.Thread(
                target=self._drain_stderr,
                args=(self._current_process.stderr, stderr_lines),
                daemon=True
            )
            stderr_drain.start()
            
            # Parse progress output from FFmpeg in real-time
            last_progress = 0.0
            
            if self._current_process.stdout:
                for line in self._current_process.stdout:
                    if self._cancel_requested:
                        break
                    
                    line = line.strip()
                    
                    # Parse out_time_ms for progress
                    if line.startswith('out_time_ms='):
                        try:
                            time_ms = int(line.split('=')[1].strip())
                            if time_ms > 0 and video_duration > 0:
                                pct = min(0.99, time_ms / 1_000_000 / video_duration)
                                if pct > last_progress and progress_callback:
                                    last_progress = pct
                                    progress_callback(pct)
                        except (ValueError, IndexError):
                            pass
                    
                    elif line.startswith('progress=end'):
                        if progress_callback:
                            progress_callback(1.0)
            
            # Wait for process and stderr thread to finish
            self._current_process.wait()
            stderr_drain.join(timeout=5)
            
            if self._cancel_requested:
                # Clean up partial file
                if output_path.exists():
                    output_path.unlink()
                return MergeResult(False, None, "Merge cancelled")
            
            if self._current_process.returncode != 0:
                error_text = ''.join(stderr_lines)
                error_msg = error_text[:500] if error_text else "Unknown error"
                return MergeResult(False, None, f"FFmpeg error: {error_msg}")
            
            if not output_path.exists():
                return MergeResult(False, None, "Output file was not created")
            
            if progress_callback:
                progress_callback(1.0)
            
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
    
    def _get_video_dimensions(self, video_path: Path) -> Optional[tuple]:
        """Get video width and height."""
        try:
            cmd = [
                self.get_ffprobe_path(),
                '-v', 'quiet',
                '-print_format', 'json',
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
            
            if result.returncode == 0:
                import json
                data = json.loads(result.stdout)
                for stream in data.get('streams', []):
                    if stream.get('codec_type') == 'video':
                        width = int(stream.get('width', 0))
                        height = int(stream.get('height', 0))
                        if width > 0 and height > 0:
                            return (width, height)
            return None
        except:
            return None
    
    def cancel(self):
        """Cancel the current merge operation."""
        self._cancel_requested = True
        if self._current_process:
            try:
                self._current_process.terminate()
            except:
                pass
    
    @staticmethod
    def _drain_stderr(pipe, collected):
        """Drain stderr in a background thread to prevent pipe deadlock."""
        try:
            for line in pipe:
                collected.append(line)
        except Exception:
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
