import argparse
import logging
from datetime import datetime

from staging.pipeline import Pipeline
from staging.config import FIRMS_MAP_KEY
from dwh.dwh_loader import DWHLoader
from dwh.queries import QUERIES
from mart.build_mart import MartBuilder

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def main():
    parser = argparse.ArgumentParser(
        description="Data Warehouse Pipeline - NASA FIRMS + USGS Earthquake (Indonesia)"
    )

    sub = parser.add_subparsers(dest="command")

    # --- STAGING ETL (existing) ---
    run_parser = sub.add_parser("run-etl", help="Run staging ETL from API to CSV")
    run_parser.add_argument("--start", default="2023-01-01")
    run_parser.add_argument("--end", default="2025-12-31")
    run_parser.add_argument("--sources", nargs="+",
                            help="FIRMS sources (default: all). Options: MODIS_SP, VIIRS_SNPP_SP, VIIRS_NOAA20_SP, VIIRS_NOAA21_NRT")
    run_parser.add_argument("--no-usgs", action="store_true")
    run_parser.add_argument("--usgs-minmag", type=float, default=0.0)

    # --- DWH INIT ---
    init_parser = sub.add_parser("init-dwh", help="Initialize DWH schema in DuckDB")

    # --- DWH LOAD ---
    load_parser = sub.add_parser("load-dwh", help="Load staging CSV into DuckDB DWH")
    load_parser.add_argument("--no-fire", action="store_true", help="Skip fire hotspots")
    load_parser.add_argument("--no-eq", action="store_true", help="Skip earthquakes")
    load_parser.add_argument("--incremental", action="store_true", help="Only load new/modified files")
    load_parser.add_argument("--reset-tracker", choices=["fire", "earthquake", "all"], const="all", nargs="?",
                             help="Reset load tracker for re-loading")

    # --- DWH QUERY ---
    query_parser = sub.add_parser("query", help="Run a predefined analytical query")
    query_parser.add_argument("name", nargs="?", choices=list(QUERIES) + ["all"], default="all",
                              help="Query name or 'all' to run all")

    # --- BUILD MART ---
    mart_parser = sub.add_parser("build-mart", help="Build Data Mart views + export Parquet/CSV")
    mart_parser.add_argument("--format", nargs="+", default=["parquet", "csv"],
                             choices=["parquet", "csv"], help="Export formats")

    # --- FULL PIPELINE ---
    full_parser = sub.add_parser("full-pipeline", help="Run ETL + Load DWH + Build Mart in one go")
    full_parser.add_argument("--start", default="2023-01-01")
    full_parser.add_argument("--end", default="2025-12-31")
    full_parser.add_argument("--sources", nargs="+")
    full_parser.add_argument("--no-usgs", action="store_true")
    full_parser.add_argument("--usgs-minmag", type=float, default=0.0)
    full_parser.add_argument("--format", nargs="+", default=["parquet", "csv"],
                             choices=["parquet", "csv"])

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    # ---------------------------------------------------------------
    if args.command == "run-etl":
        if not FIRMS_MAP_KEY or FIRMS_MAP_KEY == "your_map_key_here":
            parser.error("FIRMS_MAP_KEY not configured. Edit .env file.")
        start = datetime.strptime(args.start, "%Y-%m-%d").date()
        end = datetime.strptime(args.end, "%Y-%m-%d").date()
        pipe = Pipeline(map_key=FIRMS_MAP_KEY)
        pipe.run(
            start_date=start, end_date=end,
            fire_sources=args.sources,
            include_usgs=not args.no_usgs,
            usgs_minmag=args.usgs_minmag,
        )

    elif args.command == "init-dwh":
        loader = DWHLoader()
        loader.init_schema()
        loader.load_dim_date()
        loader.load_dim_satellite()
        loader.load_dim_event_type()
        loader.close()
        print("DWH schema initialized successfully")

    elif args.command == "load-dwh":
        loader = DWHLoader()
        loader.init_schema()
        if args.reset_tracker:
            cat = {"fire": "fire", "earthquake": "earthquake", "all": None}[args.reset_tracker]
            loader.reset_tracker(cat)
        loader.load_all(include_fire=not args.no_fire, include_eq=not args.no_eq, incremental=args.incremental)
        loader.close()
        print("DWH load complete")

    elif args.command == "query":
        loader = DWHLoader()
        loader.init_schema()
        queries = QUERIES if args.name == "all" else {args.name: QUERIES[args.name]}
        for qname, sql in queries.items():
            print(f"\n=== {qname} ===")
            df = loader.run_sql(sql)
            print(df.to_string(index=False))
        loader.close()

    elif args.command == "build-mart":
        builder = MartBuilder()
        builder.build_all(formats=args.format)
        builder.close()

    elif args.command == "full-pipeline":
        if not FIRMS_MAP_KEY or FIRMS_MAP_KEY == "your_map_key_here":
            parser.error("FIRMS_MAP_KEY not configured. Edit .env file.")
        start = datetime.strptime(args.start, "%Y-%m-%d").date()
        end = datetime.strptime(args.end, "%Y-%m-%d").date()
        pipe = Pipeline(map_key=FIRMS_MAP_KEY)
        pipe.run(
            start_date=start, end_date=end,
            fire_sources=args.sources,
            include_usgs=not args.no_usgs,
            usgs_minmag=args.usgs_minmag,
        )
        loader = DWHLoader()
        loader.init_schema()
        loader.load_all()
        loader.close()
        builder = MartBuilder()
        builder.build_all(formats=args.format)
        builder.close()
        print("Full pipeline complete: ETL → DWH → Mart")


if __name__ == "__main__":
    main()
