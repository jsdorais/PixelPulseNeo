#!/usr/bin/env python3
"""Generate screenshot for a command - minimal version."""

import sys
import os

# Mock the matrix stuff before imports
class MockMatrix:
    def __init__(self, *args, **kwargs):
        pass
    def CreateFrameCanvas(self):
        return self
    def SwapOnVSync(self, canvas):
        return canvas
    def SetImage(self, img, *args):
        pass
    @property
    def brightness(self):
        return 100
    @brightness.setter
    def brightness(self, val):
        pass

class MockOptions:
    def __init__(self):
        self.rows = 64
        self.cols = 64
        self.chain_length = 5
        self.parallel = 1
        self.hardware_mapping = "regular"
        self.brightness = 100
        self.drop_privileges = False
        self.gpio_slowdown = 2

# Patch before imports
import Matrix.config as config
config.USE_EMULATOR = False  # We'll mock it ourselves

# Now mock rgbmatrix
import sys
from unittest.mock import MagicMock

mock_rgbmatrix = MagicMock()
mock_rgbmatrix.RGBMatrix = MockMatrix
mock_rgbmatrix.RGBMatrixOptions = MockOptions
mock_rgbmatrix.graphics = MagicMock()
sys.modules['rgbmatrix'] = mock_rgbmatrix

# Now we can import
from Matrix.driver.commands.base import get_screenshots_dir

def capture_command(cmd_name: str, frames: int = 1):
    """Capture a screenshot for the given command."""
    
    # Import the command
    try:
        module_name = f"Matrix.driver.commands.{cmd_name}_cmd"
        module = __import__(module_name, fromlist=[f"{cmd_name.capitalize()}Cmd"])
        class_name = f"{cmd_name.capitalize()}Cmd"
        cmd_class = getattr(module, class_name)
        cmd = cmd_class()
    except Exception as e:
        print(f"Error loading {cmd_name}: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Initialize and generate frames
    try:
        cmd.update()
        
        # Generate multiple frames if needed (for scrolling content)
        img = None
        for i in range(frames):
            img = cmd.generate_image()
        
        if img:
            output_path = f"{get_screenshots_dir()}/{cmd_name}1.png"
            img.save(output_path)
            print(f"Saved: {output_path}")
        else:
            print(f"No image generated for {cmd_name}")
    except Exception as e:
        print(f"Error generating {cmd_name}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generate_screenshot.py <command_name> [frames]")
        print("Example: python generate_screenshot.py tides")
        print("Example: python generate_screenshot.py newsred 100")
        sys.exit(1)
    
    frames = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    capture_command(sys.argv[1], frames)
