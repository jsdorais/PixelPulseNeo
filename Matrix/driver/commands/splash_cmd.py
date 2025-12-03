"""Splash screen display."""
import os
from PIL import Image, ImageDraw, ImageFont
from Matrix.driver.commands.base import (
    PictureScrollBaseCmd,
    get_total_matrix_width,
    get_total_matrix_height,
    get_fonts_dir,
)

SPLASH_ICONS_DIR = os.path.join(os.path.dirname(__file__), "..", "icons", "splash")

class SplashCmd(PictureScrollBaseCmd):
    def __init__(self) -> None:
        super().__init__("splash", "Startup splash screen")
        self.scroll = False
        self.refresh = True
        self.recommended_duration = 6
        self.logo = None

    def update(self, args: list = [], kwargs: dict = {}) -> str:
        # Load logo
        logo_path = os.path.join(SPLASH_ICONS_DIR, "21_KNOTS_LogoV2_FC_RGB.png")
        try:
            self.logo = Image.open(logo_path).convert("RGBA")
            print(f"[splash] Loaded logo: {self.logo.size}", flush=True)
        except Exception as e:
            print(f"[splash] Error loading logo: {e}", flush=True)
            self.logo = None
        return "splash ready"

    def generate_image(self, args=[], kwargs={}) -> Image.Image:
        width = get_total_matrix_width()
        height = get_total_matrix_height()
        img = Image.new("RGB", (width, height), color=(0, 0, 0))
        
        if self.logo:
            # Resize logo to fit, maintaining aspect ratio
            logo_width, logo_height = self.logo.size
            max_height = height - 4
            max_width = width - 4
            
            ratio = min(max_width / logo_width, max_height / logo_height)
            new_size = (int(logo_width * ratio), int(logo_height * ratio))
            resized_logo = self.logo.resize(new_size, Image.Resampling.LANCZOS)
            
            # Center the logo
            x = (width - new_size[0]) // 2
            y = (height - new_size[1]) // 2
            
            # Paste with transparency
            if resized_logo.mode == 'RGBA':
                img.paste(resized_logo, (x, y), resized_logo)
            else:
                img.paste(resized_logo, (x, y))
        
        return img
