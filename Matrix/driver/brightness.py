"""Time-based brightness control for LED matrix with manual override."""
from datetime import datetime
import time
import os
import json

# Brightness schedule: (hour, brightness)
# Brightness ranges from 0-100
BRIGHTNESS_SCHEDULE = [
    (0, 20),    # Midnight - very dim
    (6, 25),    # 6 AM - dim morning
    (7, 40),    # 7 AM - waking up
    (8, 60),    # 8 AM - morning
    (9, 80),    # 9 AM - getting brighter
    (11, 100),  # 11 AM - full brightness
    (14, 100),  # 2 PM - full brightness
    (16, 90),   # 4 PM - starting to dim
    (18, 70),   # 6 PM - evening
    (20, 50),   # 8 PM - dimmer
    (22, 30),   # 10 PM - night
    (23, 20),   # 11 PM - very dim
]

# Track last update to avoid frequent changes
_last_brightness = None
_last_update_time = 0
UPDATE_INTERVAL = 5  # Check every 5 seconds for faster response

# File for cross-process brightness override
BRIGHTNESS_FILE = "/tmp/pixelpulse_brightness.json"

def _read_override_file():
    """Read manual override from shared file."""
    try:
        if os.path.exists(BRIGHTNESS_FILE):
            with open(BRIGHTNESS_FILE, 'r') as f:
                data = json.load(f)
                return data.get("manual_override")
    except Exception:
        pass
    return None

def _write_override_file(value):
    """Write manual override to shared file."""
    try:
        with open(BRIGHTNESS_FILE, 'w') as f:
            json.dump({"manual_override": value}, f)
    except Exception as e:
        print(f"[brightness] Error writing override file: {e}", flush=True)

def get_brightness_for_time(hour: int = None) -> int:
    """Get brightness level for a given hour (0-23)."""
    if hour is None:
        hour = datetime.now().hour
    
    # Find the appropriate brightness
    prev_hour, prev_brightness = BRIGHTNESS_SCHEDULE[-1]
    for sched_hour, brightness in BRIGHTNESS_SCHEDULE:
        if hour < sched_hour:
            # Interpolate between previous and current
            if prev_hour > sched_hour:  # Wrapped around midnight
                hour_diff = sched_hour - 0
                hour_progress = hour - 0
            else:
                hour_diff = sched_hour - prev_hour
                hour_progress = hour - prev_hour
            if hour_diff > 0:
                ratio = hour_progress / hour_diff
                return int(prev_brightness + (brightness - prev_brightness) * ratio)
            return brightness
        prev_hour, prev_brightness = sched_hour, brightness
    
    # Past the last scheduled time, use last brightness
    return BRIGHTNESS_SCHEDULE[-1][1]

def get_manual_override() -> int | None:
    """Get current manual override value (None if using schedule)."""
    return _read_override_file()

def get_current_brightness() -> int:
    """Get brightness for current time (or manual override)."""
    override = _read_override_file()
    if override is not None:
        return override
    return get_brightness_for_time()

def set_manual_brightness(value: int | None) -> int:
    """Set manual brightness override. Pass None to return to auto schedule."""
    global _last_brightness
    if value is not None:
        value = max(5, min(100, value))  # Clamp between 5-100
    _write_override_file(value)
    _last_brightness = None  # Force update on next check
    return get_current_brightness()

def adjust_brightness(delta: int) -> int:
    """Adjust brightness by delta amount. Enables manual override if not set."""
    current = get_current_brightness()
    new_value = max(5, min(100, current + delta))
    return set_manual_brightness(new_value)

def update_matrix_brightness(matrix) -> bool:
    """
    Update matrix brightness if needed.
    Returns True if brightness was changed.
    """
    global _last_brightness, _last_update_time
    
    current_time = time.time()
    
    # Only check every UPDATE_INTERVAL seconds
    if current_time - _last_update_time < UPDATE_INTERVAL:
        return False
    
    _last_update_time = current_time
    new_brightness = get_current_brightness()
    
    if new_brightness != _last_brightness:
        try:
            matrix.brightness = new_brightness
            override = _read_override_file()
            mode = "manual" if override is not None else "auto"
            print(f"[brightness] Updated to {new_brightness}% ({mode})", flush=True)
            _last_brightness = new_brightness
            return True
        except Exception as e:
            print(f"[brightness] Failed to update: {e}", flush=True)
    
    return False


if __name__ == "__main__":
    # Test brightness for each hour
    for h in range(24):
        print(f"{h:02d}:00 -> {get_brightness_for_time(h)}%")
