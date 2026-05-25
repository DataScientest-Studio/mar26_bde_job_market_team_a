from __future__ import annotations

from typing import Any

import pandas as pd
import requests
import streamlit as st

from src.dashboard.call_api import (
    load_analytics_summary,
    load_dashboard_stats,
    load_job_title_lookup,
    load_offer_breakdown,
    load_salary_breakdown,
)
from src.dashboard.charts import bar_chart, salary_bar_chart
from src.dashboard.dataframes import (
    build_analytics_frames,
    filter_by_labels,
    filter_by_year,
    filtered_years,
    salary_display_frame,
    selected_offers_frame,
    sorted_label_options,
    top_label,
    total_offers,
    weighted_average_salary,
)
from src.dashboard.ui import compact_currency


def select_year_range(years: list[int]) -> tuple[int | None, int | None]:
    if not years:
        return None, None
    if len(years) == 1:
        return years[0], years[0]
    return st.slider("Période", min_value=min(years), max_value=max(years), value=(min(years), max(years)))


def render_raw_data(frames: dict[str, pd.DataFrame]) -> None:
    sections = {
        "Secteurs": frames["sector"],
        "Régions": frames["region"],
        "Contrats": frames["contract"],
        "Salaires": frames["salary"],
        "Compétences": frames["skill"],
        "Avantages": frames["advantage"],
        "Sources": frames["source"],
    }

    for section, frame in sections.items():
        with st.expander(section):
            st.dataframe(frame, width="stretch", hide_index=True)


def render_signal_cards(skill_df: pd.DataFrame, advantage_df: pd.DataFrame, contract_df: pd.DataFrame) -> None:
    st.subheader("Signaux métier")
    signal_cols = st.columns(3)

    with signal_cols[0].container(border=True):
        skill_display = skill_df.copy()
        if not skill_display.empty:
            skill_display["label"] = skill_display["skill_name"] + " - " + skill_display["skill_category"]
            skill_display["nb_offres"] = pd.to_numeric(skill_display["nb_offres"], errors="coerce").fillna(0).astype(int)
            st.altair_chart(bar_chart(skill_display.head(12), "label", "nb_offres", "Top compétences"), width="stretch")
        else:
            st.info("Aucune compétence disponible.")

    with signal_cols[1].container(border=True):
        advantage_display = advantage_df.copy()
        if not advantage_display.empty:
            advantage_display["nb_offres"] = pd.to_numeric(advantage_display["nb_offres"], errors="coerce").fillna(0).astype(int)
            st.altair_chart(
                bar_chart(advantage_display.head(12), "advantage_name", "nb_offres", "Top avantages"),
                width="stretch",
            )
        else:
            st.info("Aucun avantage disponible.")

    with signal_cols[2].container(border=True):
        contract_display = contract_df.copy()
        if not contract_display.empty:
            contract_display["nb_offres"] = pd.to_numeric(contract_display["nb_offres"], errors="coerce").fillna(0).astype(int)
            contract_display = (
                contract_display.groupby("contract_type", as_index=False)["nb_offres"]
                .sum()
                .sort_values("nb_offres", ascending=False)
                .head(12)
            )
            st.altair_chart(
                bar_chart(contract_display, "contract_type", "nb_offres", "Top contrats"),
                width="stretch",
            )
        else:
            st.info("Aucun contrat disponible.")


def render_analytics_page(api_base_url: str) -> None:
    st.title("Job Market")
    st.caption("Dashboard analytique alimenté par l'API FastAPI du projet.")

    try:
        with st.spinner("Chargement des données marché..."):
            stats = load_dashboard_stats(api_base_url)
            frames = build_analytics_frames(stats)
    except requests.RequestException as exc:
        st.error(f"API indisponible: {api_base_url}")
        st.caption(str(exc))
        st.stop()

    sector_df = frames["sector"]
    region_df = frames["region"]
    contract_df = frames["contract"]
    salary_df = frames["salary"]
    skill_df = frames["skill"]
    advantage_df = frames["advantage"]
    source_df = frames["source"]

    years = filtered_years(sector_df, region_df, contract_df, salary_df)
    left_col, main_col = st.columns([1, 3])

    dimension_config: dict[str, tuple[pd.DataFrame, str, str, str]] = {
        "Secteurs": (sector_df, "sector", "secteur", "sector"),
        "Régions": (region_df, "region", "région", "region"),
        "Sources": (source_df, "source_system", "source", "source"),
    }

    with left_col.container(border=True):
        st.subheader("Filtres")
        start_year, end_year = select_year_range(years)

        salary_filtered = filter_by_year(salary_df, start_year, end_year)
        sector_filtered = filter_by_year(sector_df, start_year, end_year)
        region_filtered = filter_by_year(region_df, start_year, end_year)

        st.caption("Filtre 1")
        job_rows = load_job_title_lookup(api_base_url)
        job_options = [row["value"] for row in job_rows if row.get("value")]
        job_labels = {
            row["value"]: f"{row['label']} ({row.get('count', 0)})"
            for row in job_rows
            if row.get("value")
        }
        selected_job_title = st.selectbox(
            "Métier",
            options=["Tous les métiers"] + job_options,
            index=0,
            format_func=lambda value: value if value == "Tous les métiers" else job_labels.get(value, value),
        )
        selected_job_titles = [] if selected_job_title == "Tous les métiers" else [selected_job_title]
        selected_jobs_tuple = tuple(selected_job_titles)

        st.caption("Filtre 2")
        dimension = st.pills(
            "Analyse par",
            options=["Régions", "Sources", "Secteurs"],
            default="Régions",
        )

        trend_df, label_column, dimension_label, api_dimension = dimension_config[dimension]
        trend_filtered = filter_by_year(trend_df, start_year, end_year)
        if selected_jobs_tuple:
            try:
                dimension_rows = load_offer_breakdown(
                    api_base_url,
                    api_dimension,
                    api_dimension,
                    (),
                    selected_jobs_tuple,
                    limit=100,
                )
                dimension_options = sorted(
                    [row["label"] for row in dimension_rows if row.get("label")],
                    key=lambda value: str(value).casefold(),
                )
            except requests.RequestException:
                dimension_options = sorted_label_options(trend_filtered, label_column, limit=100)
        else:
            dimension_options = sorted_label_options(trend_filtered, label_column, limit=100)

        selected_dimension_values = st.multiselect(
            f"{dimension_label.capitalize()}s",
            options=dimension_options,
            default=[],
            placeholder=f"Toutes les valeurs de {dimension_label}",
        )

        st.caption(f"API: {api_base_url}")
        if st.button("Rafraîchir", width="stretch"):
            load_dashboard_stats.clear()
            build_analytics_frames.clear()
            load_job_title_lookup.clear()
            load_analytics_summary.clear()
            load_offer_breakdown.clear()
            load_salary_breakdown.clear()
            st.rerun()

    trend_selected = filter_by_labels(trend_filtered, label_column, selected_dimension_values)
    selected_tuple = tuple(selected_dimension_values)

    try:
        with st.spinner("Mise à jour des indicateurs..."):
            selected_summary = load_analytics_summary(api_base_url, api_dimension, selected_tuple, selected_jobs_tuple)
            offer_breakdown = pd.DataFrame(
                load_offer_breakdown(api_base_url, api_dimension, api_dimension, selected_tuple, selected_jobs_tuple)
            )
            salary_breakdown = pd.DataFrame(
                load_salary_breakdown(api_base_url, api_dimension, api_dimension, selected_tuple, selected_jobs_tuple)
            )
    except requests.RequestException:
        selected_summary: dict[str, Any] = {
            "total_offers": total_offers(trend_selected),
            "top_sector": top_label(sector_filtered, "sector"),
            "top_region": top_label(region_filtered, "region"),
            "top_contract": top_label(contract_df, "contract_type"),
            "avg_salary": weighted_average_salary(salary_filtered),
        }
        offer_breakdown = pd.DataFrame()
        salary_breakdown = pd.DataFrame()

    with main_col:
        metric_cols = st.columns(5)
        metric_cols[0].metric("Offres analysées", f"{int(selected_summary.get('total_offers') or 0):,}".replace(",", " "))
        metric_cols[1].metric("Top secteur", selected_summary.get("top_sector") or "-")
        metric_cols[2].metric("Top région", selected_summary.get("top_region") or "-")
        metric_cols[3].metric("Top contrat", selected_summary.get("top_contract") or "-")
        metric_cols[4].metric("Salaire moyen", compact_currency(selected_summary.get("avg_salary")))

        chart_cols = st.columns(2)
        offers_display = (
            offer_breakdown.rename(columns={"label": "label"})
            if not offer_breakdown.empty
            else selected_offers_frame(trend_selected, label_column)
        )
        salary_chart_frame = salary_display_frame(salary_breakdown, pd.DataFrame())

        with chart_cols[0].container(border=True):
            if offers_display.empty:
                st.info("Aucune donnée d'offre disponible pour cette sélection.")
            else:
                st.altair_chart(
                    bar_chart(offers_display, "label", "nb_offres", f"Nombre d'offres par {dimension_label}"),
                    width="stretch",
                )

        with chart_cols[1].container(border=True):
            if salary_chart_frame.empty:
                st.info("Aucune donnée de salaire disponible pour cette sélection.")
            else:
                st.altair_chart(
                    salary_bar_chart(
                        salary_chart_frame,
                        "salary_label",
                        f"Salaire moyen par {dimension_label}",
                        dimension_label.capitalize(),
                    ),
                    width="stretch",
                )

    render_signal_cards(skill_df, advantage_df, contract_df)

    st.subheader("Données API")
    render_raw_data(frames)
