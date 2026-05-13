from .config import DWH_SCHEMA, MART_SCHEMA

TOP_PROVINCES_HOTSPOT = f"""
SELECT l.province_name, COUNT(*) AS total_hotspots, AVG(f.frp) AS avg_frp
FROM {DWH_SCHEMA}.fact_fire_hotspot f
JOIN {DWH_SCHEMA}.dim_location l ON f.location_key = l.location_key
GROUP BY l.province_name
ORDER BY total_hotspots DESC
LIMIT 10;
"""

TOP_PROVINCES_EARTHQUAKE = f"""
SELECT l.province_name, COUNT(*) AS total_eq, MAX(f.mag) AS max_mag
FROM {DWH_SCHEMA}.fact_earthquake f
JOIN {DWH_SCHEMA}.dim_location l ON f.location_key = l.location_key
GROUP BY l.province_name
ORDER BY total_eq DESC
LIMIT 10;
"""

MONTHLY_FIRE_TREND = f"""
SELECT d.year, d.month, COUNT(*) AS hotspot_count
FROM {DWH_SCHEMA}.fact_fire_hotspot f
JOIN {DWH_SCHEMA}.dim_date d ON f.date_key = d.date_key
GROUP BY d.year, d.month
ORDER BY d.year, d.month;
"""

MONTHLY_EQ_TREND = f"""
SELECT d.year, d.month, COUNT(*) AS eq_count, MAX(f.mag) AS max_mag
FROM {DWH_SCHEMA}.fact_earthquake f
JOIN {DWH_SCHEMA}.dim_date d ON f.date_key = d.date_key
GROUP BY d.year, d.month
ORDER BY d.year, d.month;
"""

SATELLITE_COMPARISON = f"""
SELECT s.satellite_source, s.sensor_type, COUNT(*) AS total_detections
FROM {DWH_SCHEMA}.fact_fire_hotspot f
JOIN {DWH_SCHEMA}.dim_satellite_source s ON f.src_key = s.src_key
GROUP BY s.satellite_source, s.sensor_type
ORDER BY total_detections DESC;
"""

DAYS_WITH_MOST_EVENTS = f"""
SELECT d.full_date, COUNT(*) AS total_events
FROM (
    SELECT date_key FROM {DWH_SCHEMA}.fact_fire_hotspot
    UNION ALL
    SELECT date_key FROM {DWH_SCHEMA}.fact_earthquake
) ev
JOIN {DWH_SCHEMA}.dim_date d ON ev.date_key = d.date_key
GROUP BY d.full_date
ORDER BY total_events DESC
LIMIT 20;
"""

QUERIES = {
    "top_provinces_hotspot": TOP_PROVINCES_HOTSPOT,
    "top_provinces_earthquake": TOP_PROVINCES_EARTHQUAKE,
    "monthly_fire_trend": MONTHLY_FIRE_TREND,
    "monthly_eq_trend": MONTHLY_EQ_TREND,
    "satellite_comparison": SATELLITE_COMPARISON,
    "days_with_most_events": DAYS_WITH_MOST_EVENTS,
}
