#!/usr/bin/env python3
"""
Pixel Sorting Art - Standalone Launcher
========================================
Launch the pixel sorting art simulation.

This launcher:
- Adds the pixel_sorting_art directory to Python path
- If CLI args provided, runs main.py (CLI mode)
- Otherwise launches the GUI control panel
"""

import sys
from pathlib import Path

# Add the pixel_sorting_art directory to Python path
SIMULATION_DIR = Path(__file__).resolve().parent
PIXEL_SORTING_DIR = SIMULATION_DIR / "pixel_sorting_art"
sys.path.insert(0, str(PIXEL_SORTING_DIR))

# Also add parent for shared modules
PARENT_DIR = SIMULATION_DIR.parent
sys.path.insert(0, str(PARENT_DIR))


def main() -> int:
    """
    Main launcher entry point.
    
    Returns:
        Exit code (0 for success, 1 for error)
    """
    # Check if running with command line arguments
    if len(sys.argv) > 1:
        # If arguments provided, run main.py (CLI mode)
        try:
            import main as pixel_sorting_main
            pixel_sorting_main.main()
            return 0
        except Exception as e:
            print(f"Error running CLI mode: {e}")
            import traceback
            traceback.print_exc()
            return 1
    else:
        # Otherwise, launch the GUI control panel
        try:
            import control_panel_main
            control_panel_main.main()
            return 0
        except ImportError as e:
            print(f"Error importing control panel: {e}")
            print("\nThe GUI control panel requires PySide6.")
            print("Install with: pip install PySide6")
            print("\nAlternatively, you can run the CLI version:")
            print("  python launcher.py --image path/to/image.png")
            print("\nFor full CLI options:")
            print("  python launcher.py --help")
            return 1
        except Exception as e:
            print(f"Error launching control panel: {e}")
            import traceback
            traceback.print_exc()
            print("\nAlternatively, you can run the CLI version:")
            print("  python launcher.py --image path/to/image.png")
            return 1


if __name__ == "__main__":
    sys.exit(main())
