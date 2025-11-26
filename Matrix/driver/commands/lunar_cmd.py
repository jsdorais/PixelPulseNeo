"""Lunar phase display with moon images."""

import os
import math
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from Matrix.driver.commands.base import (
    PictureScrollBaseCmd,
    get_total_matrix_width,
    get_total_matrix_height,
    get_fonts_dir,
)

# Path to moon images
LUNAR_ICONS_DIR = os.path.join(os.path.dirname(__file__), "..", "icons", "lunar")

# Phase to image mapping
PHASE_IMAGES = {
    "New Moon": None,  # No image for new moon
    "Waxing Crescent": "waxing_crescent.png",
    "First Quarter": "first_quarter.png",
    "Waxing Gibbous": "waxing_gibbous.png",
    "Full Moon": "full_moon.png",
    "Waning Gibbous": "waning_gibbous.png",
    "Last Quarter": "last_quarter.png",
    "Waning Crescent": "waning_crescent.png",
}

# French translations
PHASE_FRENCH = {
    "New Moon": "Nouvelle Lune",
    "Waxing Crescent": "Premier Croissant",
    "First Quarter": "Premier Quartier",
    "Waxing Gibbous": "Gibbeuse Croissante",
    "Full Moon": "Pleine Lune",
    "Waning Gibbous": "Gibbeuse Décroissante",
    "Last Quarter": "Dernier Quartier",
    "Waning Crescent": "Dernier Croissant",
}


def get_moon_phase():
    """Calculate current moon phase using lunar cycle math."""
    # Known new moon reference: January 11, 2024 at 11:57 UTC
    known_new_moon = datetime(2024, 1, 11, 11, 57)
    lunar_cycle = 29.53058867  # days
    
    now = datetime.now()
    days_since = (now - known_new_moon).total_seconds() / 86400
    cycle_position = (days_since % lunar_cycle) / lunar_cycle
    
    # Illumination percentage (0 at new moon, 1 at full moon, back to 0)
    if cycle_position <= 0.5:
        illumination = cycle_position * 2
    else:
        illumination = (1 - cycle_position) * 2
    
    # Phase name
    if cycle_position < 0.025 or cycle_position >= 0.975:
        phase_name = "New Moon"
    elif cycle_position < 0.225:
        phase_name = "Waxing Crescent"
    elif cycle_position < 0.275:
        phase_name = "First Quarter"
    elif cycle_position < 0.475:
        phase_name = "Waxing Gibbous"
    elif cycle_position < 0.525:
        phase_name = "Full Moon"
    elif cycle_position < 0.725:
        phase_name = "Waning Gibbous"
    elif cycle_position < 0.775:
        phase_name = "Last Quarter"
    else:
        phase_name = "Waning Crescent"
    
    return {
        'phase_name': phase_name,
        'phase_french': PHASE_FRENCH.get(phase_name, phase_name),
        'cycle_position': cycle_position,
        'illumination': illumination,
    }


class LunarCmd(PictureScrollBaseCmd):
    def __init__(self) -> None:
        super().__init__("lunar", "Moon phase display")
        self.scroll = False
        self.refresh = False
        self.recommended_duration = 60
        self.moon_data = None
        self.moon_image = None
        self.font = None
        self.font_small = None

    def update(self, args: list = [], kwargs: dict = {}) -> str:
        self.moon_data = get_moon_phase()
        phase_name = self.moon_data['phase_name']
        print(f"[lunar] Phase: {phase_name} / {self.moon_data['phase_french']} ({self.moon_data['illumination']*100:.0f}% illuminated)", flush=True)
        
        # Load moon image for this phase
        image_file = PHASE_IMAGES.get(phase_name)
        if image_file:
            image_path = os.path.join(LUNAR_ICONS_DIR, image_file)
            try:
                self.moon_image = Image.open(image_path).convert("RGBA")
                # Resize to fit (56x56 pixels)
                self.moon_image = self.moon_image.resize((56, 56), Image.Resampling.LANCZOS)
                print(f"[lunar] Loaded image: {image_file}", flush=True)
            except Exception as e:
                print(f"[lunar] Error loading image {image_path}: {e}", flush=True)
                self.moon_image = None
        else:
            self.moon_image = None
            print(f"[lunar] No image for {phase_name}", flush=True)
        
        # Load fonts
        try:
            self.font = ImageFont.load(get_fonts_dir("10x20.pil"))
            self.font_small = ImageFont.load(get_fonts_dir("6x12.pil"))
        except:
            self.font = ImageFont.load_default()
            self.font_small = ImageFont.load_default()
        
        return super().update(args, kwargs)

    def generate_image(self, args=[], kwargs={}) -> Image.Image | None:
        width = get_total_matrix_width()
        height = get_total_matrix_height()
        
        # Create black background
        img = Image.new("RGB", (width, height), color=(0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        if not self.moon_data:
            return img
        
        # Moon position (left side, centered vertically)
        moon_x = 4
        moon_y = (height - 56) // 2
        
        # Draw moon image if available
        if self.moon_image:
            # Convert RGBA to RGB for pasting
            moon_rgb = Image.new("RGB", self.moon_image.size, (0, 0, 0))
            moon_rgb.paste(self.moon_image, mask=self.moon_image.split()[3] if self.moon_image.mode == 'RGBA' else None)
            img.paste(moon_rgb, (moon_x, moon_y))
        else:
            # New moon - draw a very faint circle outline
            cx, cy = moon_x + 28, moon_y + 28
            draw.ellipse([cx - 26, cy - 26, cx + 26, cy + 26], outline=(30, 30, 35), width=1)
        
        # Draw phase name in English (first line)
        phase_english = self.moon_data['phase_name']
        text_x = 70
        draw.text((text_x, 10), phase_english, font=self.font, fill=(230, 230, 235))
        
        # Draw phase name in French (second line)
        phase_french = self.moon_data['phase_french']
        draw.text((text_x, 32), phase_french, font=self.font_small, fill=(180, 180, 185))
        
        # Draw illumination percentage
        illum_text = f"{self.moon_data['illumination']*100:.0f}% illuminated"
        draw.text((text_x, 48), illum_text, font=self.font_small, fill=(120, 120, 125))
        
        return img
