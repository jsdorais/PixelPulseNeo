"""Tides, Sun, and Moon display command."""

from typing import Any
from PIL import Image, ImageDraw
import math
import os
from Matrix.driver.commands.base import (
    PictureScrollBaseCmd,
    get_total_matrix_width,
    get_total_matrix_height,
)
from Matrix.driver.commands.tidesandcurrents import api

# Colors
CURVE_COLOR = (0, 119, 182)       # Ocean blue for tide curve
NOW_LINE_COLOR = (255, 200, 50)   # Golden yellow for current time
TIME_COLOR = (150, 200, 220)      # Light blue for tide times
FEET_COLOR = (100, 180, 255)      # Bright blue for water levels
NAME_COLOR = (180, 180, 180)      # Gray for station name
HIGH_COLOR = (100, 255, 150)      # Green for high tide
LOW_COLOR = (255, 150, 100)       # Orange for low tide

# Sun colors
SUN_COLOR = (255, 200, 50)        # Yellow for sun
SUNRISE_COLOR = (255, 150, 80)    # Orange for sunrise
SUNSET_COLOR = (255, 100, 100)    # Red-orange for sunset

# Moon colors
MOON_LIGHT = (230, 230, 210)      # Bright side of moon
MOON_DARK = (60, 60, 70)          # Dark side of moon

# Path to moon images (shared with lunar app)
LUNAR_ICONS_DIR = os.path.join(os.path.dirname(__file__), "..", "icons", "lunar")

# Phase icon to image file mapping
MOON_IMAGES = {
    "new": None,
    "waxing_crescent": "waxing_crescent.png",
    "first_quarter": "first_quarter.png",
    "waxing_gibbous": "waxing_gibbous.png",
    "full": "full_moon.png",
    "waning_gibbous": "waning_gibbous.png",
    "last_quarter": "last_quarter.png",
    "waning_crescent": "waning_crescent.png",
}
# Path to moon images (shared with lunar app)
LUNAR_ICONS_DIR = os.path.join(os.path.dirname(__file__), "..", "icons", "lunar")

# Phase icon to image file mapping
MOON_IMAGES = {
    "new": None,
    "waxing_crescent": "waxing_crescent.png",
    "first_quarter": "first_quarter.png",
    "waxing_gibbous": "waxing_gibbous.png",
    "full": "full_moon.png",
    "waning_gibbous": "waning_gibbous.png",
    "last_quarter": "last_quarter.png",
    "waning_crescent": "waning_crescent.png",
}



class TidesCmd(PictureScrollBaseCmd):
    def __init__(self) -> None:
        super().__init__("tides", "Displays tides, sun, and moon info")
        self.scroll = False
        self.refresh = False
        self.recommended_duration = 30
        self.tides_data = {}

    def update(self, args=[], kwargs={}) -> None:
        self.tides_data = api.get_tide_data()
        super().update(args, kwargs)

    def _draw_sun_icon(self, draw, x, y, radius=6, rising=True):
        """Draw a simple sun icon with rays."""
        color = SUNRISE_COLOR if rising else SUNSET_COLOR
        # Sun circle
        draw.ellipse([x - radius, y - radius, x + radius, y + radius], fill=SUN_COLOR)
        # Rays
        ray_len = 4
        for angle in range(0, 360, 45):
            rad = math.radians(angle)
            x1 = x + int((radius + 2) * math.cos(rad))
            y1 = y + int((radius + 2) * math.sin(rad))
            x2 = x + int((radius + ray_len + 2) * math.cos(rad))
            y2 = y + int((radius + ray_len + 2) * math.sin(rad))
            draw.line([(x1, y1), (x2, y2)], fill=color, width=1)

    def _draw_moon(self, img, x, y, radius=20, phase_icon="full"):
        """Draw moon using image from lunar icons."""
        image_file = MOON_IMAGES.get(phase_icon)
        if image_file:
            image_path = os.path.join(LUNAR_ICONS_DIR, image_file)
            try:
                moon_img = Image.open(image_path).convert("RGBA")
                size = radius * 2
                moon_img = moon_img.resize((size, size), Image.Resampling.LANCZOS)
                moon_rgb = Image.new("RGB", moon_img.size, (0, 0, 10))
                moon_rgb.paste(moon_img, mask=moon_img.split()[3] if moon_img.mode == 'RGBA' else None)
                img.paste(moon_rgb, (x - radius, y - radius))
            except Exception as e:
                print(f"[tides] Error loading moon image: {e}", flush=True)
                draw = ImageDraw.Draw(img)
                draw.ellipse([x - radius, y - radius, x + radius, y + radius], fill=MOON_LIGHT)
        else:
            draw = ImageDraw.Draw(img)
            draw.ellipse([x - radius, y - radius, x + radius, y + radius], outline=MOON_DARK, width=1)
    def generate_image(self, args: list = [], kwargs: dict = {}) -> Image.Image:
        width: int = get_total_matrix_width()
        height: int = get_total_matrix_height()

        img: Image.Image = Image.new("RGB", (width, height), color=(0, 0, 10))
        draw: ImageDraw.ImageDraw = ImageDraw.Draw(img)
        
        font_small = self.getFont("5x7.pil")
        font_med = self.getFont("6x12.pil")

        # === LEFT PANEL: Sun Info (0-64px) ===
        # Sunrise - top left corner
        self._draw_sun_icon(draw, 12, 12, radius=5, rising=True)
        sunrise = self.tides_data.get("sun", {}).get("sunrise", "N/A")
        draw.text((25, 7), sunrise, font=font_med, fill=SUNRISE_COLOR)
        
        # Sunset - bottom left corner
        self._draw_sun_icon(draw, 12, 52, radius=5, rising=False)
        sunset = self.tides_data.get("sun", {}).get("sunset", "N/A")
        draw.text((25, 47), sunset, font=font_med, fill=SUNSET_COLOR)

        # === CENTER PANELS 2-4: Tide Curve (64-256px) ===
        tide_offset_x = 64
        tide_end_x = 256
        tide_width = tide_end_x - tide_offset_x

        # Draw tide curve
        if self.tides_data.get("curve"):
            original_width = 320
            scale = tide_width / original_width
            
            curve = self.tides_data["curve"]
            corrected_curve = []
            for x, y in curve:
                new_x = tide_offset_x + int(x * scale)
                new_y = height - y
                corrected_curve.append((new_x, new_y))
            
            # Draw filled area under curve
            if len(corrected_curve) > 2:
                fill_points = corrected_curve.copy()
                fill_points.append((corrected_curve[-1][0], height))
                fill_points.append((corrected_curve[0][0], height))
                draw.polygon(fill_points, fill=(0, 40, 70))
            
            # Draw the curve line
            draw.line(corrected_curve, fill=CURVE_COLOR, width=2)

            # Draw current time line
            x_now = self.tides_data.get("x_now")
            if x_now:
                x_now_scaled = tide_offset_x + int(x_now * scale)
                draw.line([(x_now_scaled, 8), (x_now_scaled, 58)], fill=NOW_LINE_COLOR, width=1)
                draw.polygon([(x_now_scaled - 3, 8), (x_now_scaled + 3, 8), (x_now_scaled, 12)], fill=NOW_LINE_COLOR)

            # Draw high/low tide markers
            for entry in self.tides_data.get("hilo", []):
                if entry.get("x") is None:
                    continue
                x = tide_offset_x + int(entry["x"] * scale)
                y = height - entry["y"]
                
                is_high = entry["type"] == "H"
                marker_color = HIGH_COLOR if is_high else LOW_COLOR
                
                # Draw marker dot
                draw.ellipse([x - 2, y - 2, x + 2, y + 2], fill=marker_color)
                
                # Time label
                t = entry["t"]
                if ":" in t:
                    parts = t.split(":")
                    hour = int(parts[0])
                    mins = parts[1]
                    t_short = f"{hour}:{mins}"
                else:
                    t_short = t
                
                # Water level
                v_text = f"{round(entry['v'], 1)}'"
                
                _, _, tw, _ = font_small.getbbox(t_short)
                _, _, vw, _ = font_small.getbbox(v_text)
                
                if is_high:
                    text_y = y + 4
                    draw.text((x - tw // 2, text_y), t_short, font=font_small, fill=TIME_COLOR)
                    draw.text((x - vw // 2, text_y + 8), v_text, font=font_small, fill=FEET_COLOR)
                else:
                    text_y = y - 18
                    draw.text((x - tw // 2, text_y), t_short, font=font_small, fill=TIME_COLOR)
                    draw.text((x - vw // 2, text_y + 8), v_text, font=font_small, fill=FEET_COLOR)

        # Station name at top of tide area
        name = self.tides_data.get("name", "Unknown")
        if name and len(name) > 18:
            name = name[:18]
        draw.text((tide_offset_x + 5, 1), name, font=font_small, fill=NAME_COLOR)

        # === RIGHT PANEL 5: Moon Info (256-320px) ===
        moon = self.tides_data.get("moon", {})
        moon_x = 288
        moon_y = 22
        
        # Draw larger moon
        self._draw_moon(img, moon_x, moon_y, radius=18, phase_icon=moon.get("icon", "full"))
        
        # Moon phase name - split into two lines if needed
        phase_name = moon.get("name", "Moon")
        words = phase_name.split()
        
        if len(words) == 2:
            _, _, tw1, _ = font_small.getbbox(words[0])
            _, _, tw2, _ = font_small.getbbox(words[1])
            draw.text((moon_x - tw1 // 2, moon_y + 22), words[0], font=font_small, fill=MOON_LIGHT)
            draw.text((moon_x - tw2 // 2, moon_y + 31), words[1], font=font_small, fill=MOON_LIGHT)
        else:
            _, _, tw, _ = font_small.getbbox(phase_name)
            draw.text((moon_x - tw // 2, moon_y + 22), phase_name, font=font_small, fill=MOON_LIGHT)

        return img
