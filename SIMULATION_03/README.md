# Magnetic Iron Filings Art Simulation

## Overview

An advanced Python-based digital art simulation that recreates the cinematic process of magnetic iron filings forming a portrait on parchment, optimized for viral social media content by blending Pygame's real-time physics with mathematical aesthetics.

## Features

- **10,000+ Metallic Particles**: Charcoal-gray metallic particles with individual inertia, friction, and dipole orientation
- **Realistic Physics**: Particles obey magnetic force with inverse-square law: $F = \frac{k \cdot q_1 \cdot q_2}{r^2}$
- **Organic Chain Formation**: Particles align into spindly, organic 'chains' and spikes following magnetic field lines
- **Portrait Reveal System**: Hidden grayscale attraction map pulls particles into high-density portrait formation
- **Cinematic Rendering**: Smooth camera zooms, motion blur, and high-fidelity transitions
- **9:16 Vertical Video Output**: Optimized for social media platforms (TikTok, Instagram Reels, YouTube Shorts)

## Visual Effects

- Textured ivory parchment background
- Drop-shadows and metallic glints on particles
- Magnetic flux visualization using vector field lines
- Stream lines showing invisible magnetic forces
- Motion blur for dynamic movement

## Quick Start

### GUI Mode (Recommended)
```bash
python launcher.py
```

### CLI Mode
```bash
python launcher.py --image path/to/portrait.png --duration 15
```

## Requirements

- Python 3.8+
- Pygame 2.0+
- NumPy
- OpenCV-Python
- SciPy
- Pillow
- PySide6 (for control panel)

## Installation

```bash
pip install -r requirements.txt
```

## Usage

1. Launch the control panel using `python launcher.py`
2. Upload a portrait image (grayscale works best)
3. Adjust simulation parameters:
   - Particle count (1,000 - 50,000)
   - Magnetic strength
   - Particle size and friction
   - Animation duration
4. Click "Launch Simulation" to start

## Output

Videos are saved to the `output/videos/` directory in high-quality MP4 format, optimized for 9:16 vertical aspect ratio.

## Technical Details

### Physics Model
- Inverse-square law magnetic attraction
- Particle inertia and velocity damping
- Friction coefficients for realistic movement
- Dipole orientation alignment

### Portrait Attraction Map
- Grayscale image converted to attraction strength map
- Darker regions = stronger attraction
- Smooth gradient interpolation for natural particle flow

## License

MIT License
