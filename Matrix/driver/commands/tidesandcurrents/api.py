import requests
from datetime import datetime, timedelta
import json
import math
import xml.etree.ElementTree as ET
from Matrix import config

# Base API URL for NOAA Tides and Currents API
BASE_API_URL = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"

# Shelter Island coordinates
LATITUDE = 41.09
LONGITUDE = -72.35

# Defines the height of the sinusoidal curve for plotting tide data
SINUS_HEIGHT: float = 40.0


def get_api_url(
    date: str = "today",
    product: str = "predictions",
    station: str = config.TIDES_STATION,
    format: str = "json",
    application: str = "LED_Matrix",
    units: str = "english",
    time_zone: str = "lst_ldt",
    datum: str = "MLLW",
    interval: str | None = None
) -> str:
    """Constructs the URL for accessing the NOAA API."""
    url: str = f"{BASE_API_URL}?date={date}&station={station}&product={product}&format={format}&units={units}&application={application}&time_zone={time_zone}&datum={datum}"
    if interval is not None:
        url = f"{url}&interval={interval}"
    return url


def call_api(
    date: str = "today",
    product: str = "predictions",
    station: str = config.TIDES_STATION,
    format: str = "json",
    application: str = "LED_Matrix",
    units: str = "english",
    time_zone: str = "lst_ldt",
    datum: str = "MLLW",
    interval: str | None = None
):
    """Makes a GET request to the NOAA API and retrieves the response."""
    url: str = get_api_url(date=date, product=product, station=station, format=format, 
                           application=application, units=units, time_zone=time_zone, 
                           datum=datum, interval=interval)
    try:
        print(f"[tides] Calling {url}", flush=True)
        response: requests.Response = requests.get(url, timeout=15)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"[tides] API error: {response.status_code}", flush=True)
    except Exception as e:
        print(f"[tides] Unable to get tides info: {e}", flush=True)
    return {}


def get_station_name():
    """Fetches the station name from NOAA's metadata API."""
    url: str = get_api_url(product="wind", format="xml")
    try:
        response: requests.Response = requests.get(url, timeout=15)
        if response.status_code == 200:
            root = ET.fromstring(response.text)
            meta: ET.Element | None = root.find("metadata")
            station_name = meta.get("name")
            return station_name
    except Exception as e:
        print(f"[tides] Unable to get station info: {e}", flush=True)
    return None


def get_sun_times():
    """Get sunrise and sunset times from Open-Meteo API."""
    url = f"https://api.open-meteo.com/v1/forecast?latitude={LATITUDE}&longitude={LONGITUDE}&daily=sunrise,sunset&timezone=America/New_York&forecast_days=1"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            sunrise = data["daily"]["sunrise"][0]  # "2025-11-26T06:50"
            sunset = data["daily"]["sunset"][0]
            # Extract just the time part
            sunrise_time = sunrise.split("T")[1] if "T" in sunrise else sunrise
            sunset_time = sunset.split("T")[1] if "T" in sunset else sunset
            return {"sunrise": sunrise_time, "sunset": sunset_time}
    except Exception as e:
        print(f"[tides] Unable to get sun times: {e}", flush=True)
    return {"sunrise": "N/A", "sunset": "N/A"}


def get_moon_phase():
    """
    Calculate moon phase based on date.
    Returns phase name and illumination percentage.
    """
    # Known new moon date for reference
    known_new_moon = datetime(2024, 1, 11, 11, 57)
    lunar_cycle = 29.53058867  # days
    
    now = datetime.now()
    days_since = (now - known_new_moon).total_seconds() / 86400
    current_cycle = days_since % lunar_cycle
    phase_pct = current_cycle / lunar_cycle
    
    # Calculate illumination (0 at new moon, 1 at full moon)
    illumination = (1 - math.cos(2 * math.pi * phase_pct)) / 2
    
    # Determine phase name
    if phase_pct < 0.025 or phase_pct >= 0.975:
        phase_name = "New Moon"
        phase_icon = "new"
    elif phase_pct < 0.225:
        phase_name = "Waxing Crescent"
        phase_icon = "waxing_crescent"
    elif phase_pct < 0.275:
        phase_name = "First Quarter"
        phase_icon = "first_quarter"
    elif phase_pct < 0.475:
        phase_name = "Waxing Gibbous"
        phase_icon = "waxing_gibbous"
    elif phase_pct < 0.525:
        phase_name = "Full Moon"
        phase_icon = "full"
    elif phase_pct < 0.725:
        phase_name = "Waning Gibbous"
        phase_icon = "waning_gibbous"
    elif phase_pct < 0.775:
        phase_name = "Last Quarter"
        phase_icon = "last_quarter"
    elif phase_pct < 0.975:
        phase_name = "Waning Crescent"
        phase_icon = "waning_crescent"
    else:
        phase_name = "New Moon"
        phase_icon = "new"
    
    return {
        "name": phase_name,
        "icon": phase_icon,
        "illumination": int(illumination * 100),
        "days_in_cycle": round(current_cycle, 1)
    }


def get_tide_data_for_plot(w=5):
    """Processes tide predictions into a format suitable for plotting."""
    raw_data = call_api().get("predictions", [])
    if not raw_data:
        return None
    
    min_v: float = 0
    max_v: float = 0
    data = []

    for entry in raw_data:
        t: str = entry["t"].split(" ")[-1]
        v: float = float(entry["v"])
        if v > max_v:
            max_v = v
        if v < min_v:
            min_v = v
        data.append((t, v))

    delta_v: float = int(SINUS_HEIGHT / (max_v - min_v))
    delta_t: float = w * 64.0 / len(data)

    Y_offset: int = int((64 - SINUS_HEIGHT) / 2)

    curve: list[tuple[int, int]] = []
    timeline: list[str] = []

    for idx, entry in enumerate(data):
        x: int = int(idx * delta_t)
        y: int = Y_offset + int(delta_v * (entry[1] - min_v))
        curve.append((x, y))
        timeline.append(entry[0])

    return {
        "curve": curve, 
        "timeline": timeline, 
        "delta_v": delta_v, 
        "delta_t": delta_t, 
        "Y_offset": Y_offset, 
        "min_v": min_v
    }


def find_x(curve, timeline, target_time):
    """Finds the x-coordinate of the given time on the tide curve."""
    if isinstance(target_time, str):
        target_time = datetime.strptime(target_time, "%H:%M")

    for idx, d in enumerate(timeline):
        t1 = datetime.strptime(d, "%H:%M")
        if t1 > target_time:
            t0 = datetime.strptime(timeline[idx - 1], "%H:%M")
            interval_delta = t1 - t0
            interval_delta_s = interval_delta.total_seconds()
            t_delta = target_time - t0
            t_delta_s = t_delta.total_seconds()
            ratio = t_delta_s / interval_delta_s
            x0 = curve[idx - 1][0]
            x1 = curve[idx][0]
            x = int(x0 + (x1 - x0) * ratio)
            return x
    return None


def get_tide_data(w=5):
    """Retrieves complete tide data including sun and moon info."""
    station_name: str | None = get_station_name()
    result = get_tide_data_for_plot()
    
    if result is None:
        return {
            "name": station_name or "Unknown",
            "curve": [],
            "timeline": [],
            "hilo": [],
            "x_now": 0,
            "sun": get_sun_times(),
            "moon": get_moon_phase()
        }

    Y_offset: int = result["Y_offset"]
    min_v: float = result["min_v"]
    delta_v: float = result["delta_v"]
    hilo_raw = call_api(interval="hilo").get("predictions", [])
    curve = result["curve"]
    timeline = result["timeline"]

    hilo = []
    for entry in hilo_raw:
        t = entry["t"]
        v = float(entry["v"])
        type = entry["type"]
        y: int = Y_offset + int(delta_v * (v - min_v))
        t = t.split(" ")[-1]
        x = find_x(curve, timeline, target_time=t)
        hilo.append({"t": t, "v": v, "y": y, "type": type, "x": x})

    x_now = find_x(curve, timeline, target_time=datetime.now().strftime("%H:%M"))

    return {
        "name": station_name,
        "curve": curve,
        "timeline": timeline,
        "hilo": hilo,
        "x_now": x_now,
        "sun": get_sun_times(),
        "moon": get_moon_phase()
    }


if __name__ == "__main__":
    data = get_tide_data()
    print(f"Station: {data['name']}")
    print(f"Sun: {data['sun']}")
    print(f"Moon: {data['moon']}")
    print(f"Hi/Lo tides: {data['hilo']}")
