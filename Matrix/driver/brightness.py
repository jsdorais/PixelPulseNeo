"""Time-based brightness control for LED matrix."""

from datetime import datetime
import time

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
UPDATE_INTERVAL = 60  # Check every 60 seconds


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


def get_current_brightness() -> int:
    """Get brightness for current time."""
    return get_brightness_for_time()


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
            print(f"[brightness] Updated to {new_brightness}%", flush=True)
            _last_brightness = new_brightness
            return True
        except Exception as e:
            print(f"[brightness] Failed to update: {e}", flush=True)
    
    return False


if __name__ == "__main__":
    # Test brightness for each hour
    for h in range(24):
        print(f"{h:02d}:00 -> {get_brightness_for_time(h)}%")
