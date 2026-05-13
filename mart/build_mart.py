import logging
from pathlib import Path
from typing import Optional

import duckdb

from dwh.config import DWH_PATH, MART_DIR

logger = logging.getLogger(__name__)


class MartBuilder:
    def __init__(self, dwh_path: Optional[Path] = None, mart_dir: Optional[Path] = None):
        self.dwh_path = dwh_path or DWH_PATH
        self.mart_dir = mart_dir or MART_DIR
        self.mart_dir.mkdir(parents=True, exist_ok=True)
        self.con = duckdb.connect(str(self.dwh_path))

    def export_view_to_parquet(self, view_name: str, filename: str | None = None):
        if filename is None:
            filename = f"{view_name.replace('.', '_')}.parquet"
        path = self.mart_dir / filename
        self.con.execute(f"""
            COPY {view_name} TO '{path.as_posix()}' (FORMAT PARQUET);
        """)
        logger.info("Exported %s -> %s (%d rows)", view_name, path,
                    self.con.execute(f"SELECT COUNT(*) FROM {view_name}").fetchone()[0])
        return path

    def export_view_to_csv(self, view_name: str, filename: str | None = None):
        if filename is None:
            filename = f"{view_name.replace('.', '_')}.csv"
        path = self.mart_dir / filename
        self.con.execute(f"""
            COPY {view_name} TO '{path.as_posix()}' (FORMAT CSV, HEADER);
        """)
        logger.info("Exported %s -> %s", view_name, path)
        return path

    def build_all(self, formats: list[str] | None = None):
        formats = formats or ["parquet", "csv"]

        views = [
            "mart.v_hotspot_daily",
            "mart.v_earthquake_daily",
            "mart.v_monthly_trend",
            "mart.v_high_risk_zones",
        ]

        for v in views:
            try:
                count = self.con.execute(f"SELECT COUNT(*) FROM {v}").fetchone()[0]
                if count == 0:
                    logger.info("Skipping %s (empty)", v)
                    continue
                for fmt in formats:
                    ext = "parquet" if fmt == "parquet" else "csv"
                    vname = v.replace("mart.", "")
                    filename = f"{vname}.{ext}"
                    if fmt == "parquet":
                        self.export_view_to_parquet(v, filename)
                    else:
                        self.export_view_to_csv(v, filename)
            except Exception as e:
                logger.error("Failed to export %s: %s", v, e)

        logger.info("Mart build complete → %s", self.mart_dir)

    def close(self):
        self.con.close()
