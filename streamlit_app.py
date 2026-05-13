"""Streamlit entry point for deployment (auto-detected by Streamlit Cloud)."""
import sys
from pathlib import Path

_root = Path(__file__).parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

# Import runs the dashboard app
import dashboard.app  # noqa: F401
