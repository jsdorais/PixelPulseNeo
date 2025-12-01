#!/usr/bin/env python3
"""Background monitor for Last.fm - switches to lastfm app when music is playing."""

import os
import time
import requests

# Configuration
LASTFM_API_KEY = os.environ.get("LASTFM_API_KEY", "b95aec57504a6bac5ec86eda809266e8")
LASTFM_USERNAME = os.environ.get("LASTFM_USERNAME", "dodotopia")
CHECK_INTERVAL = 5  # seconds
API_URL = "http://localhost:5000/api"

def get_now_playing():
    """Check if something is currently playing on Last.fm."""
    try:
        url = "http://ws.audioscrobbler.com/2.0/"
        params = {
            "method": "user.getrecenttracks",
            "user": LASTFM_USERNAME,
            "api_key": LASTFM_API_KEY,
            "format": "json",
            "limit": 1
        }
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        tracks = data.get("recenttracks", {}).get("track", [])
        if tracks and isinstance(tracks, list) and len(tracks) > 0:
            track = tracks[0]
            # Check if currently playing (has @attr with nowplaying)
            if track.get("@attr", {}).get("nowplaying") == "true":
                artist = track.get("artist", {}).get("#text", "Unknown")
                title = track.get("name", "Unknown")
                return True, f"{artist} - {title}"
        return False, None
    except Exception as e:
        print(f"[lastfm_monitor] Error checking Last.fm: {e}", flush=True)
        return False, None

def get_current_command():
    """Get the currently running command."""
    try:
        response = requests.get(f"{API_URL}/status", timeout=5)
        if response.ok:
            data = response.json()
            return data.get("current_command", {}).get("command_name")
    except Exception as e:
        print(f"[lastfm_monitor] Error getting status: {e}", flush=True)
    return None

def switch_to_lastfm():
    """Switch to the lastfm command."""
    try:
        # Use a long duration so it stays on while music plays
        response = requests.post(f"{API_URL}/command/lastfm?duration=3600", timeout=5)
        if response.ok:
            print("[lastfm_monitor] Switched to lastfm", flush=True)
            return True
    except Exception as e:
        print(f"[lastfm_monitor] Error switching to lastfm: {e}", flush=True)
    return False

def resume_schedule():
    """Resume normal schedule."""
    try:
        response = requests.post(f"{API_URL}/schedule/resume", timeout=5)
        if response.ok:
            print("[lastfm_monitor] Resumed schedule", flush=True)
            return True
    except Exception as e:
        print(f"[lastfm_monitor] Error resuming schedule: {e}", flush=True)
    return False

def main():
    print("[lastfm_monitor] Starting Last.fm monitor...", flush=True)
    
    was_playing = False
    last_switch_time = 0
    
    while True:
        try:
            is_playing, track_info = get_now_playing()
            current_cmd = get_current_command()
            
            if is_playing:
                if not was_playing:
                    print(f"[lastfm_monitor] Music started: {track_info}", flush=True)
                
                # If music is playing and we're not on lastfm, switch to it
                # But don't spam - wait at least 10 seconds between switches
                if current_cmd != "lastfm" and (time.time() - last_switch_time) > 10:
                    switch_to_lastfm()
                    last_switch_time = time.time()
                
                was_playing = True
            else:
                if was_playing:
                    print("[lastfm_monitor] Music stopped", flush=True)
                    # Music stopped - let the lastfm command's own timeout handle it
                    # or resume schedule if we want immediate switch
                    # resume_schedule()  # Uncomment if you want immediate switch back
                
                was_playing = False
            
        except Exception as e:
            print(f"[lastfm_monitor] Error in main loop: {e}", flush=True)
        
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
