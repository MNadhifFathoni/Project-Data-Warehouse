import logging
from datetime import datetime, timezone

import pandas as pd

logger = logging.getLogger(__name__)

OUTPUT_COLS = [
    "source_api", "event_id", "mag", "mag_type", "place",
    "time_epoch", "time_iso", "updated_iso", "url",
    "felt", "cdi", "mmi", "alert", "status", "tsunami",
    "sig", "net", "code", "nst", "dmin", "rms", "gap",
    "event_type", "geometry_type",
    "longitude", "latitude", "depth", "title",
]


def _epoch_to_iso(ms: int) -> str | None:
    if ms is None:
        return None
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat()


def transform_usgs(
    geojson: dict,
    minlat: float = -11.0,
    maxlat: float = 6.0,
    minlon: float = 95.0,
    maxlon: float = 141.0,
) -> pd.DataFrame:
    if not geojson or "features" not in geojson:
        return pd.DataFrame()

    records = []
    for feat in geojson["features"]:
        props = feat.get("properties", {}) or {}
        geom = feat.get("geometry") or {}
        coords = geom.get("coordinates") or [None, None, None]
        lon, lat, depth = coords[0], coords[1], coords[2] if len(coords) >= 3 else None

        if lat is not None and lon is not None:
            if not (minlat <= lat <= maxlat and minlon <= lon <= maxlon):
                continue

        records.append({
            "source_api": "usgs",
            "event_id": feat.get("id"),
            "mag": props.get("mag"),
            "mag_type": props.get("magType"),
            "place": props.get("place"),
            "time_epoch": props.get("time"),
            "time_iso": _epoch_to_iso(props.get("time")),
            "updated_iso": _epoch_to_iso(props.get("updated")),
            "url": props.get("url"),
            "felt": props.get("felt"),
            "cdi": props.get("cdi"),
            "mmi": props.get("mmi"),
            "alert": props.get("alert"),
            "status": props.get("status"),
            "tsunami": props.get("tsunami"),
            "sig": props.get("sig"),
            "net": props.get("net"),
            "code": props.get("code"),
            "nst": props.get("nst"),
            "dmin": props.get("dmin"),
            "rms": props.get("rms"),
            "gap": props.get("gap"),
            "event_type": props.get("type"),
            "geometry_type": geom.get("type") if geom else None,
            "longitude": lon,
            "latitude": lat,
            "depth": depth,
            "title": props.get("title"),
        })

    df = pd.DataFrame(records, columns=OUTPUT_COLS)
    logger.info("Transformed %d USGS records", len(df))
    return df
