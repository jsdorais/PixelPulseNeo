import requests
from datetime import datetime, timedelta
import json
import xml.etree.ElementTree as ET
from Matrix import config

# Base API URL for NOAA Tides and Currents API
BASE_API_URL = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"

# Defines the height of the sinusoidal curve for plotting tide data
SINUS_HEIGHT: float = 40.0

# Function to construct the API URL with customizable parameters
def get_api_url(
    date: str = "today",  # Date for data retrieval (default: today)
    product: str = "predictions",  # Type of data (e.g., tide predictions)
    station: str = config.TIDES_STATION,  # NOAA station ID (acquired from config.py)
    format: str = "json",  # Response format (e.g., JSON)
    application: str = "LED_Matrix",  # Application name for API usage
    units: str = "english",  # Measurement units (e.g., English or metric)
    time_zone: str = "lst_ldt",  # Time zone (local standard or daylight time)
    datum: str = "MLLW",  # Datum (e.g., Mean Lower Low Water)
    interval: str | None = None  # Optional interval for data (e.g., high/low tides)
) -> str:
    """
    Constructs the URL for accessing the NOAA API.
    Documentation: https://tidesandcurrents.noaa.gov/api/
    """
    # Base URL with required parameters
    url: str = f"{BASE_API_URL}?date={date}&station={station}&product={product}&format={format}&units={units}&application={application}&time_zone={time_zone}&datum={datum}"

    # Append interval if specified
    if interval is not None:
        url = f"{url}&interval={interval}"

    return url

# Function to call the NOAA API and return data
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
    """
    Makes a GET request to the NOAA API and retrieves the response.
    """
    # Get the API URL
    url: str = get_api_url(date=date, product=product, station=station, format=format, application=application, units=units, time_zone=time_zone, datum=datum, interval=interval)
    try:
        print(f"call {url}")  # Log the URL being called
        response: requests.Response = requests.get(url, timeout=15)  # Perform the API request
        if response.status_code == 200:  # Check if the request was successful
            return response.json()  # Return JSON data
        else:
            print(response)  # Print response details for debugging
            print(response.json())  # Print error message if available
    except Exception as e:
        # Handle connection errors or API failures
        print(f"Unable to get tides info, {e}")
    return {}  # Return an empty dictionary in case of failure

# Function to retrieve the station name
def get_station_name():
    """
    Fetches the station name from NOAA's metadata API (product="wind").
    """
    url: str = get_api_url(product="wind", format="xml")  # Request station metadata in XML format
    try:
        print(f"call {url}")  # Log the URL being called
        response: requests.Response = requests.get(url, timeout=15)  # Perform the API request
        if response.status_code == 200:  # Check if the request was successful
            root = ET.fromstring(response.text)  # Parse the XML response
            meta: ET.Element | None = root.find("metadata")  # Find the metadata tag
            station_name = meta.get("name")  # Extract the station name attribute
            return station_name
        else:
            return None  # Return None if the request failed
    except Exception as e:
        print(f"Unable to get station info, {e}")  # Log any errors
    return None

# Function to process tide data and prepare it for plotting
def get_tide_data_for_plot(w=5):
    """
    Processes tide predictions into a format suitable for plotting on an LED matrix.
    """
    raw_data = call_api()["predictions"]  # Fetch tide predictions from the API
    min_v: float = 0  # Initialize minimum tide value
    max_v: float = 0  # Initialize maximum tide value
    data = []  # List to hold processed tide data

    # Process raw data to extract time and tide values
    for entry in raw_data:
        t: str = entry["t"].split(" ")[-1]  # Extract the time (HH:MM) from the timestamp
        v: float = float(entry["v"])  # Convert the tide height to a float
        if v > max_v:
            max_v = v  # Update maximum tide height
        if v < min_v:
            min_v = v  # Update minimum tide height
        data.append((t, v))  # Append the time and tide value as a tuple

    # Calculate scaling factors for plotting
    delta_v: float = int(SINUS_HEIGHT / (max_v - min_v))  # Vertical scaling factor
    delta_t: float = w * 64.0 / len(data)  # Horizontal scaling factor

    print(f"delta_t={delta_t}")  # Debugging: Print horizontal scaling factor
    print(f"delta_v={delta_v}")  # Debugging: Print vertical scaling factor
    Y_offset: int = int((64 - SINUS_HEIGHT) / 2)  # Offset for centering the curve vertically

    curve: list[tuple[int, int]] = []  # List to hold curve points (x, y)
    timeline: list[str] = []  # List to hold timeline labels

    # Generate curve points and timeline labels
    for idx, entry in enumerate(data):
        x: int = int(idx * delta_t)  # Calculate x-coordinate
        y: int = Y_offset + int(delta_v * (entry[1] - min_v))  # Calculate y-coordinate
        curve.append((x, y))  # Add the (x, y) point to the curve
        timeline.append(entry[0])  # Add the time to the timeline

    # Return processed data
    return {"curve": curve, "timeline": timeline, "delta_v": delta_v, "delta_t": delta_t, "Y_offset": Y_offset, "min_v": min_v}

# Function to find the x-coordinate for a given time
def find_x(curve, timeline, target_time):
    """
    Finds the x-coordinate of the given time on the tide curve.
    """
    print(f"Calling find_x with target_time={target_time}")  # Log the target time
    if isinstance(target_time, str):
        target_time = datetime.strptime(target_time, "%H:%M")  # Parse time string to a datetime object

    # Iterate over the timeline to find the target time interval
    for idx, d in enumerate(timeline):
        t1 = datetime.strptime(d, "%H:%M")  # Convert timeline entry to datetime
        if t1 > target_time:  # Check if the current time exceeds the target
            t0 = datetime.strptime(timeline[idx - 1], "%H:%M")  # Get the previous time
            interval_delta = t1 - t0  # Calculate the time interval
            interval_delta_s = interval_delta.total_seconds()  # Interval in seconds
            t_delta = target_time - t0  # Calculate elapsed time from t0
            t_delta_s = t_delta.total_seconds()  # Elapsed time in seconds
            ratio = t_delta_s / interval_delta_s  # Ratio of elapsed time in the interval
            x0 = curve[idx - 1][0]  # Start x-coordinate
            x1 = curve[idx][0]  # End x-coordinate
            x = int(x0 + (x1 - x0) * ratio)  # Interpolate x-coordinate
            return x

    return None  # Return None if no matching interval is found

# Function to get complete tide data for plotting
def get_tide_data(w=5):
    """
    Retrieves tide data, including curve, high/low tide points, and current time.
    """
    station_name: str | None = get_station_name()  # Fetch the station name
    result = get_tide_data_for_plot()  # Process tide data for plotting

    Y_offset: int = result["Y_offset"]  # Get vertical offset
    min_v: float = result["min_v"]  # Get minimum tide value
    delta_v: float = result["delta_v"]  # Get vertical scaling factor
    hilo_raw = call_api(interval="hilo")["predictions"]  # Fetch high/low tide data
    curve = result["curve"]  # Get tide curve points
    timeline = result["timeline"]  # Get timeline labels

    hilo = []  # List to store high/low tide data
    for entry in hilo_raw:
        t = entry["t"]  # Time of high/low tide
        v = float(entry["v"])  # Tide height
        type = entry["type"]  # Type ("H" for high, "L" for low)
        y: int = Y_offset + int(delta_v * (v - min_v))  # Calculate y-coordinate
        t = t.split(" ")[-1]  # Extract time (HH:MM)
        x = find_x(curve, timeline, target_time=t)  # Find x-coordinate
        hilo.append({"t": t, "v": v, "y": y, "type": type, "x": x})  # Add to list

    x_now = find_x(curve, timeline, target_time=datetime.now().strftime("%H:%M"))  # Find x for the current time

    # Return all tide data
    return {
        "name": station_name,
        "curve": curve,
        "timeline": timeline,
        "hilo": hilo,
        "x_now": x_now
    }

# Main script entry point
if __name__ == "__main__":
    print(get_tide_data())  # Print the processed tide data