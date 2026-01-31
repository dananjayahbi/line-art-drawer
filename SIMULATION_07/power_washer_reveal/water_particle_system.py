"""
Water Particle System for Power Washer Reveal Simulation

Implements a realistic water particle system with physics, visual effects,
and efficient particle pooling for the power washer simulation.
"""

import pygame
import math
import random
from dataclasses import dataclass, field
from typing import List, Tuple, Optional


@dataclass
class Particle:
    """Represents a single water particle."""
    x: float = 0.0
    y: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    size: float = 3.0
    lifetime: float = 0.0
    max_lifetime: float = 1.0
    alpha: int = 255
    color: Tuple[int, int, int] = (255, 255, 255)
    active: bool = False
    is_splash: bool = False
    streak_length: float = 0.0
    bounce_count: int = 0
    max_bounces: int = 2
    
    def reset(self):
        """Reset particle to inactive state."""
        self.active = False
        self.lifetime = 0.0
        self.bounce_count = 0
        self.is_splash = False


class WaterParticleSystem:
    """
    Efficient water particle system with physics and visual effects.
    
    Features:
    - Particle pooling for memory efficiency
    - Realistic gravity and bounce physics
    - Alpha-blended translucent rendering
    - Motion blur/streak effects
    - Splash particle generation
    """
    
    # Physics constants
    GRAVITY = 980.0  # pixels per second squared
    AIR_RESISTANCE = 0.98  # velocity multiplier per frame
    BOUNCE_DAMPING = 0.4  # velocity retained after bounce
    
    # Visual constants
    BASE_COLORS = [
        (255, 255, 255),  # White
        (240, 248, 255),  # Alice blue
        (230, 245, 255),  # Light blue-white
        (220, 240, 255),  # Lighter blue
        (200, 230, 255),  # Light blue
        (180, 220, 255),  # Medium light blue
    ]
    
    def __init__(self, max_particles: int = 2000):
        """
        Initialize the water particle system.
        
        Args:
            max_particles: Maximum number of particles in the pool
        """
        self.max_particles = max_particles
        self.particles: List[Particle] = [Particle() for _ in range(max_particles)]
        self.active_count = 0
        
        # Surface bounds for collision detection
        self.surface_y: Optional[float] = None
        self.bounds: Optional[Tuple[int, int, int, int]] = None  # left, top, right, bottom
        
        # Pre-create particle surfaces for different sizes (optimization)
        self._particle_surfaces = {}
        self._streak_surfaces = {}
        self._init_particle_surfaces()
        
    def _init_particle_surfaces(self):
        """Pre-render particle surfaces for common sizes."""
        for size in range(1, 12):
            for alpha in [255, 200, 150, 100, 50]:
                key = (size, alpha)
                surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
                # Draw gradient circle for water droplet effect
                for r in range(size, 0, -1):
                    ratio = r / size
                    a = int(alpha * ratio * 0.7)
                    color = (230, 245, 255, a)
                    pygame.draw.circle(surf, color, (size, size), r)
                # Add highlight
                highlight_pos = (size - size // 3, size - size // 3)
                highlight_size = max(1, size // 3)
                pygame.draw.circle(surf, (255, 255, 255, min(255, alpha)), 
                                 highlight_pos, highlight_size)
                self._particle_surfaces[key] = surf
    
    def set_bounds(self, left: int, top: int, right: int, bottom: int):
        """
        Set the boundary for particle collisions.
        
        Args:
            left: Left boundary
            top: Top boundary
            right: Right boundary
            bottom: Bottom boundary (surface level)
        """
        self.bounds = (left, top, right, bottom)
        self.surface_y = bottom
    
    def _get_inactive_particle(self) -> Optional[Particle]:
        """Get an inactive particle from the pool."""
        for particle in self.particles:
            if not particle.active:
                return particle
        return None
    
    def emit(self, x: float, y: float, direction: float, spread: float, 
             pressure: float, count: int = 10):
        """
        Emit new water particles from the nozzle.
        
        Args:
            x: Nozzle x position
            y: Nozzle y position
            direction: Base direction in radians (0 = right, pi/2 = down)
            spread: Spray spread angle in radians
            pressure: Water pressure (0.0 to 1.0), affects velocity and size
            count: Number of particles to emit
        """
        base_speed = 400 + pressure * 800  # 400-1200 pixels per second
        
        for _ in range(count):
            particle = self._get_inactive_particle()
            if particle is None:
                break
            
            # Calculate spray angle with random spread
            angle = direction + random.uniform(-spread / 2, spread / 2)
            
            # Add some randomness to speed based on pressure
            speed = base_speed * random.uniform(0.8, 1.2)
            
            # Initialize particle
            particle.x = x + random.uniform(-2, 2)
            particle.y = y + random.uniform(-2, 2)
            particle.vx = math.cos(angle) * speed
            particle.vy = math.sin(angle) * speed
            
            # Size based on pressure with variation
            base_size = 2 + pressure * 4
            particle.size = base_size * random.uniform(0.5, 1.5)
            
            # Lifetime based on pressure
            particle.max_lifetime = 0.5 + pressure * 1.0 + random.uniform(-0.2, 0.2)
            particle.lifetime = 0.0
            
            # Random color from palette
            particle.color = random.choice(self.BASE_COLORS)
            particle.alpha = random.randint(180, 255)
            
            particle.active = True
            particle.is_splash = False
            particle.bounce_count = 0
            particle.max_bounces = random.randint(1, 3)
            
            self.active_count += 1
    
    def create_splash(self, x: float, y: float, intensity: float = 1.0):
        """
        Create splash particles when water hits a surface.
        
        Args:
            x: Splash x position
            y: Splash y position
            intensity: Splash intensity (0.0 to 1.0)
        """
        splash_count = int(5 + intensity * 15)
        
        for _ in range(splash_count):
            particle = self._get_inactive_particle()
            if particle is None:
                break
            
            # Splash particles go upward and outward
            angle = random.uniform(-math.pi, 0)  # Upper hemisphere
            speed = (50 + intensity * 150) * random.uniform(0.5, 1.0)
            
            particle.x = x + random.uniform(-5, 5)
            particle.y = y
            particle.vx = math.cos(angle) * speed
            particle.vy = math.sin(angle) * speed - 50  # Extra upward boost
            
            # Splash particles are smaller
            particle.size = random.uniform(1, 3) * intensity
            
            particle.max_lifetime = 0.3 + random.uniform(0, 0.3)
            particle.lifetime = 0.0
            
            # Slightly more blue for splash
            particle.color = random.choice([
                (220, 240, 255),
                (200, 230, 255),
                (180, 220, 255),
            ])
            particle.alpha = random.randint(100, 200)
            
            particle.active = True
            particle.is_splash = True
            particle.bounce_count = 0
            particle.max_bounces = 0  # Splash particles don't bounce
            
            self.active_count += 1
    
    def update(self, dt: float):
        """
        Update all active particles.
        
        Args:
            dt: Delta time in seconds
        """
        self.active_count = 0
        
        for particle in self.particles:
            if not particle.active:
                continue
            
            self.active_count += 1
            
            # Update lifetime
            particle.lifetime += dt
            if particle.lifetime >= particle.max_lifetime:
                particle.reset()
                continue
            
            # Calculate streak length based on velocity
            speed = math.sqrt(particle.vx ** 2 + particle.vy ** 2)
            particle.streak_length = min(speed * 0.02, 20)  # Cap streak length
            
            # Apply gravity
            particle.vy += self.GRAVITY * dt
            
            # Apply air resistance
            particle.vx *= self.AIR_RESISTANCE
            particle.vy *= self.AIR_RESISTANCE
            
            # Update position
            old_y = particle.y
            particle.x += particle.vx * dt
            particle.y += particle.vy * dt
            
            # Handle boundary collisions
            if self.bounds:
                left, top, right, bottom = self.bounds
                
                # Ground collision
                if particle.y >= bottom:
                    if particle.bounce_count < particle.max_bounces and not particle.is_splash:
                        # Bounce
                        particle.y = bottom
                        particle.vy = -particle.vy * self.BOUNCE_DAMPING
                        particle.vx *= 0.8  # Friction
                        particle.bounce_count += 1
                        
                        # Create small splash on bounce
                        if speed > 200 and random.random() < 0.3:
                            self.create_splash(particle.x, particle.y, 
                                             min(1.0, speed / 800))
                    else:
                        particle.reset()
                        continue
                
                # Side boundaries
                if particle.x < left or particle.x > right:
                    particle.reset()
                    continue
                
                # Top boundary
                if particle.y < top:
                    particle.y = top
                    particle.vy = abs(particle.vy) * 0.5
            
            # Update alpha based on lifetime
            life_ratio = particle.lifetime / particle.max_lifetime
            particle.alpha = int(particle.alpha * (1 - life_ratio * 0.5))
    
    def draw(self, surface: pygame.Surface):
        """
        Render all active particles to the surface.
        
        Args:
            surface: Pygame surface to draw on
        """
        for particle in self.particles:
            if not particle.active:
                continue
            
            # Calculate current alpha with lifetime fade
            life_ratio = particle.lifetime / particle.max_lifetime
            current_alpha = int(particle.alpha * (1 - life_ratio))
            
            if current_alpha <= 0:
                continue
            
            size = max(1, int(particle.size * (1 - life_ratio * 0.3)))
            
            # Draw motion streak for fast-moving particles
            if particle.streak_length > 2 and not particle.is_splash:
                self._draw_streak(surface, particle, current_alpha)
            
            # Draw the particle
            self._draw_particle(surface, particle.x, particle.y, 
                              size, particle.color, current_alpha)
    
    def _draw_particle(self, surface: pygame.Surface, x: float, y: float,
                       size: int, color: Tuple[int, int, int], alpha: int):
        """Draw a single water droplet particle."""
        size = max(1, min(size, 11))  # Clamp size
        alpha_key = min([255, 200, 150, 100, 50], key=lambda a: abs(a - alpha))
        
        key = (size, alpha_key)
        if key in self._particle_surfaces:
            # Use pre-rendered surface
            surf = self._particle_surfaces[key]
            # Apply color tint
            tinted = surf.copy()
            tinted.fill((*color, 0), special_flags=pygame.BLEND_RGB_ADD)
            surface.blit(tinted, (int(x) - size, int(y) - size))
        else:
            # Fallback: draw directly
            particle_surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(particle_surf, (*color, alpha), (size, size), size)
            surface.blit(particle_surf, (int(x) - size, int(y) - size))
    
    def _draw_streak(self, surface: pygame.Surface, particle: Particle, alpha: int):
        """Draw motion blur streak for a particle."""
        # Calculate streak end point (opposite to velocity direction)
        speed = math.sqrt(particle.vx ** 2 + particle.vy ** 2)
        if speed < 1:
            return
        
        # Normalize velocity and calculate streak end
        nx = -particle.vx / speed
        ny = -particle.vy / speed
        
        streak_len = particle.streak_length
        end_x = particle.x + nx * streak_len
        end_y = particle.y + ny * streak_len
        
        # Draw streak with gradient
        streak_alpha = alpha // 2
        streak_color = (*particle.color, streak_alpha)
        
        # Draw multiple lines for thickness based on particle size
        thickness = max(1, int(particle.size * 0.5))
        
        # Create streak surface
        min_x = min(particle.x, end_x) - thickness
        min_y = min(particle.y, end_y) - thickness
        width = int(abs(end_x - particle.x) + thickness * 2)
        height = int(abs(end_y - particle.y) + thickness * 2)
        
        if width > 0 and height > 0:
            streak_surf = pygame.Surface((width + 2, height + 2), pygame.SRCALPHA)
            
            # Draw gradient streak
            steps = 5
            for i in range(steps):
                ratio = i / steps
                sx = particle.x + nx * streak_len * ratio
                sy = particle.y + ny * streak_len * ratio
                step_alpha = int(streak_alpha * (1 - ratio))
                step_size = max(1, int(thickness * (1 - ratio * 0.5)))
                
                pygame.draw.circle(streak_surf, (*particle.color[:3], step_alpha),
                                 (int(sx - min_x), int(sy - min_y)), step_size)
            
            surface.blit(streak_surf, (int(min_x), int(min_y)))
    
    def get_active_count(self) -> int:
        """Return the number of currently active particles."""
        return self.active_count
    
    def clear(self):
        """Deactivate all particles."""
        for particle in self.particles:
            particle.reset()
        self.active_count = 0
    
    def get_particles_at(self, x: float, y: float, radius: float) -> List[Particle]:
        """
        Get all active particles within a radius of a point.
        
        Args:
            x: Center x position
            y: Center y position
            radius: Search radius
            
        Returns:
            List of particles within the radius
        """
        result = []
        radius_sq = radius ** 2
        
        for particle in self.particles:
            if not particle.active:
                continue
            
            dx = particle.x - x
            dy = particle.y - y
            if dx * dx + dy * dy <= radius_sq:
                result.append(particle)
        
        return result


class WaterMist:
    """
    Ambient water mist effect for background atmosphere.
    Creates a subtle mist/fog effect around the spray area.
    """
    
    def __init__(self, max_particles: int = 200):
        """Initialize the mist system."""
        self.max_particles = max_particles
        self.particles = []
        
    def emit(self, x: float, y: float, radius: float = 50):
        """Emit mist particles in an area."""
        if len(self.particles) >= self.max_particles:
            return
        
        count = random.randint(1, 3)
        for _ in range(count):
            if len(self.particles) >= self.max_particles:
                break
            
            angle = random.uniform(0, math.pi * 2)
            dist = random.uniform(0, radius)
            
            self.particles.append({
                'x': x + math.cos(angle) * dist,
                'y': y + math.sin(angle) * dist,
                'vx': random.uniform(-20, 20),
                'vy': random.uniform(-30, -10),
                'size': random.uniform(3, 8),
                'alpha': random.randint(20, 50),
                'lifetime': 0,
                'max_lifetime': random.uniform(0.5, 1.5),
            })
    
    def update(self, dt: float):
        """Update mist particles."""
        for particle in self.particles[:]:
            particle['lifetime'] += dt
            if particle['lifetime'] >= particle['max_lifetime']:
                self.particles.remove(particle)
                continue
            
            particle['x'] += particle['vx'] * dt
            particle['y'] += particle['vy'] * dt
            particle['size'] += dt * 2  # Expand slowly
    
    def draw(self, surface: pygame.Surface):
        """Draw mist particles."""
        for particle in self.particles:
            life_ratio = particle['lifetime'] / particle['max_lifetime']
            alpha = int(particle['alpha'] * (1 - life_ratio))
            size = int(particle['size'])
            
            if alpha > 0 and size > 0:
                mist_surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
                # Soft gradient circle
                for r in range(size, 0, -1):
                    ratio = r / size
                    a = int(alpha * ratio * 0.5)
                    pygame.draw.circle(mist_surf, (230, 240, 255, a), 
                                     (size, size), r)
                surface.blit(mist_surf, 
                           (int(particle['x']) - size, int(particle['y']) - size))
    
    def clear(self):
        """Clear all mist particles."""
        self.particles.clear()


# Demo/test code
if __name__ == "__main__":
    pygame.init()
    
    # Create window
    screen_width, screen_height = 800, 600
    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption("Water Particle System Demo")
    clock = pygame.time.Clock()
    
    # Create particle system
    particle_system = WaterParticleSystem(max_particles=2000)
    particle_system.set_bounds(0, 0, screen_width, screen_height - 50)
    
    # Create mist system
    mist = WaterMist(max_particles=100)
    
    # Font for stats
    font = pygame.font.Font(None, 24)
    
    # Main loop
    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    # Create splash at random position
                    particle_system.create_splash(
                        random.randint(100, screen_width - 100),
                        screen_height - 60,
                        random.uniform(0.5, 1.0)
                    )
        
        # Emit particles from mouse position when clicking
        mouse_buttons = pygame.mouse.get_pressed()
        if mouse_buttons[0]:  # Left mouse button
            mx, my = pygame.mouse.get_pos()
            # Calculate direction toward bottom right
            direction = math.atan2(1, 0.5)  # Angled down-right
            particle_system.emit(mx, my, direction, 
                               spread=0.5, pressure=0.8, count=15)
            mist.emit(mx, my, radius=30)
        
        # Update
        particle_system.update(dt)
        mist.update(dt)
        
        # Draw
        screen.fill((30, 30, 40))  # Dark background
        
        # Draw ground
        pygame.draw.rect(screen, (60, 50, 40), 
                        (0, screen_height - 50, screen_width, 50))
        
        # Draw particles
        mist.draw(screen)
        particle_system.draw(screen)
        
        # Draw stats
        stats_text = f"Particles: {particle_system.get_active_count()} / {particle_system.max_particles}"
        fps_text = f"FPS: {int(clock.get_fps())}"
        stats_surface = font.render(stats_text, True, (255, 255, 255))
        fps_surface = font.render(fps_text, True, (255, 255, 255))
        screen.blit(stats_surface, (10, 10))
        screen.blit(fps_surface, (10, 30))
        
        # Instructions
        instructions = "Click and drag to spray water | SPACE for splash | ESC to quit"
        inst_surface = font.render(instructions, True, (200, 200, 200))
        screen.blit(inst_surface, (10, screen_height - 25))
        
        pygame.display.flip()
    
    pygame.quit()
