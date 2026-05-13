import logging
from io import StringIO

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

MODIS_COLS = [
    "latitude", "longitude", "brightness", "scan", "track",
    "acq_date", "acq_time", "satellite", "confidence", "version",
    "bright_t31", "frp", "daynight",
]

VIIRS_COLS = [
    "latitude", "longitude", "brightness_t13", "scan", "track",
    "acq_date", "acq_time", "satellite", "confidence", "version",
    "bright_t14", "bright_t15", "frp", "daynight",
]

UNIFIED_COLS = [
    "latitude", "longitude", "acq_date", "acq_time", "satellite",
    "confidence", "version", "frp", "daynight", "scan", "track",
    "brightness", "brightness_t13", "brightness_t31",
    "bright_t14", "bright_t15",
    "source_api", "sensor_type", "satellite_source",
]


def transform_firms(csv_text: str, source_name: str) -> pd.DataFrame:
    if not csv_text or not csv_text.strip():
        return pd.DataFrame()

    try:
        df = pd.read_csv(StringIO(csv_text))
    except Exception as e:
        logger.error("CSV parse failed for %s: %s", source_name, e)
        return pd.DataFrame()

    if df.empty:
        return pd.DataFrame()

    is_modis = "modis" in source_name.lower()
    expected = MODIS_COLS if is_modis else VIIRS_COLS

    for col in expected:
        if col not in df.columns:
            df[col] = np.nan

    df = df[[c for c in expected if c in df.columns]].copy()

    mask = (
        df["latitude"].between(-11.0, 6.0)
        & df["longitude"].between(95.0, 141.0)
    )
    df = df[mask].copy()

    df["acq_date"] = pd.to_datetime(df["acq_date"], errors="coerce")

    tm = df["acq_time"].astype(str).str.zfill(4)
    hours = tm.str[:2].astype(int)
    minutes = tm.str[2:4].astype(int)
    df["acq_datetime"] = df["acq_date"] + pd.to_timedelta(hours, unit="h") + pd.to_timedelta(minutes, unit="m")

    df["source_api"] = "firms"
    df["sensor_type"] = "MODIS" if is_modis else "VIIRS"
    df["satellite_source"] = source_name

    for c in UNIFIED_COLS:
        if c not in df.columns:
            df[c] = np.nan

    logger.info("Transformed %d records from %s", len(df), source_name)
    return df[UNIFIED_COLS]
