# Command to run in terminal that bypasses the emulator and generates tessie_debug_output.png at the root:
# pkill -f RGBMatrixEmulator || true && python3 -c "from Matrix.driver.commands.tessie_cmd import TessieCmd; tessie = TessieCmd(); tessie.update(); img = tessie.generate_image(); img.show()"

from typing import Any
from PIL import Image, ImageDraw, ImageFont
import requests
import os
import time

# Suppress RGBMatrixEmulator interference
os.environ["RGBME_SUPPRESS_ADAPTERS"] = "1"
os.environ["RGBME_SUPPRESS_ADAPTER_LOAD_ERRORS"] = "1"
os.environ["GPIOZERO_PIN_FACTORY"] = "mock"

from Matrix.driver.commands.base import (
    PictureScrollBaseCmd,
    get_total_matrix_width,
    get_total_matrix_height,
)

# Load API key from environment
BASE_URL = "https://api.tessie.com/vehicles?access_token="
TESSIE_API_KEY = os.getenv("TESSIE_API_KEY")  # ✅ Reads from environment

if not TESSIE_API_KEY:
    print("❌ TESSIE_API_KEY is not set! Make sure to source init_env.sh")
    exit(1)  # Stop execution if API key is missing

# Define colors for the display
TEXT_COLOR = (127, 205, 255)  # Light blue for text
VALUE_COLOR = (255, 255, 255)  # White for labels
TITLE_COLOR = (216, 211, 208)  # Light gray for titles
BATTERY_YELLOW = (255, 204, 0)  # Yellow (below 40%)
BATTERY_ORANGE = (255, 140, 0)  # Orange (below 30%)
BATTERY_RED = (255, 0, 0)  # Red (below 20%)
TIRE_YELLOW = (255, 204, 0)  # Yellow for PSI below 41
TIRE_RED = (255, 0, 0)  # Red for PSI below 39

# Flashing effect for battery below 10%
BATTERY_FLASH = BATTERY_RED if int(time.time()) % 2 == 0 else (0, 0, 0)  # Alternate red and black

# Define Tesla logo path
TESLA_LOGO_PATH = os.path.join(os.getcwd(), "pictures", "tesla_logo.png")

# Default Font Paths (Adjust if needed)
FONT_DIR = os.path.join(os.getcwd(), "Matrix/driver/fonts")
FONT_PATH_PIL = os.path.join(FONT_DIR, "8x13.pil")
FONT_PATH_PBM = os.path.join(FONT_DIR, "8x13.pbm")  # Bitmap fonts require both files

# Load font, fallback if missing
try:
    if os.path.exists(FONT_PATH_PIL) and os.path.exists(FONT_PATH_PBM):
        font = ImageFont.load(FONT_PATH_PIL)  # ✅ Correct way to load a bitmap font
        print(f"✅ Loaded bitmap font: {FONT_PATH_PIL}")
    else:
        raise IOError("Bitmap font files missing")
except IOError:
    print("❌ Warning: Bitmap font not found, using default.")
    font = ImageFont.load_default()


class TessieCmd(PictureScrollBaseCmd):
    def __init__(self) -> None:
        super().__init__("tessie", "Displays Tesla battery & tire info")
        self.scroll = False
        self.refresh = True
        self.recommended_duration = 30
        self.vehicle_data = {}

    def update(self, args: list = [], kwargs: dict = {}) -> None:
        """Fetch Tesla data from Tessie API with fallback to mock data."""
        try:
            url = f"{BASE_URL}{TESSIE_API_KEY}"
            response = requests.get(url, timeout=10)
            data = response.json()

            vehicle = data["results"][0]  # First vehicle entry
            last_state = vehicle["last_state"]

           # Extract vehicle information
            self.vehicle_data["battery_level"] = last_state["charge_state"]["usable_battery_level"]
            self.vehicle_data["est_range"] = round(last_state["charge_state"]["battery_range"])  # Rounded range
            self.vehicle_data["cabin_temp"] = round(last_state["climate_state"]["inside_temp"])  # ✅ Rounded cabin temperature
            self.vehicle_data["charging_state"] = last_state["charge_state"]["charging_state"] # Get Charging State (Disconnected, Complete, ??)

            # Extract tire pressures (Bars -> PSI)
            tpms = last_state["vehicle_state"]
            self.vehicle_data["fl_psi"] = round(tpms["tpms_pressure_fl"] * 14.5038)  # Front Left
            self.vehicle_data["fr_psi"] = round(tpms["tpms_pressure_fr"] * 14.5038)  # Front Right
            self.vehicle_data["rl_psi"] = round(tpms["tpms_pressure_rl"] * 14.5038)  # Rear Left
            self.vehicle_data["rr_psi"] = round(tpms["tpms_pressure_rr"] * 14.5038)  # Rear Right

            print("✅ Tesla data fetched successfully")

        except Exception as e:
            print(f"❌ Error fetching Tesla data: {e}. Using mock data.")

            # Mock data if API fails
            self.vehicle_data = {
                "battery_level": 999,  # ✅ Mock battery level now 999%
                "est_range": 220,  # Rounded mock range
                "cabin_temp": 22.5,
                "charging_state": "Disconnected",
                "fl_psi": 40,
                "fr_psi": 41,
                "rl_psi": 39,
                "rr_psi": 40
            }

        # ✅ Directly call the overridden method
        self.image = self.generate_image()  # Calls the correct overridden method

    def get_psi_color(self, psi_value):
        """Determine the color based on tire PSI value."""
        if psi_value < 39:
            return TIRE_RED  # Red if below 39
        elif psi_value < 41:
            return TIRE_YELLOW  # Yellow if below 41
        return VALUE_COLOR  # Default white

    def generate_image(self, args=[], kwargs={}) -> Image.Image:
        """Generate the LED screen image for Tesla data."""
        print("✅ Generating Tesla display image...")
        width: int = get_total_matrix_width()
        height: int = get_total_matrix_height()

        # Create a blank image
        img: Image.Image = Image.new("RGB", (width, height), (0, 0, 0))
        draw: ImageDraw.ImageDraw = ImageDraw.Draw(img)

        # Determine battery color based on level
        battery_level = self.vehicle_data["battery_level"]
        if battery_level < 10:
            battery_color = BATTERY_FLASH  # Flashing red effect
        elif battery_level < 20:
            battery_color = BATTERY_RED
        elif battery_level < 30:
            battery_color = BATTERY_ORANGE
        elif battery_level < 40:
            battery_color = BATTERY_YELLOW
        else:
            battery_color = VALUE_COLOR  # Default white

        # Load and resize Tesla logo
        text_x_offset = 5  # Default text position
        if os.path.exists(TESLA_LOGO_PATH):
            try:
                print(f"✅ Loading Tesla logo from: {TESLA_LOGO_PATH}")
                tesla_logo = Image.open(TESLA_LOGO_PATH).convert("RGBA")

                # Scale the logo to match screen height
                aspect_ratio = tesla_logo.width / tesla_logo.height
                new_height = height
                new_width = int(aspect_ratio * new_height)
                tesla_logo = tesla_logo.resize((new_width, new_height), Image.LANCZOS)

                # Paste Tesla logo on the left side
                img.paste(tesla_logo, (0, 0), tesla_logo)
                text_x_offset = new_width + 5
            except Exception as e:
                print(f"❌ Error loading Tesla logo: {e}")

       # Left Column: Battery / Range / Cabin
        draw.text((text_x_offset, 14), f"Battery:", font=font, fill=VALUE_COLOR)
        draw.text((text_x_offset + 70, 14), f"{battery_level}%", font=font, fill=battery_color)
        draw.text((text_x_offset, 28), f"Range: {self.vehicle_data['est_range']} mi", font=font, fill=VALUE_COLOR)
        draw.text((text_x_offset, 42), f"Cabin: {self.vehicle_data['cabin_temp']}°C", font=font, fill=VALUE_COLOR)

        # Adjusted offset for better spacing
        psi_x_offset = width - 130  # Increased spacing between Battery and Tire PSI
        psi_y_offset = 28  # Aligned with Battery/Range/Cabin

        # Calculate center position for "Tire PSI" label
        tire_psi_text_width = font.getbbox("Tire PSI")[2]  # Get width of "Tire PSI"
        tire_psi_center_x = psi_x_offset + ((font.getbbox("FL: 40")[2] + font.getbbox("FR: 41")[2]) // 2) - (tire_psi_text_width // 2)

        # Draw Tire PSI title centered above the PSI values
        draw.text((tire_psi_center_x, psi_y_offset - 14), "Tire PSI", font=font, fill=TITLE_COLOR)

        # Draw Tire PSI values in a structured 2x2 grid
        draw.text((psi_x_offset, psi_y_offset), f"FL: {self.vehicle_data['fl_psi']}", font=font, fill=self.get_psi_color(self.vehicle_data['fl_psi']))
        draw.text((psi_x_offset + 60, psi_y_offset), f"FR: {self.vehicle_data['fr_psi']}", font=font, fill=self.get_psi_color(self.vehicle_data['fr_psi']))
        draw.text((psi_x_offset, psi_y_offset + 14), f"RL: {self.vehicle_data['rl_psi']}", font=font, fill=self.get_psi_color(self.vehicle_data['rl_psi']))
        draw.text((psi_x_offset + 60, psi_y_offset + 14), f"RR: {self.vehicle_data['rr_psi']}", font=font, fill=self.get_psi_color(self.vehicle_data['rr_psi']))

        return img