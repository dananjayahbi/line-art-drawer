# Sand Falling Art Simulation

A physics-based art simulation where colored sand grains fall from the top and pile up using realistic collision physics to form your target image.

## Features

- **Realistic Physics**: Uses Pymunk physics engine for accurate sand particle collision and stacking
- **Target Image Formation**: Sand particles are colored to match pixels in your uploaded image
- **Control Panel GUI**: Modern PySide6 interface with drag-and-drop image upload
- **Video Recording**: Automatically record and export your sand art creation as video
- **Customizable Parameters**: Adjust sand particle size, spawn rate, gravity, and more

## How It Works

1. Upload a target image through the control panel
2. Colored sand particles spawn from the top of the screen
3. Particles fall and collide with each other using physics simulation
4. They gradually pile up to form your target image
5. Recording captures the entire process as a video

## Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

## Usage

### GUI Mode (Recommended)
```bash
python launcher.py
```

### CLI Mode
```bash
python launcher.py --image path/to/image.png
```

## Requirements

- Python 3.8+
- FFmpeg (for video generation)
- NVIDIA GPU (optional, for GPU acceleration)

## Directory Structure

```
SIMULATION_02/
├── launcher.py                 # Main launcher
├── requirements.txt            # Python dependencies
├── sand_falling_art/          # Main simulation package
│   ├── main.py                # Core simulation logic
│   ├── control_panel_main.py  # GUI control panel
│   ├── physics_engine.py      # Pymunk physics wrapper
│   ├── sand_renderer.py       # Sand particle rendering
│   ├── settings_manager.py    # Settings persistence
│   ├── custom_widgets.py      # Custom UI widgets
│   ├── video_thread.py        # Video generation thread
│   └── assets/                # Icons and resources
├── logs/                      # Log files
└── output/videos/            # Generated videos
```

## License

MIT License
