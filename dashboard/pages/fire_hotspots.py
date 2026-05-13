import sys
from pathlib import Path
_root = Path(__file__).resolve().parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import streamlit as st
import folium
from streamlit_folium import st_folium
import plotly.express as px

from dashboard.utils import (
    fire_daily_trend,
    fire_heatmap_data,
    top_fire_provinces,
    fire_by_daynight,
    monthly_trend,
)


def show():
    st.title("🔥 Fire Hotspot Analysis")
    st.markdown("Fire hotspots detected by VIIRS NOAA-21 satellite over Indonesia.")

    trend = fire_daily_trend()
    if trend.empty:
        st.warning("No fire hotspot data available.")
        return

    # KPI
    total = trend["count"].sum()
    avg_frp = trend["avg_frp"].mean()
    peak = trend.loc[trend["count"].idxmax()]
    k1, k2, k3 = st.columns(3)
    k1.metric("Total Hotspots", f"{total:,}")
    k2.metric("Avg FRP", f"{avg_frp:.2f}")
    k3.metric("Peak Day", f"{peak['count']:,} ({peak['full_date']})")

    # Daily trend
    st.subheader("Daily Hotspot Count")
    fig = px.line(trend, x="full_date", y="count",
                  labels={"full_date": "Date", "count": "Hotspots"},
                  title="Fire Hotspots per Day")
    fig.add_scatter(x=trend["full_date"], y=trend["avg_frp"],
                    yaxis="y2", name="Avg FRP", line=dict(color="orange", dash="dot"))
    fig.update_layout(yaxis2=dict(overlaying="y", side="right", title="Avg FRP"))
    st.plotly_chart(fig, width='stretch')

    # Map
    st.subheader("Spatial Distribution")
    max_points = st.slider("Max points on map", 1000, 50000, 10000, step=1000)
    hm = fire_heatmap_data(max_rows=max_points)
    if not hm.empty:
        from folium.plugins import HeatMap
        center_lat, center_lon = -2.5, 118.0
        m = folium.Map(location=[center_lat, center_lon], zoom_start=5,
                       tiles="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
                       attr="&copy; <a href='https://www.openstreetmap.org/copyright'>OpenStreetMap</a> contributors &copy; <a href='https://carto.com/'>CARTO</a>")

        heat_data = hm[["latitude", "longitude"]].values.tolist()
        HeatMap(
            heat_data,
            radius=8,
            blur=12,
            max_zoom=8,
            min_opacity=0.3,
        ).add_to(m)

        st_folium(m, width=None, height=500)
        st.caption(f"Showing {len(hm):,} hotspots (filtered by FRP > 0)")
    else:
        st.info("No map data available.")

    # By province
    st.subheader("Hotspots by Province")
    c1, c2 = st.columns(2)

    with c1:
        fp = top_fire_provinces(20)
        if not fp.empty:
            fig = px.bar(fp, x="total", y="province_name", orientation="h",
                         color="avg_frp", color_continuous_scale="OrRd",
                         labels={"total": "Count", "province_name": ""})
            fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=500)
            st.plotly_chart(fig, width='stretch')

    with c2:
        fp2 = top_fire_provinces(20)
        if not fp2.empty:
            fig = px.bar(fp2, x="avg_frp", y="province_name", orientation="h",
                         color="total", color_continuous_scale="OrRd",
                         labels={"avg_frp": "Avg FRP", "province_name": ""})
            fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=500)
            st.plotly_chart(fig, width='stretch')

    # Day/Night split
    st.subheader("Day vs Night Detection")
    dn = fire_by_daynight()
    if not dn.empty:
        c1, c2 = st.columns(2)
        with c1:
            fig = px.pie(dn, values="total", names="daynight", title="Day vs Night")
            st.plotly_chart(fig, width='stretch')
        with c2:
            fig = px.bar(dn, x="daynight", y="avg_frp", color="daynight",
                         labels={"daynight": "Period", "avg_frp": "Avg FRP"})
            st.plotly_chart(fig, width='stretch')

    # Monthly breakdown
    st.subheader("Monthly Breakdown")
    mt = monthly_trend()
    if not mt.empty:
        fig = px.bar(mt, x="month", y="fire_count",
                     labels={"month": "Month", "fire_count": "Hotspots"},
                     title="Fire Hotspots per Month (2025)")
        st.plotly_chart(fig, width='stretch')

    st.caption("Data source: NASA FIRMS — VIIRS NOAA-21 NRT")
