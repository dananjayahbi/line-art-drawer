# Pixel Sorting Art

A cinematic pixel sorting visualization system that creates stunning glitch art animations with vaporwave/cyberpunk aesthetics.

## Features

- **Pixel Sorting Visualization**: Watch pixels sort themselves in real-time with cascading wave effects
- **Beat Drop Acceleration**: Dramatic speed increase for impactful climax moments
- **Multiple Sorting Algorithms**: Quick Sort and Shell Sort with step-by-step animation
- **Vaporwave/Cyberpunk Styling**: Neon glow effects and gradient color grading
- **Dynamic Camera Zoom**: Automatic zoom reveal for dramatic effect
- **9:16 Vertical Format**: Optimized for TikTok, Instagram Reels, YouTube Shorts
- **High-Quality Export**: Manim-based rendering for production quality videos
- **Modern GUI**: PySide6-based control panel with real-time preview

## Directory Structure

```
SIMULATION_05/
├── launcher.py                 # Main launcher script
├── README.md                   # This file
├── requirements.txt            # Python dependencies
├── logs/                       # Log files
├── output/                     # Generated outputs
│   └── videos/                 # Exported videos
└── pixel_sorting_art/          # Main application
    ├── main.py                 # Core simulation (pygame)
    ├── manim_scene.py          # High-quality Manim rendering
    ├── sorting_engine.py       # Pixel sorting algorithms
    ├── pixel_renderer.py       # Manim pixel rendering
    ├── frame_animator.py       # Decorative border animation
    ├── control_panel.py        # GUI control panel
    ├── control_panel_main.py   # Control panel launcher
    ├── settings_manager.py     # Settings persistence
    ├── custom_widgets.py       # Custom GUI widgets
    ├── ui_components.py        # UI helper components
    ├── video_thread.py         # Video generation thread
    ├── simulation.json         # Simulation metadata
    ├── assets/                 # Icons and resources
    ├── frames/                 # Generated animation frames
    └── uploads/                # Uploaded images
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
# Navigate to the SIMULATION_05 directory
cd SIMULATION_05

# Install Python packages
pip install -r requirements.txt

# For high-quality Manim rendering (recommended)
pip install manim
```

## Usage

### Method 1: Launch GUI Control Panel (Recommended)

```bash
python launcher.py
```

This opens the modern PySide6 GUI where you can:
- Upload images
- Configure sorting parameters
- Adjust visual effects
- Preview in real-time
- Generate videos

### Method 2: Command Line Interface

```bash
python launcher.py --image path/to/image.png
```

#### CLI Options

**Canvas Settings:**
```
--width WIDTH          Canvas width (default: 1080)
--height HEIGHT        Canvas height (default: 1920)
```

**Image Input:**
```
--image IMAGE          Path to source image (required)
```

**Sorting Parameters:**
```
--algorithm ALGO       Sorting algorithm: quick_sort, shell_sort (default: quick_sort)
--direction DIR        Sort direction: horizontal, vertical, both (default: horizontal)
--criteria CRIT        Sort criteria: brightness, hue (default: brightness)
--threshold VALUE      Scramble intensity 0-1 (default: 0.3)
```

**Animation Parameters:**
```
--speed SPEED          Animation speed multiplier (default: 1.0)
--target-duration SEC  Target duration in seconds (overrides --speed)
--wave-speed VALUE     Cascading wave speed (default: 0.5)
```

**Visual Effects:**
```
--style STYLE          Color style: vaporwave, cyberpunk (default: vaporwave)
--glow VALUE           Neon glow intensity 0-1 (default: 0.8)
--zoom VALUE           Dynamic zoom intensity 0-1 (default: 0.1)
--blur VALUE           Motion blur strength 0-1 (default: 0.3)
```

**Beat Drop Settings:**
```
--no-beat-drop         Disable beat drop acceleration
--beat-timing VALUE    Beat drop timing 0-1 (default: 0.7)
--beat-multiplier VAL  Beat drop speed multiplier (default: 5.0)
```

**Frame Settings:**
```
--no-frame             Disable decorative border frame
--frame-thickness N    Border frame thickness (default: 4)
--frame-speed VALUE    Border frame draw speed (default: 1.0)
--frame-margin N       Border frame margin (default: 20)
```

**Recording:**
```
--no-record            Disable auto-recording
```

### Method 3: Manim High-Quality Rendering

For production-quality video export:

```bash
cd pixel_sorting_art
python manim_scene.py --image path/to/image.png --style vaporwave
```

#### Manim Options

```
--image IMAGE          Path to source image (required)
--output OUTPUT        Output video path
--style STYLE          Color style: vaporwave, cyberpunk
--direction DIR        Sort direction: horizontal, vertical, both
--quality QUALITY      Render quality: low_quality, medium_quality, high_quality, production_quality
--horizontal           Use 16:9 horizontal format instead of 9:16 vertical
```

## Example Commands

### Basic Usage
```bash
# Simple pixel sort with default settings
python launcher.py --image portrait.jpg

# Cyberpunk style with vertical sorting
python launcher.py --image photo.png --style cyberpunk --direction vertical

# Quick 10-second video
python launcher.py --image art.jpg --target-duration 10
```

### Advanced Usage
```bash
# Full customization
python launcher.py --image portrait.jpg \
    --width 1080 --height 1920 \
    --algorithm quick_sort \
    --direction horizontal \
    --criteria brightness \
    --threshold 0.4 \
    --style vaporwave \
    --glow 0.9 \
    --beat-timing 0.6 \
    --beat-multiplier 8.0

# High-quality Manim export
python pixel_sorting_art/manim_scene.py \
    --image portrait.jpg \
    --style vaporwave \
    --quality production_quality
```

## Keyboard Controls (Preview Mode)

| Key | Action |
|-----|--------|
| `ESC` | Exit simulation |
| `SPACE` | Pause/Resume |
| `R` | Reset animation |
| `B` | Force beat drop |

## How It Works

### Pixel Sorting Algorithm

1. **Load Image**: Source image is loaded and resized to fit canvas
2. **Scramble**: Pixels are shuffled based on threshold intensity
3. **Initialize States**: Each pixel's brightness/hue value is calculated
4. **Pre-compute Steps**: Sorting algorithm generates step-by-step swaps
5. **Animate**: Pixels slide to sorted positions with wave effects
6. **Beat Drop**: At specified timing, animation accelerates dramatically
7. **Zoom Reveal**: Final zoom effect reveals completed portrait

### Visual Effects Pipeline

```
Source Image → Scrambling → Sorting Animation → Color Grading
      ↓
Neon Glow Effects → Motion Blur → Dynamic Zoom → Frame Export
```

### Color Grading Styles

**Vaporwave:**
- Magenta and cyan color shifts
- Purple tinted shadows
- Pink highlights
- Magenta neon glow

**Cyberpunk:**
- High contrast
- Neon green highlights
- Red tinted shadows
- Green neon glow

## Configuration

### simulation.json

```json
{
    "id": "pixel_sorting_art",
    "name": "Pixel Sorting Art",
    "description": "Cinematic pixel sorting visualization",
    "version": "1.0.0",
    "requires_manim": true,
    "entry_point": "main.py",
    "control_panel": "control_panel.py"
}
```

## Video Generation

Videos are automatically generated when recording is enabled:

1. **Pygame Preview**: Saves PNG frames to `frames/` folder
2. **Manim Export**: Direct MP4 export with high quality

Use FFmpeg to combine frames:
```bash
ffmpeg -framerate 60 -i frames/frame_%06d.png -c:v libx264 -pix_fmt yuv420p output.mp4
```

## Performance Tips

- Lower `--threshold` for faster sorting (fewer swaps)
- Use `--algorithm shell_sort` for different visual effect
- Reduce canvas size for faster preview
- Use Manim `low_quality` for quick tests
- Enable GPU acceleration when available

## Troubleshooting

### "Manim not found"
```bash
pip install manim
```

### "FFmpeg not found"
Install FFmpeg and add to system PATH.

### Slow performance
- Reduce canvas dimensions
- Lower glow intensity
- Disable motion blur

### Import errors
```bash
pip install -r requirements.txt
```

## Credits

- Sorting algorithms visualization inspired by classic algorithm visualizers
- Vaporwave aesthetics inspired by 80s/90s digital art
- Cyberpunk styling influenced by sci-fi visual culture

## License

MIT License - See LICENSE file for details.

## See Also

- [SIMULATION_01](../SIMULATION_01/) - Coloring Book Drawer
- [SIMULATION_02](../SIMULATION_02/) - Sand Falling Art
- [SIMULATION_03](../SIMULATION_03/) - Magnetic Iron Art
- [SIMULATION_04](../SIMULATION_04/) - Greedy String Art
