from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from src.dashboard.ui import MISSING_LABELS, clean_text_columns


@st.cache_data(show_spinner=False, ttl=300)
def build_analytics_frames(payload: dict[str, Any]) -> dict[str, pd.DataFrame]:
    return {
        "sector": prepare_trend_frame(to_frame(payload, "sector", ["sector", "year", "nb_offres"]), "sector"),
        "region": prepare_trend_frame(to_frame(payload, "region", ["region", "year", "nb_offres"]), "region"),
        "contract": prepare_trend_frame(
            to_frame(payload, "contract", ["contract_type", "year", "nb_offres"]),
            "contract_type",
        ),
        "salary": prepare_trend_frame(
            to_frame(payload, "salary", ["job_title", "year", "avg_salary", "nb_offres"]),
            "job_title",
        ),
        "skill": to_frame(payload, "skill", ["skill_name", "skill_category", "nb_offres"]),
        "advantage": to_frame(payload, "advantage", ["advantage_name", "nb_offres"]),
        "source": to_frame(payload, "source", ["source_system", "nb_offres"]),
    }


def to_frame(payload: dict[str, Any], key: str, columns: list[str]) -> pd.DataFrame:
    frame = pd.DataFrame(payload.get(key, []))
    for column in columns:
        if column not in frame.columns:
            frame[column] = pd.Series(dtype="object")
    return clean_text_columns(frame[columns])


def prepare_trend_frame(frame: pd.DataFrame, label_column: str) -> pd.DataFrame:
    if frame.empty:
        return frame

    prepared = frame.copy()
    prepared["year"] = pd.to_numeric(prepared["year"], errors="coerce")
    prepared["nb_offres"] = pd.to_numeric(prepared["nb_offres"], errors="coerce").fillna(0).astype(int)
    prepared[label_column] = prepared[label_column].fillna("Non renseigné")
    return prepared.dropna(subset=["year"]).assign(year=lambda data: data["year"].astype(int))


def filtered_years(*frames: pd.DataFrame) -> list[int]:
    years: set[int] = set()
    for frame in frames:
        if not frame.empty and "year" in frame.columns:
            years.update(pd.to_numeric(frame["year"], errors="coerce").dropna().astype(int).tolist())
    return sorted(years)


def filter_by_year(frame: pd.DataFrame, start_year: int | None, end_year: int | None) -> pd.DataFrame:
    if frame.empty or start_year is None or end_year is None or "year" not in frame.columns:
        return frame
    return frame[(frame["year"] >= start_year) & (frame["year"] <= end_year)]


def filter_by_labels(frame: pd.DataFrame, label_column: str, selected_labels: list[str]) -> pd.DataFrame:
    if frame.empty or not selected_labels:
        return frame
    return frame[frame[label_column].isin(selected_labels)]


def top_label(frame: pd.DataFrame, label_column: str) -> str:
    if frame.empty:
        return "-"
    filtered = frame[~frame[label_column].astype(str).isin(MISSING_LABELS)]
    if filtered.empty:
        return "-"
    grouped = filtered.groupby(label_column, as_index=False)["nb_offres"].sum()
    if grouped.empty:
        return "-"
    return str(grouped.sort_values("nb_offres", ascending=False).iloc[0][label_column])


def total_offers(frame: pd.DataFrame) -> int:
    if frame.empty:
        return 0
    return int(frame["nb_offres"].sum())


def weighted_average_salary(salary_frame: pd.DataFrame) -> float | None:
    if salary_frame.empty:
        return None
    prepared = salary_frame.copy()
    prepared["avg_salary"] = pd.to_numeric(prepared["avg_salary"], errors="coerce")
    prepared["nb_offres"] = pd.to_numeric(prepared["nb_offres"], errors="coerce").fillna(0)
    prepared = prepared.dropna(subset=["avg_salary"])
    total_weight = prepared["nb_offres"].sum()
    if total_weight == 0:
        return None
    return float((prepared["avg_salary"] * prepared["nb_offres"]).sum() / total_weight)


def label_options(frame: pd.DataFrame, label_column: str, limit: int = 12) -> list[str]:
    if frame.empty:
        return []
    filtered = frame[~frame[label_column].astype(str).isin(MISSING_LABELS)]
    if filtered.empty:
        return []
    filtered = filtered.copy()
    filtered["nb_offres"] = pd.to_numeric(filtered["nb_offres"], errors="coerce").fillna(0).astype(int)
    grouped = filtered.groupby(label_column, as_index=False)["nb_offres"].sum()
    return grouped.sort_values("nb_offres", ascending=False).head(limit)[label_column].tolist()


def sorted_label_options(frame: pd.DataFrame, label_column: str, limit: int = 100) -> list[str]:
    values = label_options(frame, label_column, limit=limit)
    return sorted(values, key=lambda value: str(value).casefold())


def selected_offers_frame(frame: pd.DataFrame, label_column: str) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=["label", "nb_offres"])

    prepared = frame.copy()
    prepared["nb_offres"] = pd.to_numeric(prepared["nb_offres"], errors="coerce").fillna(0).astype(int)
    return (
        prepared.groupby(label_column, as_index=False)["nb_offres"]
        .sum()
        .rename(columns={label_column: "label"})
        .sort_values("nb_offres", ascending=False)
    )


def salary_display_frame(salary_breakdown: pd.DataFrame, fallback_frame: pd.DataFrame) -> pd.DataFrame:
    if not salary_breakdown.empty:
        prepared = salary_breakdown.rename(columns={"label": "salary_label"}).copy()
    else:
        prepared = fallback_frame.copy()
        if "job_title" in prepared.columns:
            prepared = prepared.rename(columns={"job_title": "salary_label"})

    if prepared.empty:
        return pd.DataFrame(columns=["salary_label", "avg_salary", "nb_offres"])

    prepared["avg_salary"] = pd.to_numeric(prepared["avg_salary"], errors="coerce")
    prepared["nb_offres"] = pd.to_numeric(prepared["nb_offres"], errors="coerce").fillna(0).astype(int)
    return (
        prepared.dropna(subset=["avg_salary"])
        .groupby("salary_label", as_index=False)
        .agg(avg_salary=("avg_salary", "mean"), nb_offres=("nb_offres", "sum"))
        .sort_values("avg_salary", ascending=False)
    )
