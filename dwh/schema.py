from .config import DWH_SCHEMA, MART_SCHEMA

DDL = f"""

CREATE SCHEMA IF NOT EXISTS {DWH_SCHEMA};
CREATE SCHEMA IF NOT EXISTS {MART_SCHEMA};

-- ============================================================
-- DIMENSION TABLES
-- ============================================================

CREATE SEQUENCE IF NOT EXISTS seq_dim_location;

CREATE TABLE IF NOT EXISTS {DWH_SCHEMA}.dim_date (
    date_key    INTEGER PRIMARY KEY,
    full_date   DATE NOT NULL,
    year        SMALLINT NOT NULL,
    month       SMALLINT NOT NULL,
    month_name  VARCHAR(10) NOT NULL,
    quarter     SMALLINT NOT NULL,
    day         SMALLINT NOT NULL,
    day_of_week SMALLINT NOT NULL,
    is_weekend  BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS {DWH_SCHEMA}.dim_location (
    location_key  INTEGER PRIMARY KEY DEFAULT nextval('seq_dim_location'),
    longitude     DOUBLE NOT NULL,
    latitude      DOUBLE NOT NULL,
    grid_cell_id  VARCHAR(20),
    province_name VARCHAR(100),
    province_code VARCHAR(10),
    island        VARCHAR(50),
    UNIQUE (longitude, latitude)
);

CREATE TABLE IF NOT EXISTS {DWH_SCHEMA}.dim_satellite_source (
    src_key           INTEGER PRIMARY KEY,
    satellite_source  VARCHAR(50) NOT NULL UNIQUE,
    sensor_type       VARCHAR(10) NOT NULL,
    satellite         VARCHAR(10)
);

CREATE TABLE IF NOT EXISTS {DWH_SCHEMA}.dim_event_type (
    event_type_key  INTEGER PRIMARY KEY,
    event_type_name VARCHAR(50) NOT NULL UNIQUE
);

-- ============================================================
-- FACT TABLES
-- ============================================================

CREATE SEQUENCE IF NOT EXISTS seq_hotspot_id;
CREATE SEQUENCE IF NOT EXISTS seq_earthquake_id;

CREATE TABLE IF NOT EXISTS {DWH_SCHEMA}.fact_fire_hotspot (
    hotspot_id      BIGINT PRIMARY KEY DEFAULT nextval('seq_hotspot_id'),
    date_key        INTEGER REFERENCES {DWH_SCHEMA}.dim_date(date_key),
    time_key        INTEGER,
    location_key    INTEGER REFERENCES {DWH_SCHEMA}.dim_location(location_key),
    src_key         INTEGER REFERENCES {DWH_SCHEMA}.dim_satellite_source(src_key),
    frp             DOUBLE,
    brightness      DOUBLE,
    brightness_t13  DOUBLE,
    brightness_t31  DOUBLE,
    bright_t14      DOUBLE,
    bright_t15      DOUBLE,
    scan            DOUBLE,
    track           DOUBLE,
    confidence      VARCHAR(20),
    daynight        VARCHAR(1)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_hotspot_unique
    ON {DWH_SCHEMA}.fact_fire_hotspot(date_key, time_key, location_key, src_key);

CREATE TABLE IF NOT EXISTS {DWH_SCHEMA}.fact_earthquake (
    earthquake_id   BIGINT PRIMARY KEY DEFAULT nextval('seq_earthquake_id'),
    date_key        INTEGER REFERENCES {DWH_SCHEMA}.dim_date(date_key),
    time_key        INTEGER,
    location_key    INTEGER REFERENCES {DWH_SCHEMA}.dim_location(location_key),
    event_type_key  INTEGER REFERENCES {DWH_SCHEMA}.dim_event_type(event_type_key),
    event_id        VARCHAR(50) NOT NULL,
    mag             DOUBLE,
    mag_type        VARCHAR(10),
    depth           DOUBLE,
    felt            INTEGER,
    cdi             DOUBLE,
    mmi             DOUBLE,
    alert           VARCHAR(10),
    status          VARCHAR(20),
    tsunami         SMALLINT,
    sig             INTEGER,
    nst             INTEGER,
    dmin            DOUBLE,
    rms             DOUBLE,
    gap             DOUBLE,
    place           VARCHAR(500),
    title           VARCHAR(500),
    url             VARCHAR(500)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_earthquake_event_id
    ON {DWH_SCHEMA}.fact_earthquake(event_id);

-- ============================================================
-- LOAD TRACKER (incremental loading)
-- ============================================================

CREATE TABLE IF NOT EXISTS {DWH_SCHEMA}.load_tracker (
    file_name     VARCHAR(255) PRIMARY KEY,
    category      VARCHAR(20) NOT NULL,   -- 'fire' or 'earthquake'
    row_count     INTEGER NOT NULL DEFAULT 0,
    loaded_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    file_size     BIGINT,
    file_hash     VARCHAR(64)
);

-- ============================================================
-- DATA MART VIEWS
-- ============================================================

CREATE OR REPLACE VIEW {MART_SCHEMA}.v_hotspot_daily AS
SELECT
    d.full_date,
    l.province_name,
    l.island,
    s.sensor_type,
    s.satellite_source,
    COUNT(*)                    AS hotspot_count,
    AVG(f.frp)                  AS avg_frp,
    MAX(f.frp)                  AS max_frp,
    SUM(CASE WHEN f.daynight='D' THEN 1 ELSE 0 END) AS daytime_count,
    SUM(CASE WHEN f.daynight='N' THEN 1 ELSE 0 END) AS nighttime_count
FROM {DWH_SCHEMA}.fact_fire_hotspot f
JOIN {DWH_SCHEMA}.dim_date d ON f.date_key = d.date_key
JOIN {DWH_SCHEMA}.dim_location l ON f.location_key = l.location_key
JOIN {DWH_SCHEMA}.dim_satellite_source s ON f.src_key = s.src_key
GROUP BY d.full_date, l.province_name, l.island, s.sensor_type, s.satellite_source;

CREATE OR REPLACE VIEW {MART_SCHEMA}.v_earthquake_daily AS
SELECT
    d.full_date,
    l.province_name,
    l.island,
    COUNT(*)                    AS eq_count,
    MAX(f.mag)                  AS max_magnitude,
    AVG(f.mag)                  AS avg_magnitude,
    MAX(f.depth)                AS max_depth,
    SUM(f.tsunami)              AS tsunami_count
FROM {DWH_SCHEMA}.fact_earthquake f
JOIN {DWH_SCHEMA}.dim_date d ON f.date_key = d.date_key
JOIN {DWH_SCHEMA}.dim_location l ON f.location_key = l.location_key
GROUP BY d.full_date, l.province_name, l.island;

CREATE OR REPLACE VIEW {MART_SCHEMA}.v_monthly_trend AS
SELECT
    d.year,
    d.month,
    l.province_name,
    COUNT(DISTINCT fh.hotspot_id)   AS total_hotspots,
    COUNT(DISTINCT eq.earthquake_id) AS total_earthquakes
FROM {DWH_SCHEMA}.dim_date d
CROSS JOIN {DWH_SCHEMA}.dim_location l
LEFT JOIN {DWH_SCHEMA}.fact_fire_hotspot fh
    ON d.date_key = fh.date_key AND l.location_key = fh.location_key
LEFT JOIN {DWH_SCHEMA}.fact_earthquake eq
    ON d.date_key = eq.date_key AND l.location_key = eq.location_key
GROUP BY d.year, d.month, l.province_name;

CREATE OR REPLACE VIEW {MART_SCHEMA}.v_high_risk_zones AS
SELECT
    l.grid_cell_id,
    l.latitude,
    l.longitude,
    l.province_name,
    COUNT(DISTINCT fh.hotspot_id)    AS total_hotspots,
    COUNT(DISTINCT eq.earthquake_id) AS total_earthquakes
FROM {DWH_SCHEMA}.dim_location l
LEFT JOIN {DWH_SCHEMA}.fact_fire_hotspot fh ON l.location_key = fh.location_key
LEFT JOIN {DWH_SCHEMA}.fact_earthquake eq ON l.location_key = eq.location_key
GROUP BY l.grid_cell_id, l.latitude, l.longitude, l.province_name;

"""


def run_ddl(con):
    for statement in DDL.split(";"):
        stmt = statement.strip()
        if stmt:
            con.execute(stmt + ";")
