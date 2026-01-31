#!/usr/bin/env python3
"""
Magnetic Iron Filings Art - Standalone Launcher
================================================
Launch the standalone magnetic iron filings art simulation application.
"""

import sys
from pathlib import Path

# Add the magnetic_iron_art directory to Python path
EXTRACTED_DIR = Path(__file__).resolve().parent
MAGNETIC_IRON_DIR = EXTRACTED_DIR / "magnetic_iron_art"
sys.path.insert(0, str(MAGNETIC_IRON_DIR))

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
