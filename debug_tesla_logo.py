from PIL import Image
import os

# Define Tesla logo path
TESLA_LOGO_PATH = os.path.join(os.getcwd(), "pictures", "tesla_logo.png")

# Define screen dimensions
SCREEN_WIDTH = 128
SCREEN_HEIGHT = 64

# Verify if the file exists
if os.path.exists(TESLA_LOGO_PATH):
    try:
        print(f"✅ Loading Tesla logo from: {TESLA_LOGO_PATH}")
        tesla_logo = Image.open(TESLA_LOGO_PATH).convert("RGBA")

        # Ensure Tesla logo has valid dimensions
        if tesla_logo.width == 0 or tesla_logo.height == 0:
            raise ValueError("Tesla logo has invalid dimensions.")

        # Maintain aspect ratio while scaling height to match screen
        aspect_ratio = tesla_logo.width / tesla_logo.height
        new_height = SCREEN_HEIGHT  # Make it as tall as the screen
        new_width = int(aspect_ratio * new_height)  # Maintain aspect ratio

        # Resize logo using LANCZOS filter
        tesla_logo = tesla_logo.resize((new_width, new_height), Image.LANCZOS)

        # Create black background image
        img = Image.new("RGB", (SCREEN_WIDTH, SCREEN_HEIGHT), (0, 0, 0))

        # Paste Tesla logo on the left side with transparency
        img.paste(tesla_logo, (0, 0), tesla_logo)

        # Save debug output
        debug_path = "debug_output.png"
        img.save(debug_path)
        img.show()

        print(f"✅ Debug image saved as {debug_path}")

    except Exception as e:
        print(f"❌ Error loading Tesla logo: {e}")
else:
    print(f"❌ Tesla logo not found at {TESLA_LOGO_PATH}")