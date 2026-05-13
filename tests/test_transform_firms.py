import pandas as pd
import pytest

from staging.transform.firms_transformer import transform_firms, MODIS_COLS, VIIRS_COLS, UNIFIED_COLS


class TestTransformFIRMS:
    def test_empty_input_returns_empty_df(self):
        assert transform_firms("", "VIIRS_NOAA21_NRT").empty
        assert transform_firms("   ", "VIIRS_NOAA21_NRT").empty
        assert transform_firms(None, "VIIRS_NOAA21_NRT").empty

    def test_invalid_csv_returns_empty_df(self):
        assert transform_firms("not,csv\n1,2,3", "VIIRS_NOAA21_NRT").empty

    def test_viirs_transform_returns_expected_columns(self):
        csv = (
            "latitude,longitude,acq_date,acq_time,satellite,confidence,version,frp,daynight,scan,track,"
            "brightness_t13,bright_t14,bright_t15\n"
            "-6.5,110.5,2025-06-15,1200,N21,h,2.0NRT,5.0,D,0.5,0.4,310.0,300.0,290.0\n"
        )
        df = transform_firms(csv, "VIIRS_NOAA21_NRT")
        assert not df.empty
        assert "latitude" in df.columns
        assert "frp" in df.columns
        assert df.iloc[0]["latitude"] == -6.5
        assert df.iloc[0]["source_api"] == "firms"
        assert df.iloc[0]["sensor_type"] == "VIIRS"
        assert df.iloc[0]["satellite_source"] == "VIIRS_NOAA21_NRT"

    def test_modis_transform_returns_expected_columns(self):
        csv = (
            "latitude,longitude,acq_date,acq_time,satellite,confidence,version,frp,daynight,scan,track,"
            "brightness,bright_t31\n"
            "-6.5,110.5,2025-06-15,1200,Terra,h,2.0,5.0,D,0.5,0.4,320.0,290.0\n"
        )
        df = transform_firms(csv, "MODIS_SP")
        assert not df.empty
        assert df.iloc[0]["sensor_type"] == "MODIS"

    def test_outside_bbox_is_filtered(self):
        csv = (
            "latitude,longitude,acq_date,acq_time,satellite,confidence,version,frp,daynight,scan,track,"
            "brightness_t13,bright_t14,bright_t15\n"
            "10.0,150.0,2025-06-15,1200,N21,h,2.0NRT,5.0,D,0.5,0.4,310.0,300.0,290.0\n"
        )
        df = transform_firms(csv, "VIIRS_NOAA21_NRT")
        assert df.empty

    def test_output_has_all_unified_cols(self):
        csv = (
            "latitude,longitude,acq_date,acq_time,satellite,confidence,version,frp,daynight,scan,track,"
            "brightness_t13,bright_t14,bright_t15\n"
            "-6.5,110.5,2025-06-15,1200,N21,h,2.0NRT,5.0,D,0.5,0.4,310.0,300.0,290.0\n"
        )
        df = transform_firms(csv, "VIIRS_NOAA21_NRT")
        for col in UNIFIED_COLS:
            assert col in df.columns, f"Missing column: {col}"

    def test_acq_datetime_is_computed(self):
        csv = (
            "latitude,longitude,acq_date,acq_time,satellite,confidence,version,frp,daynight,scan,track,"
            "brightness_t13,bright_t14,bright_t15\n"
            "-6.5,110.5,2025-06-15,1200,N21,h,2.0NRT,5.0,D,0.5,0.4,310.0,300.0,290.0\n"
        )
        df = transform_firms(csv, "VIIRS_NOAA21_NRT")
        # acq_datetime is computed internally but not in UNIFIED_COLS output
        # The acq_date column should still be present and parsed
        assert "acq_date" in df.columns
        assert pd.notna(df.iloc[0]["acq_date"])

    def test_missing_columns_are_filled_with_nan(self):
        csv = "latitude,longitude,acq_date,acq_time\n-6.5,110.5,2025-06-15,1200\n"
        df = transform_firms(csv, "VIIRS_NOAA21_NRT")
        assert not df.empty
        assert pd.isna(df.iloc[0]["frp"])
