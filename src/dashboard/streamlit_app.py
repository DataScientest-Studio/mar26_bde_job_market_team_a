from __future__ import annotations

import streamlit as st

from src.dashboard.app_pages.analytics import render_analytics_page
from src.dashboard.app_pages.machine_learning import render_ml_page
from src.dashboard.config import API_BASE_URL
from src.dashboard.ui import inject_styles


st.set_page_config(
    page_title="Job Market Dashboard",
    layout="wide",
)

inject_styles()


def analytics_page() -> None:
    render_analytics_page(API_BASE_URL)


def predictions_page() -> None:
    render_ml_page(API_BASE_URL)


page = st.navigation(
    [
        st.Page(analytics_page, title="Analyse du marché", default=True),
        st.Page(predictions_page, title="Prédictions"),
    ],
    position="sidebar",
)
st.sidebar.caption(f"API: {API_BASE_URL}")
page.run()
