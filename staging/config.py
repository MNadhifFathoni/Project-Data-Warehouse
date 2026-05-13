import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# FIRMS API
FIRMS_MAP_KEY = os.getenv("FIRMS_MAP_KEY", "")
FIRMS_BASE_URL = "https://firms.modaps.eosdis.nasa.gov"
FIRMS_AREA_ENDPOINT = "/api/area/csv"

# Indonesia bounding box (west, south, east, north)
INDONESIA_BBOX_STR = "95.0,-11.0,141.0,6.0"
INDONESIA_BBOX = {"west": 95.0, "south": -11.0, "east": 141.0, "north": 6.0}

# FIRMS sources available for this project
# max_day_range: API limit is 5 days per request for all sources
# min_date: data availability start (NOAA-21 mulai 17 Jan 2024)
FIRMS_SOURCES = {
    "MODIS_SP":         {"sensor": "MODIS", "type": "SP",  "max_day_range": 5, "min_date": "2000-11-01"},
    "VIIRS_SNPP_SP":    {"sensor": "VIIRS", "type": "SP",  "max_day_range": 5, "min_date": "2012-01-20"},
    "VIIRS_NOAA20_SP":  {"sensor": "VIIRS", "type": "SP",  "max_day_range": 5, "min_date": "2020-01-01"},
    "VIIRS_NOAA21_NRT": {"sensor": "VIIRS", "type": "NRT", "max_day_range": 5, "min_date": "2024-01-17"},
}

# USGS Earthquake API
USGS_BASE_URL = "https://earthquake.usgs.gov"
USGS_QUERY_ENDPOINT = "/fdsnws/event/1/query"

# Staging output directories
STAGING_DIR = PROJECT_ROOT / "data" / "staging"
FIRE_STAGING_DIR = STAGING_DIR / "fire_hotspots"
EARTHQUAKE_STAGING_DIR = STAGING_DIR / "earthquakes"
