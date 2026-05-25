from __future__ import annotations

import pandas as pd
import requests
import streamlit as st

from src.dashboard.call_api import load_lookups, load_ml_stats, post_api
from src.dashboard.ui import compact_currency, compact_number, lookup_options, metric_value, optional_select


def render_ml_page(api_base_url: str) -> None:
    st.title("Machine Learning")
    st.caption("Prédiction de salaire et recommandation d'offres via l'API FastAPI.")

    try:
        with st.spinner("Chargement des artefacts ML et des listes de valeurs..."):
            ml_stats = load_ml_stats(api_base_url)
            lookups = load_lookups(api_base_url)
    except requests.RequestException as exc:
        st.error(f"API indisponible: {api_base_url}")
        st.caption(str(exc))
        st.stop()

    metrics = ml_stats.get("metrics", {})
    ranking_metrics = metrics.get("ranking", {})
    salary_metrics = metrics.get("salary", {})

    overview_cols = st.columns(4)
    overview_cols[0].metric("Offres d'entraînement", compact_number(ml_stats.get("training_rows"), digits=0))
    overview_cols[1].metric("Compétences encodées", compact_number(ml_stats.get("encoded_skills"), digits=0))
    overview_cols[2].metric("F1 recommandation", compact_number(metric_value(ranking_metrics, "ranking_f1")))
    overview_cols[3].metric("MAE salaire", compact_currency(metric_value(salary_metrics, "salary_mae")))

    with st.container(border=True):
        st.subheader("Pipeline ML")
        flow_cols = st.columns(5)
        flow_cols[0].markdown("**1. PostgreSQL**\n\nTables `analytics`")
        flow_cols[1].markdown("**2. Préparation**\n\nNettoyage, encodage, standardisation")
        flow_cols[2].markdown("**3. Évaluation**\n\nTrain/test split 80/20")
        flow_cols[3].markdown("**4. Artefacts**\n\nModèles sauvegardés")
        flow_cols[4].markdown("**5. API**\n\nPrédictions dynamiques")

    metric_cols = st.columns(2)
    with metric_cols[0].container(border=True):
        st.subheader("Recommandation")
        st.caption("Classification avec labels synthétiques. Les métriques valident surtout le pipeline ML.")
        st.metric("Accuracy", compact_number(metric_value(ranking_metrics, "ranking_accuracy")))
        st.metric("Precision", compact_number(metric_value(ranking_metrics, "ranking_precision")))
        st.metric("Recall", compact_number(metric_value(ranking_metrics, "ranking_recall")))
        st.metric("F1-score", compact_number(metric_value(ranking_metrics, "ranking_f1")))
        st.caption(f"Modèle: {ml_stats.get('ranking_model')} | Préfiltre: {ml_stats.get('candidate_prefilter')}")

    with metric_cols[1].container(border=True):
        st.subheader("Salaire")
        st.caption("Régression supervisée avec `salary` comme variable cible.")
        st.metric("MAE", compact_currency(metric_value(salary_metrics, "salary_mae")))
        st.metric("RMSE", compact_currency(metric_value(salary_metrics, "salary_rmse")))
        st.metric("R2", compact_number(metric_value(salary_metrics, "salary_r2")))
        st.caption(f"Modèle: {ml_stats.get('salary_model')}")

    st.subheader("Tester une prédiction")
    skill_values, skill_labels = lookup_options(lookups, "skills")
    contract_values, contract_labels = lookup_options(lookups, "contracts")
    location_values, location_labels = lookup_options(lookups, "locations")

    with st.form("ml_prediction_form"):
        form_cols = st.columns(2)
        with form_cols[0]:
            prediction_type = st.selectbox(
                "Type de prédiction",
                options=["Recommandation", "Salaire"],
                index=0
            )
            selected_skills = st.multiselect(
                "Compétences",
                options=skill_values,
                default=skill_values[:2],
                format_func=lambda value: skill_labels.get(value, value),
            )
            experience_years = st.number_input("Années d'expérience", min_value=0, max_value=45, value=2, step=1)
            expected_salary = st.number_input("Salaire attendu annuel (recommandation)", min_value=0.0, value=28_000.0, step=1_000.0)

        with form_cols[1]:
            location = optional_select("Localisation", location_values, location_labels)
            contract_type = optional_select("Contrat", contract_values, contract_labels)
            limit = st.slider("Nombre de recommandations", min_value=1, max_value=10, value=5)

        submitted = st.form_submit_button("Lancer les prédictions", width="stretch")

    if not submitted:
        return

    salary_payload = {
        "skills": selected_skills,
        "experience_years": experience_years,
        "location": location,
        "contract_type": contract_type,
    }

    ranking_payload = {
        **salary_payload,
        "expected_salary": expected_salary,
        "limit": limit
    }

    input_missing = False

    if not selected_skills:
        st.error("Sélectionnez au moins une compétence.")
        input_missing = True

    if not location:
        st.error("Sélectionnez une localisation.")
        input_missing = True

    if not contract_type:
        st.error("Sélectionnez un type de contrat.")
        input_missing = True

    if input_missing:
        return

    try:
        with st.spinner("Calcul des prédictions..."):
            if prediction_type == "Recommandation":
                predict_result = post_api(api_base_url, "/predict/recommendation", ranking_payload)
            else:
                predict_result = post_api(api_base_url, "/predict/salary", salary_payload)
    except requests.RequestException as exc:
        st.error("Prédiction impossible pour le moment.")
        st.caption(str(exc))
        return

    result_cols = st.columns(1)

    with result_cols[0]:
        with st.container(border=True):
            if prediction_type == "Recommandation":
                st.subheader("Offres recommandées")
                recommendations = pd.DataFrame(predict_result.get("recommended_jobs", []))
                recommendations = recommendations.drop(columns=["job_id"], errors="ignore")
                if recommendations.empty:
                    st.info("Aucune recommandation disponible pour ce profil.")
                else:
                    st.dataframe(recommendations, width='stretch', hide_index=True)
            else:
                st.subheader("Salaire prédit", text_alignment='center')
                st.metric("Salaire annuel", compact_currency(predict_result.get("predicted_salary")))

    with st.expander("Payload envoyé à l'API"):
        st.json({"salary": salary_payload, "recommendation": ranking_payload})
