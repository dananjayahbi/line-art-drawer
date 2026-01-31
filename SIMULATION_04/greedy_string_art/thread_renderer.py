#!/usr/bin/env python3
"""
Thread Renderer for Greedy String Art
======================================
Handles rendering of string art threads with visual effects and optional Manim integration.
Features semi-transparent threads, glow effects, camera tracking, and cinematic rendering.
"""

import pygame
import numpy as np
from typing import Tuple, List, Optional, Dict
import cv2
import math

# Optional Manim integration
try:
    from manim import *
    MANIM_AVAILABLE = True
except ImportError:
    MANIM_AVAILABLE = False


class ThreadRenderer:
    """
    Handles Pygame rendering of string art threads with visual effects.
    Supports semi-transparent threads, glow effects, and camera tracking.
    """
    
    def __init__(
        self,
        canvas_size: Tuple[int, int] = (1080, 1920),
        thread_color: Tuple[int, int, int] = (255, 255, 255),
        thread_alpha: int = 25,
        thread_thickness: int = 1,
        glow_enabled: bool = True,
        glow_radius: int = 3,
        glow_strength: float = 0.5,
        nail_color: Tuple[int, int, int] = (180, 140, 80),
        nail_radius: int = 3,
        canvas_color: Tuple[int, int, int] = (40, 35, 30),
        use_camera: bool = True,
        camera_zoom: float = 2.0,
        camera_smooth: float = 0.1
    ):
        """
        Initialize the Thread Renderer.
        
        Args:
            canvas_size: Size of the rendering canvas (width, height)
            thread_color: RGB color of the thread (default white)
            thread_alpha: Transparency of threads (0-255, lower is more transparent)
            thread_thickness: Thickness of thread lines in pixels
            glow_enabled: Enable glow/bloom effect on threads
            glow_radius: Radius of the glow effect
            glow_strength: Strength of the glow (0.0-1.0)
            nail_color: RGB color of nail heads (default brass/gold)
            nail_radius: Radius of nail heads in pixels
            canvas_color: RGB color of wooden canvas background
            use_camera: Enable camera tracking system
            camera_zoom: Zoom level for camera (1.0 = no zoom)
            camera_smooth: Camera interpolation smoothness (0.0-1.0)
        """
        self.canvas_size = canvas_size
        self.thread_color = thread_color
        self.thread_alpha = thread_alpha
        self.thread_thickness = thread_thickness
        self.glow_enabled = glow_enabled
        self.glow_radius = glow_radius
        self.glow_strength = glow_strength
        self.nail_color = nail_color
        self.nail_radius = nail_radius
        self.canvas_color = canvas_color
        self.use_camera = use_camera
        self.camera_zoom = camera_zoom
        self.camera_smooth = camera_smooth
        
        # Camera state
        self.camera_pos = np.array([canvas_size[0] / 2, canvas_size[1] / 2])
        self.camera_target = np.array([canvas_size[0] / 2, canvas_size[1] / 2])
        
        # Thread accumulation for glow effect
        self.thread_layer = None
        self.glow_layer = None
        
        # Motion blur support
        self.motion_blur_enabled = False
        self.motion_blur_strength = 0.3
        self.prev_frames = []
        
        # Initialize layers
        self._init_layers()
    
    def _init_layers(self):
        """Initialize rendering layers."""
        self.thread_layer = pygame.Surface(self.canvas_size, pygame.SRCALPHA)
        self.glow_layer = pygame.Surface(self.canvas_size, pygame.SRCALPHA)
        self.thread_layer.fill((0, 0, 0, 0))
        self.glow_layer.fill((0, 0, 0, 0))
    
    def draw_canvas(self, surface: pygame.Surface):
        """
        Render the wooden canvas background with texture.
        
        Args:
            surface: Pygame surface to draw on
        """
        # Fill with base wood color
        surface.fill(self.canvas_color)
        
        # Add subtle wood grain texture
        wood_texture = np.random.randint(
            -10, 10, 
            (self.canvas_size[1], self.canvas_size[0], 3)
        ).astype(np.int16)
        
        # Apply texture
        arr = pygame.surfarray.pixels3d(surface)
        arr[:] = np.clip(
            arr.astype(np.int16) + wood_texture.transpose(1, 0, 2),
            0, 255
        ).astype(np.uint8)
        del arr
    
    def draw_nail(self, surface: pygame.Surface, pos: Tuple[float, float]):
        """
        Draw a nail head at the given position.
        
        Args:
            surface: Pygame surface to draw on
            pos: (x, y) position of the nail
        """
        # Draw nail body (darker)
        body_color = tuple(int(c * 0.7) for c in self.nail_color)
        pygame.draw.circle(
            surface,
            body_color,
            (int(pos[0]), int(pos[1])),
            self.nail_radius
        )
        
        # Draw nail head highlight (lighter)
        highlight_color = tuple(min(255, int(c * 1.2)) for c in self.nail_color)
        pygame.draw.circle(
            surface,
            highlight_color,
            (int(pos[0] - self.nail_radius * 0.3), int(pos[1] - self.nail_radius * 0.3)),
            max(1, self.nail_radius // 2)
        )
    
    def draw_thread_line(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float],
        accumulate: bool = True
    ):
        """
        Draw a semi-transparent thread line with optional accumulation.
        
        Args:
            start: Starting position (x, y)
            end: Ending position (x, y)
            accumulate: Whether to accumulate on the thread layer
        """
        if accumulate:
            # Draw on thread accumulation layer
            # Use full opacity white - alpha controlled by layer blending
            pygame.draw.line(
                self.thread_layer,
                (255, 255, 255, 255),  # Full white with full alpha
                (int(start[0]), int(start[1])),
                (int(end[0]), int(end[1])),
                self.thread_thickness
            )
            
            # Add anti-aliasing for smoother lines
            pygame.draw.aaline(
                self.thread_layer,
                (255, 255, 255, 255),
                (int(start[0]), int(start[1])),
                (int(end[0]), int(end[1]))
            )
    
    def apply_glow_effect(self):
        """
        Apply glow/bloom effect to accumulated threads.
        Creates a cinematic glowing appearance.
        """
        if not self.glow_enabled:
            return
        
        # Convert thread layer to numpy array
        thread_arr = pygame.surfarray.array3d(self.thread_layer).astype(np.float32)
        alpha_arr = pygame.surfarray.array_alpha(self.thread_layer).astype(np.float32)
        
        # Create glow by blurring the alpha channel
        if alpha_arr.max() > 0:
            # Transpose to get correct dimensions for OpenCV (height, width)
            alpha_transposed = alpha_arr.T
            
            # Normalize alpha
            alpha_normalized = alpha_transposed / 255.0
            
            # Apply Gaussian blur
            glow = cv2.GaussianBlur(
                alpha_normalized,
                (self.glow_radius * 2 + 1, self.glow_radius * 2 + 1),
                0
            )
            
            # Amplify glow
            glow = np.power(glow, 0.8) * self.glow_strength * 255
            glow = np.clip(glow, 0, 255).astype(np.uint8)
            
            # Transpose back for pygame (width, height)
            glow = glow.T
            
            # Apply glow to glow layer
            self.glow_layer.fill((0, 0, 0, 0))
            glow_surf_arr = pygame.surfarray.pixels_alpha(self.glow_layer)
            glow_surf_arr[:] = glow
            del glow_surf_arr
            
            # Colorize glow layer
            glow_arr = pygame.surfarray.pixels3d(self.glow_layer)
            glow_arr[:] = self.thread_color
            del glow_arr
    
    def update_camera(self, target_pos: Tuple[float, float]):
        """
        Update camera position to follow target with smooth interpolation.
        
        Args:
            target_pos: Target position (x, y) to follow
        """
        if not self.use_camera:
            return
        
        self.camera_target = np.array(target_pos)
        
        # Smooth camera movement
        self.camera_pos += (self.camera_target - self.camera_pos) * self.camera_smooth
    
    def get_camera_transform(self) -> Tuple[float, float, float]:
        """
        Get camera transformation parameters.
        
        Returns:
            Tuple of (offset_x, offset_y, zoom)
        """
        if not self.use_camera:
            return (0, 0, 1.0)
        
        # Calculate offset to center camera on target
        offset_x = self.canvas_size[0] / 2 - self.camera_pos[0] * self.camera_zoom
        offset_y = self.canvas_size[1] / 2 - self.camera_pos[1] * self.camera_zoom
        
        return (offset_x, offset_y, self.camera_zoom)
    
    def apply_camera_transform(
        self,
        surface: pygame.Surface,
        source: pygame.Surface
    ) -> pygame.Surface:
        """
        Apply camera transformation to a surface.
        
        Args:
            surface: Target surface to draw on
            source: Source surface to transform
            
        Returns:
            Transformed surface
        """
        offset_x, offset_y, zoom = self.get_camera_transform()
        
        if zoom != 1.0:
            # Scale the source surface
            new_size = (
                int(source.get_width() * zoom),
                int(source.get_height() * zoom)
            )
            scaled = pygame.transform.scale(source, new_size)
            surface.blit(scaled, (offset_x, offset_y))
        else:
            surface.blit(source, (offset_x, offset_y))
        
        return surface
    
    def apply_motion_blur(self, surface: pygame.Surface):
        """
        Apply motion blur effect by blending with previous frames.
        
        Args:
            surface: Surface to apply motion blur to
        """
        if not self.motion_blur_enabled:
            return
        
        # Store current frame
        frame_copy = surface.copy()
        self.prev_frames.append(frame_copy)
        
        # Keep only last few frames
        max_frames = 3
        if len(self.prev_frames) > max_frames:
            self.prev_frames.pop(0)
        
        # Blend with previous frames
        if len(self.prev_frames) > 1:
            for i, prev_frame in enumerate(self.prev_frames[:-1]):
                weight = self.motion_blur_strength * (i + 1) / len(self.prev_frames)
                prev_frame.set_alpha(int(255 * weight))
                surface.blit(prev_frame, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
    
    def render_frame(
        self,
        nail_positions: List[Tuple[float, float]],
        current_nail_idx: Optional[int] = None,
        show_nails: bool = True,
        apply_camera: bool = True
    ) -> pygame.Surface:
        """
        Render a complete frame with threads, nails, and effects.
        
        Args:
            nail_positions: List of (x, y) positions for all nails
            current_nail_idx: Index of the current nail being drawn from
            show_nails: Whether to render nail heads
            apply_camera: Whether to apply camera transformation
            
        Returns:
            Rendered Pygame surface
        """
        # Create output surface
        output = pygame.Surface(self.canvas_size)
        
        # Draw canvas background
        self.draw_canvas(output)
        
        # Apply glow effect to threads
        if self.glow_enabled:
            self.apply_glow_effect()
            
            # Draw glow layer first
            if apply_camera:
                temp_surface = pygame.Surface(self.canvas_size, pygame.SRCALPHA)
                temp_surface.blit(self.glow_layer, (0, 0))
                self.apply_camera_transform(output, temp_surface)
            else:
                output.blit(self.glow_layer, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        
        # Draw thread layer
        if apply_camera:
            temp_surface = pygame.Surface(self.canvas_size, pygame.SRCALPHA)
            temp_surface.blit(self.thread_layer, (0, 0))
            self.apply_camera_transform(output, temp_surface)
        else:
            output.blit(self.thread_layer, (0, 0))
        
        # Draw nails on top
        if show_nails:
            for i, nail_pos in enumerate(nail_positions):
                # Highlight current nail
                if i == current_nail_idx:
                    # Draw larger, brighter highlight
                    highlight_color = (255, 200, 100)
                    pygame.draw.circle(
                        output,
                        highlight_color,
                        (int(nail_pos[0]), int(nail_pos[1])),
                        self.nail_radius + 2
                    )
                
                self.draw_nail(output, nail_pos)
        
        # Apply motion blur if enabled
        self.apply_motion_blur(output)
        
        return output
    
    def clear_threads(self):
        """Clear accumulated thread layer."""
        self.thread_layer.fill((0, 0, 0, 0))
        self.glow_layer.fill((0, 0, 0, 0))
    
    def reset_camera(self):
        """Reset camera to default position."""
        self.camera_pos = np.array([self.canvas_size[0] / 2, self.canvas_size[1] / 2])
        self.camera_target = np.array([self.canvas_size[0] / 2, self.canvas_size[1] / 2])
    
    def set_thread_alpha(self, alpha: int):
        """
        Update thread transparency.
        
        Args:
            alpha: New alpha value (0-255)
        """
        self.thread_alpha = np.clip(alpha, 0, 255)
    
    def set_glow_strength(self, strength: float):
        """
        Update glow effect strength.
        
        Args:
            strength: New strength (0.0-1.0)
        """
        self.glow_strength = np.clip(strength, 0.0, 1.0)


# ============================================================================
# MANIM INTEGRATION (Optional)
# ============================================================================

if MANIM_AVAILABLE:
    class ManimThreadRenderer(Scene):
        """
        Manim-based renderer for creating animated string art videos.
        Supports smooth thread drawing animations and camera tracking.
        """
        
        def __init__(
            self,
            nail_positions: List[Tuple[float, float]],
            thread_sequence: List[Tuple[int, int]],
            canvas_size: Tuple[int, int] = (1080, 1920),
            **kwargs
        ):
            """
            Initialize the Manim Thread Renderer.
            
            Args:
                nail_positions: List of (x, y) nail positions
                thread_sequence: List of (start_nail_idx, end_nail_idx) tuples
                canvas_size: Size of the canvas (width, height)
                **kwargs: Additional Manim Scene arguments
            """
            super().__init__(**kwargs)
            self.nail_positions = nail_positions
            self.thread_sequence = thread_sequence
            self.canvas_size = canvas_size
            
            # Convert positions to Manim coordinate system
            self._convert_coordinates()
            
            # Visual settings
            self.thread_color = WHITE
            self.thread_stroke_width = 1
            self.nail_color = GOLD_E
            self.nail_radius = 0.05
            self.canvas_color = "#28231e"
            
            # Animation settings
            self.thread_draw_time = 0.01  # Time per thread
            self.camera_follow_enabled = True
            self.final_zoom_out = True
        
        def _convert_coordinates(self):
            """Convert Pygame coordinates to Manim coordinate system."""
            # Manim uses center-origin coordinates
            # Convert from top-left origin to center origin
            center_x = self.canvas_size[0] / 2
            center_y = self.canvas_size[1] / 2
            
            # Scale to Manim's coordinate system (typically -7 to 7 for width)
            scale = 14 / max(self.canvas_size)
            
            self.manim_nail_positions = []
            for x, y in self.nail_positions:
                manim_x = (x - center_x) * scale
                manim_y = -(y - center_y) * scale  # Flip Y axis
                self.manim_nail_positions.append([manim_x, manim_y, 0])
        
        def construct(self):
            """Main Manim scene construction."""
            # Set background color
            self.camera.background_color = self.canvas_color
            
            # Create nail objects
            nails = VGroup(*[
                Dot(point=pos, radius=self.nail_radius, color=self.nail_color)
                for pos in self.manim_nail_positions
            ])
            
            # Draw nails
            self.play(Create(nails, run_time=1))
            self.wait(0.5)
            
            # Create thread group
            threads = VGroup()
            
            # Animate thread drawing
            batch_size = 50  # Draw threads in batches for performance
            
            for i, (start_idx, end_idx) in enumerate(self.thread_sequence):
                start_pos = self.manim_nail_positions[start_idx]
                end_pos = self.manim_nail_positions[end_idx]
                
                # Create thread line
                thread = Line(
                    start=start_pos,
                    end=end_pos,
                    stroke_color=self.thread_color,
                    stroke_width=self.thread_stroke_width,
                    stroke_opacity=0.3
                )
                
                threads.add(thread)
                
                # Animate in batches
                if (i + 1) % batch_size == 0 or i == len(self.thread_sequence) - 1:
                    # Get threads to animate in this batch
                    batch_start = max(0, len(threads) - batch_size)
                    batch_threads = threads[batch_start:]
                    
                    self.play(
                        *[Create(t, run_time=self.thread_draw_time) for t in batch_threads],
                        run_time=self.thread_draw_time * len(batch_threads)
                    )
                    
                    # Camera follow
                    if self.camera_follow_enabled and i % 100 == 0:
                        self.play(
                            self.camera.frame.animate.move_to(end_pos),
                            run_time=0.5
                        )
            
            # Final zoom out reveal
            if self.final_zoom_out:
                self.play(
                    self.camera.frame.animate.scale(2).move_to(ORIGIN),
                    run_time=2
                )
            
            self.wait(2)
        
        def render_video(self, output_path: str, quality: str = "high_quality"):
            """
            Render the Manim scene to a video file.
            
            Args:
                output_path: Path to save the output video
                quality: Render quality ('low_quality', 'medium_quality', 'high_quality')
            """
            # Configure render settings
            config.quality = quality
            config.output_file = output_path
            
            # Render the scene
            self.render()


class ManimThreadAnimation:
    """
    Helper class to create Manim animations from string art data.
    Simplifies the process of generating animated videos.
    """
    
    def __init__(
        self,
        nail_positions: List[Tuple[float, float]],
        canvas_size: Tuple[int, int] = (1080, 1920)
    ):
        """
        Initialize animation helper.
        
        Args:
            nail_positions: List of (x, y) nail positions
            canvas_size: Size of the canvas (width, height)
        """
        self.nail_positions = nail_positions
        self.canvas_size = canvas_size
        self.thread_sequence = []
    
    def add_thread(self, start_nail_idx: int, end_nail_idx: int):
        """
        Add a thread to the animation sequence.
        
        Args:
            start_nail_idx: Index of starting nail
            end_nail_idx: Index of ending nail
        """
        self.thread_sequence.append((start_nail_idx, end_nail_idx))
    
    def create_scene(self) -> Optional['ManimThreadRenderer']:
        """
        Create a Manim scene from the accumulated thread data.
        
        Returns:
            ManimThreadRenderer scene or None if Manim not available
        """
        if not MANIM_AVAILABLE:
            print("Warning: Manim not available. Cannot create scene.")
            return None
        
        return ManimThreadRenderer(
            nail_positions=self.nail_positions,
            thread_sequence=self.thread_sequence,
            canvas_size=self.canvas_size
        )
    
    def export_video(
        self,
        output_path: str,
        quality: str = "high_quality"
    ) -> bool:
        """
        Export the animation to a video file.
        
        Args:
            output_path: Path to save the output video
            quality: Render quality
            
        Returns:
            True if successful, False otherwise
        """
        if not MANIM_AVAILABLE:
            print("Error: Manim not available. Cannot export video.")
            return False
        
        try:
            scene = self.create_scene()
            if scene:
                scene.render_video(output_path, quality)
                return True
        except Exception as e:
            print(f"Error exporting video: {e}")
        
        return False


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def create_thread_renderer(config: Dict) -> ThreadRenderer:
    """
    Factory function to create a ThreadRenderer from configuration.
    
    Args:
        config: Dictionary with renderer configuration
        
    Returns:
        Initialized ThreadRenderer
    """
    return ThreadRenderer(
        canvas_size=config.get("canvas_size", (1080, 1920)),
        thread_color=config.get("thread_color", (255, 255, 255)),
        thread_alpha=config.get("thread_alpha", 25),
        thread_thickness=config.get("thread_thickness", 1),
        glow_enabled=config.get("glow_enabled", True),
        glow_radius=config.get("glow_radius", 3),
        glow_strength=config.get("glow_strength", 0.5),
        nail_color=config.get("nail_color", (180, 140, 80)),
        nail_radius=config.get("nail_radius", 3),
        canvas_color=config.get("canvas_color", (40, 35, 30)),
        use_camera=config.get("use_camera", True),
        camera_zoom=config.get("camera_zoom", 2.0),
        camera_smooth=config.get("camera_smooth", 0.1)
    )


def interpolate_color(
    color1: Tuple[int, int, int],
    color2: Tuple[int, int, int],
    t: float
) -> Tuple[int, int, int]:
    """
    Interpolate between two RGB colors.
    
    Args:
        color1: First color (R, G, B)
        color2: Second color (R, G, B)
        t: Interpolation factor (0.0-1.0)
        
    Returns:
        Interpolated color (R, G, B)
    """
    t = np.clip(t, 0.0, 1.0)
    r = int(color1[0] * (1 - t) + color2[0] * t)
    g = int(color1[1] * (1 - t) + color2[1] * t)
    b = int(color1[2] * (1 - t) + color2[2] * t)
    return (r, g, b)
