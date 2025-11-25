"""Last.fm Now Playing command for LED Matrix."""

from typing import Any
from PIL import Image, ImageDraw
from io import BytesIO
import requests
import os
import time

from Matrix.driver.commands.base import (
    PictureScrollBaseCmd,
    get_total_matrix_width,
    get_total_matrix_height,
)
from Matrix.driver.commands.lastfm.api import get_now_playing


# Colors
TEXT_COLOR = (255, 255, 255)       # White for main text
ARTIST_COLOR = (127, 205, 255)     # Light blue for artist
ALBUM_COLOR = (150, 150, 150)      # Gray for album
NOW_PLAYING_COLOR = (255, 165, 0)  # Orange for "NOW PLAYING"
LAST_PLAYED_COLOR = (255, 165, 0)  # Orange for "LAST PLAYED"
PLAYCOUNT_COLOR = (200, 200, 200)  # Light gray for playcount
PREVIOUS_COLOR = (180, 180, 180)   # Gray for previous track


class LastfmCmd(PictureScrollBaseCmd):
    def __init__(self) -> None:
        super().__init__("lastfm", "Displays Now Playing from Last.fm")
        self.scroll = False
        self.refresh = True
        self.refresh_timer = 1 / 30.0
        self.recommended_duration = 30
        self.track_data = None
        self.album_art = None
        self.last_fetch_time = 0

    def update(self, args: list = [], kwargs: dict = {}) -> None:
        """Fetch current track from Last.fm."""
        self._fetch_fresh_data()
        super().update(args=args, kwargs=kwargs)

    def _fetch_fresh_data(self) -> None:
        """Always fetch fresh data from Last.fm API."""
        self.track_data = get_now_playing()
        self.album_art = None
        
        # Fetch album art if URL available
        if self.track_data and self.track_data.get("image_url"):
            self.album_art = self._fetch_album_art(self.track_data["image_url"])
        
        self.last_fetch_time = time.time()

    def _fetch_album_art(self, url: str) -> Image.Image | None:
        """Download and resize album art."""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            img = Image.open(BytesIO(response.content)).convert("RGB")
            # Resize to fit left side of display (square, fits height)
            art_size = get_total_matrix_height() - 8  # Leave 4px margin top/bottom
            img = img.resize((art_size, art_size), Image.Resampling.LANCZOS)
            return img
        except Exception as e:
            print(f"[lastfm] Failed to fetch album art: {e}")
            return None

    def reset_state(self) -> None:
        super().reset_state()
        self.album_art = None
        self.track_data = None

    def generate_image(self, args=[], kwargs={}) -> Image.Image | None:
        """Generate the display image with album art on left, info on right."""
        # Fetch fresh data if stale (older than 5 seconds)
        if time.time() - self.last_fetch_time > 5:
            self._fetch_fresh_data()
        
        width = get_total_matrix_width()
        height = get_total_matrix_height()
        
        img = Image.new("RGB", (width, height), color=(0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Load fonts
        font_large = self.getFont("6x12.pil")
        font_small = self.getFont("5x7.pil")
        
        if not self.track_data:
            # No data - show error
            draw.text((10, 20), "No Last.fm data", font=font_large, fill=TEXT_COLOR)
            draw.text((10, 35), "Check API key", font=font_small, fill=ALBUM_COLOR)
            return img
        
        # === LEFT SIDE: Album Art ===
        art_size = height - 8  # e.g., 56px if height is 64
        art_x = 4
        art_y = 4
        
        if self.album_art:
            img.paste(self.album_art, (art_x, art_y))
        else:
            # Draw placeholder box if no art
            draw.rectangle(
                [art_x, art_y, art_x + art_size, art_y + art_size],
                outline=(80, 80, 80),
                fill=(30, 30, 30)
            )
            # Music note placeholder
            draw.text((art_x + 18, art_y + 20), "?", font=font_large, fill=(80, 80, 80))
        
        # === RIGHT SIDE: Track Info ===
        text_x = art_x + art_size + 8  # Start text after album art + margin
        max_chars = (width - text_x) // 6  # Approximate char width for truncation
        
        # Status header (NOW PLAYING / LAST PLAYED)
        if self.track_data["now_playing"]:
            status = "NOW PLAYING"
            status_color = NOW_PLAYING_COLOR
        else:
            status = "LAST PLAYED"
            status_color = LAST_PLAYED_COLOR
        
        draw.text((text_x, 2), status, font=font_small, fill=status_color)
        
        # Track name
        track_name = self.track_data.get("track", "Unknown")
        if len(track_name) > max_chars:
            track_name = track_name[:max_chars-1] + "..."
        draw.text((text_x, 12), track_name, font=font_large, fill=TEXT_COLOR)
        
        # Artist
        artist = self.track_data.get("artist", "Unknown")
        if len(artist) > max_chars:
            artist = artist[:max_chars-1] + "..."
        draw.text((text_x, 26), artist, font=font_large, fill=ARTIST_COLOR)
        
        # Previous track (Last Played)
        previous = self.track_data.get("previous")
        if previous:
            prev_track = previous.get("track", "")
            prev_artist = previous.get("artist", "")
            prev_text = f"Last: {prev_track} - {prev_artist}"
            if len(prev_text) > max_chars + 4:
                prev_text = prev_text[:max_chars+3] + "..."
            draw.text((text_x, 40), prev_text, font=font_small, fill=PREVIOUS_COLOR)
        
        # Playcount
        playcount = self.track_data.get("playcount")
        if playcount:
            pc_text = f"Plays: {playcount}"
            draw.text((text_x, 52), pc_text, font=font_small, fill=PLAYCOUNT_COLOR)
        
        return img
