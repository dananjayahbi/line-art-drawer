# Greedy String Art Simulation

A sophisticated Python simulation that recreates the **'Greedy String Art'** algorithm, where a single continuous thread is woven between a circular perimeter of pins to reconstruct a target grayscale portrait.

## Features

- **200-300 Equidistant Nails**: Circular perimeter of pins on a dark wooden canvas
- **Greedy Optimization Algorithm**: Iteratively finds the darkest path between nails
- **Brightness Subtraction**: Simulates physical thread coverage to prevent over-saturation
- **Manim Integration**: Creates cinematic animations with dynamic camera follows
- **9:16 Vertical Format**: Optimized for social media (TikTok, Instagram Reels, YouTube Shorts)
- **60 FPS Rendering**: High-quality motion blur for viral-worthy reveals
- **GPU Acceleration**: Optional CUDA support for faster processing

## Installation

### Prerequisites

1. **Python 3.10+**
2. **FFmpeg**: Required for video generation
   ```bash
   # Windows (using Chocolatey)
   choco install ffmpeg
   
   # Or download from: https://ffmpeg.org/download.html
   ```

### Setup

```bash
# Navigate to SIMULATION_04 directory
cd SIMULATION_04

# Install dependencies
pip install -r requirements.txt

# Optional: Install GPU support (NVIDIA only)
pip install cupy-cuda12x
```

## Usage

### GUI Mode (Recommended)

```bash
python launcher.py
```

This opens the **Control Panel** where you can:
- Upload a target portrait image
- Adjust nail count, thread opacity, and optimization parameters
- Configure window size and visual themes
- Enable/disable recording
- Generate videos from captured frames

### CLI Mode

```bash
python greedy_string_art/main.py \
  --image path/to/portrait.jpg \
  --width 1080 \
  --height 1920 \
  --nail-count 250 \
  --max-lines 3000 \
  --thread-opacity 0.15 \
  --use-manim \
  --record
```

### Command-Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--image` | Path to target portrait image | Required |
| `--width` | Canvas width (pixels) | 1080 |
| `--height` | Canvas height (pixels) | 1920 |
| `--nail-count` | Number of pins on circle | 250 |
| `--max-lines` | Maximum thread lines to draw | 3000 |
| `--thread-opacity` | Thread transparency (0.0-1.0) | 0.15 |
| `--brightness-reduction` | Subtraction per line (0.0-1.0) | 0.12 |
| `--use-manim` | Enable Manim animation | False |
| `--use-gpu` | Enable GPU acceleration | Auto-detect |
| `--record` | Save frames for video | False |
| `--target-duration` | Auto-calculate speed for duration (seconds) | None |

## Algorithm Overview

1. **Initialization**: Place 200-300 nails evenly around a circle
2. **Greedy Selection**: For each iteration:
   - Calculate line from current nail to all others
   - Compute darkness score by sampling pixels along each line
   - Select the line that traverses the darkest pixels
3. **Brightness Subtraction**: Reduce pixel values along the selected line to simulate thread coverage
4. **Rendering**: Draw semi-transparent white line to build up thread density
5. **Repeat**: Continue until max lines reached or convergence

## Output

- **Frames**: Saved to `greedy_string_art/frames/` (if recording enabled)
- **Videos**: Generated in `output/videos/` with timestamp names
- **Format**: MP4 (H.264, 60 FPS, 9:16 aspect ratio)

## Performance Tips

- **GPU**: Enable GPU mode for 10-50x speedup on NVIDIA cards
- **Nail Count**: More nails = better detail but slower (250 is a good balance)
- **Max Lines**: 2000-5000 lines typical for recognizable portraits
- **Image Size**: Pre-scale large images to canvas size for faster processing

## Troubleshooting

**Simulation runs slowly:**
- Reduce nail count or max lines
- Enable GPU acceleration
- Use smaller canvas dimensions

**Generated video is too fast/slow:**
- Use `--target-duration` to auto-calculate speed
- Adjust frame capture frequency in code

**Portrait not recognizable:**
- Increase max lines (try 4000-6000)
- Adjust brightness reduction (lower = more detail retention)
- Use high-contrast images with clear features

**Import errors:**
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Check Python version: `python --version` (must be 3.10+)

## Project Structure

```
SIMULATION_04/
├── launcher.py                     # GUI/CLI entry point
├── README.md                       # This file
├── requirements.txt                # Dependencies
├── logs/                           # Simulation logs
├── output/
│   └── videos/                     # Generated videos
└── greedy_string_art/
    ├── main.py                     # Simulation core
    ├── string_art_engine.py        # Greedy algorithm implementation
    ├── thread_renderer.py          # Thread drawing with Manim
    ├── manim_scene.py              # Manim scene setup
    ├── control_panel_main.py       # GUI window
    ├── settings_manager.py         # Configuration management
    ├── video_thread.py             # Async video generation
    ├── custom_widgets.py           # UI components
    ├── simulation.json             # Metadata
    ├── assets/                     # Icons and static files
    ├── frames/                     # Captured frames (gitignored)
    └── uploads/                    # User images (gitignored)
```

## Credits

- **Algorithm**: Inspired by Petros Vrellis' "A New Way to Knit" (2016)
- **Manim**: 3Blue1Brown's Mathematical Animation Engine
- **GUI**: PySide6 (Qt for Python)

## License

MIT License - See LICENSE file for details

## Contributing

This is part of a larger simulation suite. Follow the established patterns:
- Use the same control panel UI design
- Maintain 60 FPS simulation rate
- Support both GUI and CLI modes
- Include comprehensive settings management

## Support

For issues, questions, or contributions, please refer to the main project repository.
