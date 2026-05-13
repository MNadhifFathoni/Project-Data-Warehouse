import pandas as pd
import pytest

from staging.transform.usgs_transformer import transform_usgs, OUTPUT_COLS
from tests.conftest import SAMPLE_EQ_GEOJSON


class TestTransformUSGS:
    def test_empty_input_returns_empty_df(self):
        assert transform_usgs({}).empty
        assert transform_usgs({"features": []}).empty
        assert transform_usgs(None).empty

    def test_missing_geojson_keys_handled_gracefully(self):
        result = transform_usgs({"features": [{"properties": None, "geometry": None}]})
        assert not result.empty

    def test_transform_returns_expected_columns(self):
        df = transform_usgs(SAMPLE_EQ_GEOJSON)
        assert len(df) == 2
        assert df.iloc[0]["event_id"] == "us7000rr5p"
        assert df.iloc[0]["mag"] == 4.5
        assert df.iloc[0]["mag_type"] == "mb"
        assert df.iloc[0]["source_api"] == "usgs"

    def test_output_has_all_required_columns(self):
        df = transform_usgs(SAMPLE_EQ_GEOJSON)
        for col in OUTPUT_COLS:
            assert col in df.columns, f"Missing column: {col}"

    def test_coordinates_parsed_correctly(self):
        df = transform_usgs(SAMPLE_EQ_GEOJSON)
        row = df[df["event_id"] == "us7000rr5p"].iloc[0]
        assert row["longitude"] == 128.8654
        assert row["latitude"] == 3.0448
        assert row["depth"] == 10.0

    def test_outside_bbox_is_filtered(self):
        data = {
            "features": [
                {
                    "type": "Feature",
                    "id": "test1",
                    "properties": {"mag": 5.0, "place": "Far away", "time": 0, "type": "earthquake"},
                    "geometry": {"type": "Point", "coordinates": [200.0, 50.0, 10.0]},
                }
            ]
        }
        df = transform_usgs(data)
        assert df.empty

    def test_time_iso_is_parsed(self):
        df = transform_usgs(SAMPLE_EQ_GEOJSON)
        row = df[df["event_id"] == "us7000rr5p"].iloc[0]
        assert row["time_epoch"] == 1767134169826
        assert row["time_iso"] is not None
        assert "2025-12-30" in row["time_iso"]

    def test_title_and_place_are_present(self):
        df = transform_usgs(SAMPLE_EQ_GEOJSON)
        row = df.iloc[0]
        assert row["place"] is not None
        assert row["title"] is not None
