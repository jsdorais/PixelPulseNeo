"""SpaceX upcoming launch display with countdown."""

import os
import requests
from datetime import datetime, timezone
from PIL import Image, ImageDraw, ImageFont
from Matrix.driver.commands.base import (
    PictureScrollBaseCmd,
    get_total_matrix_width,
    get_total_matrix_height,
    get_fonts_dir,
)

# Path to SpaceX logo
SPACEX_ICONS_DIR = os.path.join(os.path.dirname(__file__), "..", "icons", "spacex")

# Colors
WHITE = (255, 255, 255)
GRAY = (150, 150, 150)
YELLOW = (255, 200, 50)
CYAN = (100, 200, 255)

# API URL (Launch Library 2)
API_URL = "https://ll.thespacedevs.com/2.2.0/launch/upcoming/?search=spacex&limit=5"


class SpacexCmd(PictureScrollBaseCmd):
    def __init__(self) -> None:
        super().__init__("spacex", "SpaceX upcoming launch countdown")
        self.scroll = False
        self.refresh = True
        self.refresh_timer = 1 / 30.0  # 30 fps for smooth scrolling
        self.recommended_duration = 120
        self.launch_data = None
        self.logo = None
        self.font_large = None
        self.font_med = None
        self.font_small = None
        self.scroll_x = 0
        self.description_width = 0

    def update(self, args: list = [], kwargs: dict = {}) -> str:
        # Load fonts
        try:
            self.font_large = ImageFont.load(get_fonts_dir("10x20.pil"))
            self.font_med = ImageFont.load(get_fonts_dir("6x12.pil"))
            self.font_small = ImageFont.load(get_fonts_dir("5x7.pil"))
        except Exception as e:
            print(f"[spacex] Font error: {e}", flush=True)
        
        # Load logo
        logo_path = os.path.join(SPACEX_ICONS_DIR, "spacex_logo.png")
        try:
            self.logo = Image.open(logo_path).convert("RGBA")
            print(f"[spacex] Original logo size: {self.logo.size}", flush=True)
            # Resize to fit within max bounds, maintain aspect ratio
            max_width = 100
            max_height = 50
            ratio = min(max_width / self.logo.width, max_height / self.logo.height)
            new_size = (int(self.logo.width * ratio), int(self.logo.height * ratio))
            self.logo = self.logo.resize(new_size, Image.Resampling.LANCZOS)
            print(f"[spacex] Resized logo: {new_size}", flush=True)
        except Exception as e:
            print(f"[spacex] Error loading logo: {e}", flush=True)
            self.logo = None
        
        # Fetch launch data
        self._fetch_launch_data()
        
        # Initialize scroll position
        self.scroll_x = get_total_matrix_width()
        
        return super().update(args, kwargs)

    def _fetch_launch_data(self):
        """Fetch next SpaceX launch from Launch Library 2 API."""
        try:
            response = requests.get(API_URL, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Find next SpaceX launch
            for launch in data.get("results", []):
                provider = launch.get("launch_service_provider", {}).get("name", "")
                if "SpaceX" in provider:
                    mission = launch.get("mission", {}) or {}
                    self.launch_data = {
                        "name": mission.get("name") or launch.get("name", "Unknown"),
                        "description": mission.get("description", ""),
                        "status": launch.get("status", {}).get("name", ""),
                        "net": launch.get("net"),  # ISO format datetime
                        "window_start": launch.get("window_start"),
                        "window_end": launch.get("window_end"),
                        "pad": launch.get("pad", {}).get("name", ""),
                        "location": launch.get("pad", {}).get("location", {}).get("name", ""),
                        "orbit": mission.get("orbit", {}).get("name", "") if mission.get("orbit") else "",
                        "rocket": launch.get("rocket", {}).get("configuration", {}).get("full_name", "Falcon 9"),
                    }
                    print(f"[spacex] Next launch: {self.launch_data['name']} at {self.launch_data['net']}", flush=True)
                    return
            
            print("[spacex] No SpaceX launches found", flush=True)
            self.launch_data = None
            
        except Exception as e:
            print(f"[spacex] API error: {e}", flush=True)
            self.launch_data = None

    def _get_countdown(self):
        """Calculate countdown to launch."""
        if not self.launch_data or not self.launch_data.get("net"):
            return None
        
        try:
            # Parse launch time (ISO format)
            launch_time = datetime.fromisoformat(self.launch_data["net"].replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            
            diff = launch_time - now
            total_seconds = int(diff.total_seconds())
            
            if total_seconds < 0:
                return {"passed": True, "text": "LAUNCHED"}
            
            days = total_seconds // 86400
            hours = (total_seconds % 86400) // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            
            return {
                "passed": False,
                "days": days,
                "hours": hours,
                "minutes": minutes,
                "seconds": seconds,
                "text": f"T-{days}d {hours:02d}:{minutes:02d}:{seconds:02d}"
            }
        except Exception as e:
            print(f"[spacex] Countdown error: {e}", flush=True)
            return None

    def _format_launch_date(self):
        """Format launch date as dd/mm/yy."""
        if not self.launch_data or not self.launch_data.get("net"):
            return "TBD"
        
        try:
            from zoneinfo import ZoneInfo
            launch_time = datetime.fromisoformat(self.launch_data["net"].replace("Z", "+00:00"))
            et_time = launch_time.astimezone(ZoneInfo("America/New_York"))
            return et_time.strftime("%m/%d/%y %I:%M%p")
        except Exception as e:
            print(f"[spacex] Time format error: {e}", flush=True)
            return "TBD"

    def generate_image(self, args=[], kwargs={}) -> Image.Image | None:
        width = get_total_matrix_width()
        height = get_total_matrix_height()
        
        # Create black background
        img = Image.new("RGB", (width, height), color=(0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Draw logo on top-left with padding
        logo_x = 8
        logo_y = 14
        text_start_x = 115  # Default if no logo
        
        if self.logo:
            logo_rgb = Image.new("RGB", self.logo.size, (0, 0, 0))
            if self.logo.mode == 'RGBA':
                logo_rgb.paste(self.logo, mask=self.logo.split()[3])
            else:
                logo_rgb.paste(self.logo)
            img.paste(logo_rgb, (logo_x, logo_y))
            text_start_x = logo_x + self.logo.width + 12
        
        if not self.launch_data:
            draw.text((text_start_x, 25), "No launch data", font=self.font_med, fill=WHITE)
            return img
        
        # Mission name - use shorter version (just mission name without rocket)
        mission_name = self.launch_data.get("name", "Unknown")
        # Remove "(Dedicated SSO Rideshare)" if present for shorter display
        if "(" in mission_name:
            mission_name = mission_name.split("(")[0].strip()
        draw.text((text_start_x, 2), mission_name, font=self.font_large, fill=WHITE)
        
        # Rocket and location (second line)
        rocket = self.launch_data.get("rocket", "Falcon 9")
        if "Block 5" in rocket:
            rocket = rocket.replace(" Block 5", "")
        location = self.launch_data.get("location", "")
        loc_line = f"{rocket}, {location}"
        draw.text((text_start_x, 25), loc_line, font=self.font_small, fill=GRAY)
        
        # Date and countdown on same line
        launch_date = self._format_launch_date()
        countdown = self._get_countdown()
        
        # Draw date
        draw.text((text_start_x, 34), launch_date, font=self.font_med, fill=CYAN)
        
        # Draw countdown next to date
        if countdown:
            # Measure date width to position countdown
            date_bbox = draw.textbbox((0, 0), launch_date, font=self.font_med)
            date_width = date_bbox[2] - date_bbox[0]
            countdown_x = text_start_x + date_width + 8
            
            countdown_text = countdown["text"]
            draw.text((countdown_x, 34), countdown_text, font=self.font_med, fill=YELLOW)
        
        # Scrolling description on bottom line
        description = self.launch_data.get("description", "")
        if description:
            # Calculate description width
            desc_bbox = draw.textbbox((0, 0), description, font=self.font_small)
            self.description_width = desc_bbox[2] - desc_bbox[0]
            
            # Draw scrolling text
            desc_y = height - 10
            draw.text((int(self.scroll_x), desc_y), description, font=self.font_small, fill=GRAY)
            
            # Update scroll position (faster scrolling)
            self.scroll_x -= 1
            if self.scroll_x < -self.description_width:
                self.scroll_x = width
        
        return img
