# shared - Common utilities and base classes for all simulations
# Use lazy imports to avoid loading pygame when not needed

# Video generator doesn't need pygame
from .video_generator import VideoGenerator, generate_video, VideoGeneratorError

# BaseSimulation requires pygame - only import when needed
def get_base_simulation():
    """Lazy import for BaseSimulation to avoid pygame dependency when not needed."""
    from .base_simulation import BaseSimulation
    return BaseSimulation

__all__ = ['VideoGenerator', 'generate_video', 'VideoGeneratorError', 'get_base_simulation']
