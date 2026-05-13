import sys
from pathlib import Path

# Ensure project root is on path
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import streamlit as st

from dashboard.pages import overview, fire_hotspots, earthquakes

st.set_page_config(
    page_title="Disaster Monitoring Dashboard — Indonesia",
    page_icon="🌋",
    layout="wide",
)

pages = {
    "📊 Overview": overview.show,
    "🔥 Fire Hotspots": fire_hotspots.show,
    "🌍 Earthquakes": earthquakes.show,
}

with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/9/9f/Flag_of_Indonesia.svg", width=60)
    st.title("Disaster Monitoring")
    st.caption("NASA FIRMS + USGS Earthquake")
    st.divider()
    choice = st.radio("Navigation", list(pages.keys()), label_visibility="collapsed")
    st.divider()
    st.caption("Data Warehouse Project")
    st.caption("Semester 4 — 2025/2026")

pages[choice]()
