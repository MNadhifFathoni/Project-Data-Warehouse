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
    eq_daily_trend,
    eq_map_data,
    top_eq_provinces,
    eq_magnitude_distribution,
    monthly_trend,
)


def show():
    st.title("🌍 Earthquake Analysis")
    st.markdown("Earthquake events detected by USGS in the Indonesia region.")

    trend = eq_daily_trend()
    if trend.empty:
        st.warning("No earthquake data available.")
        return

    total = trend["count"].sum()
    max_mag = trend["max_mag"].max()
    peak = trend.loc[trend["count"].idxmax()]
    k1, k2, k3 = st.columns(3)
    k1.metric("Total Earthquakes", f"{total:,}")
    k2.metric("Max Magnitude", max_mag)
    k3.metric("Peak Day", f"{peak['count']:,} ({peak['full_date']})")

    # Daily trend
    st.subheader("Daily Earthquake Count")
    fig = px.line(trend, x="full_date", y="count",
                  labels={"full_date": "Date", "count": "Earthquakes"},
                  title="Earthquakes per Day")
    fig.add_scatter(x=trend["full_date"], y=trend["max_mag"],
                    yaxis="y2", name="Max Mag", line=dict(color="red", dash="dot"))
    fig.update_layout(yaxis2=dict(overlaying="y", side="right", title="Max Magnitude"))
    st.plotly_chart(fig, width='stretch')

    # Map
    st.subheader("Earthquake Map")
    eq = eq_map_data()
    if not eq.empty:
        center_lat, center_lon = -2.5, 118.0
        m = folium.Map(location=[center_lat, center_lon], zoom_start=5,
                       tiles="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
                       attr="&copy; <a href='https://www.openstreetmap.org/copyright'>OpenStreetMap</a> contributors &copy; <a href='https://carto.com/'>CARTO</a>")

        for _, r in eq.iterrows():
            mag = r["mag"] or 2.0
            radius = max(mag * 3, 3)
            color = "#ff4444" if r["tsunami"] == 1 else "#ffaa00"
            popup = f"M {mag} | depth {r['depth']}km | {r['province_name'] or 'Unknown'}"
            folium.CircleMarker(
                location=[r["latitude"], r["longitude"]],
                radius=radius,
                color=color,
                fill=True,
                fillOpacity=0.6,
                popup=popup,
                tooltip=f"M{mag}",
            ).add_to(m)

        st_folium(m, width=None, height=500)
        st.caption(f"Showing {len(eq):,} earthquakes. Red = tsunami alert.")
    else:
        st.info("No map data available.")

    # Magnitude distribution
    st.subheader("Magnitude Distribution")
    md = eq_magnitude_distribution()
    if not md.empty:
        fig = px.bar(md, x="mag_bucket", y="total",
                     labels={"mag_bucket": "Magnitude Range", "total": "Count"},
                     title="Earthquake Count by Magnitude")
        st.plotly_chart(fig, width='stretch')

    # Top provinces
    st.subheader("Earthquakes by Province")
    c1, c2 = st.columns(2)

    with c1:
        ep = top_eq_provinces(15)
        if not ep.empty:
            fig = px.bar(ep, x="total", y="province_name", orientation="h",
                         color="max_mag", color_continuous_scale="Blues",
                         labels={"total": "Count", "province_name": ""})
            fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=500)
            st.plotly_chart(fig, width='stretch')

    with c2:
        ep2 = top_eq_provinces(15)
        if not ep2.empty:
            fig = px.bar(ep2, x="max_mag", y="province_name", orientation="h",
                         color="total", color_continuous_scale="Blues",
                         labels={"max_mag": "Max Magnitude", "province_name": ""})
            fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=500)
            st.plotly_chart(fig, width='stretch')

    # Monthly breakdown
    st.subheader("Monthly Breakdown")
    mt = monthly_trend()
    if not mt.empty:
        fig = px.bar(mt, x="month", y="eq_count",
                     labels={"month": "Month", "eq_count": "Earthquakes"},
                     title="Earthquakes per Month (2025)",
                     color_discrete_sequence=["#1f77b4"])
        st.plotly_chart(fig, width='stretch')

    st.caption("Data source: USGS Earthquake Hazards Program")
