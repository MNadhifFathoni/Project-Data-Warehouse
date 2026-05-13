import sys
from pathlib import Path
_root = Path(__file__).resolve().parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import streamlit as st
import plotly.express as px

from dashboard.utils import (
    overview_stats,
    monthly_trend,
    top_fire_provinces,
    top_eq_provinces,
    satellite_comparison,
)


def show():
    st.title("📊 Overview")
    st.markdown("Disaster monitoring dashboard for Indonesia — data from **NASA FIRMS** (fire hotspots) and **USGS Earthquake** API.")

    stats = overview_stats()
    if stats.empty:
        st.warning("No data loaded. Run `python main.py load-dwh` first.")
        return

    r = stats.iloc[0]

    # KPI row
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("🔥 Fire Hotspots", f"{r['total_hotspots']:,}")
    k2.metric("🌍 Earthquakes", f"{r['total_earthquakes']:,}")
    k3.metric("📍 Unique Locations", f"{r['total_locations']:,}")
    k4.metric("Avg FRP", r["avg_frp"])
    k5.metric("Max Magnitude", r["max_magnitude"])

    st.caption(f"Data range: {r['data_start']} → {r['data_end']}")

    # Monthly trend
    st.subheader("Monthly Trend Comparison")
    trend = monthly_trend()
    if not trend.empty:
        fig = px.line(
            trend, x="month", y=["fire_count", "eq_count"],
            labels={"value": "Count", "month": "Month", "variable": "Type"},
            title="Fire Hotspots vs Earthquakes per Month (2025)",
            markers=True,
        )
        fig.update_layout(legend=dict(orientation="h", y=1.1))
        st.plotly_chart(fig, width='stretch')

    # Top provinces
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("🔥 Top Fire Provinces")
        fp = top_fire_provinces()
        if not fp.empty:
            fig = px.bar(fp, x="total", y="province_name", orientation="h",
                         color="avg_frp", color_continuous_scale="OrRd",
                         labels={"total": "Hotspot Count", "province_name": ""})
            fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=400)
            st.plotly_chart(fig, width='stretch')

    with c2:
        st.subheader("🌍 Top Earthquake Provinces")
        ep = top_eq_provinces()
        if not ep.empty:
            fig = px.bar(ep, x="total", y="province_name", orientation="h",
                         color="max_mag", color_continuous_scale="Blues",
                         labels={"total": "Earthquake Count", "province_name": ""})
            fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=400)
            st.plotly_chart(fig, width='stretch')

    # Satellite comparison
    st.subheader("🛰️ Satellite Source Comparison")
    sat = satellite_comparison()
    if not sat.empty:
        fig = px.pie(sat, values="total", names="satellite_source", title="Detections by Satellite")
        st.plotly_chart(fig, width='stretch')
