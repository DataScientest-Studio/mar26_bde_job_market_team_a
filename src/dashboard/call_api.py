from __future__ import annotations

from typing import Any

import requests
import streamlit as st

from src.dashboard.config import REQUEST_TIMEOUT


@st.cache_data(show_spinner=False, ttl=300)
def load_dashboard_stats(api_base_url: str) -> dict[str, Any]:
    response = requests.get(f"{api_base_url}/stats", timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


@st.cache_data(show_spinner=False, ttl=300)
def load_ml_stats(api_base_url: str) -> dict[str, Any]:
    response = requests.get(f"{api_base_url}/stats/ml", timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


@st.cache_data(show_spinner=False, ttl=300)
def load_lookups(api_base_url: str, limit: int = 200) -> dict[str, Any]:
    response = requests.get(f"{api_base_url}/lookups", params={"limit": limit}, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


@st.cache_data(show_spinner=False, ttl=300)
def load_job_title_lookup(api_base_url: str) -> list[dict[str, Any]]:
    response = requests.get(f"{api_base_url}/lookups/job-titles", timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


@st.cache_data(show_spinner=False, ttl=300)
def load_analytics_summary(
    api_base_url: str,
    dimension: str,
    selected_values: tuple[str, ...],
    selected_job_titles: tuple[str, ...] = (),
) -> dict[str, Any]:
    params: list[tuple[str, str]] = [("dimension", dimension)]
    params.extend(("values", value) for value in selected_values)
    params.extend(("job_titles", value) for value in selected_job_titles)
    response = requests.get(f"{api_base_url}/stats/summary", params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


@st.cache_data(show_spinner=False, ttl=300)
def load_offer_breakdown(
    api_base_url: str,
    group_dimension: str,
    filter_dimension: str,
    selected_values: tuple[str, ...],
    selected_job_titles: tuple[str, ...] = (),
    limit: int = 30,
) -> list[dict[str, Any]]:
    params: list[tuple[str, str]] = [
        ("group_dimension", group_dimension),
        ("filter_dimension", filter_dimension),
        ("limit", str(limit)),
    ]
    params.extend(("values", value) for value in selected_values)
    params.extend(("job_titles", value) for value in selected_job_titles)
    response = requests.get(f"{api_base_url}/stats/breakdown", params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


@st.cache_data(show_spinner=False, ttl=300)
def load_salary_breakdown(
    api_base_url: str,
    group_dimension: str,
    filter_dimension: str,
    selected_values: tuple[str, ...],
    selected_job_titles: tuple[str, ...] = (),
) -> list[dict[str, Any]]:
    params: list[tuple[str, str]] = [
        ("group_dimension", group_dimension),
        ("filter_dimension", filter_dimension),
        ("limit", "30"),
    ]
    params.extend(("values", value) for value in selected_values)
    params.extend(("job_titles", value) for value in selected_job_titles)
    response = requests.get(f"{api_base_url}/stats/salary_breakdown", params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


def post_api(api_base_url: str, path: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = requests.post(f"{api_base_url}{path}", json=payload, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()
