from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st

DWH_PATH = Path(__file__).resolve().parent.parent / "data" / "dwh" / "disaster.duckdb"


@st.cache_resource
def get_connection():
    return duckdb.connect(str(DWH_PATH), read_only=True)


def query(sql: str) -> pd.DataFrame:
    con = get_connection()
    return con.execute(sql).fetchdf()


# ---------------------------------------------------------------------------
# Reusable queries
# ---------------------------------------------------------------------------

@st.cache_data(ttl="10m")
def overview_stats():
    return query("""
        SELECT
            (SELECT COUNT(*) FROM dwh.fact_fire_hotspot)   AS total_hotspots,
            (SELECT COUNT(*) FROM dwh.fact_earthquake)     AS total_earthquakes,
            (SELECT COUNT(*) FROM dwh.dim_location)        AS total_locations,
            (SELECT ROUND(AVG(mag), 2) FROM dwh.fact_earthquake) AS avg_magnitude,
            (SELECT ROUND(AVG(frp), 2) FROM dwh.fact_fire_hotspot) AS avg_frp,
            (SELECT MAX(mag) FROM dwh.fact_earthquake)     AS max_magnitude,
            (SELECT MIN(acq_date) FROM (
                SELECT MIN(full_date) AS acq_date FROM dwh.fact_fire_hotspot f JOIN dwh.dim_date d ON f.date_key = d.date_key
                UNION
                SELECT MIN(full_date) FROM dwh.fact_earthquake f2 JOIN dwh.dim_date d2 ON f2.date_key = d2.date_key
            )) AS data_start,
            (SELECT MAX(acq_date) FROM (
                SELECT MAX(full_date) AS acq_date FROM dwh.fact_fire_hotspot f JOIN dwh.dim_date d ON f.date_key = d.date_key
                UNION
                SELECT MAX(full_date) FROM dwh.fact_earthquake f2 JOIN dwh.dim_date d2 ON f2.date_key = d2.date_key
            )) AS data_end
    """)


@st.cache_data(ttl="10m")
def monthly_trend():
    return query("""
        SELECT d.year, d.month,
               COUNT(DISTINCT fh.hotspot_id)   AS fire_count,
               COUNT(DISTINCT eq.earthquake_id) AS eq_count
        FROM dwh.dim_date d
        LEFT JOIN dwh.fact_fire_hotspot fh ON d.date_key = fh.date_key
        LEFT JOIN dwh.fact_earthquake eq ON d.date_key = eq.date_key
        WHERE d.year = 2025
        GROUP BY d.year, d.month
        ORDER BY d.month
    """)


@st.cache_data(ttl="10m")
def top_fire_provinces(limit: int = 10):
    return query(f"""
        SELECT l.province_name, COUNT(*) AS total, ROUND(AVG(f.frp), 2) AS avg_frp
        FROM dwh.fact_fire_hotspot f
        JOIN dwh.dim_location l ON f.location_key = l.location_key
        WHERE l.province_name IS NOT NULL AND l.province_name != 'Unknown'
        GROUP BY l.province_name
        ORDER BY total DESC
        LIMIT {limit}
    """)


@st.cache_data(ttl="10m")
def top_eq_provinces(limit: int = 10):
    return query(f"""
        SELECT l.province_name, COUNT(*) AS total, ROUND(MAX(f.mag), 2) AS max_mag
        FROM dwh.fact_earthquake f
        JOIN dwh.dim_location l ON f.location_key = l.location_key
        WHERE l.province_name IS NOT NULL AND l.province_name != 'Unknown'
        GROUP BY l.province_name
        ORDER BY total DESC
        LIMIT {limit}
    """)


@st.cache_data(ttl="10m")
def fire_daily_trend():
    return query("""
        SELECT d.full_date, COUNT(*) AS count, ROUND(AVG(f.frp), 2) AS avg_frp
        FROM dwh.fact_fire_hotspot f
        JOIN dwh.dim_date d ON f.date_key = d.date_key
        GROUP BY d.full_date
        ORDER BY d.full_date
    """)


@st.cache_data(ttl="10m")
def fire_heatmap_data(max_rows: int = 50000):
    return query(f"""
        SELECT l.latitude, l.longitude, f.frp, l.province_name
        FROM dwh.fact_fire_hotspot f
        JOIN dwh.dim_location l ON f.location_key = l.location_key
        WHERE f.frp > 0
        ORDER BY f.frp DESC
        LIMIT {max_rows}
    """)


@st.cache_data(ttl="10m")
def eq_map_data():
    return query("""
        SELECT l.latitude, l.longitude, f.mag, f.depth, f.tsunami, l.province_name
        FROM dwh.fact_earthquake f
        JOIN dwh.dim_location l ON f.location_key = l.location_key
        WHERE f.mag IS NOT NULL
    """)


@st.cache_data(ttl="10m")
def eq_daily_trend():
    return query("""
        SELECT d.full_date, COUNT(*) AS count, ROUND(MAX(f.mag), 2) AS max_mag
        FROM dwh.fact_earthquake f
        JOIN dwh.dim_date d ON f.date_key = d.date_key
        GROUP BY d.full_date
        ORDER BY d.full_date
    """)


@st.cache_data(ttl="10m")
def fire_by_daynight():
    return query("""
        SELECT f.daynight, COUNT(*) AS total, ROUND(AVG(f.frp), 2) AS avg_frp
        FROM dwh.fact_fire_hotspot f
        WHERE f.daynight IS NOT NULL
        GROUP BY f.daynight
    """)


@st.cache_data(ttl="10m")
def eq_magnitude_distribution():
    return query("""
        SELECT ROUND(f.mag, 0) AS mag_bucket, COUNT(*) AS total
        FROM dwh.fact_earthquake f
        WHERE f.mag IS NOT NULL
        GROUP BY mag_bucket
        ORDER BY mag_bucket
    """)


@st.cache_data(ttl="10m")
def satellite_comparison():
    return query("""
        SELECT s.satellite_source, s.sensor_type, COUNT(*) AS total
        FROM dwh.fact_fire_hotspot f
        JOIN dwh.dim_satellite_source s ON f.src_key = s.src_key
        GROUP BY s.satellite_source, s.sensor_type
    """)
