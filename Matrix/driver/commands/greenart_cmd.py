"""Ambient art display with fading colored squares."""

import random
from PIL import Image, ImageDraw
from Matrix.driver.commands.base import (
    PictureScrollBaseCmd,
    get_total_matrix_width,
    get_total_matrix_height,
)

# Square size
SQUARE_SIZE = 8

# Color palettes (teal-green and warm orange-red)
GREEN_SHADES = [
    (0, 30, 30),
    (0, 50, 50),
    (0, 70, 60),
    (0, 90, 80),
    (0, 110, 100),
    (0, 130, 110),
    (0, 150, 120),
    (0, 170, 130),
]

ORANGE_SHADES = [
    (60, 15, 0),
    (90, 25, 0),
    (120, 35, 0),
    (150, 45, 0),
    (180, 50, 0),
    (200, 55, 0),
    (220, 60, 0),
    (255, 70, 0),
]

# Fade speed (0 to 1 per frame)
FADE_SPEED = 0.05


class GreenartCmd(PictureScrollBaseCmd):
    def __init__(self) -> None:
        super().__init__("greenart", "Ambient fading colored squares")
        self.scroll = False
        self.refresh = True
        self.refresh_timer = 1 / 20.0  # 20 fps for smooth fading
        self.recommended_duration = 120
        self.squares = []
        self.palette = []

    def update(self, args: list = [], kwargs: dict = {}) -> str:
        width = get_total_matrix_width()
        height = get_total_matrix_height()
        
        # Randomly choose green or orange palette
        self.palette = random.choice([GREEN_SHADES, ORANGE_SHADES])
        palette_name = "green" if self.palette == GREEN_SHADES else "orange"
        print(f"[greenart] Using {palette_name} palette", flush=True)
        
        # Calculate grid
        cols = width // SQUARE_SIZE
        rows = height // SQUARE_SIZE
        
        # Initialize squares - ~15% start fading in
        self.squares = []
        for row in range(rows):
            for col in range(cols):
                starting = random.random() < 0.15
                square = {
                    'x': col * SQUARE_SIZE,
                    'y': row * SQUARE_SIZE,
                    'target': 1.0 if starting else 0.0,  # Target brightness
                    'brightness': 0.0,  # Current brightness
                    'color_idx': random.randint(0, len(self.palette) - 1),
                }
                self.squares.append(square)
        
        return super().update(args, kwargs)

    def generate_image(self, args=[], kwargs={}) -> Image.Image | None:
        width = get_total_matrix_width()
        height = get_total_matrix_height()
        
        # Create black background
        img = Image.new("RGB", (width, height), color=(0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Count squares that are on or fading in
        active_count = sum(1 for s in self.squares if s['target'] > 0 or s['brightness'] > 0.1)
        target_active = len(self.squares) * 0.15  # Target ~15% active
        
        # Update and draw each square
        for square in self.squares:
            # Fade toward target
            if square['brightness'] < square['target']:
                square['brightness'] = min(square['brightness'] + FADE_SPEED, square['target'])
            elif square['brightness'] > square['target']:
                square['brightness'] = max(square['brightness'] - FADE_SPEED, square['target'])
            
            # Occasionally decide to fade in or out (~1% chance per frame)
            if random.random() < 0.01:
                if square['target'] == 0 and active_count < target_active * 1.3:
                    # Start fading in
                    square['target'] = 1.0
                    square['color_idx'] = random.randint(0, len(self.palette) - 1)
                    active_count += 1
                elif square['target'] == 1.0 and square['brightness'] > 0.9:
                    # Start fading out
                    square['target'] = 0.0
                    active_count -= 1
            
            # Only draw if visible
            if square['brightness'] > 0.01:
                base_color = self.palette[square['color_idx']]
                color = (
                    int(base_color[0] * square['brightness']),
                    int(base_color[1] * square['brightness']),
                    int(base_color[2] * square['brightness']),
                )
                x, y = square['x'], square['y']
                draw.rectangle(
                    [x, y, x + SQUARE_SIZE - 2, y + SQUARE_SIZE - 2],
                    fill=color
                )
        
        return img
