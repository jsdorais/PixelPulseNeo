

from typing import Any
from PIL import Image
from PIL import ImageDraw
from Matrix.driver.commands.base import (
    PictureScrollBaseCmd,
    get_total_matrix_width,
    get_total_matrix_height,
)
from Matrix import config
import Matrix.driver.commands.mta.route as route
from Matrix.driver.commands.mta.stops import stopResolverSingleton
import Matrix.driver.commands.mta.bus as bus

from Matrix.driver.commands.tidesandcurrents import api
from Matrix import config
from PIL import Image
from PIL import ImageDraw

# Define colors for different elements of the image
CURVE_COLOR = (29, 162, 216)  # Blue color for the tide curve
LINE_COLOR = (2, 26, 46)      # Dark color for optional vertical lines (currently unused)
TIME_COLOR = (125, 187, 185)  # Light teal color for time text
FEET_COLOR = (127, 205, 255)  # Blue color for water level text
NOW_COLOR = (118, 182, 196)   # Teal color for the "current time" line
NAME_COLOR = (216, 211, 208)  # Light gray color for the station name

class TidesCmd(PictureScrollBaseCmd):
    def __init__(self) -> None:
        # Initialize the Tides command with default parameters
        super().__init__(
            "tides", "Displays tides info from station"
        )
        self.scroll = False  # Disable scrolling
        self.refresh = False  # Disable automatic refresh
        self.speed_x = 0  # Horizontal scrolling speed (not used)
        self.speed_y = 0  # Vertical scrolling speed (not used)
        self.recommended_duration = 30  # Recommended display duration in seconds
        self.tides_data = {}  # Placeholder for tide data

    def update(self, args=[], kwargs={}) -> None:
        # Fetch the tide data from the API and store it in `self.tides_data`
        self.tides_data = api.get_tide_data()
        super().update(args, kwargs)

    def generate_image(self, args: list = [], kwargs: dict = {}) -> Image.Image:
        # Get the dimensions of the display matrix
        width: int = get_total_matrix_width()
        height: int = get_total_matrix_height()

        # Create a blank image with a black background
        img: Image.Image = Image.new("RGB", (width, height), color=(0, 0, 0))
        draw: ImageDraw.ImageDraw = ImageDraw.Draw(img)
        font = self.getFont("5x7.pil")  # Load the font for text

        # Correct y-coordinates for the tide curve to invert them for the display
        corrected_curve = [(x, height - y) for x, y in self.tides_data["curve"]]
        # Draw the tide curve
        draw.line(corrected_curve, fill=CURVE_COLOR, width=1)

        offset = 1  # Add a small vertical offset for text placement

        # Iterate over High (H) and Low (L) tide data points
        for entry in self.tides_data["hilo"]:
            # Determine the direction of the offset based on whether it's High or Low tide
            line_delta = 1
            if entry['type'] == "H":
                line_delta = -1

            # Time text for the tide point
            txt = f"{entry['t']}"  # Format the time as a string
            _, _, text_width, text_height = font.getbbox(txt)  # Get text dimensions
            draw.text(
                (entry['x'] - text_width / 2, entry['y'] + line_delta * 25 - text_height + offset),
                txt,
                font=font,
                fill=TIME_COLOR,  # Use the defined time color
            )

            # Water level text for the tide point
            txt = f"{round(entry['v'], 1)} ft"  # Format the water level with 1 decimal and add 'ft'
            _, _, text_width, text_height = font.getbbox(txt)  # Get text dimensions
            draw.text(
                (entry['x'] - text_width / 2, entry['y'] + line_delta * 25 - text_height + 10 + offset),
                txt,
                font=font,
                fill=FEET_COLOR,  # Use the defined feet color
            )

        # Draw the "current time" vertical line
        x_now = self.tides_data["x_now"]  # X-coordinate of the current time
        draw.line([(x_now, 5), (x_now, 59)], fill=NOW_COLOR)

        # Draw the station name at the top-left corner
        font = self.getFont("6x12.pil")  # Load a larger font for the station name
        name = self.tides_data["name"]  # Get the name of the station
        draw.text((5, 1), name, font=font, fill=NAME_COLOR)

        # Return the generated image
        return img