import logging
from datetime import date, timedelta
from typing import List, Optional

from .config import (
    FIRMS_MAP_KEY,
    FIRMS_SOURCES,
    INDONESIA_BBOX_STR,
    INDONESIA_BBOX,
    FIRE_STAGING_DIR,
    EARTHQUAKE_STAGING_DIR,
)
from .extract.firms_client import FIRMSClient
from .extract.usgs_client import USGSClient
from .transform.firms_transformer import transform_firms
from .transform.usgs_transformer import transform_usgs
from .load.staging_loader import StagingLoader

logger = logging.getLogger(__name__)


class Pipeline:
    def __init__(self, map_key: str = FIRMS_MAP_KEY):
        self.firms = FIRMSClient(map_key=map_key)
        self.usgs = USGSClient()
        self.loader = StagingLoader(FIRE_STAGING_DIR.parent)

    @staticmethod
    def _date_chunks(start: date, end: date, chunk_days: int):
        cur = start
        while cur <= end:
            chunk_end = min(cur + timedelta(days=chunk_days - 1), end)
            yield cur, chunk_end
            cur = chunk_end + timedelta(days=1)

    def run_firms(self, start_date: date, end_date: date, sources: Optional[List[str]] = None):
        sources_to_run = {k: v for k, v in FIRMS_SOURCES.items() if sources is None or k in sources}
        if not sources_to_run:
            logger.warning("No FIRMS sources selected")
            return

        for src_name, src_cfg in sources_to_run.items():
            src_min = date.fromisoformat(src_cfg["min_date"])
            src_start = max(start_date, src_min)
            if src_start > end_date:
                logger.info("SKIP %s — data starts %s", src_name, src_cfg["min_date"])
                continue

            logger.info("=== FIRMS source: %s ===", src_name)
            max_dr = src_cfg["max_day_range"]
            for cs, ce in self._date_chunks(src_start, end_date, max_dr):
                dr = (ce - cs).days + 1
                s = cs.strftime("%Y-%m-%d")
                try:
                    raw = self.firms.fetch_area(
                        source=src_name,
                        bbox=INDONESIA_BBOX_STR,
                        day_range=dr,
                        ref_date=s,
                    )
                    df = transform_firms(raw, src_name)
                    if not df.empty:
                        self.loader.save_fire_data(df, src_name, cs.year, cs.month)
                except Exception as e:
                    logger.error("FIRMS %s %s failed: %s", src_name, s, e)

    def run_usgs(self, start_date: date, end_date: date, minmagnitude: float = 0.0):
        logger.info("=== USGS Earthquake ===")
        b = INDONESIA_BBOX
        for cs, ce in self._date_chunks(start_date, end_date, 30):
            s, e = cs.strftime("%Y-%m-%d"), ce.strftime("%Y-%m-%d")
            try:
                geo = self.usgs.fetch_events(
                    starttime=s,
                    endtime=e,
                    minlatitude=b["south"],
                    maxlatitude=b["north"],
                    minlongitude=b["west"],
                    maxlongitude=b["east"],
                    minmagnitude=minmagnitude,
                )
                df = transform_usgs(geo)
                if not df.empty:
                    self.loader.save_earthquake_data(df, cs.year, cs.month)
            except Exception as ex:
                logger.error("USGS %s – %s failed: %s", s, e, ex)

    def run(
        self,
        start_date: date,
        end_date: date,
        fire_sources: Optional[List[str]] = None,
        include_usgs: bool = True,
        usgs_minmag: float = 0.0,
    ):
        logger.info("=" * 50)
        logger.info("Pipeline started  %s  →  %s", start_date, end_date)
        logger.info("=" * 50)

        self.run_firms(start_date, end_date, fire_sources)
        if include_usgs:
            self.run_usgs(start_date, end_date, usgs_minmag)

        logger.info("=" * 50)
        logger.info("Pipeline finished successfully")
        logger.info("=" * 50)
