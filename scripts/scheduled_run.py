"""Scheduled runner untuk update data periodik.

Usage (via Windows Task Scheduler / cron):
    python scripts/scheduled_run.py [--weeks 2]

Default: mengambil data 2 minggu terakhir, load incremental, build mart.
"""

import argparse
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Ensure project root is on path
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

from staging.pipeline import Pipeline
from staging.config import FIRMS_MAP_KEY
from dwh.dwh_loader import DWHLoader
from mart.build_mart import MartBuilder


def main():
    parser = argparse.ArgumentParser(description="Scheduled DWH update")
    parser.add_argument("--weeks", type=int, default=2, help="Lookback weeks for ETL (default: 2)")
    parser.add_argument("--skip-etl", action="store_true", help="Skip API fetch, only DWH + Mart")
    parser.add_argument("--skip-mart", action="store_true", help="Skip mart build")
    parser.add_argument("--log-file", type=str, help="Log to file instead of stdout")
    args = parser.parse_args()

    if args.log_file:
        fh = logging.FileHandler(args.log_file, mode="a", encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s  %(levelname)-8s  %(message)s"))
        logging.getLogger().addHandler(fh)

    today = datetime.now()
    start_date = (today - timedelta(weeks=args.weeks)).date()
    end_date = today.date()

    logger = logging.getLogger(__name__)
    logger.info("=" * 50)
    logger.info("Scheduled run started: %s → %s", start_date, end_date)
    logger.info("=" * 50)

    # Step 1: Staging ETL
    if not args.skip_etl:
        logger.info("--- Step 1: Staging ETL ---")
        if not FIRMS_MAP_KEY or FIRMS_MAP_KEY == "your_map_key_here":
            logger.error("FIRMS_MAP_KEY not configured. Skipping ETL.")
        else:
            pipe = Pipeline(map_key=FIRMS_MAP_KEY)
            pipe.run(
                start_date=start_date,
                end_date=end_date,
                include_usgs=True,
                usgs_minmag=0.0,
            )
    else:
        logger.info("--- Step 1: Skipped (--skip-etl) ---")

    # Step 2: Incremental DWH load
    logger.info("--- Step 2: Incremental DWH Load ---")
    loader = DWHLoader()
    loader.init_schema()
    loader.load_all(incremental=True)
    loader.close()

    # Step 3: Build Mart
    if not args.skip_mart:
        logger.info("--- Step 3: Build Mart ---")
        builder = MartBuilder()
        builder.build_all()
        builder.close()
    else:
        logger.info("--- Step 3: Skipped (--skip-mart) ---")

    logger.info("=" * 50)
    logger.info("Scheduled run complete")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
