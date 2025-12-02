"""Sleep schedule manager - automatic sleep/wake based on time and day."""

import json
import os
import threading
import time
from datetime import datetime

# Default schedule - sleep at 11pm, wake at 7am every day
# Format: {day_of_week: {"sleep": "HH:MM", "wake": "HH:MM", "enabled": True}}
# day_of_week: 0=Monday, 6=Sunday
DEFAULT_SCHEDULE = {
    "0": {"sleep": "23:00", "wake": "07:00", "enabled": True},  # Monday
    "1": {"sleep": "23:00", "wake": "07:00", "enabled": True},  # Tuesday
    "2": {"sleep": "23:00", "wake": "07:00", "enabled": True},  # Wednesday
    "3": {"sleep": "23:00", "wake": "07:00", "enabled": True},  # Thursday
    "4": {"sleep": "23:00", "wake": "07:00", "enabled": True},  # Friday
    "5": {"sleep": "23:30", "wake": "08:00", "enabled": True},  # Saturday
    "6": {"sleep": "23:30", "wake": "08:00", "enabled": True},  # Sunday
}

SCHEDULE_FILE = "/etc/PixelPulseNeo/sleep_schedule.json"
CHECK_INTERVAL = 60  # Check every minute

_schedule = None
_scheduler_thread = None
_stop_scheduler = threading.Event()
_executor = None
_last_action = None  # Track last action to avoid repeated calls


def load_schedule():
    """Load schedule from file or use defaults."""
    global _schedule
    try:
        if os.path.exists(SCHEDULE_FILE):
            with open(SCHEDULE_FILE, 'r') as f:
                _schedule = json.load(f)
                print(f"[sleep_schedule] Loaded schedule from {SCHEDULE_FILE}", flush=True)
        else:
            _schedule = DEFAULT_SCHEDULE.copy()
            save_schedule()
            print(f"[sleep_schedule] Created default schedule", flush=True)
    except Exception as e:
        print(f"[sleep_schedule] Error loading schedule: {e}", flush=True)
        _schedule = DEFAULT_SCHEDULE.copy()
    return _schedule


def save_schedule():
    """Save current schedule to file."""
    global _schedule
    try:
        os.makedirs(os.path.dirname(SCHEDULE_FILE), exist_ok=True)
        with open(SCHEDULE_FILE, 'w') as f:
            json.dump(_schedule, f, indent=2)
        print(f"[sleep_schedule] Saved schedule to {SCHEDULE_FILE}", flush=True)
        return True
    except Exception as e:
        print(f"[sleep_schedule] Error saving schedule: {e}", flush=True)
        return False


def get_schedule():
    """Get current schedule."""
    global _schedule
    if _schedule is None:
        load_schedule()
    return _schedule


def set_schedule(new_schedule):
    """Set new schedule."""
    global _schedule
    _schedule = new_schedule
    save_schedule()
    return _schedule


def set_day_schedule(day, sleep_time=None, wake_time=None, enabled=None):
    """Set schedule for a specific day."""
    global _schedule
    if _schedule is None:
        load_schedule()
    
    day_str = str(day)
    if day_str not in _schedule:
        _schedule[day_str] = {"sleep": "23:00", "wake": "07:00", "enabled": True}
    
    if sleep_time is not None:
        _schedule[day_str]["sleep"] = sleep_time
    if wake_time is not None:
        _schedule[day_str]["wake"] = wake_time
    if enabled is not None:
        _schedule[day_str]["enabled"] = enabled
    
    save_schedule()
    return _schedule


def time_to_minutes(time_str):
    """Convert HH:MM to minutes since midnight."""
    h, m = map(int, time_str.split(':'))
    return h * 60 + m


def should_be_sleeping():
    """Check if we should be in sleep mode based on current time and schedule."""
    global _schedule
    if _schedule is None:
        load_schedule()
    
    now = datetime.now()
    day_str = str(now.weekday())
    current_minutes = now.hour * 60 + now.minute
    
    day_schedule = _schedule.get(day_str, {})
    if not day_schedule.get("enabled", False):
        return False
    
    sleep_minutes = time_to_minutes(day_schedule.get("sleep", "23:00"))
    wake_minutes = time_to_minutes(day_schedule.get("wake", "07:00"))
    
    # Handle overnight sleep (e.g., sleep at 23:00, wake at 07:00)
    if sleep_minutes > wake_minutes:
        # Sleep period crosses midnight
        return current_minutes >= sleep_minutes or current_minutes < wake_minutes
    else:
        # Sleep period within same day (unusual but supported)
        return sleep_minutes <= current_minutes < wake_minutes
    
    return False


def _scheduler_loop():
    """Background thread that checks schedule and triggers sleep/wake."""
    global _executor, _last_action, _stop_scheduler
    
    print("[sleep_schedule] Scheduler loop started", flush=True)
    
    while not _stop_scheduler.is_set():
        try:
            if _executor is not None:
                should_sleep = should_be_sleeping()
                is_sleeping = getattr(_executor, 'sleep_mode_activated', False)
                
                if should_sleep and not is_sleeping and _last_action != "sleep":
                    print("[sleep_schedule] Time to sleep - activating sleep mode", flush=True)
                    _executor.sleep()
                    _last_action = "sleep"
                elif not should_sleep and is_sleeping and _last_action != "wake":
                    print("[sleep_schedule] Time to wake - deactivating sleep mode", flush=True)
                    _executor.wakeup()
                    _last_action = "wake"
        except Exception as e:
            print(f"[sleep_schedule] Error in scheduler loop: {e}", flush=True)
        
        # Wait for next check
        _stop_scheduler.wait(CHECK_INTERVAL)
    
    print("[sleep_schedule] Scheduler loop stopped", flush=True)


def start_scheduler(executor):
    """Start the sleep scheduler with reference to executor."""
    global _scheduler_thread, _stop_scheduler, _executor
    
    _executor = executor
    load_schedule()
    
    if _scheduler_thread is not None and _scheduler_thread.is_alive():
        print("[sleep_schedule] Scheduler already running", flush=True)
        return
    
    _stop_scheduler.clear()
    _scheduler_thread = threading.Thread(target=_scheduler_loop, daemon=True)
    _scheduler_thread.start()
    print("[sleep_schedule] Sleep scheduler started", flush=True)


def stop_scheduler():
    """Stop the sleep scheduler."""
    global _scheduler_thread, _stop_scheduler
    
    _stop_scheduler.set()
    if _scheduler_thread is not None:
        _scheduler_thread.join(timeout=5)
        _scheduler_thread = None
    print("[sleep_schedule] Sleep scheduler stopped", flush=True)


# Day names for API responses
DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

def get_schedule_with_names():
    """Get schedule with day names included."""
    schedule = get_schedule()
    result = {}
    for day_num, settings in schedule.items():
        result[day_num] = {
            **settings,
            "day_name": DAY_NAMES[int(day_num)]
        }
    return result
