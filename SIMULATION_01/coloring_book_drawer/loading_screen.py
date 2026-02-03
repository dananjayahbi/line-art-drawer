#!/usr/bin/env python3
"""
Loading Screen for Coloring Book Drawer
========================================
Displays an animated loading screen while image processing occurs in a background thread.
This prevents the "Not Responding" issue during heavy computation.
"""

import pygame
import threading
import time
import math
from typing import Optional, Callable, Any
from dataclasses import dataclass


@dataclass
class LoadingProgress:
    """Tracks loading progress state."""
    current_step: int = 0
    total_steps: int = 6
    step_name: str = "Initializing..."
    is_complete: bool = False
    error: Optional[str] = None
    result: Any = None


class LoadingScreen:
    """
    Animated loading screen with progress indicator.
    
    Shows:
    - Spinning animation
    - Current processing step
    - Progress bar
    - Elapsed time
    """
    
    def __init__(self, screen: pygame.Surface, width: int, height: int):
        """
        Initialize loading screen.
        
        Args:
            screen: Pygame surface to draw on
            width: Screen width
            height: Screen height
        """
        self.screen = screen
        self.width = width
        self.height = height
        
        # Colors (matching terracotta theme)
        self.bg_color = (255, 255, 255)
        self.accent_color = (194, 120, 90)  # Terracotta
        self.text_color = (74, 52, 40)
        self.light_gray = (220, 210, 200)
        self.dark_accent = (168, 93, 68)
        
        # Animation state
        self.animation_angle = 0
        self.start_time = time.time()
        self.dots_count = 0
        self.last_dot_update = 0
        
        # Progress state
        self.progress = LoadingProgress()
        
        # Fonts
        pygame.font.init()
        self.title_font = pygame.font.Font(None, 48)
        self.step_font = pygame.font.Font(None, 32)
        self.info_font = pygame.font.Font(None, 24)
    
    def update_progress(self, step: int, step_name: str):
        """Update current progress step."""
        self.progress.current_step = step
        self.progress.step_name = step_name
    
    def set_complete(self, result: Any = None):
        """Mark loading as complete."""
        self.progress.is_complete = True
        self.progress.result = result
    
    def set_error(self, error: str):
        """Mark loading as failed with error."""
        self.progress.error = error
    
    def draw(self):
        """Draw the loading screen."""
        # Clear screen
        self.screen.fill(self.bg_color)
        
        # Calculate center
        cx, cy = self.width // 2, self.height // 2
        
        # Draw title
        title_text = "Processing Image..."
        title_surface = self.title_font.render(title_text, True, self.text_color)
        title_rect = title_surface.get_rect(center=(cx, cy - 120))
        self.screen.blit(title_surface, title_rect)
        
        # Draw spinning loader
        self._draw_spinner(cx, cy - 40)
        
        # Draw progress bar
        self._draw_progress_bar(cx, cy + 40)
        
        # Draw current step name with animated dots
        current_time = time.time()
        if current_time - self.last_dot_update > 0.5:
            self.dots_count = (self.dots_count + 1) % 4
            self.last_dot_update = current_time
        
        dots = "." * self.dots_count
        step_text = f"[{self.progress.current_step}/{self.progress.total_steps}] {self.progress.step_name}{dots}"
        step_surface = self.step_font.render(step_text, True, self.accent_color)
        step_rect = step_surface.get_rect(center=(cx, cy + 90))
        self.screen.blit(step_surface, step_rect)
        
        # Draw elapsed time
        elapsed = time.time() - self.start_time
        time_text = f"Elapsed: {elapsed:.1f}s"
        time_surface = self.info_font.render(time_text, True, self.light_gray)
        time_rect = time_surface.get_rect(center=(cx, cy + 130))
        self.screen.blit(time_surface, time_rect)
        
        # Draw tip
        tip_text = "💡 Complex images require more processing time"
        tip_surface = self.info_font.render(tip_text, True, self.light_gray)
        tip_rect = tip_surface.get_rect(center=(cx, cy + 170))
        self.screen.blit(tip_surface, tip_rect)
        
        # Update animation angle
        self.animation_angle += 5
        
        pygame.display.flip()
    
    def _draw_spinner(self, cx: int, cy: int):
        """Draw animated spinning loader."""
        radius = 30
        num_dots = 12
        dot_radius = 5
        
        for i in range(num_dots):
            angle = math.radians(self.animation_angle + i * (360 / num_dots))
            x = cx + int(radius * math.cos(angle))
            y = cy + int(radius * math.sin(angle))
            
            # Fade dots based on position (creates trailing effect)
            alpha = int(255 * (i / num_dots))
            # Calculate color interpolation
            r = int(self.accent_color[0] * (alpha / 255) + self.light_gray[0] * (1 - alpha / 255))
            g = int(self.accent_color[1] * (alpha / 255) + self.light_gray[1] * (1 - alpha / 255))
            b = int(self.accent_color[2] * (alpha / 255) + self.light_gray[2] * (1 - alpha / 255))
            
            pygame.draw.circle(self.screen, (r, g, b), (x, y), dot_radius)
    
    def _draw_progress_bar(self, cx: int, cy: int):
        """Draw progress bar."""
        bar_width = 300
        bar_height = 12
        
        # Background
        bg_rect = pygame.Rect(cx - bar_width // 2, cy - bar_height // 2, bar_width, bar_height)
        pygame.draw.rect(self.screen, self.light_gray, bg_rect, border_radius=6)
        
        # Progress fill
        progress = self.progress.current_step / self.progress.total_steps
        fill_width = int(bar_width * progress)
        if fill_width > 0:
            fill_rect = pygame.Rect(cx - bar_width // 2, cy - bar_height // 2, fill_width, bar_height)
            pygame.draw.rect(self.screen, self.accent_color, fill_rect, border_radius=6)
        
        # Border
        pygame.draw.rect(self.screen, self.dark_accent, bg_rect, width=2, border_radius=6)


class BackgroundProcessor:
    """
    Runs image processing in a background thread while showing loading screen.
    """
    
    def __init__(self, screen: pygame.Surface, width: int, height: int):
        """
        Initialize background processor.
        
        Args:
            screen: Pygame surface for loading screen
            width: Screen width
            height: Screen height
        """
        self.screen = screen
        self.width = width
        self.height = height
        self.loading_screen = LoadingScreen(screen, width, height)
        self.clock = pygame.time.Clock()
        
        # Thread control
        self.processing_thread: Optional[threading.Thread] = None
        self.result = None
        self.error = None
    
    def process_with_loading(self, 
                             process_func: Callable,
                             progress_callback: Optional[Callable[[int, str], None]] = None) -> Any:
        """
        Run a processing function in background while showing loading screen.
        
        Args:
            process_func: Function to run in background (should call progress_callback)
            progress_callback: Callback for progress updates (step_num, step_name)
            
        Returns:
            Result from process_func, or raises exception on error
        """
        # Create progress callback that updates loading screen
        def update_progress(step: int, name: str):
            self.loading_screen.update_progress(step, name)
            if progress_callback:
                progress_callback(step, name)
        
        # Start processing in background thread
        def run_processing():
            try:
                self.result = process_func(update_progress)
                self.loading_screen.set_complete(self.result)
            except Exception as e:
                self.error = str(e)
                self.loading_screen.set_error(self.error)
                import traceback
                traceback.print_exc()
        
        self.processing_thread = threading.Thread(target=run_processing, daemon=True)
        self.processing_thread.start()
        
        # Run loading screen loop while processing
        running = True
        while running:
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    pygame.quit()
                    return None
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                        pygame.quit()
                        return None
            
            # Draw loading screen
            self.loading_screen.draw()
            
            # Check if processing is complete
            if self.loading_screen.progress.is_complete or self.loading_screen.progress.error:
                running = False
            
            # Limit frame rate
            self.clock.tick(30)
        
        # Wait for thread to finish
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=1.0)
        
        # Check for errors
        if self.error:
            raise RuntimeError(f"Processing failed: {self.error}")
        
        return self.result


def run_with_loading_screen(screen: pygame.Surface, width: int, height: int,
                            process_func: Callable,
                            progress_callback: Optional[Callable] = None) -> Any:
    """
    Convenience function to run processing with a loading screen.
    
    Args:
        screen: Pygame surface
        width: Screen width
        height: Screen height
        process_func: Function to process (receives progress_callback as argument)
        progress_callback: Optional external callback for progress updates
        
    Returns:
        Result from process_func
    """
    processor = BackgroundProcessor(screen, width, height)
    return processor.process_with_loading(process_func, progress_callback)
