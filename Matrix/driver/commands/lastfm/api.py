#!/usr/bin/env python3
"""Last.fm API client for Now Playing functionality."""

import os
import requests

API_URL = "https://ws.audioscrobbler.com/2.0/"

# Load from environment (set in secrets.conf or init_env.sh)
LASTFM_API_KEY = os.getenv("LASTFM_API_KEY")
LASTFM_USERNAME = os.getenv("LASTFM_USERNAME")


def get_recent_tracks(username: str = None, api_key: str = None, limit: int = 2):
    """Fetch recent tracks from Last.fm."""
    username = username or LASTFM_USERNAME
    api_key = api_key or LASTFM_API_KEY
    
    if not username or not api_key:
        print("❌ LASTFM_API_KEY or LASTFM_USERNAME not set!")
        return []
    
    params = {
        "method": "user.getRecentTracks",
        "user": username,
        "api_key": api_key,
        "limit": limit,
        "format": "json",
    }
    
    try:
        resp = requests.get(API_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        tracks = data.get("recenttracks", {}).get("track")
        if not tracks:
            return []
        
        # Always normalize to a list
        if isinstance(tracks, dict):
            return [tracks]
        return tracks
    except Exception as e:
        print(f"❌ Last.fm API error: {e}")
        return []


def get_user_playcount(artist: str, track: str, api_key: str = None, username: str = None):
    """Get user's play count for a specific track."""
    username = username or LASTFM_USERNAME
    api_key = api_key or LASTFM_API_KEY
    
    params = {
        "method": "track.getInfo",
        "api_key": api_key,
        "artist": artist,
        "track": track,
        "username": username,
        "format": "json"
    }
    
    try:
        resp = requests.get(API_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return data.get("track", {}).get("userplaycount")
    except Exception as e:
        print(f"❌ Playcount error: {e}")
        return None


def extract_track_info(track_obj):
    """Convert Last.fm track object into a clean dict."""
    return {
        "track": track_obj.get("name"),
        "artist": track_obj.get("artist", {}).get("#text"),
        "album": track_obj.get("album", {}).get("#text"),
        "now_playing": track_obj.get("@attr", {}).get("nowplaying") == "true",
        "image_url": extract_largest_image(track_obj.get("image", []))
    }


def extract_largest_image(images):
    """Pull largest album art URL."""
    if not images:
        return None
    for img in reversed(images):
        if img.get("#text"):
            return img["#text"]
    return None


def get_now_playing():
    """Main function to get current/recent track info."""
    recent_tracks = get_recent_tracks(limit=2)
    
    if not recent_tracks:
        return None
    
    current = extract_track_info(recent_tracks[0])
    
    # Get playcount
    if current["artist"] and current["track"]:
        current["playcount"] = get_user_playcount(current["artist"], current["track"])
    else:
        current["playcount"] = None
    
    # Get previous track if available
    if len(recent_tracks) > 1:
        current["previous"] = extract_track_info(recent_tracks[1])
    else:
        current["previous"] = None
    
    return current
