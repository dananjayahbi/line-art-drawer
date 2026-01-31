"""
Nozzle Renderer for Power Washer Reveal Simulation.

Renders a professional power washer nozzle/wand with water stream effects,
pressure-based visuals, and camera shake simulation.
"""

import pygame
import math
import random
from typing import Tuple, Optional, List


class NozzleRenderer:
    """
    Renders the power washer nozzle/wand visual with water stream effects.
    
    Features:
    - Professional power washer wand design with metal/chrome appearance
    - Pressure-based tip glow indication
    - High-pressure water stream with cone/fan spray pattern
    - Camera shake simulation for recoil effect
    """
    
    def __init__(self, custom_nozzle_path: Optional[str] = None, scale: float = 1.0):
        """
        Initialize the nozzle renderer.
        
        Args:
            custom_nozzle_path: Optional path to a custom nozzle image.
            scale: Scale factor for the nozzle size.
        """
        self.custom_nozzle_path = custom_nozzle_path
        self.scale = scale
        
        # Position and orientation
        self.x = 0.0
        self.y = 0.0
        self.angle = 0.0  # Angle in degrees
        self.target_angle = 0.0
        self.angle_smoothing = 0.15  # How quickly angle catches up to target
        
        # Pressure settings (0.0 to 1.0)
        self.pressure = 0.5
        self.target_pressure = 0.5
        self.pressure_smoothing = 0.1
        
        # Nozzle dimensions (base values, scaled)
        self.wand_length = int(120 * scale)
        self.wand_width = int(16 * scale)
        self.grip_length = int(40 * scale)
        self.grip_width = int(22 * scale)
        self.tip_length = int(25 * scale)
        self.tip_width = int(10 * scale)
        
        # Colors
        self.chrome_color = (180, 185, 190)
        self.chrome_highlight = (220, 225, 230)
        self.chrome_shadow = (120, 125, 130)
        self.grip_color = (40, 40, 45)
        self.grip_accent = (60, 60, 65)
        self.tip_base_color = (150, 155, 160)
        
        # Glow colors for pressure indication
        self.glow_colors = [
            (100, 150, 255),   # Low pressure - blue
            (100, 200, 255),   # Medium-low - cyan
            (150, 255, 200),   # Medium - green-cyan
            (255, 200, 100),   # Medium-high - orange
            (255, 100, 100),   # High pressure - red
        ]
        
        # Water stream settings
        self.stream_base_color = (150, 200, 255)
        self.stream_highlight_color = (200, 230, 255)
        self.stream_length = int(300 * scale)
        self.stream_base_width = int(8 * scale)
        self.spray_angle = 15  # Cone angle in degrees
        self.stream_particles: List[dict] = []
        self.max_particles = 50
        
        # Camera shake settings
        self.shake_intensity = 0.0
        self.max_shake_intensity = 10.0
        self.shake_decay = 0.85  # How quickly shake diminishes
        self.shake_offset_x = 0.0
        self.shake_offset_y = 0.0
        self.shake_frequency = 0.3  # Chance of new shake per frame
        
        # Animation
        self.animation_time = 0.0
        self.glow_pulse = 0.0
        
        # Custom nozzle image
        self.custom_nozzle_surface = None
        if custom_nozzle_path:
            self._load_custom_nozzle(custom_nozzle_path)
    
    def _load_custom_nozzle(self, path: str) -> None:
        """Load a custom nozzle image."""
        try:
            self.custom_nozzle_surface = pygame.image.load(path).convert_alpha()
            # Scale the custom image
            if self.scale != 1.0:
                new_size = (
                    int(self.custom_nozzle_surface.get_width() * self.scale),
                    int(self.custom_nozzle_surface.get_height() * self.scale)
                )
                self.custom_nozzle_surface = pygame.transform.scale(
                    self.custom_nozzle_surface, new_size
                )
        except (pygame.error, FileNotFoundError) as e:
            print(f"Warning: Could not load custom nozzle image: {e}")
            self.custom_nozzle_surface = None
    
    def set_position(self, x: float, y: float) -> None:
        """
        Set the nozzle position.
        
        Args:
            x: X coordinate of the nozzle base.
            y: Y coordinate of the nozzle base.
        """
        self.x = x
        self.y = y
    
    def set_angle(self, angle: float) -> None:
        """
        Set the spray angle (direction nozzle points).
        
        Args:
            angle: Angle in degrees (0 = right, 90 = down).
        """
        self.target_angle = angle
    
    def set_pressure(self, pressure: float) -> None:
        """
        Set the pressure level (affects visuals).
        
        Args:
            pressure: Pressure value from 0.0 (off) to 1.0 (maximum).
        """
        self.target_pressure = max(0.0, min(1.0, pressure))
    
    def get_spray_origin(self) -> Tuple[float, float]:
        """
        Get the position where water comes from (tip of nozzle).
        
        Returns:
            Tuple of (x, y) coordinates of the spray origin.
        """
        # Calculate tip position based on nozzle angle
        angle_rad = math.radians(self.angle)
        total_length = self.wand_length + self.tip_length
        
        tip_x = self.x + math.cos(angle_rad) * total_length
        tip_y = self.y + math.sin(angle_rad) * total_length
        
        return (tip_x + self.shake_offset_x, tip_y + self.shake_offset_y)
    
    def apply_shake(self) -> Tuple[float, float]:
        """
        Apply camera shake effect based on pressure.
        
        Returns:
            Tuple of (offset_x, offset_y) for camera shake.
        """
        # Shake intensity scales with pressure
        target_intensity = self.pressure * self.max_shake_intensity
        
        # Apply shake with some randomness
        if random.random() < self.shake_frequency and self.pressure > 0.1:
            self.shake_intensity = target_intensity
        
        # Calculate shake offsets
        if self.shake_intensity > 0.1:
            shake_angle = random.uniform(0, 2 * math.pi)
            magnitude = random.uniform(0, self.shake_intensity)
            self.shake_offset_x = math.cos(shake_angle) * magnitude
            self.shake_offset_y = math.sin(shake_angle) * magnitude
            
            # Decay shake
            self.shake_intensity *= self.shake_decay
        else:
            # Dampen back to neutral
            self.shake_offset_x *= 0.8
            self.shake_offset_y *= 0.8
        
        return (self.shake_offset_x, self.shake_offset_y)
    
    def update(self, dt: float = 1/60) -> None:
        """
        Update animation and smoothing.
        
        Args:
            dt: Delta time in seconds.
        """
        self.animation_time += dt
        
        # Smooth angle transition
        angle_diff = self.target_angle - self.angle
        # Handle angle wrapping
        if angle_diff > 180:
            angle_diff -= 360
        elif angle_diff < -180:
            angle_diff += 360
        self.angle += angle_diff * self.angle_smoothing
        
        # Smooth pressure transition
        self.pressure += (self.target_pressure - self.pressure) * self.pressure_smoothing
        
        # Update glow pulse
        self.glow_pulse = (math.sin(self.animation_time * 8) + 1) * 0.5
        
        # Apply shake
        self.apply_shake()
        
        # Update stream particles
        self._update_stream_particles(dt)
    
    def _update_stream_particles(self, dt: float) -> None:
        """Update water stream particles."""
        # Add new particles if spraying
        if self.pressure > 0.1 and len(self.stream_particles) < self.max_particles:
            spray_origin = self.get_spray_origin()
            angle_rad = math.radians(self.angle)
            
            # Add variation to spray angle
            spray_variation = random.uniform(-self.spray_angle, self.spray_angle)
            particle_angle = angle_rad + math.radians(spray_variation)
            
            speed = 400 + self.pressure * 300 + random.uniform(-50, 50)
            
            self.stream_particles.append({
                'x': spray_origin[0],
                'y': spray_origin[1],
                'vx': math.cos(particle_angle) * speed,
                'vy': math.sin(particle_angle) * speed,
                'life': 1.0,
                'decay': random.uniform(1.5, 2.5),
                'size': random.uniform(2, 5) * self.scale * self.pressure,
            })
        
        # Update existing particles
        particles_to_keep = []
        for p in self.stream_particles:
            p['x'] += p['vx'] * dt
            p['y'] += p['vy'] * dt
            p['vy'] += 200 * dt  # Gravity
            p['life'] -= p['decay'] * dt
            
            if p['life'] > 0:
                particles_to_keep.append(p)
        
        self.stream_particles = particles_to_keep
    
    def _get_pressure_glow_color(self) -> Tuple[int, int, int]:
        """Get the glow color based on current pressure."""
        # Interpolate between glow colors based on pressure
        idx = self.pressure * (len(self.glow_colors) - 1)
        lower_idx = int(idx)
        upper_idx = min(lower_idx + 1, len(self.glow_colors) - 1)
        t = idx - lower_idx
        
        lower_color = self.glow_colors[lower_idx]
        upper_color = self.glow_colors[upper_idx]
        
        return (
            int(lower_color[0] + (upper_color[0] - lower_color[0]) * t),
            int(lower_color[1] + (upper_color[1] - lower_color[1]) * t),
            int(lower_color[2] + (upper_color[2] - lower_color[2]) * t),
        )
    
    def _draw_nozzle_body(self, surface: pygame.Surface) -> None:
        """Draw the nozzle/wand body."""
        angle_rad = math.radians(self.angle)
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
        
        # Calculate perpendicular direction for width
        perp_cos = math.cos(angle_rad + math.pi/2)
        perp_sin = math.sin(angle_rad + math.pi/2)
        
        # Apply shake offset to base position
        base_x = self.x + self.shake_offset_x
        base_y = self.y + self.shake_offset_y
        
        # Draw grip section (back part, thicker)
        grip_start = (base_x, base_y)
        grip_end = (
            base_x + cos_a * self.grip_length,
            base_y + sin_a * self.grip_length
        )
        
        # Grip polygon (rounded rectangle approximation)
        half_grip = self.grip_width / 2
        grip_points = [
            (grip_start[0] + perp_cos * half_grip, grip_start[1] + perp_sin * half_grip),
            (grip_end[0] + perp_cos * half_grip, grip_end[1] + perp_sin * half_grip),
            (grip_end[0] - perp_cos * half_grip, grip_end[1] - perp_sin * half_grip),
            (grip_start[0] - perp_cos * half_grip, grip_start[1] - perp_sin * half_grip),
        ]
        pygame.draw.polygon(surface, self.grip_color, grip_points)
        
        # Grip texture lines
        for i in range(5):
            offset = (i + 1) * self.grip_length / 6
            line_start = (
                base_x + cos_a * offset + perp_cos * half_grip * 0.9,
                base_y + sin_a * offset + perp_sin * half_grip * 0.9
            )
            line_end = (
                base_x + cos_a * offset - perp_cos * half_grip * 0.9,
                base_y + sin_a * offset - perp_sin * half_grip * 0.9
            )
            pygame.draw.line(surface, self.grip_accent, line_start, line_end, 2)
        
        # Draw wand body (chrome/metal section)
        wand_start = grip_end
        wand_end = (
            wand_start[0] + cos_a * (self.wand_length - self.grip_length),
            wand_start[1] + sin_a * (self.wand_length - self.grip_length)
        )
        
        half_wand = self.wand_width / 2
        wand_points = [
            (wand_start[0] + perp_cos * half_wand, wand_start[1] + perp_sin * half_wand),
            (wand_end[0] + perp_cos * half_wand, wand_end[1] + perp_sin * half_wand),
            (wand_end[0] - perp_cos * half_wand, wand_end[1] - perp_sin * half_wand),
            (wand_start[0] - perp_cos * half_wand, wand_start[1] - perp_sin * half_wand),
        ]
        pygame.draw.polygon(surface, self.chrome_color, wand_points)
        
        # Chrome highlight (top edge)
        highlight_points = [
            (wand_start[0] + perp_cos * half_wand * 0.6, wand_start[1] + perp_sin * half_wand * 0.6),
            (wand_end[0] + perp_cos * half_wand * 0.6, wand_end[1] + perp_sin * half_wand * 0.6),
            (wand_end[0] + perp_cos * half_wand, wand_end[1] + perp_sin * half_wand),
            (wand_start[0] + perp_cos * half_wand, wand_start[1] + perp_sin * half_wand),
        ]
        pygame.draw.polygon(surface, self.chrome_highlight, highlight_points)
        
        # Chrome shadow (bottom edge)
        shadow_points = [
            (wand_start[0] - perp_cos * half_wand * 0.6, wand_start[1] - perp_sin * half_wand * 0.6),
            (wand_end[0] - perp_cos * half_wand * 0.6, wand_end[1] - perp_sin * half_wand * 0.6),
            (wand_end[0] - perp_cos * half_wand, wand_end[1] - perp_sin * half_wand),
            (wand_start[0] - perp_cos * half_wand, wand_start[1] - perp_sin * half_wand),
        ]
        pygame.draw.polygon(surface, self.chrome_shadow, shadow_points)
        
        # Draw tip section
        tip_start = wand_end
        tip_end = (
            tip_start[0] + cos_a * self.tip_length,
            tip_start[1] + sin_a * self.tip_length
        )
        
        # Tip tapers to a point
        half_tip_base = self.tip_width / 2
        half_tip_end = self.tip_width / 4
        tip_points = [
            (tip_start[0] + perp_cos * half_tip_base, tip_start[1] + perp_sin * half_tip_base),
            (tip_end[0] + perp_cos * half_tip_end, tip_end[1] + perp_sin * half_tip_end),
            (tip_end[0] - perp_cos * half_tip_end, tip_end[1] - perp_sin * half_tip_end),
            (tip_start[0] - perp_cos * half_tip_base, tip_start[1] - perp_sin * half_tip_base),
        ]
        pygame.draw.polygon(surface, self.tip_base_color, tip_points)
        
        # Draw pressure glow on tip
        if self.pressure > 0.05:
            glow_color = self._get_pressure_glow_color()
            glow_alpha = int(100 + 100 * self.pressure * (0.7 + 0.3 * self.glow_pulse))
            glow_radius = int((self.tip_width / 2 + 5) * self.pressure * (0.8 + 0.2 * self.glow_pulse))
            
            # Create glow surface
            glow_size = glow_radius * 4
            glow_surface = pygame.Surface((glow_size, glow_size), pygame.SRCALPHA)
            
            # Draw multiple circles for glow effect
            for i in range(3):
                radius = glow_radius * (1 - i * 0.25)
                alpha = glow_alpha // (i + 1)
                color_with_alpha = (*glow_color, min(255, alpha))
                pygame.draw.circle(
                    glow_surface,
                    color_with_alpha,
                    (glow_size // 2, glow_size // 2),
                    int(radius)
                )
            
            # Blit glow at tip
            glow_pos = (tip_end[0] - glow_size // 2, tip_end[1] - glow_size // 2)
            surface.blit(glow_surface, glow_pos, special_flags=pygame.BLEND_RGBA_ADD)
    
    def _draw_water_stream(self, surface: pygame.Surface) -> None:
        """Draw the high-pressure water stream."""
        if self.pressure < 0.05:
            return
        
        spray_origin = self.get_spray_origin()
        angle_rad = math.radians(self.angle)
        
        # Draw main stream cone
        stream_alpha = int(50 + 150 * self.pressure)
        stream_surface = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        
        # Calculate stream end points for cone shape
        stream_end_distance = self.stream_length * self.pressure
        half_spray = math.radians(self.spray_angle * self.pressure)
        
        # Left edge of spray
        left_angle = angle_rad - half_spray
        left_end = (
            spray_origin[0] + math.cos(left_angle) * stream_end_distance,
            spray_origin[1] + math.sin(left_angle) * stream_end_distance
        )
        
        # Right edge of spray
        right_angle = angle_rad + half_spray
        right_end = (
            spray_origin[0] + math.cos(right_angle) * stream_end_distance,
            spray_origin[1] + math.sin(right_angle) * stream_end_distance
        )
        
        # Draw cone as triangle with gradient effect
        cone_points = [spray_origin, left_end, right_end]
        
        # Main stream color
        stream_color = (*self.stream_base_color, stream_alpha)
        pygame.draw.polygon(stream_surface, stream_color, cone_points)
        
        # Draw highlight in center of stream
        center_width = self.stream_base_width * self.pressure
        highlight_end = (
            spray_origin[0] + math.cos(angle_rad) * stream_end_distance * 0.7,
            spray_origin[1] + math.sin(angle_rad) * stream_end_distance * 0.7
        )
        
        highlight_color = (*self.stream_highlight_color, stream_alpha // 2)
        pygame.draw.line(
            stream_surface,
            highlight_color,
            spray_origin,
            highlight_end,
            max(1, int(center_width))
        )
        
        surface.blit(stream_surface, (0, 0))
        
        # Draw stream particles
        for p in self.stream_particles:
            alpha = int(200 * p['life'] * self.pressure)
            size = max(1, int(p['size'] * p['life']))
            
            particle_color = (
                self.stream_base_color[0],
                self.stream_base_color[1],
                self.stream_base_color[2],
                alpha
            )
            
            particle_surface = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(particle_surface, particle_color, (size, size), size)
            surface.blit(particle_surface, (int(p['x'] - size), int(p['y'] - size)))
    
    def _draw_mist_effect(self, surface: pygame.Surface) -> None:
        """Draw mist/spray effect around the stream."""
        if self.pressure < 0.2:
            return
        
        spray_origin = self.get_spray_origin()
        angle_rad = math.radians(self.angle)
        
        mist_surface = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        
        # Draw random mist particles
        num_mist = int(20 * self.pressure)
        for _ in range(num_mist):
            # Random position along stream
            distance = random.uniform(20, self.stream_length * 0.5 * self.pressure)
            spray_var = random.uniform(-self.spray_angle * 1.5, self.spray_angle * 1.5)
            particle_angle = angle_rad + math.radians(spray_var)
            
            mist_x = spray_origin[0] + math.cos(particle_angle) * distance
            mist_y = spray_origin[1] + math.sin(particle_angle) * distance
            
            # Add some random offset
            mist_x += random.uniform(-15, 15)
            mist_y += random.uniform(-15, 15)
            
            alpha = int(30 * self.pressure * random.uniform(0.3, 1.0))
            size = random.randint(2, 6)
            
            mist_color = (200, 220, 255, alpha)
            pygame.draw.circle(mist_surface, mist_color, (int(mist_x), int(mist_y)), size)
        
        surface.blit(mist_surface, (0, 0))
    
    def draw(self, surface: pygame.Surface) -> None:
        """
        Render the nozzle and water stream.
        
        Args:
            surface: Pygame surface to draw on.
        """
        # Update animations
        self.update()
        
        # Draw in order: mist (back), stream, nozzle (front)
        self._draw_mist_effect(surface)
        self._draw_water_stream(surface)
        
        # Use custom nozzle if available
        if self.custom_nozzle_surface:
            # Rotate custom nozzle image
            rotated = pygame.transform.rotate(self.custom_nozzle_surface, -self.angle)
            rect = rotated.get_rect(center=(
                self.x + self.shake_offset_x,
                self.y + self.shake_offset_y
            ))
            surface.blit(rotated, rect)
        else:
            self._draw_nozzle_body(surface)
    
    def get_shake_offset(self) -> Tuple[float, float]:
        """
        Get the current camera shake offset.
        
        Returns:
            Tuple of (offset_x, offset_y) for camera shake.
        """
        return (self.shake_offset_x, self.shake_offset_y)
    
    def set_shake_intensity(self, intensity: float) -> None:
        """
        Set the maximum shake intensity.
        
        Args:
            intensity: Maximum shake intensity in pixels.
        """
        self.max_shake_intensity = max(0.0, intensity)
    
    def set_spray_angle(self, angle: float) -> None:
        """
        Set the spray cone angle.
        
        Args:
            angle: Spray cone half-angle in degrees.
        """
        self.spray_angle = max(1.0, min(45.0, angle))
    
    def set_stream_length(self, length: float) -> None:
        """
        Set the maximum stream length.
        
        Args:
            length: Stream length in pixels.
        """
        self.stream_length = max(50, length)


class NozzleEffects:
    """Additional visual effects for the nozzle renderer."""
    
    @staticmethod
    def create_splash_particles(
        x: float,
        y: float,
        pressure: float,
        count: int = 20
    ) -> List[dict]:
        """
        Create splash particle data when stream hits a surface.
        
        Args:
            x: X coordinate of impact.
            y: Y coordinate of impact.
            pressure: Current pressure level.
            count: Number of particles to create.
            
        Returns:
            List of particle dictionaries.
        """
        particles = []
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(50, 150) * pressure
            
            particles.append({
                'x': x,
                'y': y,
                'vx': math.cos(angle) * speed,
                'vy': math.sin(angle) * speed - random.uniform(50, 100),
                'life': 1.0,
                'decay': random.uniform(2.0, 4.0),
                'size': random.uniform(1, 4) * pressure,
                'color': (180, 210, 255),
            })
        
        return particles
    
    @staticmethod
    def draw_impact_ring(
        surface: pygame.Surface,
        x: float,
        y: float,
        radius: float,
        pressure: float
    ) -> None:
        """
        Draw an impact ring effect at the spray target.
        
        Args:
            surface: Pygame surface to draw on.
            x: X coordinate of impact center.
            y: Y coordinate of impact center.
            radius: Base radius of the ring.
            pressure: Current pressure level.
        """
        ring_surface = pygame.Surface(
            (int(radius * 4), int(radius * 4)),
            pygame.SRCALPHA
        )
        center = (int(radius * 2), int(radius * 2))
        
        # Draw multiple rings for effect
        for i in range(3):
            ring_radius = int(radius * (0.5 + i * 0.3) * pressure)
            alpha = int(80 * pressure / (i + 1))
            color = (200, 220, 255, alpha)
            
            if ring_radius > 0:
                pygame.draw.circle(ring_surface, color, center, ring_radius, 2)
        
        blit_pos = (int(x - radius * 2), int(y - radius * 2))
        surface.blit(ring_surface, blit_pos)


# Example usage and testing
if __name__ == "__main__":
    pygame.init()
    
    # Create window
    screen_width, screen_height = 1280, 720
    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption("Nozzle Renderer Test")
    
    # Create nozzle renderer
    nozzle = NozzleRenderer(scale=1.0)
    nozzle.set_position(200, screen_height // 2)
    nozzle.set_pressure(0.7)
    
    # Main loop
    clock = pygame.time.Clock()
    running = True
    
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEWHEEL:
                # Adjust pressure with scroll wheel
                current = nozzle.target_pressure
                nozzle.set_pressure(current + event.y * 0.1)
        
        # Get mouse position and calculate angle
        mouse_x, mouse_y = pygame.mouse.get_pos()
        dx = mouse_x - nozzle.x
        dy = mouse_y - nozzle.y
        angle = math.degrees(math.atan2(dy, dx))
        nozzle.set_angle(angle)
        
        # Update pressure based on mouse button
        if pygame.mouse.get_pressed()[0]:
            nozzle.set_pressure(min(1.0, nozzle.target_pressure + 0.02))
        else:
            nozzle.set_pressure(max(0.0, nozzle.target_pressure - 0.01))
        
        # Clear screen
        screen.fill((30, 35, 40))
        
        # Draw nozzle
        nozzle.draw(screen)
        
        # Draw impact effect at cursor when spraying
        if nozzle.pressure > 0.1:
            spray_origin = nozzle.get_spray_origin()
            NozzleEffects.draw_impact_ring(screen, mouse_x, mouse_y, 30, nozzle.pressure)
        
        # Draw info
        font = pygame.font.Font(None, 24)
        info_text = f"Pressure: {nozzle.pressure:.2f} | Angle: {nozzle.angle:.1f}° | Scroll to adjust, Click to spray"
        text_surface = font.render(info_text, True, (200, 200, 200))
        screen.blit(text_surface, (10, 10))
        
        pygame.display.flip()
        clock.tick(60)
    
    pygame.quit()
