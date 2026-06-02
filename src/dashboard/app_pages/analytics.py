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

ALL_JOBS_LABEL = "Tous les métiers (aucun filtre)"
JOB_TITLE_KEY = "analytics_job_title"


def clear_job_title_filter() -> None:
    st.session_state[JOB_TITLE_KEY] = ALL_JOBS_LABEL


def select_year_range(years: list[int]) -> tuple[int | None, int | None]:
    if not years:
        return None, None
    if len(years) == 1:
        return years[0], years[0]
    return st.slider(
        "Période",
        min_value=min(years),
        max_value=max(years),
        value=(min(years), max(years)),
        help="Limiter les indicateurs aux offres publiées sur la période sélectionnée",
    )


def render_raw_data(frames: dict[str, pd.DataFrame]) -> None:
    sections = {
        "Secteurs": frames["sector"],
        "Régions": frames["region"],
        "Contrats": frames["contract"],
        "Salaires": frames["salary"],
        "Compétences": frames["skill"],
        "Avantages": frames["advantage"],
        "Entreprises": frames["company"],
        "Sources": frames["source"],
    }

    for section, frame in sections.items():
        with st.expander(section):
            st.dataframe(frame, width="stretch", hide_index=True)


def render_signal_cards(
    skill_df: pd.DataFrame,
    advantage_df: pd.DataFrame,
    contract_df: pd.DataFrame,
    company_df: pd.DataFrame,
) -> None:
    st.subheader("Signaux métier")
    signal_cols = st.columns(2)

    with signal_cols[0].container(border=True):
        skill_display = skill_df.copy()
        if not skill_display.empty:
            skill_display["label"] = skill_display["skill_name"] + " - " + skill_display["skill_category"]
            skill_display["nb_offres"] = pd.to_numeric(skill_display["nb_offres"], errors="coerce").fillna(0).astype(int)
            st.altair_chart(bar_chart(skill_display.head(12), "label", "nb_offres", "Top compétences"), width="stretch")
        else:
            st.info("Aucune compétence disponible")

    with signal_cols[1].container(border=True):
        advantage_display = advantage_df.copy()
        if not advantage_display.empty:
            advantage_display["nb_offres"] = pd.to_numeric(advantage_display["nb_offres"], errors="coerce").fillna(0).astype(int)
            st.altair_chart(
                bar_chart(advantage_display.head(12), "advantage_name", "nb_offres", "Top avantages"),
                width="stretch",
            )
        else:
            st.info("Aucun avantage disponible")

    signal_cols = st.columns(2)
    with signal_cols[0].container(border=True):
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
            st.info("Aucun contrat disponible")

    with signal_cols[1].container(border=True):
        company_display = company_df.copy()
        if not company_display.empty:
            company_display["nb_offres"] = pd.to_numeric(company_display["nb_offres"], errors="coerce").fillna(0).astype(int)
            st.altair_chart(
                bar_chart(company_display.head(20), "company_name", "nb_offres", "Top entreprises recruteuses"),
                width="stretch",
            )
        else:
            st.info("Aucune entreprise disponible")


def render_analytics_page(api_base_url: str) -> None:
    st.title("Job Market")
    st.caption("Dashboard analytique alimenté par l'API FastAPI du projet")

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
    company_df = frames["company"]
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
        job_select_options = [ALL_JOBS_LABEL] + job_options
        if st.session_state.get(JOB_TITLE_KEY) not in job_select_options:
            st.session_state[JOB_TITLE_KEY] = ALL_JOBS_LABEL

        job_select_col, clear_job_col = st.columns([0.82, 0.18])
        with job_select_col:
            selected_job_title = st.selectbox(
                "Métier",
                options=job_select_options,
                index=0,
                key=JOB_TITLE_KEY,
                format_func=lambda value: value if value == ALL_JOBS_LABEL else job_labels.get(value, value),
                help="Filtrer les indicateurs sur un métier précis. Garder l'option par défaut pour inclure tous les métiers",
            )
        with clear_job_col:
            st.write("")
            st.write("")
            if selected_job_title != ALL_JOBS_LABEL:
                st.button(
                    "X",
                    help="Effacer le métier sélectionné",
                    on_click=clear_job_title_filter,
                    width="stretch",
                )

        selected_job_titles = [] if selected_job_title == ALL_JOBS_LABEL else [selected_job_title]
        selected_jobs_tuple = tuple(selected_job_titles)

        st.caption("Filtre 2")
        dimension = st.pills(
            "Analyse par",
            options=["Régions", "Sources", "Secteurs"],
            default="Régions",
            help="Choisir l'axe utilisé pour les graphiques d'offres et de salaires",
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
                    start_year=start_year,
                    end_year=end_year,
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
            placeholder=f"Toutes les valeurs de {dimension_label} (aucun filtre)",
            help=f"Limiter l'analyse à une ou plusieurs valeurs de {dimension_label}. Laisser vide pour tout inclure",
        )
        selected_tuple = tuple(selected_dimension_values)

        st.caption(f"API: {api_base_url}")
        if st.button(
            "Rafraîchir",
            width="stretch",
            help="Vider le cache Streamlit et recharger les données depuis l'API",
        ):
            load_dashboard_stats.clear()
            build_analytics_frames.clear()
            load_job_title_lookup.clear()
            load_analytics_summary.clear()
            load_offer_breakdown.clear()
            load_salary_breakdown.clear()
            st.rerun()

    trend_selected = filter_by_labels(trend_filtered, label_column, selected_dimension_values)

    try:
        with st.spinner("Mise à jour des indicateurs..."):
            selected_summary = load_analytics_summary(
                api_base_url,
                api_dimension,
                selected_tuple,
                selected_jobs_tuple,
                start_year,
                end_year,
            )
            offer_breakdown = pd.DataFrame(
                load_offer_breakdown(
                    api_base_url,
                    api_dimension,
                    api_dimension,
                    selected_tuple,
                    selected_jobs_tuple,
                    start_year=start_year,
                    end_year=end_year,
                )
            )
            salary_breakdown = pd.DataFrame(
                load_salary_breakdown(
                    api_base_url,
                    api_dimension,
                    api_dimension,
                    selected_tuple,
                    selected_jobs_tuple,
                    start_year,
                    end_year,
                )
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
                st.info("Aucune donnée d'offre disponible pour cette sélection")
            else:
                st.altair_chart(
                    bar_chart(offers_display, "label", "nb_offres", f"Nombre d'offres par {dimension_label}"),
                    width="stretch",
                )

        with chart_cols[1].container(border=True):
            if salary_chart_frame.empty:
                st.info("Aucune donnée de salaire disponible pour cette sélection")
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

    render_signal_cards(skill_df, advantage_df, contract_df, company_df)

    st.subheader("Données API")
    render_raw_data(frames)
