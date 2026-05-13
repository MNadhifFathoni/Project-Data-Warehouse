import logging
import time
from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st

DWH_PATH = Path(__file__).resolve().parent.parent / "data" / "dwh" / "disaster.duckdb"
STAGING_DIR = Path(__file__).resolve().parent.parent / "data" / "staging"

logger = logging.getLogger(__name__)


def _ensure_db():
    if DWH_PATH.exists():
        return True

    st.warning("Database belum siap. Membangun dari staging CSV...")
    progress = st.progress(0, "Initializing schema...")

    try:
        import sys
        _root = Path(__file__).resolve().parent.parent
        if str(_root) not in sys.path:
            sys.path.insert(0, str(_root))

        from dwh.dwh_loader import DWHLoader
        loader = DWHLoader()

        # Init schema
        progress.progress(10, "Creating schema...")
        loader.init_schema()

        # Load dimensions
        progress.progress(20, "Loading dimensions...")
        loader.load_dim_date()
        loader.load_dim_satellite()
        loader.load_dim_event_type()

        # Load facts
        fire_csvs = list((STAGING_DIR / "fire_hotspots").glob("*.csv"))
        eq_csvs = list((STAGING_DIR / "earthquakes").glob("*.csv"))

        if fire_csvs:
            progress.progress(40, f"Loading {len(fire_csvs)} fire hotspot files...")
            loader.load_fact_fire()

        if eq_csvs:
            progress.progress(70, f"Loading {len(eq_csvs)} earthquake files...")
            loader.load_fact_earthquake()

        progress.progress(90, "Building mart views...")
        loader.con.execute("""
            CREATE OR REPLACE VIEW mart.v_hotspot_daily AS
            SELECT d.full_date, l.province_name, l.island,
                   COUNT(*) AS hotspot_count, AVG(f.frp) AS avg_frp, MAX(f.frp) AS max_frp
            FROM dwh.fact_fire_hotspot f
            JOIN dwh.dim_date d ON f.date_key = d.date_key
            JOIN dwh.dim_location l ON f.location_key = l.location_key
            GROUP BY d.full_date, l.province_name, l.island
        """)
        loader.con.execute("""
            CREATE OR REPLACE VIEW mart.v_earthquake_daily AS
            SELECT d.full_date, l.province_name, l.island,
                   COUNT(*) AS eq_count, MAX(f.mag) AS max_magnitude
            FROM dwh.fact_earthquake f
            JOIN dwh.dim_date d ON f.date_key = d.date_key
            JOIN dwh.dim_location l ON f.location_key = l.location_key
            GROUP BY d.full_date, l.province_name, l.island
        """)
        loader.close()

        progress.progress(100, "Database siap!")
        time.sleep(1)
        progress.empty()
        st.success(f"Database berhasil dibangun: {fire_csvs and len(fire_csvs) or 0} fire files + {eq_csvs and len(eq_csvs) or 0} eq files")
        return True

    except Exception as e:
        progress.empty()
        st.error(f"Gagal membangun database: {e}")
        logger.error("DB init failed", exc_info=True)
        return False


@st.cache_resource
def get_connection():
    if not DWH_PATH.exists():
        if not _ensure_db():
            return None
    try:
        return duckdb.connect(str(DWH_PATH), read_only=True)
    except Exception:
        return duckdb.connect(str(DWH_PATH))


def query(sql: str) -> pd.DataFrame:
    con = get_connection()
    if con is None:
        return pd.DataFrame()
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
