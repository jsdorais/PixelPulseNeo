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
TEXT_COLOR = (255, 255, 255)
ARTIST_COLOR = (127, 205, 255)
NOW_PLAYING_COLOR = (255, 165, 0)
PLAYCOUNT_COLOR = (200, 200, 200)
PREVIOUS_COLOR = (180, 180, 180)

REFRESH_INTERVAL = 5  # seconds between API calls


def log(msg: str) -> None:
    """Print with flush for systemd."""
    print(msg, flush=True)


class LastfmCmd(PictureScrollBaseCmd):
    def __init__(self) -> None:
        super().__init__("lastfm", "Displays Now Playing from Last.fm")
        self.scroll = False
        self.refresh = True
        self.refresh_timer = 1 / 30.0
        self.recommended_duration = 3600
        self.track_data = None
        self.album_art = None
        self.last_fetch_time = 0
        self.cached_image = None
        self.last_track_name = None
        self.is_playing = False
        self.consecutive_not_playing = 0

    def update(self, args: list = [], kwargs: dict = {}) -> None:
        """Fetch current track from Last.fm."""
        log("[lastfm] update() called - forcing API check")
        self._fetch_fresh_data(force=True)
        super().update(args=args, kwargs=kwargs)

    def _fetch_fresh_data(self, force: bool = False) -> None:
        """Fetch fresh data from Last.fm API."""
        current_time = time.time()
        time_since_fetch = current_time - self.last_fetch_time
        
        # Time gate - only fetch every REFRESH_INTERVAL seconds
        if not force and time_since_fetch < REFRESH_INTERVAL:
            return  # Too soon, skip
        
        self.last_fetch_time = current_time
        log(f"[lastfm] Checking API (force={force}, time_since={time_since_fetch:.1f}s)...")
        
        self.track_data = get_now_playing()
        
        # Check if currently playing
        self.is_playing = self.track_data.get("now_playing", False) if self.track_data else False
        
        if not self.is_playing:
            self.consecutive_not_playing += 1
            log(f"[lastfm] NOT PLAYING (count: {self.consecutive_not_playing})")
            self.cached_image = None  # Clear cache to trigger exit check
            return
        
        # Reset counter when playing
        self.consecutive_not_playing = 0
        log(f"[lastfm] Playing: {self.track_data.get('track')} by {self.track_data.get('artist')}")

        # Only fetch album art if track changed
        new_track = self.track_data.get("track") if self.track_data else None
        if new_track != self.last_track_name:
            log(f"[lastfm] Track changed: {self.last_track_name} -> {new_track}")
            self.album_art = None
            self.cached_image = None
            self.last_track_name = new_track

            if self.track_data and self.track_data.get("image_url"):
                self.album_art = self._fetch_album_art(self.track_data["image_url"])

    def _fetch_album_art(self, url: str) -> Image.Image | None:
        """Download and resize album art."""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            img = Image.open(BytesIO(response.content)).convert("RGB")
            art_size = get_total_matrix_height() - 8
            img = img.resize((art_size, art_size), Image.Resampling.LANCZOS)
            return img
        except Exception as e:
            log(f"[lastfm] Failed to fetch album art: {e}")
            return None

    def reset_state(self) -> None:
        super().reset_state()
        self.album_art = None
        self.track_data = None
        self.cached_image = None
        self.last_track_name = None
        self.is_playing = False
        self.consecutive_not_playing = 0
        self.last_fetch_time = 0

    def generate_image(self, args=[], kwargs={}) -> Image.Image | None:
        """Generate the display image."""
        # Check for fresh data (time-gated inside _fetch_fresh_data)
        self._fetch_fresh_data()

        # If not playing for 2+ consecutive checks, exit this command
        if not self.is_playing and self.consecutive_not_playing >= 2:
            log(f"[lastfm] EXITING - music stopped (count={self.consecutive_not_playing})")
            self.execution_done = True
            return self.cached_image or Image.new("RGB", (get_total_matrix_width(), get_total_matrix_height()), color=(0, 0, 0))

        # If not playing but first check, show cached or blank
        if not self.is_playing:
            if self.cached_image:
                return self.cached_image
            # No music, no cache - exit immediately
            log(f"[lastfm] No music on start, skipping")
            self.execution_done = True
            return Image.new("RGB", (get_total_matrix_width(), get_total_matrix_height()), color=(0, 0, 0))

        # Return cached image if available
        if self.cached_image:
            return self.cached_image

        width = get_total_matrix_width()
        height = get_total_matrix_height()

        img = Image.new("RGB", (width, height), color=(0, 0, 0))
        draw = ImageDraw.Draw(img)

        font_large = self.getFont("6x12.pil")
        font_small = self.getFont("5x7.pil")

        if not self.track_data:
            self.execution_done = True
            return img

        # === LEFT SIDE: Album Art ===
        art_size = height - 8
        art_x = 4
        art_y = 4

        if self.album_art:
            img.paste(self.album_art, (art_x, art_y))
        else:
            draw.rectangle(
                [art_x, art_y, art_x + art_size, art_y + art_size],
                outline=(80, 80, 80),
                fill=(30, 30, 30)
            )
            draw.text((art_x + 18, art_y + 20), "?", font=font_large, fill=(80, 80, 80))

        # === RIGHT SIDE: Track Info ===
        text_x = art_x + art_size + 8
        max_chars = (width - text_x) // 6

        draw.text((text_x, 2), "NOW PLAYING", font=font_small, fill=NOW_PLAYING_COLOR)

        track_name = self.track_data.get("track", "Unknown")
        if len(track_name) > max_chars:
            track_name = track_name[:max_chars-1] + "..."
        draw.text((text_x, 12), track_name, font=font_large, fill=TEXT_COLOR)

        artist = self.track_data.get("artist", "Unknown")
        if len(artist) > max_chars:
            artist = artist[:max_chars-1] + "..."
        draw.text((text_x, 26), artist, font=font_large, fill=ARTIST_COLOR)

        previous = self.track_data.get("previous")
        if previous:
            prev_track = previous.get("track", "")
            prev_artist = previous.get("artist", "")
            prev_text = f"Last: {prev_track} - {prev_artist}"
            if len(prev_text) > max_chars + 4:
                prev_text = prev_text[:max_chars+3] + "..."
            draw.text((text_x, 40), prev_text, font=font_small, fill=PREVIOUS_COLOR)

        playcount = self.track_data.get("playcount")
        if playcount:
            draw.text((text_x, 52), f"Plays: {playcount}", font=font_small, fill=PLAYCOUNT_COLOR)

        self.cached_image = img
        return img
