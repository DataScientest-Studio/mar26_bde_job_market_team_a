from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st


CHART_COLORS = [
    "#2563eb",
    "#059669",
    "#f97316",
    "#7c3aed",
    "#dc2626",
    "#0891b2",
    "#4b5563",
    "#ca8a04",
]
MISSING_LABELS = {"", "Non renseigné", "Non renseignÃ©", "None", "nan"}


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 1.4rem;
            padding-bottom: 2.5rem;
        }
        [data-testid="stMetric"] {
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 0.85rem 1rem;
            background: #ffffff;
        }
        [data-testid="stMetricLabel"] {
            color: #475569;
        }
        [data-testid="stMetricValue"] {
            color: #111827;
        }
        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 8px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def clean_display_text(value: Any) -> Any:
    if not isinstance(value, str) or not any(marker in value for marker in ("Ãƒ", "Ã‚", "Ã¢")):
        return value
    try:
        return value.encode("latin1").decode("utf-8")
    except UnicodeError:
        return value


def clean_text_columns(frame: pd.DataFrame) -> pd.DataFrame:
    cleaned = frame.copy()
    object_columns = cleaned.select_dtypes(include=["object"]).columns
    for column in object_columns:
        cleaned[column] = cleaned[column].map(clean_display_text)
    return cleaned


def compact_currency(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:,.0f} EUR".replace(",", " ")


def compact_number(value: float | int | None, digits: int = 3) -> str:
    if value is None:
        return "-"
    if isinstance(value, int):
        return f"{value:,}".replace(",", " ")
    return f"{value:.{digits}f}"


def metric_value(metrics: dict[str, Any], key: str) -> float | None:
    value = metrics.get(key)
    return float(value) if value is not None else None


def lookup_options(lookups: dict[str, Any], key: str) -> tuple[list[str], dict[str, str]]:
    rows = lookups.get(key, [])
    values = [row["value"] for row in rows if row.get("value")]
    labels = {
        row["value"]: f"{row['label']} ({row.get('count', 0)})"
        for row in rows
        if row.get("value")
    }
    return values, labels


def optional_select(label: str, values: list[str], labels: dict[str, str], *, index: int = 0) -> str | None:
    options = [""] + values
    selected = st.selectbox(
        label,
        options=options,
        index=min(index, len(options) - 1),
        format_func=lambda value: "Non renseigné" if value == "" else labels.get(value, value),
    )
    return selected or None
