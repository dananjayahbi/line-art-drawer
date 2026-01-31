#!/usr/bin/env python3
"""
Launcher for Greedy String Art Simulation
==========================================
Entry point for both GUI and CLI modes

Usage:
    GUI Mode:  python launcher.py
    CLI Mode:  python launcher.py --image path.jpg [options]
"""

import sys
from pathlib import Path

# Add the simulation directory to Python path
SIMULATION_DIR = Path(__file__).resolve().parent / "greedy_string_art"
sys.path.insert(0, str(SIMULATION_DIR))

def main():
    """
    Main entry point for the simulation
    Detects GUI vs CLI mode based on command-line arguments
    """
    try:
        if len(sys.argv) > 1:
            # CLI mode: Run the simulation directly with arguments
            print("Starting Greedy String Art Simulation (CLI mode)...")
            import main as sim_main
            sim_main.main()
        else:
            # GUI mode: Launch the control panel
            print("Starting Greedy String Art Control Panel (GUI mode)...")
            import control_panel_main
            control_panel_main.main()
    
    except ImportError as e:
        print(f"Error: Could not import required modules: {e}")
        print("\nPlease install dependencies:")
        print("  pip install -r requirements.txt")
        sys.exit(1)
    
    except Exception as e:
        print(f"Error launching simulation: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
