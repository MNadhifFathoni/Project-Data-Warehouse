import logging
import time
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3


def _save_csv(df: pd.DataFrame, path: Path):
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            write_header = not path.exists()
            df.to_csv(path, mode="a", header=write_header, index=False)
            return
        except PermissionError:
            if attempt == _MAX_RETRIES:
                raise
            logger.warning("File locked, retrying %s (%d/3)", path.name, attempt)
            time.sleep(1.0)


class StagingLoader:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_fire_data(self, df: pd.DataFrame, source_name: str, year: int, month: int) -> Path | None:
        if df.empty:
            return None

        subdir = self.base_dir / "fire_hotspots"
        subdir.mkdir(parents=True, exist_ok=True)

        path = subdir / f"{source_name}_{year}{month:02d}.csv"
        _save_csv(df, path)
        logger.info("Saved %d FIRMS rows → %s", len(df), path)
        return path

    def save_earthquake_data(self, df: pd.DataFrame, year: int, month: int) -> Path | None:
        if df.empty:
            return None

        subdir = self.base_dir / "earthquakes"
        subdir.mkdir(parents=True, exist_ok=True)

        path = subdir / f"earthquakes_{year}{month:02d}.csv"
        _save_csv(df, path)
        logger.info("Saved %d USGS rows → %s", len(df), path)
        return path
