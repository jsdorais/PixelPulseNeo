"""Stock ticker display showing 5 stocks across 5 LED panels."""

import yfinance as yf
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timedelta
import pytz
from Matrix.driver.commands.base import (
    PictureScrollBaseCmd,
    get_total_matrix_width,
    get_total_matrix_height,
    get_fonts_dir,
)

# Stock symbols to display
SYMBOLS = ["AAPL", "AMZN", "NVDA", "TSLA", "GOOG"]

# Colors
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
GRAY = (100, 100, 100)

# Panel dimensions
PANEL_WIDTH = 64
PANEL_HEIGHT = 64


class StocksCmd(PictureScrollBaseCmd):
    def __init__(self) -> None:
        super().__init__("stocks", "Stock ticker display")
        self.scroll = False
        self.refresh = True
        self.refresh_timer = 1 / 30.0  # 30 fps for smooth display
        self.recommended_duration = 120  # 2 minutes
        self.stock_data = {}
        self.last_fetch = None
        self.fetch_interval = 60  # Fetch new data every 60 seconds
        self.font_large = None
        self.font_small = None

    def update(self, args: list = [], kwargs: dict = {}) -> str:
        # Load fonts
        try:
            self.font_large = ImageFont.truetype(
                "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf", 12
            )
            self.font_small = ImageFont.truetype(
                "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf", 10
            )
        except Exception as e:
            print(f"[stocks] Font error: {e}", flush=True)
            self.font_large = ImageFont.load_default()
            self.font_small = ImageFont.load_default()
        
        # Fetch initial data
        self._fetch_stock_data()
        
        return super().update(args, kwargs)

    def _fetch_stock_data(self):
        """Fetch stock data from Yahoo Finance."""
        now = datetime.now()
        
        # Only fetch if interval has passed
        if self.last_fetch and (now - self.last_fetch).seconds < self.fetch_interval:
            return
        
        print(f"[stocks] Fetching stock data...", flush=True)
        
        for symbol in SYMBOLS:
            try:
                ticker = yf.Ticker(symbol)
                
                # Get today's intraday data (1 minute intervals)
                hist = ticker.history(period="1d", interval="5m")
                
                if hist.empty:
                    # Market might be closed, try getting last trading day
                    hist = ticker.history(period="2d", interval="5m")
                
                if not hist.empty:
                    # Get current price and change
                    current_price = hist['Close'].iloc[-1]
                    open_price = hist['Open'].iloc[0]
                    change_pct = ((current_price - open_price) / open_price) * 100
                    
                    # Get chart data (closing prices)
                    prices = hist['Close'].tolist()
                    
                    self.stock_data[symbol] = {
                        'price': current_price,
                        'change_pct': change_pct,
                        'prices': prices,
                        'high': max(prices),
                        'low': min(prices),
                    }
                    print(f"[stocks] {symbol}: ${current_price:.2f} ({change_pct:+.2f}%)", flush=True)
                else:
                    print(f"[stocks] No data for {symbol}", flush=True)
                    
            except Exception as e:
                print(f"[stocks] Error fetching {symbol}: {e}", flush=True)
        
        self.last_fetch = now

    def _draw_stock_panel(self, symbol: str, x_offset: int, draw: ImageDraw.ImageDraw, img: Image.Image):
        """Draw a single stock panel."""
        data = self.stock_data.get(symbol)
        
        if not data:
            # No data available
            draw.text((x_offset + 10, 25), symbol, font=self.font_large, fill=WHITE)
            draw.text((x_offset + 10, 40), "N/A", font=self.font_small, fill=GRAY)
            return
        
        price = data['price']
        change_pct = data['change_pct']
        prices = data['prices']
        
        # Choose color based on change
        color = GREEN if change_pct >= 0 else RED
        
        # Draw ticker symbol (centered at top)
        bbox = draw.textbbox((0, 0), symbol, font=self.font_large)
        text_width = bbox[2] - bbox[0]
        x_text = x_offset + (PANEL_WIDTH - text_width) // 2
        draw.text((x_text, 2), symbol, font=self.font_large, fill=WHITE)
        
        # Draw price
        price_str = f"${price:.2f}"
        bbox = draw.textbbox((0, 0), price_str, font=self.font_small)
        text_width = bbox[2] - bbox[0]
        x_text = x_offset + (PANEL_WIDTH - text_width) // 2
        draw.text((x_text, 16), price_str, font=self.font_small, fill=WHITE)
        
        # Draw percent change
        change_str = f"{change_pct:+.2f}%"
        bbox = draw.textbbox((0, 0), change_str, font=self.font_small)
        text_width = bbox[2] - bbox[0]
        x_text = x_offset + (PANEL_WIDTH - text_width) // 2
        draw.text((x_text, 28), change_str, font=self.font_small, fill=color)
        
        # Draw chart
        chart_top = 42
        chart_bottom = 62
        chart_left = x_offset + 4
        chart_right = x_offset + PANEL_WIDTH - 4
        chart_width = chart_right - chart_left
        chart_height = chart_bottom - chart_top
        
        if len(prices) > 1:
            high = data['high']
            low = data['low']
            price_range = high - low if high != low else 1
            
            # Draw chart line
            points = []
            for i, p in enumerate(prices):
                x = chart_left + int(i * chart_width / (len(prices) - 1))
                y = chart_bottom - int((p - low) / price_range * chart_height)
                points.append((x, y))
            
            # Draw the line
            for i in range(len(points) - 1):
                draw.line([points[i], points[i + 1]], fill=color, width=1)
            
            # Fill under the curve
            if len(points) > 1:
                # Create polygon points for fill
                fill_points = points.copy()
                fill_points.append((points[-1][0], chart_bottom))
                fill_points.append((points[0][0], chart_bottom))
                
                # Draw semi-transparent fill (darker shade of the color)
                fill_color = (color[0] // 4, color[1] // 4, color[2] // 4)
                draw.polygon(fill_points, fill=fill_color)
                
                # Redraw the line on top
                for i in range(len(points) - 1):
                    draw.line([points[i], points[i + 1]], fill=color, width=1)

    def generate_image(self, args=[], kwargs={}) -> Image.Image | None:
        width = get_total_matrix_width()
        height = get_total_matrix_height()
        
        # Check if we need to refresh data
        if self.last_fetch:
            elapsed = (datetime.now() - self.last_fetch).seconds
            if elapsed >= self.fetch_interval:
                self._fetch_stock_data()
        
        # Create black background
        img = Image.new("RGB", (width, height), color=(0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Draw each stock panel
        for i, symbol in enumerate(SYMBOLS):
            x_offset = i * PANEL_WIDTH
            self._draw_stock_panel(symbol, x_offset, draw, img)
        
        return img
