import random
from PIL import Image
from PIL import ImageDraw
from Matrix.driver.commands.base import (
    PictureScrollBaseCmd,
    get_total_matrix_width,
    get_total_matrix_height,
    get_icons_dir,
)
from Matrix.driver.commands.news import feed

feeds: list[dict[str, str]] = [
    {
        "url": "https://rss.nytimes.com/services/xml/rss/nyt/NYRegion.xml",
        "name": "NYT NY Region",
        "logo": "nyt.png",
    },
    {
        "url": "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
        "name": "NYT Homepage",
        "logo": "nyt.png",
    },
    {
        "url": "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
        "name": "NYT Tech",
        "logo": "nyt.png",
    },
    {
        "url": "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml",
        "name": "NYT Business",
        "logo": "nyt.png",
    },
    {
        "url": "https://www.wired.com/feed/rss",
        "name": "Wired",
        "logo": "wired.png"
    },
    {
        "url": "https://www.wired.com/feed/category/science/latest/rss",
        "name": "Wired Science",
        "logo": "wired.png",
    },
    {
        "url": "https://feeds.macrumors.com/MacRumors-Front",
        "name": "MacRumors",
        "logo": "macrumors.png",
    },
    {
        "url": "https://9to5mac.com/feed/",
        "name": "9to5Mac",
        "logo": "9to5mac.png",
    },
    {
        "url": "https://nypost.com/feed/",
        "name": "NY Post",
        "logo": "nypost.png",
    },
    {
        "url": "https://newyorker.com/feed/everything",
        "name": "New Yorker",
        "logo": "newyorker.png",
    },
    {
        "url": "https://gothamist.com/feed",
        "name": "Gothamist",
        "logo": "gothamist.png",
    },
]

# Global pool of all articles from all feeds
_article_pool = []
_pool_loaded = False


def load_article_pool():
    """Load articles from all feeds into a single pool."""
    global _article_pool, _pool_loaded
    _article_pool = []
    
    for feed_def in feeds:
        try:
            f = feed.get(
                feed_def["url"],
                get_total_matrix_width(),
                get_total_matrix_height(),
            )
            if f and f.feed.entries:
                for entry in f.feed.entries:
                    _article_pool.append({
                        "entry": entry,
                        "feed_def": feed_def,
                    })
                print(f"[news] Loaded {len(f.feed.entries)} from {feed_def['name']}")
        except Exception as e:
            print(f"[news] Error loading feed {feed_def['name']}: {e}")
    
    random.shuffle(_article_pool)
    _pool_loaded = True
    print(f"[news] Total: {len(_article_pool)} articles from {len(feeds)} feeds")


def get_random_article():
    """Get a random article from the pool."""
    global _article_pool, _pool_loaded
    
    if not _pool_loaded or len(_article_pool) == 0:
        load_article_pool()
    
    if len(_article_pool) == 0:
        return None, None
    
    article = _article_pool.pop()
    return article["entry"], article["feed_def"]


class NewsCmd(PictureScrollBaseCmd):
    def __init__(self) -> None:
        super().__init__("news", "Displays News from RSS feeds")
        self.scroll = False
        self.refresh = True
        self.speed_x = 0
        self.speed_y = 0
        self.current_entry = None
        self.feed_definition: dict[str, str] | None = None
        self.recommended_duration = 120
        self.scroll_x = 0
        self.text_width = 0
        self.thumb_width = 0
        self.thumb_img = None
        self.logo_img = None
        self.logo_x = 0

    def update(self, args: list = [], kwargs: dict = {}) -> str:
        # Get a random article from the pool
        self.current_entry, self.feed_definition = get_random_article()
        self.scroll_x = 0
        self.thumb_img = None
        self.logo_img = None
        self.thumb_width = 0
        
        # Pre-load thumbnail and logo
        if self.current_entry and self.feed_definition:
            width = get_total_matrix_width()
            height = get_total_matrix_height()
            
            # Try to get thumbnail
            try:
                thumb_url = self.current_entry.media_thumbnail[0]["url"]
                thumb = feed.getImage(thumb_url)
                self.thumb_img = self._resize_icon(thumb, max_height=height)
                self.thumb_width = self.thumb_img.size[0]
            except Exception:
                self.thumb_img = None
                self.thumb_width = 0

            # Logo
            try:
                icon = Image.open(
                    get_icons_dir(f"news/{self.feed_definition['logo']}")
                ).convert("RGB")
                self.logo_img = self._resize_icon(icon, max_height=30)
                self.logo_x = width - self.logo_img.size[0] - 1
            except Exception:
                self.logo_img = None

            # Calculate text width
            font_big = self.getFont("10x20.pil")
            summary = getattr(self.current_entry, 'title', '') or getattr(self.current_entry, 'summary', '')
            _, _, self.text_width, _ = font_big.getbbox(summary)
        
        return super().update(args, kwargs)

    def generate_image(self, args=[], kwargs={}) -> Image.Image | None:
        if self.current_entry is None or self.feed_definition is None:
            print("No article available")
            return None

        width = get_total_matrix_width()
        height = get_total_matrix_height()
        font_big = self.getFont("10x20.pil")
        font5 = self.getFont("5x7.pil")

        # Create fresh image each frame
        img = Image.new("RGB", (width, height), color=(0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Draw scrolling text FIRST (so it goes under everything)
        summary = getattr(self.current_entry, 'title', '') or getattr(self.current_entry, 'summary', '')
        text_y = 38
        
        if self.text_width > width:
            self.scroll_x += 1
            if self.scroll_x > self.text_width + 50:
                # Article done scrolling - get next article
                self.current_entry, self.feed_definition = get_random_article()
                self.scroll_x = 0
                # Reload assets for new article
                self.thumb_img = None
                self.logo_img = None
                self.thumb_width = 0
                if self.current_entry and self.feed_definition:
                    try:
                        thumb_url = self.current_entry.media_thumbnail[0]["url"]
                        thumb = feed.getImage(thumb_url)
                        self.thumb_img = self._resize_icon(thumb, max_height=height)
                        self.thumb_width = self.thumb_img.size[0]
                    except:
                        pass
                    try:
                        icon = Image.open(
                            get_icons_dir(f"news/{self.feed_definition['logo']}")
                        ).convert("RGB")
                        self.logo_img = self._resize_icon(icon, max_height=30)
                        self.logo_x = width - self.logo_img.size[0] - 1
                    except:
                        pass
                    summary = getattr(self.current_entry, 'title', '') or getattr(self.current_entry, 'summary', '')
                    _, _, self.text_width, _ = font_big.getbbox(summary)
            
            text_x = width - self.scroll_x
            draw.text((text_x, text_y), summary, font=font_big)
        else:
            draw.text((5, text_y), summary, font=font_big)

        # Now paste thumbnail ON TOP of text (so text scrolls under it)
        if self.thumb_img:
            img.paste(self.thumb_img, (0, 0))

        # Paste logo on top
        if self.logo_img:
            img.paste(self.logo_img, (self.logo_x, 1))

        # Source name (after thumbnail)
        source_name = self.feed_definition.get("name", "")[:25]
        thumb_w = self.thumb_width if self.thumb_img else 0
        draw.text((thumb_w + 5, 5), source_name, font=font5, fill=(150, 150, 150))

        return img

    def handle_text_payload(self, msg: str):
        if msg.lower() == "next":
            self.update()
