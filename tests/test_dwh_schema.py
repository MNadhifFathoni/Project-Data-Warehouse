import os
import tempfile
from pathlib import Path

import duckdb
import pytest

from dwh import schema


@pytest.fixture
def con():
    with tempfile.NamedTemporaryFile(suffix=".duckdb", delete=True) as f:
        db_path = f.name
    db = duckdb.connect(db_path)
    schema.run_ddl(db)
    db.commit()
    yield db
    db.close()
    try:
        os.unlink(db_path)
    except (PermissionError, FileNotFoundError):
        pass


class TestDWHLoader:
    def test_init_schema_creates_tables(self, con):
        tables = con.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'dwh'"
        ).fetchdf()
        expected = {"dim_date", "dim_location", "dim_satellite_source", "dim_event_type",
                    "fact_fire_hotspot", "fact_earthquake", "load_tracker"}
        for t in expected:
            assert t in tables["table_name"].values, f"Missing table: {t}"

    def test_init_schema_creates_mart_views(self, con):
        views = con.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'mart'"
        ).fetchdf()
        expected = {"v_hotspot_daily", "v_earthquake_daily", "v_monthly_trend", "v_high_risk_zones"}
        for v in expected:
            assert v in views["table_name"].values, f"Missing view: {v}"

    def test_dim_date_schema(self, con):
        cols = con.execute("PRAGMA table_info('dwh.dim_date')").fetchdf()
        assert "date_key" in cols["name"].values
        assert "full_date" in cols["name"].values

    def test_fact_fire_hotspot_has_unique_index(self, con):
        indexes = con.execute("SELECT index_name FROM duckdb_indexes() WHERE table_name = 'fact_fire_hotspot'").fetchdf()
        names = indexes["index_name"].astype(str).str.lower().tolist()
        assert any("idx_hotspot_unique" in n for n in names)

    def test_fact_earthquake_has_event_id_index(self, con):
        indexes = con.execute("SELECT index_name FROM duckdb_indexes() WHERE table_name = 'fact_earthquake'").fetchdf()
        names = indexes["index_name"].astype(str).str.lower().tolist()
        assert any("idx_earthquake_event_id" in n for n in names)

    def test_run_ddl_is_idempotent(self, con):
        schema.run_ddl(con)
        count = con.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'dwh'").fetchone()[0]
        assert count == 7
