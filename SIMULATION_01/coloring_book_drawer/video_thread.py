#!/usr/bin/env python3
"""
Video Generation Thread for Coloring Book Drawer
=================================================
Threaded video generation using FFmpeg.
"""

import subprocess
from pathlib import Path

from PySide6.QtCore import QThread, Signal


class VideoGenerationThread(QThread):
    """Thread for video generation with proper duration preservation."""
    
    finished = Signal(str)  # Emits output file path
    error = Signal(str)  # Emits error message
    
    def __init__(self, frames_folder, output_path, sim_fps, quality_crf, output_fps=60):
        """
        Initialize video generation thread.
        
        Args:
            frames_folder: Path to folder containing captured frames
            output_path: Path for output video file
            sim_fps: The FPS at which frames were captured (simulation FPS)
            quality_crf: Quality setting (18-28, lower = better)
            output_fps: Target output FPS (default 60 for smooth playback)
        """
        super().__init__()
        self.frames_folder = frames_folder
        self.output_path = output_path
        self.sim_fps = sim_fps  # Input framerate (how fast frames were captured)
        self.quality_crf = quality_crf
        self.output_fps = output_fps  # Output framerate (always 60 for smoothness)
    
    def run(self):
        """Run FFmpeg video generation with proper duration preservation."""
        try:
            # Build FFmpeg command
            # Key insight: -framerate tells FFmpeg the INPUT rate (simulation FPS)
            # Then we use fps filter to convert to OUTPUT rate (60 FPS) while
            # preserving duration by duplicating/dropping frames as needed
            
            cmd = [
                'ffmpeg',
                '-y',  # Overwrite output
                '-framerate', str(self.sim_fps),  # Input: How fast frames were captured
                '-i', str(self.frames_folder / 'frame_%06d.png'),
                '-vf', f'fps={self.output_fps}',  # Output: Always 60 FPS (duplicates frames if needed)
                '-c:v', 'libx264',  # H.264 codec
                '-crf', str(self.quality_crf),  # Quality
                '-pix_fmt', 'yuv420p',  # Compatibility
                str(self.output_path)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(self.frames_folder.parent)
            )
            
            if result.returncode == 0:
                self.finished.emit(str(self.output_path))
            else:
                error_msg = result.stderr[-500:] if result.stderr else "Unknown error"
                self.error.emit(f"FFmpeg failed:\n{error_msg}")
                
        except FileNotFoundError:
            self.error.emit("FFmpeg not found. Please install FFmpeg and add it to your PATH.")
        except Exception as e:
            self.error.emit(f"Video generation failed: {str(e)}")
