import pandas as pd
import pytest

from dwh.geo_utils import GeoResolver, _grid_region, INDONESIA_REGIONS


class TestGridRegion:
    def test_known_regions(self):
        cases = [
            # (lat, lon, expected_region)
            # Point clearly inside each island's core area
            (-2.0, 100.0, "Sumatra"),
            (-2.0, 117.0, "Kalimantan"),
            (-3.0, 121.0, "Sulawesi"),
            (-2.0, 130.0, "Maluku"),
            (-8.5, 118.0, "Bali & Nusa Tenggara"),
            (-7.5, 110.0, "Jawa"),
            (-4.0, 139.0, "Papua"),
        ]
        for lat, lon, expected in cases:
            result = _grid_region(lat, lon)
            assert result == expected, f"({lat}, {lon}): expected {expected}, got {result}"

    def test_unknown_region(self):
        assert _grid_region(0.0, 0.0) == "Unknown"
        assert _grid_region(90.0, 180.0) == "Unknown"

    def test_all_regions_defined(self):
        assert len(INDONESIA_REGIONS) > 0
        for reg in INDONESIA_REGIONS:
            assert "name" in reg
            assert "lat_min" in reg
            assert "lat_max" in reg
            assert "lon_min" in reg
            assert "lon_max" in reg
            assert reg["lat_min"] < reg["lat_max"]
            assert reg["lon_min"] < reg["lon_max"]

    def test_no_gaps_in_main_area(self):
        resolution = 2.0
        lats = [round(-9.0 + i * resolution, 1) for i in range(int((6.0 + 9.0) / resolution) + 1)]
        lons = [round(97.0 + i * resolution, 1) for i in range(int((139.0 - 97.0) / resolution) + 1)]
        uncovered = []
        for lat in lats:
            for lon in lons:
                if _grid_region(lat, lon) == "Unknown":
                    uncovered.append((lat, lon))
        # Allow a few edge points to be Unknown (coastal boundaries)
        assert len(uncovered) < 20, f"Too many uncovered: {uncovered[:15]}"


class TestGeoResolver:
    def test_no_shapefile_fallback(self):
        resolver = GeoResolver(shapefile_path=None)
        result = resolver.resolve(-2.0, 117.0)
        assert result["province_name"] is not None
        assert result["island"] is not None
        assert result["island"] == "Kalimantan"

    def test_unknown_coord_returns_unknown(self):
        resolver = GeoResolver(shapefile_path=None)
        result = resolver.resolve(0.0, 0.0)
        assert result["island"] == "Unknown"

    def test_batch_resolve_no_shapefile(self):
        resolver = GeoResolver(shapefile_path=None)
        df = pd.DataFrame({"latitude": [-2.0, -2.0], "longitude": [100.0, 117.0]})
        result = resolver.resolve_batch(df)
        assert "province_name" in result.columns
        assert "island" in result.columns

    def test_resolve_returns_correct_keys(self):
        resolver = GeoResolver(shapefile_path=None)
        result = resolver.resolve(-6.0, 106.0)
        assert "province_name" in result
        assert "province_code" in result
        assert "island" in result
