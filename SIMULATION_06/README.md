# Pendulum Paint Art - Standalone Application

A mesmerizing pendulum paint simulation that creates artwork through physics-based pendulum motion with dripping paint effects. The pendulum follows realistic dual-axis oscillation while dripping paint to recreate target images.

## Features

- **Dual-Axis Pendulum Physics**: Realistic pendulum motion with damping and gravitational effects
- **Attraction-Weighted Dripping**: Paint drips more frequently over dark areas of target image
- **Glossy Paint Rendering**: Thick, wet acrylic paint look with bevel effects and specular highlights
- **Manim Integration**: 3D rendering capabilities for pendulum visualization
- **Video Generation**: Built-in video export via FFmpeg
- **Modern GUI**: PySide6-based control panel with real-time preview

## Directory Structure

```
SIMULATION_06/
├── pendulum_paint_art/        # Main application
│   ├── main.py                # Core simulation engine
│   ├── pendulum_physics_engine.py  # Dual-axis pendulum physics
│   ├── drip_engine.py         # Paint dripping with attraction mapping
│   ├── paint_renderer.py      # Glossy paint VMobject rendering
│   ├── frame_animator.py      # Animation frame handling
│   ├── control_panel.py       # GUI control panel
│   ├── control_panel_main.py  # Control panel launcher
│   ├── video_thread.py        # Video generation thread
│   ├── custom_widgets.py      # Custom GUI widgets
│   ├── settings_manager.py    # Settings persistence
│   ├── simulation.json        # Simulation metadata
│   ├── control_settings.json  # User settings
│   ├── requirements.txt       # Python dependencies
│   ├── assets/                # Icons and resources
│   │   └── icons/             # UI icons
│   ├── frames/                # Generated animation frames
│   └── uploads/               # Uploaded images
├── logs/                      # Log files
├── output/
│   └── videos/                # Generated videos
├── launcher.py                # Main entry point
├── README.md                  # This file
└── requirements.txt           # Complete dependencies
```

## Installation

### Prerequisites

1. **Python 3.8+** - Make sure Python is installed
2. **FFmpeg** - Required for video generation
   - **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH
   - **Linux**: `sudo apt-get install ffmpeg`
   - **macOS**: `brew install ffmpeg`

### Install Dependencies

```bash
# Navigate to the SIMULATION_06 directory
cd SIMULATION_06

# Install Python packages
pip install -r requirements.txt
```

## Usage

### Method 1: Launch Control Panel (Recommended)

```bash
python launcher.py
```

This opens the modern PySide6 GUI where you can:
- Upload target images
- Configure pendulum physics parameters
- Adjust paint dripping settings
- Preview in real-time
- Generate videos

### Method 2: Command Line

```bash
python launcher.py --image path/to/image.png
```

## Physics Parameters

### Pendulum Settings
- **Length**: Pendulum arm length (affects oscillation period)
- **Initial Angle X**: Starting horizontal angle (degrees)
- **Initial Angle Y**: Starting vertical angle (degrees)  
- **Damping X/Y**: Air resistance coefficients (0.0-1.0)
- **Gravity**: Gravitational acceleration multiplier

### Paint Settings
- **Drip Rate**: Base frequency of paint drips
- **Paint Thickness**: Radius of paint drops
- **Viscosity**: How much paint spreads on impact
- **Paint Color**: Color of dripping paint

## How It Works

1. **Pendulum Physics**: A dual-axis spherical pendulum oscillates with damping
2. **Attraction Mapping**: Target image is processed to create a probability map
3. **Drip Decision**: At each frame, probability of dripping is weighted by darkness below
4. **Paint Accumulation**: Paint drops accumulate on the canvas with glossy rendering
5. **Image Reveal**: Over time, the accumulated paint recreates the target image

## Tips for Best Results

- Use high-contrast images with clear dark/light regions
- Start with moderate damping (0.02-0.05) for smooth motion
- Adjust drip rate based on image complexity
- Higher viscosity creates thicker, more defined strokes

## License

MIT License - See LICENSE file for details.
