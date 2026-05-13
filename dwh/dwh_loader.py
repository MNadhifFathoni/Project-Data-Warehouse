import logging
from datetime import date
from pathlib import Path
from typing import Optional

import duckdb
import pandas as pd

from . import schema
from .config import (
    DWH_PATH,
    STAGING_FIRE_DIR,
    STAGING_EQ_DIR,
    DWH_SCHEMA,
    SATELLITE_SOURCES,
    SHAPEFILE_PATH,
)
from .geo_utils import GeoResolver

logger = logging.getLogger(__name__)


class DWHLoader:
    def __init__(self, db_path: Optional[Path] = None, shapefile_path: Optional[Path] = None):
        self.db_path = db_path or DWH_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.con = duckdb.connect(str(self.db_path))
        self.con.execute("SET enable_progress_bar = false;")
        self.geo = GeoResolver(shapefile_path or SHAPEFILE_PATH)

    def init_schema(self):
        logger.info("Initializing DWH schema...")
        schema.run_ddl(self.con)
        self.con.commit()
        logger.info("Schema ready")

    def close(self):
        self.con.close()

    # ---------------------------------------------------------------
    # LOAD TRACKER (incremental)
    # ---------------------------------------------------------------

    def get_loaded_files(self, category: str = None) -> set:
        q = "SELECT file_name FROM dwh.load_tracker"
        params = []
        if category:
            q += " WHERE category = ?"
            params.append(category)
        return {r[0] for r in self.con.execute(q, params).fetchall()}

    def _is_file_loaded(self, file_name: str) -> bool:
        return self.con.execute(
            "SELECT COUNT(*) FROM dwh.load_tracker WHERE file_name = ?", [file_name]
        ).fetchone()[0] > 0

    def _mark_file_loaded(self, file_name: str, category: str, row_count: int, file_size: int = 0):
        self.con.execute("""
            INSERT OR REPLACE INTO dwh.load_tracker (file_name, category, row_count, file_size, loaded_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, [file_name, category, row_count, file_size])
        self.con.commit()

    def reset_tracker(self, category: str = None):
        if category == "fire":
            self.con.execute("DELETE FROM dwh.fact_fire_hotspot")
            self.con.execute("DELETE FROM dwh.load_tracker WHERE category = 'fire'")
            logger.info("Reset: cleared fire facts + tracker")
        elif category == "earthquake":
            self.con.execute("DELETE FROM dwh.fact_earthquake")
            self.con.execute("DELETE FROM dwh.load_tracker WHERE category = 'earthquake'")
            logger.info("Reset: cleared earthquake facts + tracker")
        elif category is None:
            self.con.execute("DELETE FROM dwh.fact_fire_hotspot")
            self.con.execute("DELETE FROM dwh.fact_earthquake")
            self.con.execute("DELETE FROM dwh.load_tracker")
            logger.info("Reset: cleared all facts + tracker")
        self.con.commit()

    # ---------------------------------------------------------------
    # DIMENSION LOADERS
    # ---------------------------------------------------------------

    def load_dim_date(self, start_year: int = 2020, end_year: int = 2030):
        existing = self.con.execute(f"SELECT COUNT(*) FROM {DWH_SCHEMA}.dim_date").fetchone()[0]
        if existing > 0:
            logger.info("dim_date already has %d rows, skipping", existing)
            return

        rows = []
        d = date(start_year, 1, 1)
        end = date(end_year, 12, 31)
        while d <= end:
            date_key = int(d.strftime("%Y%m%d"))
            rows.append((
                date_key, d,
                d.year, d.month,
                d.strftime("%B"),
                (d.month - 1) // 3 + 1,
                d.day, d.isoweekday(),
                d.isoweekday() in (6, 7),
            ))
            d += pd.Timedelta(days=1)

        df = pd.DataFrame(rows, columns=[
            "date_key", "full_date", "year", "month", "month_name",
            "quarter", "day", "day_of_week", "is_weekend",
        ])
        self.con.execute(f"INSERT INTO {DWH_SCHEMA}.dim_date SELECT * FROM df")
        self.con.commit()
        logger.info("Loaded dim_date: %d rows (%s – %s)", len(df), start_year, end_year)

    def load_dim_satellite(self):
        existing = self.con.execute(f"SELECT COUNT(*) FROM {DWH_SCHEMA}.dim_satellite_source").fetchone()[0]
        if existing > 0:
            logger.info("dim_satellite_source already has %d rows, skipping", existing)
            return
        rows = [(idx, src_name, cfg["sensor"], cfg["satellite"])
                for idx, (src_name, cfg) in enumerate(SATELLITE_SOURCES.items(), start=1)]
        df = pd.DataFrame(rows, columns=["src_key", "satellite_source", "sensor_type", "satellite"])
        self.con.execute(f"INSERT INTO {DWH_SCHEMA}.dim_satellite_source SELECT * FROM df")
        self.con.commit()
        logger.info("Loaded %d satellite sources", len(rows))

    def load_dim_event_type(self):
        existing = self.con.execute(f"SELECT COUNT(*) FROM {DWH_SCHEMA}.dim_event_type").fetchone()[0]
        if existing > 0:
            logger.info("dim_event_type already has %d rows, skipping", existing)
            return
        types = ["earthquake", "quarry", "explosion", "rockfall", "landslide", "sonic boom", "unknown"]
        rows = [(idx, t) for idx, t in enumerate(types, start=1)]
        df = pd.DataFrame(rows, columns=["event_type_key", "event_type_name"])
        self.con.execute(f"INSERT INTO {DWH_SCHEMA}.dim_event_type SELECT * FROM df")
        self.con.commit()
        logger.info("Loaded %d event types", len(types))

    # ---------------------------------------------------------------
    # BULK DIM LOCATION LOADER
    # ---------------------------------------------------------------

    def _load_dim_location_bulk(self, csv_glob: str, lat_col: str = "latitude", lon_col: str = "longitude"):
        q = f"""
            CREATE OR REPLACE TEMP VIEW raw_coords AS
            SELECT DISTINCT {lon_col} AS longitude, {lat_col} AS latitude
            FROM read_csv_auto('{csv_glob}', union_by_name=true, all_varchar=false);
        """
        self.con.execute(q)

        new_count = self.con.execute(f"""
            SELECT COUNT(*) FROM raw_coords rc
            WHERE NOT EXISTS (
                SELECT 1 FROM {DWH_SCHEMA}.dim_location dl
                WHERE dl.longitude = rc.longitude AND dl.latitude = rc.latitude
            )
        """).fetchone()[0]

        if new_count == 0:
            logger.info("No new locations to add")
            return

        self.con.execute(f"""
            INSERT OR IGNORE INTO {DWH_SCHEMA}.dim_location (longitude, latitude, grid_cell_id)
            SELECT rc.longitude, rc.latitude,
                   'grid_' || ROUND(rc.latitude * 2) / 2 || '_' || ROUND(rc.longitude * 2) / 2
            FROM raw_coords rc
            WHERE NOT EXISTS (
                SELECT 1 FROM {DWH_SCHEMA}.dim_location dl
                WHERE dl.longitude = rc.longitude AND dl.latitude = rc.latitude
            );
        """)
        self.con.commit()

        if self.geo.is_ready():
            all_locs = self.con.execute(f"""
                SELECT location_key, longitude, latitude
                FROM {DWH_SCHEMA}.dim_location
                WHERE province_name IS NULL
            """).fetchdf()
            if not all_locs.empty:
                resolved = self.geo.resolve_batch(all_locs)
                self.con.execute(f"CREATE OR REPLACE TEMP VIEW resolved_locs AS SELECT * FROM resolved")
                self.con.execute(f"""
                    UPDATE {DWH_SCHEMA}.dim_location dl
                    SET province_name = rl.province_name,
                        province_code = rl.province_code,
                        island       = rl.island
                    FROM resolved_locs rl
                    WHERE dl.location_key = rl.location_key;
                """)
                self.con.commit()
                logger.info("Resolved provinces for %d locations", len(all_locs))

    # ---------------------------------------------------------------
    # FACT LOADERS — BULK DuckDB-native
    # ---------------------------------------------------------------

    def load_fact_fire(self, incremental: bool = False):
        csv_files = sorted(STAGING_FIRE_DIR.glob("*.csv"))
        if not csv_files:
            logger.warning("No FIRMS staging CSV files found in %s", STAGING_FIRE_DIR)
            return

        # Filter for new files if incremental
        if incremental:
            loaded = self.get_loaded_files(category="fire")
            new_files = [f for f in csv_files if f.name not in loaded]
            skipped = len(csv_files) - len(new_files)
            if skipped:
                logger.info("Skipping %d already-loaded fire files", skipped)
            csv_files = new_files
            if not csv_files:
                logger.info("All fire files already loaded")
                return

        csv_glob = (STAGING_FIRE_DIR / "*.csv").as_posix()
        self._load_dim_location_bulk(csv_glob)

        total = 0
        for fpath in csv_files:
            src_name = fpath.stem.rsplit("_", 1)[0]
            src_key = self.con.execute(f"""
                SELECT src_key FROM {DWH_SCHEMA}.dim_satellite_source WHERE satellite_source = ?
            """, [src_name]).fetchone()
            if not src_key:
                logger.warning("Unknown source %s, skipping", src_name)
                continue
            src_key = src_key[0]

            fpath_posix = fpath.as_posix()
            inserted = self.con.execute(f"""
                INSERT INTO {DWH_SCHEMA}.fact_fire_hotspot
                    (date_key, time_key, location_key, src_key,
                     frp, brightness, brightness_t13, brightness_t31,
                     bright_t14, bright_t15, scan, track, confidence, daynight)
                SELECT
                    CAST(STRFTIME(acq_date, '%Y%m%d') AS INTEGER),
                    CASE WHEN LENGTH(CAST(acq_time AS VARCHAR)) >= 4
                         THEN CAST(SUBSTR(CAST(acq_time AS VARCHAR), 1, 4) AS INTEGER)
                         ELSE 0 END,
                    dl.location_key,
                    {src_key},
                    frp, brightness, brightness_t13, brightness_t31,
                    bright_t14, bright_t15, scan, track,
                    confidence, daynight
                FROM read_csv_auto('{fpath_posix}', union_by_name=true) src
                JOIN {DWH_SCHEMA}.dim_location dl
                    ON ROUND(dl.latitude::DOUBLE, 6) = ROUND(src.latitude::DOUBLE, 6)
                   AND ROUND(dl.longitude::DOUBLE, 6) = ROUND(src.longitude::DOUBLE, 6)
                WHERE src.latitude IS NOT NULL AND src.longitude IS NOT NULL
                  AND acq_date IS NOT NULL
                ON CONFLICT (date_key, time_key, location_key, src_key) DO NOTHING
            """).fetchone()[0]

            total += inserted
            self._mark_file_loaded(fpath.name, "fire", inserted, fpath.stat().st_size)
            logger.info("Loaded %d records from %s", inserted, fpath.name)
            self.con.commit()

        logger.info("Total fire hotspots loaded this run: %d", total)

    def load_fact_earthquake(self, incremental: bool = False):
        csv_files = sorted(STAGING_EQ_DIR.glob("*.csv"))
        if not csv_files:
            logger.warning("No earthquake staging CSV files found in %s", STAGING_EQ_DIR)
            return

        # Filter for new files if incremental
        if incremental:
            loaded = self.get_loaded_files(category="earthquake")
            new_files = [f for f in csv_files if f.name not in loaded]
            skipped = len(csv_files) - len(new_files)
            if skipped:
                logger.info("Skipping %d already-loaded earthquake files", skipped)
            csv_files = new_files
            if not csv_files:
                logger.info("All earthquake files already loaded")
                return

        csv_glob = (STAGING_EQ_DIR / "*.csv").as_posix()
        self._load_dim_location_bulk(csv_glob)

        total = 0
        for fpath in csv_files:
            fpath_posix = fpath.as_posix()

            inserted = self.con.execute(f"""
                INSERT INTO {DWH_SCHEMA}.fact_earthquake
                    (date_key, time_key, location_key, event_type_key, event_id,
                     mag, mag_type, depth, felt, cdi, mmi, alert, status, tsunami,
                     sig, nst, dmin, rms, gap, place, title, url)
                SELECT
                    CAST(STRFTIME(TIMESTAMP 'epoch' + (time_epoch / 1000) * INTERVAL '1 second', '%Y%m%d') AS INTEGER),
                    CAST(STRFTIME(TIMESTAMP 'epoch' + (time_epoch / 1000) * INTERVAL '1 second', '%H%M') AS INTEGER),
                    dl.location_key,
                    det.event_type_key,
                    src.event_id,
                    src.mag, src.mag_type, src.depth,
                    src.felt, src.cdi, src.mmi, src.alert, src.status, src.tsunami,
                    src.sig, src.nst, src.dmin, src.rms, src.gap,
                    src.place, src.title, src.url
                FROM read_csv_auto('{fpath_posix}', union_by_name=true) src
                JOIN {DWH_SCHEMA}.dim_location dl
                    ON ROUND(dl.latitude::DOUBLE, 6) = ROUND(src.latitude::DOUBLE, 6)
                   AND ROUND(dl.longitude::DOUBLE, 6) = ROUND(src.longitude::DOUBLE, 6)
                LEFT JOIN {DWH_SCHEMA}.dim_event_type det
                    ON LOWER(COALESCE(src.event_type, 'unknown')) = LOWER(det.event_type_name)
                WHERE src.latitude IS NOT NULL AND src.longitude IS NOT NULL
                  AND src.event_id IS NOT NULL
                  AND NOT EXISTS (
                      SELECT 1 FROM {DWH_SCHEMA}.fact_earthquake fe
                      WHERE fe.event_id = src.event_id
                  )
            """).fetchone()[0]

            total += inserted
            self._mark_file_loaded(fpath.name, "earthquake", inserted, fpath.stat().st_size)
            logger.info("Loaded %d records from %s", inserted, fpath.name)
            self.con.commit()

        logger.info("Total earthquakes loaded this run: %d", total)

    # ---------------------------------------------------------------
    # FULL LOAD
    # ---------------------------------------------------------------

    def load_all(self, include_fire: bool = True, include_eq: bool = True, incremental: bool = False):
        self.load_dim_date()
        self.load_dim_satellite()
        self.load_dim_event_type()

        if include_fire:
            self.load_fact_fire(incremental=incremental)
        if include_eq:
            self.load_fact_earthquake(incremental=incremental)

        logger.info("DWH load complete")

    def run_sql(self, query: str) -> pd.DataFrame:
        return self.con.execute(query).fetchdf()
