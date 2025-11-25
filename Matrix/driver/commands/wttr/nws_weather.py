"""National Weather Service API client."""

import requests
import re

# Shelter Island coordinates
LAT = 41.09
LON = -72.35

# Cache the grid info
_grid_cache = None

def get_icon_name(short_forecast):
    """Map NWS shortForecast to icon name."""
    forecast_lower = short_forecast.lower()
    
    if "thunder" in forecast_lower:
        if "heavy" in forecast_lower:
            return "ThunderyHeavyRain"
        if "snow" in forecast_lower:
            return "ThunderySnowShowers"
        return "ThunderyShowers"
    
    if "snow" in forecast_lower:
        if "heavy" in forecast_lower:
            return "HeavySnow"
        if "shower" in forecast_lower:
            return "LightSnowShowers"
        return "LightSnow"
    
    if "sleet" in forecast_lower or "freezing" in forecast_lower or "ice" in forecast_lower:
        if "shower" in forecast_lower:
            return "LightSleetShowers"
        return "LightSleet"
    
    if "rain" in forecast_lower or "shower" in forecast_lower:
        if "heavy" in forecast_lower:
            return "HeavyRain"
        if "light" in forecast_lower or "chance" in forecast_lower or "slight" in forecast_lower:
            return "LightShowers"
        return "HeavyShowers"
    
    if "fog" in forecast_lower or "mist" in forecast_lower or "haze" in forecast_lower:
        return "Fog"
    
    if "sunny" in forecast_lower or "clear" in forecast_lower:
        if "partly" in forecast_lower or "mostly" in forecast_lower:
            return "PartlyCloudy"
        return "Sunny"
    
    if "cloudy" in forecast_lower:
        if "partly" in forecast_lower:
            return "PartlyCloudy"
        if "mostly" in forecast_lower:
            return "Cloudy"
        return "VeryCloudy"
    
    return "Unknown"

def _get_grid_info():
    """Get NWS grid info for the location (cached)."""
    global _grid_cache
    if _grid_cache:
        return _grid_cache
    
    url = f"https://api.weather.gov/points/{LAT},{LON}"
    headers = {"User-Agent": "PixelPulseNeo"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            _grid_cache = {
                "forecast": data["properties"]["forecast"],
                "forecastHourly": data["properties"]["forecastHourly"],
                "city": data["properties"]["relativeLocation"]["properties"]["city"],
                "state": data["properties"]["relativeLocation"]["properties"]["state"],
            }
            return _grid_cache
    except Exception as e:
        print(f"[nws] Error getting grid info: {e}")
    return None

def get_forecast():
    """Get the forecast from NWS API."""
    grid = _get_grid_info()
    if not grid:
        return None
    
    headers = {"User-Agent": "PixelPulseNeo"}
    
    try:
        response = requests.get(grid["forecast"], headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data["properties"]["periods"]
    except Exception as e:
        print(f"[nws] Error getting forecast: {e}")
    return None

def f_to_c(fahrenheit):
    """Convert Fahrenheit to Celsius."""
    return round((fahrenheit - 32) * 5 / 9)

def mph_to_knots(mph):
    """Convert mph to knots."""
    return round(mph * 0.869)

def convert_detailed_to_metric(text):
    """Convert F temperatures to C and mph to knots in detailed forecast."""
    
    # First, convert wind speeds (mph to knots) - do this first to avoid conflicts
    def replace_wind(match):
        mph = int(match.group(1))
        knots = mph_to_knots(mph)
        return f"{knots} knots"
    
    # Match "X mph" or "X to Y mph"
    text = re.sub(r'(\d+) mph', replace_wind, text)
    text = re.sub(r'(\d+) to (\d+) knots', lambda m: f"{mph_to_knots(int(m.group(1)))} to {m.group(2)} knots", text)
    
    # Now convert temperatures - only match temperature contexts (not wind)
    def replace_temp(match):
        prefix = match.group(1)
        temp_f = int(match.group(2))
        suffix = match.group(3)
        temp_c = f_to_c(temp_f)
        return f"{prefix}{temp_c}C{suffix}"
    
    # Match temperatures: "near 57," or "around 54 in" but NOT "around 10 knots"
    # Only match if NOT followed by "knots" or "mph"
    text = re.sub(r'(near )(\d{1,3})([,. ])', replace_temp, text)
    text = re.sub(r'(around )(\d{1,3})( in)', replace_temp, text)
    text = re.sub(r'(to )(\d{1,3})([,.])', replace_temp, text)
    text = re.sub(r'(of )(\d{1,3})([,. ])', replace_temp, text)
    
    return text

def get_current_weather():
    """Get current weather formatted for display."""
    periods = get_forecast()
    if not periods:
        return None
    
    current = periods[0]
    
    result = {
        "period_name": current["name"],
        "temp_c": f_to_c(current["temperature"]),
        "condition": current["shortForecast"],
        "icon": get_icon_name(current["shortForecast"]),
        "detailed": convert_detailed_to_metric(current["detailedForecast"]),
        "wind": current["windSpeed"],
        "wind_dir": current["windDirection"],
        "is_daytime": current["isDaytime"],
    }
    
    # Get next few periods for forecast
    result["periods"] = []
    for i, period in enumerate(periods[:6]):
        result["periods"].append({
            "name": period["name"],
            "temp_c": f_to_c(period["temperature"]),
            "condition": period["shortForecast"],
            "icon": get_icon_name(period["shortForecast"]),
            "detailed": convert_detailed_to_metric(period["detailedForecast"]),
            "is_daytime": period["isDaytime"],
        })
    
    return result

if __name__ == "__main__":
    weather = get_current_weather()
    if weather:
        print(f"Current: {weather['period_name']}")
        print(f"Temp: {weather['temp_c']}C")
        print(f"Condition: {weather['condition']} -> Icon: {weather['icon']}")
        print(f"Detailed: {weather['detailed']}")
        print("\nForecast:")
        for p in weather['periods']:
            print(f"  {p['name']}: {p['temp_c']}C - {p['condition']} -> {p['icon']}")
