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
from unittest.mock import MagicMock, patch

mock_rgbmatrix = MagicMock()
mock_rgbmatrix.RGBMatrix = MockMatrix
mock_rgbmatrix.RGBMatrixOptions = MockOptions
mock_rgbmatrix.graphics = MagicMock()
sys.modules['rgbmatrix'] = mock_rgbmatrix

# Mock for YouTube API
class MockYouTubeAPI:
    """Mock YouTube API responses."""
    
    @staticmethod
    def get_mock_channel_data():
        return {
            "subscriber_count": 1740,
            "view_count": 126353,
            "video_count": 45
        }
    
    @staticmethod
    def get_mock_top_video():
        return {
            "title": "Creating a Project Management App in Salesforce - Part 1",
            "views": 37000
        }
    
    @staticmethod
    def get_mock_analytics():
        return {
            "views_7d": 80,
            "watch_hours": 113.6,
            "top_video_7d": {
                "title": "Salesforce How-To Thursdays",
                "views": 161
            }
        }

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

    # For YouTube, inject mock data
    if cmd_name == "youtube":
        mock_data = MockYouTubeAPI.get_mock_channel_data()
        mock_top = MockYouTubeAPI.get_mock_top_video()
        mock_analytics = MockYouTubeAPI.get_mock_analytics()
        
        cmd.channel_data = mock_data
        cmd.top_video = mock_top
        cmd.views_7d = mock_analytics["views_7d"]
        cmd.watch_hours = mock_analytics["watch_hours"]
        cmd.top_video_48h = mock_analytics["top_video_7d"]
        
        # Build combined scroll text
        cmd.combined_scroll_text = (
            f"Top Video (all time): {mock_top['title']} ({mock_top['views']} views)     "
            f"Top Video (last 7 days): {mock_analytics['top_video_7d']['title']} ({mock_analytics['top_video_7d']['views']} views)"
        )
        cmd.scroll_x = 0

    # Initialize and generate frames
    try:
        # Skip update for youtube since we injected data
        if cmd_name != "youtube":
            cmd.update()
        else:
            # Just load fonts and logo for youtube
            from PIL import ImageFont, Image
            from Matrix.driver.commands.base import get_fonts_dir
            cmd.font_large = ImageFont.load(get_fonts_dir("10x20.pil"))
            cmd.font_med = ImageFont.load(get_fonts_dir("6x12.pil"))
            cmd.font_small = ImageFont.load(get_fonts_dir("5x7.pil"))
            
            # Load logo
            logo_path = os.path.join(os.path.dirname(__file__), "Matrix/driver/icons/youtube/youtube_logo.png")
            cmd.logo = Image.open(logo_path).convert("RGBA")
            max_width, max_height = 60, 40
            ratio = min(max_width / cmd.logo.width, max_height / cmd.logo.height)
            new_size = (int(cmd.logo.width * ratio), int(cmd.logo.height * ratio))
            cmd.logo = cmd.logo.resize(new_size, Image.Resampling.LANCZOS)

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
