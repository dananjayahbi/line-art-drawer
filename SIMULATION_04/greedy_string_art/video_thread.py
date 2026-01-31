"""
Video Generation Thread for Greedy String Art Simulation
Handles asynchronous video generation from frames using FFmpeg
"""

import subprocess
from pathlib import Path
from PySide6.QtCore import QThread, Signal


class VideoGenerationThread(QThread):
    """
    QThread for non-blocking video generation from frames
    
    Signals:
        finished: Emitted with output path when video is successfully created
        error: Emitted with error message if video generation fails
        progress: Emitted with progress percentage (0-100)
    """
    
    finished = Signal(str)  # Output video path
    error = Signal(str)     # Error message
    progress = Signal(int)  # Progress percentage
    
    def __init__(self, frames_folder, output_path, sim_fps=60, quality_crf=18, 
                 output_fps=60, motion_blur=True):
        """
        Initialize video generation thread
        
        Args:
            frames_folder: Path to folder containing frame images
            output_path: Path where output video should be saved
            sim_fps: Simulation FPS (frame rate of captured frames)
            quality_crf: FFmpeg CRF quality (18=high, 23=medium, 28=low)
            output_fps: Output video FPS
            motion_blur: Whether to apply motion blur filter
        """
        super().__init__()
        self.frames_folder = Path(frames_folder)
        self.output_path = Path(output_path)
        self.sim_fps = sim_fps
        self.quality_crf = quality_crf
        self.output_fps = output_fps
        self.motion_blur = motion_blur
        self._is_running = True
    
    def run(self):
        """
        Generate video from frames using FFmpeg
        
        This method runs in a separate thread to avoid blocking the UI
        """
        try:
            # Ensure output directory exists
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Build FFmpeg command
            cmd = self._build_ffmpeg_command()
            
            # Emit initial progress
            self.progress.emit(10)
            
            # Run FFmpeg
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False
            )
            
            # Check result
            if result.returncode == 0 and self.output_path.exists():
                self.progress.emit(100)
                self.finished.emit(str(self.output_path))
            else:
                error_msg = result.stderr if result.stderr else "Unknown FFmpeg error"
                self.error.emit(f"FFmpeg failed: {error_msg}")
        
        except FileNotFoundError:
            self.error.emit(
                "FFmpeg not found. Please install FFmpeg and ensure it's in your PATH.\n"
                "Download from: https://ffmpeg.org/download.html"
            )
        except Exception as e:
            self.error.emit(f"Video generation error: {str(e)}")
    
    def _build_ffmpeg_command(self):
        """
        Build FFmpeg command with appropriate filters and settings
        
        Returns:
            List of command arguments
        """
        cmd = [
            'ffmpeg',
            '-y',  # Overwrite output file
            '-framerate', str(self.sim_fps),  # Input frame rate
            '-i', str(self.frames_folder / 'frame_%06d.png'),  # Input pattern
        ]
        
        # Build filter chain
        filters = []
        
        # Frame rate conversion
        filters.append(f'fps={self.output_fps}')
        
        # Motion blur (creates smoother animations)
        if self.motion_blur:
            # Blend multiple frames for motion blur effect
            filters.append('minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1')
        
        # Apply filters if any
        if filters:
            cmd.extend(['-vf', ','.join(filters)])
        
        # Video encoding settings
        cmd.extend([
            '-c:v', 'libx264',              # H.264 codec
            '-crf', str(self.quality_crf),   # Quality (18-28)
            '-preset', 'slow',               # Encoding speed (slow = better quality)
            '-pix_fmt', 'yuv420p',           # Pixel format (compatible with most players)
            '-movflags', '+faststart',       # Enable fast start for web playback
            str(self.output_path)            # Output file
        ])
        
        return cmd
    
    def stop(self):
        """Stop the video generation thread"""
        self._is_running = False
        self.terminate()


class VideoGenerationThreadSimple(QThread):
    """
    Simplified video generation thread without motion blur
    Faster but less smooth output
    """
    
    finished = Signal(str)
    error = Signal(str)
    
    def __init__(self, frames_folder, output_path, sim_fps=60, quality_crf=18, output_fps=60):
        super().__init__()
        self.frames_folder = Path(frames_folder)
        self.output_path = Path(output_path)
        self.sim_fps = sim_fps
        self.quality_crf = quality_crf
        self.output_fps = output_fps
    
    def run(self):
        """Generate video with simple FFmpeg command"""
        try:
            # Ensure output directory exists
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Simple FFmpeg command
            cmd = [
                'ffmpeg',
                '-y',
                '-framerate', str(self.sim_fps),
                '-i', str(self.frames_folder / 'frame_%06d.png'),
                '-vf', f'fps={self.output_fps}',
                '-c:v', 'libx264',
                '-crf', str(self.quality_crf),
                '-pix_fmt', 'yuv420p',
                str(self.output_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            
            if result.returncode == 0 and self.output_path.exists():
                self.finished.emit(str(self.output_path))
            else:
                self.error.emit(f"FFmpeg failed: {result.stderr}")
        
        except FileNotFoundError:
            self.error.emit(
                "FFmpeg not found. Please install FFmpeg and ensure it's in your PATH."
            )
        except Exception as e:
            self.error.emit(f"Video generation error: {str(e)}")
