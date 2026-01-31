#!/usr/bin/env python3
"""
Frame Animator for Pendulum Paint Art
=======================================
Handles animation timing, frame capture, and progress tracking.
"""

import pygame
import time


class FrameAnimator:
    """
    Manages animation timing and frame progression for the simulation.
    """
    
    def __init__(self, width, height, fps=60, target_duration=30.0):
        """
        Initialize frame animator.
        
        Args:
            width: Canvas width
            height: Canvas height
            fps: Target frames per second
            target_duration: Target animation duration in seconds
        """
        self.width = width
        self.height = height
        self.fps = fps
        self.target_duration = target_duration
        
        # Frame tracking
        self.frame_count = 0
        self.target_frames = int(fps * target_duration)
        self.start_time = None
        self.elapsed_time = 0.0
        
        # Animation state
        self.is_running = False
        self.is_complete = False
        self.is_paused = False
        
        # Progress
        self.progress = 0.0
    
    def start(self):
        """Start the animation."""
        self.is_running = True
        self.is_complete = False
        self.is_paused = False
        self.start_time = time.time()
        self.frame_count = 0
        self.elapsed_time = 0.0
        self.progress = 0.0
    
    def update(self):
        """
        Update animation state for current frame.
        
        Returns:
            bool: True if animation should continue, False if complete
        """
        if not self.is_running or self.is_paused:
            return not self.is_complete
        
        self.frame_count += 1
        self.elapsed_time = time.time() - self.start_time if self.start_time else 0
        
        # Calculate progress
        self.progress = min(1.0, self.frame_count / self.target_frames)
        
        # Check for completion
        if self.frame_count >= self.target_frames:
            self.is_complete = True
            self.is_running = False
            print(f"Animation complete: {self.frame_count} frames in {self.elapsed_time:.2f}s")
        
        return not self.is_complete
    
    def pause(self):
        """Pause the animation."""
        self.is_paused = True
    
    def resume(self):
        """Resume the animation."""
        self.is_paused = False
    
    def toggle_pause(self):
        """Toggle pause state."""
        self.is_paused = not self.is_paused
        return self.is_paused
    
    def reset(self):
        """Reset animation to beginning."""
        self.frame_count = 0
        self.start_time = None
        self.elapsed_time = 0.0
        self.is_running = False
        self.is_complete = False
        self.is_paused = False
        self.progress = 0.0
    
    def get_frame_count(self):
        """Get current frame count."""
        return self.frame_count
    
    def get_progress(self):
        """Get animation progress (0.0-1.0)."""
        return self.progress
    
    def get_elapsed_time(self):
        """Get elapsed time in seconds."""
        return self.elapsed_time
    
    def get_remaining_time(self):
        """Get estimated remaining time in seconds."""
        if self.progress > 0:
            total_time = self.elapsed_time / self.progress
            return max(0, total_time - self.elapsed_time)
        return self.target_duration
    
    def get_status_text(self):
        """Get formatted status text for display."""
        progress_pct = self.progress * 100
        elapsed = self.elapsed_time
        remaining = self.get_remaining_time()
        
        status = f"Frame: {self.frame_count}/{self.target_frames} | "
        status += f"Progress: {progress_pct:.1f}% | "
        status += f"Elapsed: {elapsed:.1f}s | "
        status += f"Remaining: {remaining:.1f}s"
        
        if self.is_paused:
            status = "[PAUSED] " + status
        elif self.is_complete:
            status = "[COMPLETE] " + status
        
        return status
    
    def set_target_duration(self, duration):
        """Set new target duration."""
        self.target_duration = duration
        self.target_frames = int(self.fps * duration)
    
    def set_fps(self, fps):
        """Set target FPS."""
        self.fps = fps
        self.target_frames = int(fps * self.target_duration)
