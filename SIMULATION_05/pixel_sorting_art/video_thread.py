#!/usr/bin/env python3
"""
Video Generation Thread for Pixel Sorting Art
==============================================
Threaded video generation using FFmpeg.
"""

import subprocess
from pathlib import Path

from PySide6.QtCore import QThread, Signal


class VideoGenerationThread(QThread):
    """Thread for video generation with proper duration preservation."""
    
    finished = Signal(str)  # Emits output file path
    error = Signal(str)  # Emits error message
    progress = Signal(int)  # Emits progress percentage (0-100)
    
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
        self.frames_folder = Path(frames_folder)
        self.output_path = Path(output_path)
        self.sim_fps = sim_fps  # Input framerate (how fast frames were captured)
        self.quality_crf = quality_crf
        self.output_fps = output_fps  # Output framerate (always 60 for smoothness)
    
    def run(self):
        """Run FFmpeg video generation with proper duration preservation."""
        try:
            # Ensure output directory exists
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Check for frames
            frame_pattern = str(self.frames_folder / 'frame_%06d.png')
            frames = list(self.frames_folder.glob('frame_*.png'))
            
            if not frames:
                self.error.emit("No frames found in frames folder.")
                return
            
            # Build FFmpeg command
            # Key insight: -framerate tells FFmpeg the INPUT rate (simulation FPS)
            # Then we use fps filter to convert to OUTPUT rate (60 FPS) while
            # preserving duration by duplicating/dropping frames as needed
            
            cmd = [
                'ffmpeg',
                '-y',  # Overwrite output
                '-framerate', str(self.sim_fps),  # Input: How fast frames were captured
                '-i', frame_pattern,
                '-vf', f'fps={self.output_fps}',  # Output: Always 60 FPS (duplicates frames if needed)
                '-c:v', 'libx264',  # H.264 codec
                '-crf', str(self.quality_crf),  # Quality
                '-pix_fmt', 'yuv420p',  # Compatibility
                '-preset', 'medium',  # Encoding speed/quality tradeoff
                '-movflags', '+faststart',  # Enable streaming
                str(self.output_path)
            ]
            
            # Run FFmpeg with progress capture
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(self.frames_folder.parent)
            )
            
            if result.returncode == 0:
                self.finished.emit(str(self.output_path))
            else:
                error_msg = result.stderr[-1000:] if result.stderr else "Unknown error"
                self.error.emit(f"FFmpeg failed:\n{error_msg}")
                
        except FileNotFoundError:
            self.error.emit(
                "FFmpeg not found. Please install FFmpeg and add it to your PATH.\n\n"
                "Installation instructions:\n"
                "- Windows: Download from https://ffmpeg.org/download.html\n"
                "- macOS: brew install ffmpeg\n"
                "- Linux: sudo apt install ffmpeg"
            )
        except Exception as e:
            self.error.emit(f"Video generation failed: {str(e)}")


class VideoGenerationThreadAdvanced(QThread):
    """Advanced thread for video generation with more options."""
    
    finished = Signal(str)  # Emits output file path
    error = Signal(str)  # Emits error message
    progress = Signal(int, str)  # Emits progress percentage and status message
    
    def __init__(self, frames_folder, output_path, settings=None):
        """
        Initialize advanced video generation thread.
        
        Args:
            frames_folder: Path to folder containing captured frames
            output_path: Path for output video file
            settings: Dictionary with video settings
        """
        super().__init__()
        self.frames_folder = Path(frames_folder)
        self.output_path = Path(output_path)
        
        # Default settings
        self.settings = {
            'input_fps': 60,
            'output_fps': 60,
            'codec': 'libx264',
            'crf': 18,
            'preset': 'medium',
            'pix_fmt': 'yuv420p',
            'audio_path': None,
            'audio_offset': 0.0,
        }
        
        if settings:
            self.settings.update(settings)
    
    def run(self):
        """Run FFmpeg video generation with advanced options."""
        try:
            # Ensure output directory exists
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            
            self.progress.emit(10, "Preparing video generation...")
            
            # Check for frames
            frame_pattern = str(self.frames_folder / 'frame_%06d.png')
            frames = sorted(self.frames_folder.glob('frame_*.png'))
            
            if not frames:
                self.error.emit("No frames found in frames folder.")
                return
            
            frame_count = len(frames)
            self.progress.emit(20, f"Found {frame_count} frames...")
            
            # Build base FFmpeg command
            cmd = [
                'ffmpeg',
                '-y',  # Overwrite output
                '-framerate', str(self.settings['input_fps']),
                '-i', frame_pattern,
            ]
            
            # Add audio if specified
            if self.settings.get('audio_path') and Path(self.settings['audio_path']).exists():
                audio_offset = self.settings.get('audio_offset', 0.0)
                if audio_offset > 0:
                    cmd.extend(['-itsoffset', str(audio_offset)])
                cmd.extend(['-i', str(self.settings['audio_path'])])
            
            # Video filter chain
            vf_filters = [f"fps={self.settings['output_fps']}"]
            
            # Add any additional video filters
            if self.settings.get('scale'):
                vf_filters.append(f"scale={self.settings['scale']}")
            
            cmd.extend(['-vf', ','.join(vf_filters)])
            
            # Video codec settings
            cmd.extend([
                '-c:v', self.settings['codec'],
                '-crf', str(self.settings['crf']),
                '-preset', self.settings['preset'],
                '-pix_fmt', self.settings['pix_fmt'],
            ])
            
            # Audio codec if audio is included
            if self.settings.get('audio_path'):
                cmd.extend([
                    '-c:a', 'aac',
                    '-b:a', '192k',
                    '-shortest',  # End when shortest input ends
                ])
            
            # Output file
            cmd.extend([
                '-movflags', '+faststart',
                str(self.output_path)
            ])
            
            self.progress.emit(40, "Running FFmpeg...")
            
            # Run FFmpeg
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(self.frames_folder.parent)
            )
            
            if result.returncode == 0:
                self.progress.emit(100, "Video generation complete!")
                self.finished.emit(str(self.output_path))
            else:
                error_msg = result.stderr[-1000:] if result.stderr else "Unknown error"
                self.error.emit(f"FFmpeg failed:\n{error_msg}")
                
        except FileNotFoundError:
            self.error.emit(
                "FFmpeg not found. Please install FFmpeg and add it to your PATH."
            )
        except Exception as e:
            self.error.emit(f"Video generation failed: {str(e)}")


def get_quality_crf(quality: str) -> int:
    """
    Convert quality string to CRF value.
    
    Args:
        quality: Quality setting ('low', 'medium', 'high', 'ultra')
        
    Returns:
        CRF value (lower = better quality, higher file size)
    """
    quality_map = {
        'low': 28,
        'medium': 23,
        'high': 18,
        'ultra': 15,
        'lossless': 0,
    }
    return quality_map.get(quality.lower(), 23)
