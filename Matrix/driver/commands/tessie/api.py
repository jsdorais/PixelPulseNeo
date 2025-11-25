import requests
import json
from datetime import datetime

# Tessie API base URL
BASE_API_URL = "https://api.tessie.com/vehicles"

# Your personal Tessie API token (keep this secure!)
ACCESS_TOKEN = "pqlGEWaP9zdpCAJHpSV5DSj18cRP06dW"

def get_tessie_data():
    """
    Calls the Tessie API to fetch vehicle data.
    Returns the full JSON response from the Tessie API.
    """
    url = f"{BASE_API_URL}?access_token={ACCESS_TOKEN}"
    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error: {response.status_code}")
            print(response.json())
    except Exception as e:
        print(f"Unable to fetch Tessie data: {e}")
    return {}

def get_battery_level():
    """
    Extracts the battery level from the Tessie API response.
    Returns the battery percentage (integer) if available, else None.
    """
    data = get_tessie_data()
    if "results" in data and len(data["results"]) > 0:
        return data["results"][0]["last_state"]["charge_state"]["battery_level"]
    return None

if __name__ == "__main__":
    print(f"Battery Level: {get_battery_level()}%")