#!/usr/bin/env python3
"""
Coloring Book Drawer - Standalone Launcher
===========================================
Launch the standalone coloring book drawer application.
"""

import sys
from pathlib import Path

# Add the coloring_book_drawer directory to Python path
EXTRACTED_DIR = Path(__file__).resolve().parent
COLORING_BOOK_DIR = EXTRACTED_DIR / "coloring_book_drawer"
sys.path.insert(0, str(COLORING_BOOK_DIR))

# Import and run the control panel
if __name__ == "__main__":
    # Check if running with command line arguments
    if len(sys.argv) > 1:
        # If arguments provided, run main.py (CLI mode)
        import main
        main.main()
    else:
        # Otherwise, launch the GUI control panel
        try:
            import control_panel_main
            control_panel_main.main()
        except Exception as e:
            print(f"Error launching control panel: {e}")
            print("\nAlternatively, you can run the CLI version:")
            print("python launcher.py --image path/to/image.png")
            sys.exit(1)
