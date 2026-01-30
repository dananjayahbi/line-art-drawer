# base_simulation.py - Base class for all simulations
import pygame
import os
from abc import ABC, abstractmethod


class BaseSimulation(ABC):
    """
    Abstract base class for all simulations.
    Provides common functionality for pygame-based visualizations.
    """
    
    def __init__(self, width=1200, height=700, fps=60, title="Simulation"):
        pygame.init()
        self.width = width
        self.height = height
        self.fps = fps
        self.title = title
        
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption(title)
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont('Arial', 24)
        
        # Recording settings
        self.recording = False
        self.frame_count = 0
        self.frames_folder = "frames"
        
        # State
        self.running = True
        self.paused = False
    
    def setup_frames_folder(self, folder_path=None):
        """Create frames folder for recording."""
        if folder_path:
            self.frames_folder = folder_path
        if not os.path.exists(self.frames_folder):
            os.makedirs(self.frames_folder)
    
    def save_frame(self):
        """Save current frame as PNG for video rendering."""
        if self.recording:
            filename = os.path.join(self.frames_folder, f"frame_{self.frame_count:06d}.png")
            pygame.image.save(self.screen, filename)
            self.frame_count += 1
    
    def start_recording(self):
        """Start recording frames."""
        self.recording = True
        self.frame_count = 0
        self.setup_frames_folder()
    
    def stop_recording(self):
        """Stop recording frames."""
        self.recording = False
    
    @abstractmethod
    def handle_events(self):
        """Handle pygame events. Must be implemented by subclass."""
        pass
    
    @abstractmethod
    def update(self):
        """Update simulation state. Must be implemented by subclass."""
        pass
    
    @abstractmethod
    def draw(self):
        """Draw simulation. Must be implemented by subclass."""
        pass
    
    def run(self):
        """Main simulation loop."""
        while self.running:
            self.handle_events()
            
            if not self.paused:
                self.update()
            
            self.draw()
            
            if self.recording:
                self.save_frame()
            
            pygame.display.flip()
            self.clock.tick(self.fps)
        
        pygame.quit()
    
    def quit(self):
        """Clean up and quit."""
        self.running = False
