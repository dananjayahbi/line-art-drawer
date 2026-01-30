# Coloring Book Drawer - Standalone Application

A revolutionary pixel-reveal coloring book animation system that creates handwriting-like reveal animations with 100% accuracy to the original artwork.

## Features

- **Pixel-Perfect Reproduction**: Uses a revolutionary pixel-reveal approach instead of vector tracing
- **GPU Acceleration**: Optional NVIDIA GPU support via CuPy
- **Advanced Image Processing**: Skeleton extraction and distance transforms
- **Video Generation**: Built-in video export via FFmpeg
- **Modern GUI**: PySide6-based control panel with real-time preview

## Directory Structure

```
extracted/
├── coloring_book_drawer/      # Main application
│   ├── main.py                # Core simulation engine
│   ├── control_panel.py       # GUI control panel
│   ├── control_panel_main.py  # Control panel launcher
│   ├── pixel_reveal_engine.py # Pixel-reveal algorithm
│   ├── pen_renderer.py        # Drawing renderer
│   ├── frame_animator.py      # Animation generator
│   ├── video_thread.py        # Video generation thread
│   ├── custom_widgets.py      # Custom GUI widgets
│   ├── ui_components.py       # UI helper components
│   ├── settings_manager.py    # Settings persistence
│   ├── simulation.json        # Simulation metadata
│   ├── requirements.txt       # Python dependencies
│   ├── assets/                # Icons and resources
│   ├── frames/                # Generated animation frames
│   └── uploads/               # Uploaded images
├── shared/                    # Shared utilities
│   ├── base_simulation.py     # Base simulation class
│   ├── video_generator.py     # FFmpeg video generator
│   └── __init__.py            # Module initialization
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
# Navigate to the extracted directory
cd extracted

# Install Python packages
pip install -r requirements.txt

# Optional: For GPU acceleration (NVIDIA GPUs with CUDA 12.x)
pip install cupy-cuda12x
```

## Usage

### Method 1: Launch Control Panel (Recommended)

```bash
cd coloring_book_drawer
python control_panel_main.py
```

This opens the modern PySide6 GUI where you can:
- Upload images
- Configure animation settings
- Preview in real-time
- Generate videos

### Method 2: Command Line

```bash
cd coloring_book_drawer
python main.py --image path/to/your/image.png --record --duration 10
```

#### Command Line Options

```
--image IMAGE          Path to input image
--width WIDTH          Canvas width (default: 1200)
--height HEIGHT        Canvas height (default: 700)
--fps FPS              Frames per second (default: 60)
--record               Enable frame recording
--duration DURATION    Animation duration in seconds (default: 10)
--pen-size SIZE        Pen size (default: 2.0)
--speed SPEED          Animation speed (default: 1.0)
--smoothness VALUE     Smoothness factor (default: 0.8)
--pressure-var VALUE   Pressure variation (default: 0.3)
--wiggle VALUE         Wiggle amount (default: 0.5)
```

## How It Works

### Pixel-Reveal Approach

Unlike traditional vector tracing methods, this system:

1. **Extracts Skeleton**: Uses distance transform to find the centerline of ink regions
2. **Measures Thickness**: Calculates line thickness at each skeleton point
3. **Progressive Reveal**: Reveals original image pixels along skeleton paths
4. **Variable Brush**: Adjusts brush size to match local line thickness

### Animation Pipeline

```
Input Image → Preprocessing → Skeleton Extraction → Path Generation
     ↓
Distance Transform → Thickness Mapping → Stroke Ordering
     ↓
Frame Generation → Pixel Reveal → Video Encoding
```

## Configuration

### Simulation Settings (simulation.json)

```json
{
    "name": "coloring_book_drawer",
    "title": "Coloring Book Drawer",
    "description": "Pixel-reveal coloring book animation",
    "version": "3.0.0",
    "author": "Your Name",
    "main_file": "main.py",
    "control_panel": "control_panel_main.py",
    "has_control_panel": true,
    "default_settings": {
        "canvas_width": 1200,
        "canvas_height": 700,
        "fps": 60,
        "record": false,
        "duration": 10.0
    }
}
```

## Video Generation

Videos are automatically generated when recording is enabled. The system uses FFmpeg to encode frames into high-quality MP4 videos.

### Video Settings

- **Default FPS**: 60 (smooth animation)
- **Quality**: High (CRF 18)
- **Codec**: H.264 (libx264)
- **Format**: MP4
- **Output**: `coloring_book_drawer/frames/` → Video

### Manual Video Generation

```python
from shared.video_generator import VideoGenerator

generator = VideoGenerator()
video_path = generator.generate_video(
    frame_folder="coloring_book_drawer/frames",
    output_name="my_animation",
    fps=60,
    quality="high"
)
```

## Troubleshooting

### FFmpeg Not Found

If you get "FFmpeg not found" errors:

1. Install FFmpeg (see Prerequisites)
2. Add FFmpeg to your system PATH
3. Restart your terminal/IDE
4. Verify: `ffmpeg -version`

### scikit-image Not Found

If skeleton extraction fails:

```bash
pip install scikit-image>=0.21.0
```

### GPU Acceleration Issues

For NVIDIA GPUs:

```bash
# Check CUDA version
nvidia-smi

# Install matching CuPy version
pip install cupy-cuda12x  # For CUDA 12.x
# OR
pip install cupy-cuda11x  # For CUDA 11.x
```

### Import Errors

Make sure you're running from the correct directory:

```bash
cd extracted/coloring_book_drawer
python main.py
```

## Development

### Extending the Application

The modular architecture makes it easy to extend:

- **Custom Renderers**: Extend `pen_renderer.py`
- **New Algorithms**: Modify `pixel_reveal_engine.py`
- **Additional Effects**: Add to `frame_animator.py`
- **GUI Enhancements**: Update `control_panel.py`

### Shared Utilities

The `shared/` folder provides reusable components:

- **base_simulation.py**: Base class for pygame simulations
- **video_generator.py**: Universal video generation service

## License

Check the main project for license information.

## Credits

Created as part of the Loops simulation system.
Pixel-reveal algorithm designed for 100% accurate reproduction of original artwork.

---

**Note**: This is a standalone extraction from the main Loops system. It includes all necessary components to run independently.
