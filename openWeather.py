#! python3
# openWeather.py gets the latest weather info from OpenWeather and saves it to current_weather.json
# Date: 20250106

import os, json, requests, pathlib, logging
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from requests.exceptions import RequestException

load_dotenv()
# Configuration for standard output logging
logging.basicConfig(filename='log.txt', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
# logging.disable(logging.DEBUG)

# Configuration
OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY')
RAW_LOC = os.getenv('CAMERA_LOC', '0,0')
# Parse "lat,lon" string from .env into a tuple of floats
CAM_LOC = tuple(float(x.strip()) for x in RAW_LOC.split(','))
ARCHIVE_DIR = pathlib.Path(os.getenv("ARCHIVE_DIR") or "./archive")
BASE_DIR = pathlib.Path(__file__).parent.resolve()
LOG_FILE = ARCHIVE_DIR / "detectionResults.txt"
CACHE_FILE = BASE_DIR / "current_weather.json"
# CACHE_FILE = 'current_weather.json'

def get_cached_weather(filename: str) -> dict:
    """Reads the local JSON file and checks if it's less than 10 minutes old."""
    if not os.path.exists(filename):
        return None

    try:
        with open(filename, 'r') as f:
            cached_data = json.load(f)
        
        # Parse the ISO timestamp back into a datetime object
        last_call_time = datetime.fromisoformat(cached_data['timestamp_utc'])
        now = datetime.now(timezone.utc)
        
        # Calculate age
        age = now - last_call_time
        
        if age < timedelta(minutes=10):
            logging.debug(f"--- OpenWeather: using cached data ({age.total_seconds() / 60:.1f} mins old) ---")
            return cached_data
            
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        logging.error(f"OpenWeather: cache read error: {e}")
    
    return None

def fetch_weather_by_coords(coords: tuple, api_key: str) -> dict:
    """Fetches fresh data from OpenWeather API."""
    lat, lon = coords
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {'lat': lat, 'lon': lon, 'appid': api_key, 'units': 'metric'}
    
    try:
        logging.debug("--- OpenWeather: fetching fresh data from OpenWeather API ---")
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except RequestException as e:
        logging.error(f"OpenWeather: network error: {e}")
        return None

def save_weather_data(data: dict, filename: str):
    """Parses and saves fresh API data to the cache file."""
    # If data is already parsed (from cache), we don't need to re-parse
    if 'timestamp_utc' in data:
        return data

    weather_info = {
        'timestamp_utc': datetime.now(timezone.utc).isoformat(),
        'location_name': data.get('name', 'Unknown'),
        'temperature_c': data['main']['temp'],
        'humidity_percent': data['main']['humidity'],
        'description': data['weather'][0]['description']
    }
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(weather_info, f, indent=4)
    
    return weather_info

def currentWeather():
    # 1. Try to get data from cache first
    weather_data = get_cached_weather(CACHE_FILE)
    
    # 2. If no cache or cache expired, call the API
    if not weather_data:
        raw_api_response = fetch_weather_by_coords(CAM_LOC, OPENWEATHER_API_KEY)
        if raw_api_response:
            weather_data = save_weather_data(raw_api_response, CACHE_FILE)
    
    # 3. Final Output
    if weather_data:
        logging.debug(weather_data)
        return weather_data
    else:
        logging.error("OpenWeather: Failed to retrieve weather data.")
        return None

""" Example use of currentWeather() function
if __name__ == "__main__":
    data = currentWeather()
    message = (f"It is now {data['description']} at {data['location_name']}. The temp is {data['temperature_c']}c and humidity is {data['humidity_percent']}%.")
    print(message)
"""
