import logging
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

# Fallback island/region mapping based on lat/lon grid
# Mencakup seluruh Indonesia bounding box (95,-11) hingga (141,6) tanpa gap
INDONESIA_REGIONS = [
    {"name": "Sumatra",           "lat_min": -8.0, "lat_max": 7.0, "lon_min": 95.0,  "lon_max": 108.0},
    {"name": "Kep. Riau",         "lat_min": -2.0, "lat_max": 7.0, "lon_min": 103.0, "lon_max": 111.0},
    {"name": "Kalimantan",        "lat_min": -5.0, "lat_max": 7.0, "lon_min": 108.0, "lon_max": 120.0},
    {"name": "Jawa",              "lat_min": -9.0, "lat_max": -5.0,"lon_min": 105.0, "lon_max": 116.0},
    {"name": "Bali & Nusa Tenggara","lat_min": -11.0,"lat_max": -7.0,"lon_min": 114.0, "lon_max": 126.0},
    {"name": "Sulawesi",          "lat_min": -8.0, "lat_max": 7.0, "lon_min": 118.0, "lon_max": 127.0},
    {"name": "Maluku",            "lat_min": -10.0,"lat_max": 7.0, "lon_min": 124.0, "lon_max": 135.0},
    {"name": "Papua Barat",       "lat_min": -5.0, "lat_max": 1.0, "lon_min": 130.0, "lon_max": 138.0},
    {"name": "Papua",             "lat_min": -12.0,"lat_max": 0.0, "lon_min": 135.0, "lon_max": 141.0},
]


def _grid_region(lat: float, lon: float) -> str:
    for reg in INDONESIA_REGIONS:
        if reg["lat_min"] <= lat <= reg["lat_max"] and reg["lon_min"] <= lon <= reg["lon_max"]:
            return reg["name"]
    return "Unknown"


class GeoResolver:
    def __init__(self, shapefile_path: Optional[Path] = None):
        self.shapefile_path = shapefile_path
        self._gdf = None
        self._sindex = None
        self._is_admin0 = False

    def _normalize_columns(self):
        cols = list(self._gdf.columns)
        col_lower = {c: c for c in cols}
        pref_name = ["name", "name_1", "province", "gn_name"]
        pref_code = ["iso_3166_2", "adm1_code", "code_hasc"]
        pref_admin = ["admin", "adm0_a3", "iso_a3", "sov_a3"]
        self._name_col = next((col_lower[c] for c in pref_name if c in col_lower), None)
        self._code_col = next((col_lower[c] for c in pref_code if c in col_lower), None)
        self._admin_col = next((col_lower[c] for c in pref_admin if c in col_lower), None)
        self._region_col = next((c for c in cols if c.lower() in ("region", "type_en")), None)

    def _detect_level(self):
        cols_lower = {c.lower() for c in self._gdf.columns}
        has_admin1 = bool(self._name_col) and bool(self._code_col)
        has_admin0 = "adm0_a3" in cols_lower or "iso_a3" in cols_lower
        self._is_admin0 = has_admin0 and not has_admin1

    def _load_if_needed(self):
        if self._gdf is not None:
            return
        if not self.shapefile_path or not self.shapefile_path.exists():
            logger.info("No shapefile found — using grid-based region fallback")
            return
        try:
            import geopandas as gpd
            self._gdf = gpd.read_file(self.shapefile_path)
            self._normalize_columns()
            self._detect_level()
            self._sindex = self._gdf.sindex
            logger.info("Loaded shapefile: %d features from %s (admin%d), name_col=%s, code_col=%s",
                        len(self._gdf), self.shapefile_path,
                        0 if self._is_admin0 else 1,
                        self._name_col, self._code_col)
        except Exception as e:
            logger.error("Failed to load shapefile: %s", e)

    def resolve(self, latitude: float, longitude: float) -> dict:
        self._load_if_needed()
        result = {
            "province_name": None,
            "province_code": None,
            "island": _grid_region(latitude, longitude),
        }

        if self._gdf is None:
            result["province_name"] = result["island"] if result["island"] != "Unknown" else None
            return result

        from shapely import Point
        point = Point(longitude, latitude)
        possible_matches = list(self._sindex.intersection(point.bounds))
        for idx in possible_matches:
            row = self._gdf.iloc[idx]
            if row.geometry.contains(point):
                if self._is_admin0:
                    result["province_name"] = _grid_region(latitude, longitude)
                    result["province_code"] = str(row.get(self._admin_col, "")) if self._admin_col else None
                else:
                    result["province_name"] = row.get(self._name_col) if self._name_col else None
                    result["province_code"] = str(row.get(self._code_col, "")) if self._code_col else None
                break
        else:
            result["province_name"] = result["island"] if result["island"] != "Unknown" else None

        return result

    def resolve_batch(self, df: pd.DataFrame, lat_col: str = "latitude", lon_col: str = "longitude") -> pd.DataFrame:
        df = df.copy()
        fallback_regions = df.apply(lambda r: _grid_region(r[lat_col], r[lon_col]), axis=1)
        df["island"] = fallback_regions

        self._load_if_needed()
        if self._gdf is None:
            df["province_name"] = df["island"].where(df["island"] != "Unknown", None)
            df["province_code"] = None
            return df

        try:
            import geopandas as gpd
            points = gpd.GeoDataFrame(
                df,
                geometry=gpd.points_from_xy(df[lon_col], df[lat_col]),
                crs=self._gdf.crs,
            )
            joined = gpd.sjoin(points, self._gdf, how="left", predicate="within")

            if self._is_admin0:
                df["province_name"] = fallback_regions
                df["province_code"] = joined.get(self._admin_col) if self._admin_col else None
            else:
                df["province_name"] = joined[self._name_col].fillna(fallback_regions) if self._name_col else fallback_regions
                df["province_code"] = joined[self._code_col] if self._code_col else None

        except Exception as e:
            logger.error("Batch reverse geocode failed: %s", e)
            df["province_name"] = fallback_regions
            df["province_code"] = None

        return df

    def is_ready(self) -> bool:
        self._load_if_needed()
        return self._gdf is not None
