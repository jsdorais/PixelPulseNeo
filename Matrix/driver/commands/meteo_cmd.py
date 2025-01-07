from datetime import datetime
import locale  # Allows setting the locale for French dates
import re  # Provides support for regular expressions to manipulate strings
from typing import Any
from PIL import Image
from PIL import ImageDraw
from Matrix.driver.commands.base import (
    PictureScrollBaseCmd,
    get_icons_dir,
    get_total_matrix_width,
    get_total_matrix_height,
    format_date,
    format_time,
)

from Matrix.driver.commands.wttr.weather import getTodayWeather

from Matrix import config

class MeteoCmd(PictureScrollBaseCmd):
    def __init__(self) -> None:
        # Initialize the weather command with a display name and description
        super().__init__("meteo", "Displays Weather forecast from wttr.in")
        self.refresh_timer = 1 / 30.0  # Refresh rate for updates (every 1/30 seconds)
        self.scroll = config.WEATHER_SCROLL  # Enable or disable scrolling text
        self.refresh = True  # Enable refreshing of the display
        self.background: Image.Image | None = None  # Placeholder for the weather background image
        self.weather: dict[Any, Any] | None = None  # Placeholder for fetched weather data
        self.recommended_duration = 30  # Recommended duration for displaying this command

    def update(self, args: list = [], kwargs: dict = {}) -> None:
        # Fetch today's weather data using the wttr.in API
        self.weather = getTodayWeather()
        super().update(args=[], kwargs={})

    def reset_state(self) -> None:
        # Reset the internal state of the command
        super().reset_state()
        self.background = None  # Clear the cached background image
        
    def getWeatherBackground(self):
        # Generate or retrieve the weather background image
        if not self.background:
            width: int = get_total_matrix_width()  # Get the matrix width
            height: int = get_total_matrix_height()  # Get the matrix height
            img: Image.Image = Image.new("RGB", (width, height), color=(0, 0, 0))  # Create a blank black image

            if self.weather:  # If weather data is available
                weatherLabel: str = self.weather["weatherLabel"]  # Retrieve weather condition label
                temp = self.weather["temp"]  # Retrieve the current temperature
                tempFeelsLike = self.weather["tempFeelsLike"]  # Retrieve "feels like" temperature

                # Get the corresponding weather icon based on the condition
                weatherIcon: Image.Image = Image.open(
                    get_icons_dir(f"wttr_codes/128/{weatherLabel}.png")
                ).convert("RGB")
                weatherIcon = weatherIcon.resize((48, 48), Image.Resampling.LANCZOS)  # Resize the icon

                # Add the weather icon to the image
                img.paste(weatherIcon, (8 + config.WEATHER_TEXT_OFFSET, 8))
                draw: ImageDraw.ImageDraw = ImageDraw.Draw(img)  # Initialize drawing on the image

                # Load fonts for text
                font5 = self.getFont("5x7.pil")
                font6 = self.getFont("6x12.pil")

                # Calculate dimensions of the temperature texts
                temp_text_width, temp_text_height = font6.getbbox(temp)[2], font6.getbbox(temp)[3]  # Width and height of temp
                feels_like_text_width, feels_like_text_height = font5.getbbox(tempFeelsLike)[2], font5.getbbox(tempFeelsLike)[3]  # Width and height of feels-like temp
                total_text_height = temp_text_height + feels_like_text_height + 2  # Total height including spacing

                # Calculate x and y positions to position the texts to the right of the icon
                icon_right_x = 8 + weatherIcon.size[0] + 40  # X position to the right of the weather icon
                centered_y = 8 + (weatherIcon.size[1] - total_text_height) // 2  # Y position to center vertically

                # Draw the current temperature text (-4°C)
                draw.text((icon_right_x, centered_y), temp, font=font6)

                # Draw the "feels like" temperature text (-13°C), slightly below the main temperature
                draw.text(
                    (icon_right_x, centered_y + temp_text_height + 2),  # Add spacing below main temp
                    tempFeelsLike,
                    font=font5,
                    fill=(150, 150, 150),  # Gray color
                )

                # Set the locale to French for date formatting
                locale.setlocale(locale.LC_TIME, "fr_FR.UTF-8")
                # Format the date in French without leading zeros or ordinal suffixes
                date_str: str = datetime.now().strftime("%A %-d %B").capitalize()
                date_str = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", date_str)  # Remove ordinal suffixes

                # Calculate the position to center the date on the display
                _, _, text_width, text_height = font6.getbbox(date_str)
                draw.text((width / 2 - text_width / 2 + config.WEATHER_TEXT_OFFSET, 5), date_str, font=font6)

                # Store the background image
                self.background = img
            else:  # If no weather data is available
                print("NO Weather info")  # Log a message
                # Display an error icon indicating no data
                deadIcon: Image.Image = Image.open(
                    get_icons_dir(f"wttr_codes/dead.png")
                ).convert("RGB")
                deadIcon = deadIcon.resize((32, 41), Image.Resampling.LANCZOS)
                img.paste(deadIcon, (0, 8))

                # Add error text to the image
                draw: ImageDraw.ImageDraw = ImageDraw.Draw(img)
                font6 = self.getFont("6x12.pil")
                font5 = self.getFont("5x7.pil")
                draw.text((40, 4), " WTTR.in site is down", font=font6)
                draw.text((40, 42), "  -- no weather info --", font=font5)

                # Store the fallback image
                self.background = img

        # Return a copy of the background image (or None if unavailable)
        if self.background:
            return self.background.copy()
        else:
            return None

    def generate_image(self, args=[], kwargs={}) -> Image.Image | None:
        # Retrieve the weather background image
        img: Image.Image | None = self.getWeatherBackground()

        if img:  # If the background image is available
            # Add the current time to the image
            draw: ImageDraw.ImageDraw = ImageDraw.Draw(img)
            font = self.getFont("9x18B.pil")
            time_str: str = format_time()  # Format the current time

            if self.scroll:  # If scrolling is enabled
                draw.text((self.tempPos[0] + 30, 24), time_str, font=font)
            else:  # Center the time text if scrolling is disabled
                _, _, text_width, text_height = font.getbbox(time_str)
                width: int = get_total_matrix_width()
                draw.text((width / 2 - text_width / 2 + config.WEATHER_TEXT_OFFSET, 24), time_str, font=font)

        return img  # Return the final image with the weather and time