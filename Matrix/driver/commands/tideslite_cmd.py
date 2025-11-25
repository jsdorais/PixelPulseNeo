
from typing import Any, Dict, List, Tuple
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import requests

from Matrix.driver.commands.base import (
    PictureScrollBaseCmd,
    get_total_matrix_width,
    get_total_matrix_height,
)
from Matrix.driver.commands.tidesandcurrents import api  # NOAA helper

def _station_id_from(data) -> str:
    import os
    if isinstance(data, dict):
        for k in ("station","stationId","stationID"):
            v = data.get(k)
            if v: return str(v)
        meta = data.get("meta") or {}
        if isinstance(meta, dict):
            for k in ("station","stationId","id"):
                v = meta.get(k)
                if v: return str(v)
        info = data.get("station_info") or {}
        if isinstance(info, dict):
            for k in ("id","station","stationId"):
                v = info.get(k)
                if v: return str(v)
    return os.getenv("TIDES_STATION") or os.getenv("NOAA_STATION") or ""

def _station_name_from_noaa(station_id: str) -> str:
    if not station_id:
        return ""
    try:
        url = f"https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations/{station_id}.json"
        resp = requests.get(url, timeout=3)
        j = resp.json()
        if isinstance(j, dict):
            if "stations" in j and isinstance(j["stations"], list) and j["stations"]:
                return j["stations"][0].get("name") or ""
            if "station" in j and isinstance(j["station"], dict):
                return j["station"].get("name") or ""
            for k in ("metadata","meta","properties"):
                v = j.get(k)
                if isinstance(v, dict) and v.get("name"):
                    return v["name"]
    except Exception:
        pass
    return ""

def _station_text(data) -> str:
    import os
    # Try common locations/keys
    cands = []
    if isinstance(data, dict):
        cands += [
            data.get("station"),
            data.get("station_name"),
            data.get("stationId"),
            data.get("stationID"),
        ]
        meta = data.get("meta") or {}
        if isinstance(meta, dict):
            cands += [
                meta.get("station"),
                meta.get("station_name"),
                meta.get("stationName"),
                meta.get("stationid"),
                meta.get("id"),
                meta.get("name"),
            ]
        info = data.get("station_info") or {}
        if isinstance(info, dict):
            cands += [
                info.get("name"),
                info.get("id"),
            ]
        # NOAA JSON sometimes sticks raw station id at top-level 'predictions' meta
        preds = data.get("predictions_meta") or data.get("predictions") or {}
        if isinstance(preds, dict):
            for k in ("station","station_name","name","id"):
                v = preds.get(k)
                if v:
                    cands.append(v)
    # Environment fallback (from init_env.sh), then hard fallback
    cands += [os.getenv("TIDES_STATION"), os.getenv("NOAA_STATION"), "Tides"]
    # Return first truthy
    for v in cands:
        if isinstance(v, (str, int)) and str(v).strip():
            return str(v).strip()
    return "Tides"

CURVE_COLOR = (29, 162, 216)
TEXT_COLOR  = (216, 211, 208)
MARK_COLOR  = (180, 180, 180)

def _load_small_font() -> ImageFont.ImageFont:
    # Try your repo's bitmap font first (8x13)
    fonts_dir = Path(__file__).with_name("fonts")
    f_pil = fonts_dir / "8x13.pil"
    f_pbm = fonts_dir / "8x13.pbm"
    try:
        if f_pil.exists() and f_pbm.exists():
            return ImageFont.load(str(f_pil))
    except Exception:
        pass
    return ImageFont.load_default()

class TidesLiteCmd(PictureScrollBaseCmd):
    """
    Minimal tides display tuned for a 64px-high matrix (supports multi-panel width).
    Adds Hi/Lo markers with time labels and a station header.
    """
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__("tideslite", "Displays tides (lite)")
        self.scroll = False
        self.refresh = False
        self.speed_x = 0
        self.speed_y = 0
        self.recommended_duration = 30
        self.tides_data: Dict[str, Any] = {}
        self._station_title = 'Tides'
        self.font = _load_small_font()

    def update(self, *args, **kwargs) -> None:
        try:
            self.tides_data = api.get_tide_data()
        except Exception as e:
            self.tides_data = {
                "station": "Tides",
                "hilo": [
                    {"t":"06:30","type":"H","v":4.1,"x":16},
                    {"t":"12:47","type":"L","v":0.2,"x":44},
                ],
                "curve": [(x, 32) for x in range(320)],  # 320-wide default curve
                "error": str(e),
            }
        super().update(*args, **kwargs)

    def _draw_curve(self, draw: ImageDraw.ImageDraw, width: int, height: int) -> None:
        curve: List[Tuple[int,int]] = self.tides_data.get("curve", [])
        if not curve:
            return
        pts = []
        H = height - 1
        for x, y in curve:
            x = max(0, min(width-1, int(x)))
            y = max(0, min(H, int(H - y)))  # invert Y for screen coords
            pts.append((x, y))
        for i in range(len(pts) - 1):
            draw.line([pts[i], pts[i+1]], fill=CURVE_COLOR, width=1)

    
    def _draw_hilo_markers(self, draw: ImageDraw.ImageDraw, width: int, height: int, font: ImageFont.ImageFont, title_bbox) -> None:
        hilo = self.tides_data.get("hilo", [])
        if not hilo:
            return

        H = height - 1
        title_w, title_h = title_bbox[2], title_bbox[3]
        top_margin  = 1
        label_pad   = 1
        line_top    = top_margin + title_h + 3
        line_bot    = H - 2
        reserved_x  = title_w + 6

        entries = []
        for entry in hilo:
            x = int(entry.get("x", 0))
            x = max(0, min(width-1, x))
            entries.append((x, entry))
        entries.sort(key=lambda t: t[0])

        last_tx_end_top = -9999
        last_tx_end_bot = -9999

        for x, entry in entries:
            t  = str(entry.get("t","--:--"))
            ty = str(entry.get("type","?")).upper()

            draw.line([(x, line_top), (x, line_bot)], fill=MARK_COLOR, width=1)

            w, h = font.getbbox(t)[2], font.getbbox(t)[3]
            if ty == "H":
                y = max(top_margin, line_top - h - label_pad)
            else:
                y = min(line_bot - h, H - h - label_pad)

            tx = max(0, min(width - w, x - w // 2))

            if ty == "H" and tx < reserved_x:
                y = line_top + 1

            if ty == "H":
                if tx < last_tx_end_top + 4:
                    tx = last_tx_end_top + 4
                last_tx_end_top = tx + w
            else:
                if tx < last_tx_end_bot + 4:
                    tx = last_tx_end_bot + 4
                last_tx_end_bot = tx + w

            draw.text((tx, y), t, fill=TEXT_COLOR, font=font)


    def generate_image(self, args=[], kwargs={}) -> Image.Image:
        # Render directly at 320x64 (5 panels) for crisp output
        width  = 64 * 5
        height = 64
        img  = Image.new("RGB", (width, height), color=(0,0,0))
        draw = ImageDraw.Draw(img)
        font = self.font

        # Title line: station
        # Resolve title deterministically from env or data
        sid = os.getenv("TIDES_STATION") or str(
            self.tides_data.get("station")
            or (self.tides_data.get("meta") or {}).get("station")
            or (self.tides_data.get("station_info") or {}).get("id")
            or ""
        )
        name = os.getenv("TIDES_STATION_NAME") or str(
            (self.tides_data.get("meta") or {}).get("name")
            or (self.tides_data.get("station_info") or {}).get("name")
            or ""
        )
        station = f"{name} ({sid})" if (name and sid) else (name or sid or "Tides")
        try:
            print("[tideslite] RESOLVED:", {"sid": sid, "name": name, "title": station})
        except Exception:
            pass
        err = " !" if "error" in self.tides_data else ""
        title_bbox = font.getbbox(f"Station: {station}{err}")
        draw.text((2, 1), f"Station: {station}{err}", fill=TEXT_COLOR, font=font)

        # Curve first
        self._draw_curve(draw, width, height)

        # Hi/Lo markers + time labels (avoid title + de-overlap)
        self._draw_hilo_markers(draw, width, height, font, title_bbox)

        return img
