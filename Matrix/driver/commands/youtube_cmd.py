"""YouTube channel stats display."""

import os
import json
import requests
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from Matrix.driver.commands.base import (
    PictureScrollBaseCmd,
    get_total_matrix_width,
    get_total_matrix_height,
    get_fonts_dir,
)

# Path to YouTube logo and OAuth token
YOUTUBE_TOKEN_FILE = os.path.join(os.path.dirname(__file__), "youtube_token.json")

YOUTUBE_ICONS_DIR = os.path.join(os.path.dirname(__file__), "..", "icons", "youtube")

# Colors
WHITE = (255, 255, 255)
GRAY = (150, 150, 150)
RED = (255, 0, 0)
LIGHT_RED = (255, 100, 100)
TEAL = (47, 90, 97)

# Channel ID for 21-Knots
CHANNEL_ID = "UCF3xJel04U2fzcaem_9r9_w"
UPLOADS_PLAYLIST_ID = "UUF3xJel04U2fzcaem_9r9_w"

# API base URL
API_BASE = "https://www.googleapis.com/youtube/v3"


class YoutubeCmd(PictureScrollBaseCmd):
    def __init__(self) -> None:
        super().__init__("youtube", "YouTube channel stats display")
        self.scroll = False
        self.refresh = True
        self.refresh_timer = 1 / 30.0  # 30 fps for smooth scrolling
        self.recommended_duration = 120
        self.channel_data = None
        self.top_video = None
        self.logo = None
        self.font_large = None
        self.font_med = None
        self.font_small = None
        self.scroll_x = 0
        self.video_title_width = 0
        self.api_key = None
        self.combined_scroll_text = ""
        self.views_7d = None
        self.watch_hours = None
        self.top_video_48h = None
        self.analytics_service = None

    def update(self, args: list = [], kwargs: dict = {}) -> str:
        # Get API key from environment
        self.api_key = os.environ.get("YOUTUBE_API_KEY")
        if not self.api_key:
            print("[youtube] Error: YOUTUBE_API_KEY not set", flush=True)
        
        # Load fonts
        try:
            self.font_large = ImageFont.load(get_fonts_dir("10x20.pil"))
            self.font_med = ImageFont.load(get_fonts_dir("6x12.pil"))
            self.font_small = ImageFont.load(get_fonts_dir("5x7.pil"))
        except Exception as e:
            print(f"[youtube] Font error: {e}", flush=True)
        
        # Load logo
        logo_path = os.path.join(YOUTUBE_ICONS_DIR, "youtube_logo.png")
        try:
            self.logo = Image.open(logo_path).convert("RGBA")
            print(f"[youtube] Original logo size: {self.logo.size}", flush=True)
            # Resize to fit
            max_width = 60
            max_height = 40
            ratio = min(max_width / self.logo.width, max_height / self.logo.height)
            new_size = (int(self.logo.width * ratio), int(self.logo.height * ratio))
            self.logo = self.logo.resize(new_size, Image.Resampling.LANCZOS)
            print(f"[youtube] Resized logo: {new_size}", flush=True)
        except Exception as e:
            print(f"[youtube] Error loading logo: {e}", flush=True)
            self.logo = None
        
        # Fetch channel data
        self._fetch_channel_data()
        self._fetch_top_video()
        self._fetch_analytics_data()
        
        # Initialize scroll position
        self.scroll_x = get_total_matrix_width()
        
        return super().update(args, kwargs)

    def _fetch_channel_data(self):
        """Fetch channel statistics from YouTube API."""
        if not self.api_key:
            return
        
        try:
            url = f"{API_BASE}/channels?part=snippet,statistics&id={CHANNEL_ID}&key={self.api_key}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get("items"):
                item = data["items"][0]
                stats = item.get("statistics", {})
                snippet = item.get("snippet", {})
                
                self.channel_data = {
                    "title": snippet.get("title", "Unknown"),
                    "subscribers": int(stats.get("subscriberCount", 0)),
                    "views": int(stats.get("viewCount", 0)),
                    "videos": int(stats.get("videoCount", 0)),
                }
                print(f"[youtube] Channel: {self.channel_data['title']}, Subs: {self.channel_data['subscribers']}, Views: {self.channel_data['views']}", flush=True)
        except Exception as e:
            print(f"[youtube] API error: {e}", flush=True)

    def _fetch_top_video(self):
        """Fetch the most viewed video from the channel."""
        if not self.api_key:
            return
        
        try:
            # Get video IDs from uploads playlist
            url = f"{API_BASE}/playlistItems?part=snippet&playlistId={UPLOADS_PLAYLIST_ID}&maxResults=50&key={self.api_key}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            video_ids = []
            for item in data.get("items", []):
                video_id = item.get("snippet", {}).get("resourceId", {}).get("videoId")
                if video_id:
                    video_ids.append(video_id)
            
            if not video_ids:
                return
            
            # Get video statistics
            ids_str = ",".join(video_ids)
            url = f"{API_BASE}/videos?part=snippet,statistics&id={ids_str}&key={self.api_key}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Find most viewed video
            max_views = 0
            for item in data.get("items", []):
                views = int(item.get("statistics", {}).get("viewCount", 0))
                if views > max_views:
                    max_views = views
                    self.top_video = {
                        "title": item.get("snippet", {}).get("title", "Unknown"),
                        "views": views,
                    }
            
            if self.top_video:
                print(f"[youtube] Top video: {self.top_video['title']} ({self.top_video['views']} views)", flush=True)
                
        except Exception as e:
            print(f"[youtube] Error fetching top video: {e}", flush=True)

    def _load_credentials(self):
        """Load OAuth credentials from token file."""
        try:
            if not os.path.exists(YOUTUBE_TOKEN_FILE):
                print("[youtube] Token file not found", flush=True)
                return None
            
            with open(YOUTUBE_TOKEN_FILE, 'r') as f:
                token_data = json.load(f)
            
            credentials = Credentials(
                token=token_data['token'],
                refresh_token=token_data['refresh_token'],
                token_uri=token_data['token_uri'],
                client_id=token_data['client_id'],
                client_secret=token_data['client_secret'],
                scopes=token_data['scopes']
            )
            
            # Refresh if expired
            if credentials.expired:
                credentials.refresh(Request())
                # Save refreshed token
                token_data['token'] = credentials.token
                with open(YOUTUBE_TOKEN_FILE, 'w') as f:
                    json.dump(token_data, f, indent=2)
            
            return credentials
        except Exception as e:
            print(f"[youtube] Error loading credentials: {e}", flush=True)
            return None

    def _fetch_analytics_data(self):
        """Fetch data from YouTube Analytics API."""
        try:
            credentials = self._load_credentials()
            if not credentials:
                return
            
            # Build Analytics service
            analytics = build('youtubeAnalytics', 'v2', credentials=credentials)
            youtube = build('youtube', 'v3', credentials=credentials)
            
            # Date range for last 48 hours (API uses dates, so we use last 2 days)
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date_7d = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            start_date_365d = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
            
            # Get views last 48 hours
            response = analytics.reports().query(
                ids='channel==MINE',
                startDate=start_date_7d,
                endDate=end_date,
                metrics='views'
            ).execute()
            
            if response.get('rows'):
                self.views_7d = int(response['rows'][0][0])
                print(f"[youtube] Views last 7d: {self.views_7d}", flush=True)
            
            # Get watch hours last 365 days
            response = analytics.reports().query(
                ids='channel==MINE',
                startDate=start_date_365d,
                endDate=end_date,
                metrics='estimatedMinutesWatched'
            ).execute()
            
            if response.get('rows'):
                minutes = int(response['rows'][0][0])
                self.watch_hours = round(minutes / 60, 1)
                print(f"[youtube] Watch hours (365d): {self.watch_hours}", flush=True)
            
            # Get top video last 48 hours
            response = analytics.reports().query(
                ids='channel==MINE',
                startDate=start_date_7d,
                endDate=end_date,
                metrics='views',
                dimensions='video',
                sort='-views',
                maxResults=1
            ).execute()
            
            if response.get('rows'):
                video_id = response['rows'][0][0]
                video_views = int(response['rows'][0][1])
                
                # Get video title
                video_response = youtube.videos().list(
                    part='snippet',
                    id=video_id
                ).execute()
                
                if video_response.get('items'):
                    video_title = video_response['items'][0]['snippet']['title']
                    self.top_video_48h = {
                        'title': video_title,
                        'views': video_views
                    }
                    print(f"[youtube] Top video 7d: {video_title} ({video_views} views)", flush=True)
                    
        except Exception as e:
            print(f"[youtube] Analytics API error: {e}", flush=True)

    def _format_number(self, num):
        """Format number with K/M suffix."""
        if num >= 1000000:
            return f"{num/1000000:.1f}M"
        elif num >= 1000:
            return f"{num/1000:.1f}K"
        else:
            return str(num)

    def generate_image(self, args=[], kwargs={}) -> Image.Image | None:
        width = get_total_matrix_width()
        height = get_total_matrix_height()
        
        # Create black background
        img = Image.new("RGB", (width, height), color=(0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Draw logo on top-left
        logo_x = 8
        logo_y = 10
        text_start_x = 100
        
        if self.logo:
            logo_rgb = Image.new("RGB", self.logo.size, (0, 0, 0))
            if self.logo.mode == 'RGBA':
                logo_rgb.paste(self.logo, mask=self.logo.split()[3])
            else:
                logo_rgb.paste(self.logo)
            img.paste(logo_rgb, (logo_x, logo_y))
            text_start_x = logo_x + self.logo.width + 12
        
        if not self.channel_data:
            draw.text((text_start_x, 25), "No data", font=self.font_med, fill=WHITE)
            return img
        
        # Channel name (static)
        draw.text((text_start_x, 10), "21 Knots YouTube Stats", font=self.font_large, fill=TEAL)
        
        # Stats line: Subs | Views | Watch hrs
        subs = self._format_number(self.channel_data.get("subscribers", 0))
        total_views = self._format_number(self.channel_data.get("views", 0))
        watch_hrs = self._format_number(self.watch_hours) if self.watch_hours else "--"
        stats_text = f"{subs} subs  |  {total_views} views  |  {watch_hrs} watch hrs"
        draw.text((text_start_x, 32), stats_text, font=self.font_small, fill=GRAY)
        
        # Views last 48 hours line (placeholder - requires Analytics API with OAuth)
        views_7d_text = str(self.views_7d) if self.views_7d is not None else "--"
        draw.text((text_start_x, 44), f"Views - Last 7 Days: {views_7d_text}", font=self.font_small, fill=GRAY)
        
        # Scrolling video titles on bottom line (both concatenated)
        if self.top_video:
            desc_y = height - 10
            
            # Build combined scroll text parts
            prefix1 = "Top Video (all time): "
            video_title = self.top_video.get("title", "")
            video_views = self._format_number(self.top_video.get("views", 0))
            suffix1 = f"{video_title} ({video_views} views)"
            
            spacer = "     "  # 5 spaces
            
            prefix2 = "Top Video (last 7 days): "
            if self.top_video_48h:
                suffix2 = f"{self.top_video_48h['title']} ({self._format_number(self.top_video_48h['views'])} views)"
            else:
                suffix2 = "No data"
            
            # Calculate widths
            prefix1_bbox = draw.textbbox((0, 0), prefix1, font=self.font_small)
            prefix1_width = prefix1_bbox[2] - prefix1_bbox[0]
            
            suffix1_bbox = draw.textbbox((0, 0), suffix1, font=self.font_small)
            suffix1_width = suffix1_bbox[2] - suffix1_bbox[0]
            
            spacer_bbox = draw.textbbox((0, 0), spacer, font=self.font_small)
            spacer_width = spacer_bbox[2] - spacer_bbox[0]
            
            prefix2_bbox = draw.textbbox((0, 0), prefix2, font=self.font_small)
            prefix2_width = prefix2_bbox[2] - prefix2_bbox[0]
            
            suffix2_bbox = draw.textbbox((0, 0), suffix2, font=self.font_small)
            suffix2_width = suffix2_bbox[2] - suffix2_bbox[0]
            
            # Total width
            self.video_title_width = prefix1_width + suffix1_width + spacer_width + prefix2_width + suffix2_width
            
            # Draw each segment at correct position
            x = int(self.scroll_x)
            
            # Draw "Top Video (all time): " in red
            draw.text((x, desc_y), prefix1, font=self.font_small, fill=RED)
            x += prefix1_width
            
            # Draw video title in gray
            draw.text((x, desc_y), suffix1, font=self.font_small, fill=GRAY)
            x += suffix1_width
            
            # Draw spacer
            x += spacer_width
            
            # Draw "Top Video (last 7 days): " in red
            draw.text((x, desc_y), prefix2, font=self.font_small, fill=RED)
            x += prefix2_width
            
            # Draw placeholder in gray
            draw.text((x, desc_y), suffix2, font=self.font_small, fill=GRAY)
            
            # Update scroll position
            self.scroll_x -= 1
            if self.scroll_x < -self.video_title_width:
                self.scroll_x = width
        
        return img
