"""Batch script: backfill semua data 2023–2025."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

from staging.pipeline import Pipeline
from staging.config import FIRMS_MAP_KEY

if __name__ == "__main__":
    if not FIRMS_MAP_KEY or FIRMS_MAP_KEY == "your_map_key_here":
        raise RuntimeError("FIRMS_MAP_KEY not configured. Edit .env file.")

    pipe = Pipeline(map_key=FIRMS_MAP_KEY)
    pipe.run(
        start_date="2023-01-01",
        end_date="2025-12-31",
        fire_sources=["MODIS_SP", "VIIRS_SNPP_SP", "VIIRS_NOAA20_SP", "VIIRS_NOAA21_NRT"],
        include_usgs=True,
        usgs_minmag=0.0,
    )
