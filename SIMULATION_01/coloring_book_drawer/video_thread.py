#!/usr/bin/env python3
"""
Video Generation Thread for Coloring Book Drawer
=================================================
Threaded video generation using FFmpeg with progress reporting.
"""

import os
import subprocess
import threading
from pathlib import Path

from PySide6.QtCore import QThread, Signal


class VideoGenerationThread(QThread):
    """Thread for video generation with proper duration preservation and progress reporting."""
    
    finished = Signal(str)      # Emits output file path
    error = Signal(str)         # Emits error message
    progress = Signal(int)      # Emits progress percentage (0-100)
    status = Signal(str)        # Emits status text updates
    
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
        self.sim_fps = sim_fps
        self.quality_crf = quality_crf
        self.output_fps = output_fps
        self._cancel_requested = False
        self._process = None
    
    def cancel(self):
        """Request cancellation of the video generation."""
        self._cancel_requested = True
        if self._process is not None:
            try:
                self._process.terminate()
            except Exception:
                pass
    
    @staticmethod
    def _drain_stderr(pipe, collected):
        """Drain stderr in a background thread to prevent pipe deadlock."""
        try:
            for line in pipe:
                collected.append(line)
        except Exception:
            pass
    
    def run(self):
        """Run FFmpeg video generation with progress reporting."""
        try:
            # Count total frames for progress calculation
            frame_files = list(Path(self.frames_folder).glob('frame_*.png'))
            total_frames = len(frame_files)
            
            if total_frames == 0:
                self.error.emit("No frames found in the frames folder.")
                return
            
            # Calculate expected duration for progress tracking
            expected_duration = total_frames / max(1, self.sim_fps)
            
            self.status.emit(f"Starting video generation ({total_frames} frames)...")
            self.progress.emit(0)
            
            # Build FFmpeg command with -progress flag for machine-readable output
            cmd = [
                'ffmpeg',
                '-y',
                '-framerate', str(self.sim_fps),
                '-i', str(Path(self.frames_folder) / 'frame_%06d.png'),
                '-vf', f'fps={self.output_fps}',
                '-c:v', 'libx264',
                '-crf', str(self.quality_crf),
                '-pix_fmt', 'yuv420p',
                '-progress', 'pipe:1',   # Progress output to stdout
                '-nostats',               # Suppress stats on stderr to reduce output
                str(self.output_path)
            ]
            
            self.status.emit("Encoding video...")
            
            # Launch FFmpeg with Popen for real-time progress
            creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(Path(self.frames_folder).parent),
                creationflags=creation_flags
            )
            
            # CRITICAL: Drain stderr in a separate thread to prevent pipe deadlock.
            # FFmpeg writes encoding info to stderr. If we only read stdout,
            # the stderr buffer fills up (64KB) and FFmpeg blocks waiting to
            # write to stderr, which stalls our stdout reads.
            stderr_lines = []
            stderr_thread = threading.Thread(
                target=self._drain_stderr,
                args=(self._process.stderr, stderr_lines),
                daemon=True
            )
            stderr_thread.start()
            
            # Parse FFmpeg -progress output (key=value pairs on stdout)
            last_progress = 0
            
            for line in self._process.stdout:
                if self._cancel_requested:
                    self._process.terminate()
                    self._process.wait()
                    output = Path(self.output_path)
                    if output.exists():
                        output.unlink()
                    self.error.emit("Video generation cancelled.")
                    return
                
                line = line.strip()
                
                # Parse frame count
                if line.startswith('frame='):
                    try:
                        current_frame = int(line.split('=')[1].strip())
                        total_output_frames = int(expected_duration * self.output_fps)
                        if total_output_frames > 0:
                            pct = min(99, int(current_frame / total_output_frames * 100))
                            if pct > last_progress:
                                last_progress = pct
                                self.progress.emit(pct)
                                self.status.emit(
                                    f"Encoding frame {current_frame}/{total_output_frames}..."
                                )
                    except (ValueError, IndexError):
                        pass
                
                # Parse out_time_ms for more accurate progress
                elif line.startswith('out_time_ms='):
                    try:
                        time_ms = int(line.split('=')[1].strip())
                        if time_ms > 0 and expected_duration > 0:
                            time_sec = time_ms / 1_000_000
                            pct = min(99, int(time_sec / expected_duration * 100))
                            if pct > last_progress:
                                last_progress = pct
                                self.progress.emit(pct)
                    except (ValueError, IndexError):
                        pass
                
                elif line.startswith('progress=end'):
                    self.progress.emit(100)
                    self.status.emit("Finalizing video...")
            
            # Wait for process and stderr thread to finish
            self._process.wait()
            stderr_thread.join(timeout=5)
            
            if self._cancel_requested:
                output = Path(self.output_path)
                if output.exists():
                    output.unlink()
                self.error.emit("Video generation cancelled.")
                return
            
            if self._process.returncode == 0:
                self.progress.emit(100)
                self.status.emit("Video generation complete!")
                self.finished.emit(str(self.output_path))
            else:
                error_text = ''.join(stderr_lines)
                error_msg = error_text[-500:] if error_text else "Unknown error"
                self.error.emit(f"FFmpeg failed:\n{error_msg}")
                
        except FileNotFoundError:
            self.error.emit("FFmpeg not found. Please install FFmpeg and add it to your PATH.")
        except Exception as e:
            self.error.emit(f"Video generation failed: {str(e)}")
        finally:
            self._process = None
