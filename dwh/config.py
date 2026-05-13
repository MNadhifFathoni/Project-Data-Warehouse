from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DWH_DIR = PROJECT_ROOT / "data" / "dwh"
DWH_PATH = DWH_DIR / "disaster.duckdb"

STAGING_FIRE_DIR = PROJECT_ROOT / "data" / "staging" / "fire_hotspots"
STAGING_EQ_DIR = PROJECT_ROOT / "data" / "staging" / "earthquakes"

SHAPEFILE_DIR = PROJECT_ROOT / "data" / "shapefile"
SHAPEFILE_PATH = SHAPEFILE_DIR / "indonesia_provinces.shp"

MART_DIR = PROJECT_ROOT / "data" / "mart"

DWH_SCHEMA = "dwh"
MART_SCHEMA = "mart"

SATELLITE_SOURCES = {
    "MODIS_SP":         {"sensor": "MODIS", "satellite": "Terra"},
    "VIIRS_SNPP_SP":    {"sensor": "VIIRS", "satellite": "SNPP"},
    "VIIRS_NOAA20_SP":  {"sensor": "VIIRS", "satellite": "NOAA20"},
    "VIIRS_NOAA21_NRT": {"sensor": "VIIRS", "satellite": "NOAA21"},
}
