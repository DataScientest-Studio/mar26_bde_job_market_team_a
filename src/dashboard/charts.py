from __future__ import annotations

import altair as alt
import pandas as pd

from src.dashboard.ui import CHART_COLORS


def bar_chart(frame: pd.DataFrame, label_column: str, value_column: str, title: str) -> alt.Chart:
    return (
        alt.Chart(frame)
        .mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4)
        .encode(
            alt.X(f"{value_column}:Q", title="Offres"),
            alt.Y(f"{label_column}:N", title=None, sort="-x"),
            alt.Color(f"{value_column}:Q", legend=None, scale=alt.Scale(scheme="blues")),
            tooltip=[
                alt.Tooltip(f"{label_column}:N", title=None),
                alt.Tooltip(f"{value_column}:Q", title="Offres", format=",.0f"),
            ],
        )
        .properties(title=title, height=320)
    )


def salary_bar_chart(frame: pd.DataFrame, label_column: str, title: str, tooltip_label: str) -> alt.Chart:
    return (
        alt.Chart(frame)
        .mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4, color="#059669")
        .encode(
            alt.X("avg_salary:Q", title="Salaire annuel moyen"),
            alt.Y(f"{label_column}:N", title=None, sort="-x"),
            tooltip=[
                alt.Tooltip(f"{label_column}:N", title=tooltip_label),
                alt.Tooltip("avg_salary:Q", title="Salaire", format=",.0f"),
            ],
        )
        .properties(title=title, height=320)
    )


def source_donut_chart(frame: pd.DataFrame) -> alt.Chart:
    return (
        alt.Chart(frame)
        .mark_arc(innerRadius=55, outerRadius=110)
        .encode(
            theta=alt.Theta("nb_offres:Q"),
            color=alt.Color("source_system:N", title=None, scale=alt.Scale(range=CHART_COLORS)),
            tooltip=[
                alt.Tooltip("source_system:N", title="Source"),
                alt.Tooltip("nb_offres:Q", title="Offres", format=",.0f"),
            ],
        )
        .properties(title="Sources", height=320)
    )
