"""Old school red LED dot-matrix scrolling news ticker."""

import feedparser
import random
from PIL import Image, ImageDraw, ImageFont
from Matrix.driver.commands.base import (
    PictureScrollBaseCmd,
    get_total_matrix_width,
    get_total_matrix_height,
    get_fonts_dir,
)

# NYT Homepage RSS feed
RSS_URL = "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml"

# Classic LED red color
LED_RED = (255, 0, 0)

# Headlines pool
_headlines = []
_pool_loaded = False


def load_headlines():
    """Load headlines from NYT RSS feed."""
    global _headlines, _pool_loaded
    _headlines = []
    
    try:
        feed = feedparser.parse(RSS_URL)
        for entry in feed.entries:
            title = entry.get("title", "").strip()
            if title:
                _headlines.append(title.upper())
        random.shuffle(_headlines)
        print(f"[newsred] Loaded {len(_headlines)} headlines", flush=True)
    except Exception as e:
        print(f"[newsred] Error loading feed: {e}", flush=True)
        _headlines = ["NEWS FEED UNAVAILABLE"]
    
    _pool_loaded = True


def get_next_headline():
    """Get the next headline from the pool."""
    global _headlines, _pool_loaded
    
    if not _pool_loaded or len(_headlines) == 0:
        load_headlines()
    
    if len(_headlines) == 0:
        return "NO HEADLINES AVAILABLE"
    
    return _headlines.pop()


class NewsredCmd(PictureScrollBaseCmd):
    def __init__(self) -> None:
        super().__init__("newsred", "Old school red LED news ticker")
        self.scroll = False
        self.refresh = True
        self.refresh_timer = 1 / 30.0  # 30 fps
        self.recommended_duration = 300  # 5 minutes
        self.scroll_x = 0
        self.current_headline = ""
        self.text_width = 0
        self.font = None
        self.cached_text_img = None

    def update(self, args: list = [], kwargs: dict = {}) -> str:
        self.scroll_x = 0
        self.current_headline = get_next_headline()
        self.cached_text_img = None
        
        # Load Liberation Sans Bold font
        try:
            self.font = ImageFont.truetype(
                "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf", 
                54
            )
        except Exception as e:
            print(f"[newsred] Font error: {e}", flush=True)
            self.font = ImageFont.load_default()
        
        # Pre-render the text
        self._render_text()
        
        return super().update(args, kwargs)

    def _render_text(self):
        """Pre-render the headline text."""
        if not self.current_headline:
            return
        
        height = get_total_matrix_height()
        
        # Render at 2x resolution then scale down for cleaner edges
        scale = 2
        render_height = height * scale
        
        # Measure text at scaled size
        scaled_font = ImageFont.truetype(
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
            54 * scale
        )
        
        temp_img = Image.new("RGB", (1, 1))
        temp_draw = ImageDraw.Draw(temp_img)
        bbox = temp_draw.textbbox((0, 0), self.current_headline, font=scaled_font)
        scaled_text_width = bbox[2] - bbox[0] + 40 * scale
        text_height = bbox[3] - bbox[1]
        
        # Create high-res image for the text
        hires_img = Image.new("RGB", (scaled_text_width, render_height), color=(0, 0, 0))
        draw = ImageDraw.Draw(hires_img)
        
        # Center vertically
        y_pos = (render_height - text_height) // 2 - bbox[1]
        
        # Draw text in red
        draw.text((20 * scale, y_pos), self.current_headline, font=scaled_font, fill=LED_RED)
        
        # Scale down to target resolution
        self.text_width = scaled_text_width // scale
        self.cached_text_img = hires_img.resize(
            (self.text_width, height), 
            Image.Resampling.NEAREST  # Use NEAREST to keep sharp pixels
        )

    def generate_image(self, args=[], kwargs={}) -> Image.Image | None:
        width = get_total_matrix_width()
        height = get_total_matrix_height()
        
        # Black background
        img = Image.new("RGB", (width, height), color=(0, 0, 0))
        
        if self.cached_text_img is None:
            return img
        
        # Calculate position - text scrolls from right to left
        x_pos = width - self.scroll_x
        
        # Paste visible portion of text
        if x_pos < width and x_pos + self.text_width > 0:
            src_x = max(0, -x_pos)
            dst_x = max(0, x_pos)
            copy_width = min(self.text_width - src_x, width - dst_x)
            
            if copy_width > 0:
                text_portion = self.cached_text_img.crop((src_x, 0, src_x + copy_width, height))
                img.paste(text_portion, (dst_x, 0))
        
        # Advance scroll position
        self.scroll_x += 2
        
        # Check if headline has fully scrolled off
        if self.scroll_x > width + self.text_width:
            self.current_headline = get_next_headline()
            self.scroll_x = 0
            self._render_text()
        
        return img
