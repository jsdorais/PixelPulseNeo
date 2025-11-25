"""Weather display command using NWS API."""

from datetime import datetime
from PIL import Image, ImageDraw

from Matrix.driver.commands.base import (
    PictureScrollBaseCmd,
    get_icons_dir,
    get_total_matrix_width,
    get_total_matrix_height,
)
from Matrix.driver.commands.wttr.nws_weather import get_current_weather


def ordinal(n):
    """Return ordinal string for a number (1st, 2nd, 3rd, etc.)"""
    if 11 <= n <= 13:
        return f"{n}th"
    return f"{n}{['th', 'st', 'nd', 'rd', 'th'][min(n % 10, 4)]}"


def shorten_period_name(name):
    """Shorten period names for display."""
    # Replace long names with shorter versions
    name = name.replace("This Afternoon", "Afternoon")
    name = name.replace("This Morning", "Morning")
    name = name.replace("Thanksgiving Day", "Thu")
    name = name.replace("Wednesday", "Wed")
    name = name.replace("Thursday", "Thu")
    name = name.replace("Friday", "Fri")
    name = name.replace("Saturday", "Sat")
    name = name.replace("Sunday", "Sun")
    name = name.replace("Monday", "Mon")
    name = name.replace("Tuesday", "Tue")
    name = name.replace(" Night", " Nite")
    return name[:10]  # Max 10 chars


class MeteoCmd(PictureScrollBaseCmd):
    def __init__(self) -> None:
        super().__init__("meteo", "Displays Weather forecast from NWS")
        self.refresh_timer = 1 / 30.0
        self.scroll = False
        self.refresh = True
        self.weather = None
        self.recommended_duration = 60
        self.scroll_x = 0

    def update(self, args: list = [], kwargs: dict = {}) -> None:
        self.weather = get_current_weather()
        self.scroll_x = 0
        super().update(args=[], kwargs={})

    def reset_state(self) -> None:
        super().reset_state()
        self.scroll_x = 0

    def _draw_mini_forecast(self, draw, img, period, x, y, font):
        """Draw a mini forecast with name, small icon and temp."""
        # Draw period name (shortened)
        period_name = shorten_period_name(period.get("name", ""))
        draw.text((x, y), period_name, font=font, fill=(150, 150, 150))
        
        # Draw icon
        icon_name = period.get("icon", "Unknown")
        try:
            icon = Image.open(get_icons_dir(f"wttr_codes/128/{icon_name}.png")).convert("RGB")
            icon = icon.resize((18, 18), Image.Resampling.LANCZOS)
            img.paste(icon, (x, y + 10))
        except:
            pass
        
        # Draw temp next to icon
        temp_str = f"{period['temp_c']}C"
        draw.text((x + 20, y + 14), temp_str, font=font, fill=(200, 200, 200))

    def generate_image(self, args=[], kwargs={}) -> Image.Image | None:
        width = get_total_matrix_width()
        height = get_total_matrix_height()
        img = Image.new("RGB", (width, height), color=(0, 0, 0))
        draw = ImageDraw.Draw(img)

        font6 = self.getFont("6x12.pil")
        font5 = self.getFont("5x7.pil")
        font9 = self.getFont("9x18B.pil")

        if not self.weather:
            # No weather data - show error
            deadIcon = Image.open(get_icons_dir("wttr_codes/dead.png")).convert("RGB")
            deadIcon = deadIcon.resize((32, 41), Image.Resampling.LANCZOS)
            img.paste(deadIcon, (0, 8))
            draw.text((40, 4), "NWS API down", font=font6)
            draw.text((40, 42), "-- no weather --", font=font5)
            return img

        # === TOP: Date (Tuesday, November 25th, 2025) ===
        now = datetime.now()
        day_ord = ordinal(now.day)
        date_str = now.strftime(f"%A, %B {day_ord}, %Y")
        text_width = font6.getbbox(date_str)[2]
        draw.text((width // 2 - text_width // 2, 2), date_str, font=font6)

        # === LEFT: Weather Icon ===
        icon_name = self.weather.get("icon", "Unknown")
        try:
            icon = Image.open(get_icons_dir(f"wttr_codes/128/{icon_name}.png")).convert("RGB")
            icon = icon.resize((40, 40), Image.Resampling.LANCZOS)
            img.paste(icon, (4, 14))
        except:
            draw.text((10, 25), "?", font=font9, fill=(100, 100, 100))

        # === CENTER-LEFT: Current Temp & Condition ===
        temp_str = f"{self.weather['temp_c']}C"
        draw.text((50, 16), temp_str, font=font9)
        
        condition = self.weather.get("condition", "")[:18]
        draw.text((50, 36), condition, font=font5, fill=(180, 180, 180))

        # === RIGHT: 3 Mini forecasts side by side (next 3 periods from API) ===
        periods = self.weather.get("periods", [])
        
        forecast_start_x = 150
        forecast_spacing = 55
        forecast_y = 16
        
        # Show periods 1, 2, 3 (skip period 0 which is current)
        for i in range(1, 4):
            if i < len(periods):
                x_pos = forecast_start_x + (i - 1) * forecast_spacing
                self._draw_mini_forecast(draw, img, periods[i], x_pos, forecast_y, font5)

        # === BOTTOM: Scrolling Detailed Forecast ===
        detailed = self.weather.get("detailed", "")
        detail_y = 54
        
        # Calculate scroll
        detail_width = font5.getbbox(detailed)[2]
        if detail_width > width:
            self.scroll_x += 1
            if self.scroll_x > detail_width + 50:
                self.scroll_x = -width
            draw.text((-self.scroll_x, detail_y), detailed, font=font5, fill=(150, 150, 150))
        else:
            draw.text((4, detail_y), detailed, font=font5, fill=(150, 150, 150))

        return img
