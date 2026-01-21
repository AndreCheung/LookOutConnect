#! python3
# openWeather.py | 2026-01-21 | Modular Version
# Purpose: Fetch and cache weather data from OpenWeather API

import os, json, requests, pathlib, logging
from datetime import datetime, timezone, timedelta

# Local directory setup for cache storage
BASE_DIR = pathlib.Path(__file__).parent.resolve()
CACHE_FILE = BASE_DIR / "current_weather.json"

def get_cached_weather(filename):
    """Checks if local weather cache exists and is fresh (under 10 mins)."""
    if not os.path.exists(filename):
        return None

    try:
        with open(filename, 'r') as f:
            cached_data = json.load(f)
        
        # Verify age of cached data
        last_call = datetime.fromisoformat(cached_data['timestamp_utc'])
        now = datetime.now(timezone.utc)
        
        if (now - last_call) < timedelta(minutes=10):
            logging.debug(f"OpenWeather: Using cached data.")
            return cached_data
            
    except Exception as e:
        logging.error(f"OpenWeather: Cache error: {e}")
    
    return None

def fetch_and_save(coords, api_key, filename):
    """Calls OpenWeather API and updates the local cache file."""
    lat, lon = coords
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {'lat': lat, 'lon': lon, 'appid': api_key, 'units': 'metric'}
    
    try:
        logging.debug("OpenWeather: Fetching fresh API data.")
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        # Extract only relevant fields for the wildfire system
        weather_info = {
            'timestamp_utc': datetime.now(timezone.utc).isoformat(),
            'location_name': data.get('name', 'Unknown'),
            'temperature_c': data['main']['temp'],
            'humidity_percent': data['main']['humidity'],
            'description': data['weather'][0]['description']
        }
        
        # Write to local cache
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(weather_info, f, indent=4)
        
        return weather_info

    except Exception as e:
        logging.error(f"OpenWeather: API failure: {e}")
        return None

def get_current_weather(coords, api_key):
    """
    Primary Entry Point: Returns weather dictionary.
    Arguments: coords (tuple of floats), api_key (string)
    """
    if not api_key:
        logging.warning("OpenWeather: API Key missing.")
        return None

    # 1. Try Cache
    weather_data = get_cached_weather(CACHE_FILE)
    
    # 2. If no cache, fetch fresh
    if not weather_data:
        weather_data = fetch_and_save(coords, api_key, CACHE_FILE)
    
    return weather_data
