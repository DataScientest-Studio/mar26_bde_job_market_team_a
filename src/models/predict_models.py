"""
Helpers utilisés par l'API de prédiction.

Important : on garde ici une V0 volontairement simple. L'API appelle le modèle
entraîné depuis PostgreSQL dans features_preparation.py.
"""

from __future__ import annotations

import pandas as pd
from functools import lru_cache
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from src.api.schemas import RecommendedJob, RecommendationInput, SalaryPredictionInput
from src.models.features_preparation import (
    get_features_for_job,
    load_job_market_artifacts,
    get_model_dir,
    clean_data
)
from src.models.train_models import ml_train_pipeline
from src.models.utils import retrieve_jobs, encode_user_input

@lru_cache(maxsize=1)
def load_model_artifacts():
    """
    Charge les artefacts ML utilisés par l'API.

    Flux normal :
    - make ml-train crée models/job_market_model_artifacts.pkl ;
    - l'API charge ce fichier et le garde en cache mémoire.

    Fallback dev :
    - si le fichier n'existe pas encore, on entraîne depuis PostgreSQL et on
      sauvegarde les artefacts pour les prochains appels.
    """
    try:
        return load_job_market_artifacts()
    except FileNotFoundError:
        return ml_train_pipeline(model_dir=get_model_dir())


def _payload_to_user_input(payload: RecommendationInput | SalaryPredictionInput) -> dict:
    salary = getattr(payload, "expected_salary", None)
    if salary is None:
        # TODO : use average salary 
        salary = 0.0

    return {
        "skills": [skill for skill in payload.skills],
        "experience_years": float(payload.experience_years),
        "expected_salary": float(salary or 0),
        "location": getattr(payload, "location", None) or "",
        "contract_preference": getattr(payload, "contract_type", None),
    }


def get_model_stats() -> dict:
    artifacts = load_model_artifacts()
    return {
        "training_rows": len(artifacts.training_df),
        "encoded_skills": len(artifacts.mlbs["skills"].classes_),
        "encoded_contracts": len(artifacts.mlbs["contract"].classes_),
        "ranking_model": type(artifacts.ranking_model).__name__,
        "salary_model": type(artifacts.salary_model).__name__,
        "candidate_prefilter": type(artifacts.kmeans_model).__name__,
        "metrics": artifacts.metrics,
    }


def _optional_text(value) -> str | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    return text or None


def _optional_float(value) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)


def _candidate_jobs(payload: RecommendationInput) -> pd.DataFrame:
    artifacts = load_model_artifacts()
    user_input = _payload_to_user_input(payload)
    candidate_limit = max(getattr(payload, "limit", 100), 100)

    encoded_user_input = encode_user_input(user_input, artifacts.mlbs)
    kmeans_input = artifacts.kmeans_scaler.transform(encoded_user_input)
    cluster_id = artifacts.kmeans_model.predict(kmeans_input)[0]

    jobs = retrieve_jobs()
    jobs_cleaned = clean_data(jobs)
    reduced_jobs_ids = artifacts.training_df[artifacts.training_df["cluster"] == cluster_id]["job_id"].to_list()
    reduced_jobs = jobs_cleaned[jobs_cleaned["job_id"].isin(reduced_jobs_ids)]

    ranked_candidates = _rank_jobs_for_user(artifacts.ranking_model, user_input, reduced_jobs, artifacts.ranking_scaler)

    return ranked_candidates.head(candidate_limit)


def _rank_jobs_for_user(model: LogisticRegression, user: dict, jobs: pd.DataFrame, scaler: StandardScaler) -> pd.DataFrame:
    rows = []

    for _, job in jobs.iterrows():

        row = {
            "job_id": job["job_id"],
        } | get_features_for_job(job, user)

        rows.append(row)

    df_features = pd.DataFrame(rows)

    feature_columns = [
        "skill_match_score",
        "location_match_score",
        "salary_match_score",
        "contract_match",
        "experience_years_score"
    ]

    # Probability of match
    scaled_features = scaler.transform(df_features[feature_columns])

    scores = model.predict_proba(scaled_features)[:, 1]

    df_features["relevance_score"] = scores

    sorted_jobs = df_features.sort_values(
        by="relevance_score",
        ascending=False
    )
    return sorted_jobs


def predict_salary_amount(payload: SalaryPredictionInput) -> float | None:
    artifacts = load_model_artifacts()
    if artifacts.training_df.empty:
        return None
    user_input = _payload_to_user_input(payload)
    user_df = encode_user_input(user_input, artifacts.mlbs).drop(columns=["salary_bucket"])
    user_vector_scaled = artifacts.salary_scaler.transform(user_df)
    salary = float(artifacts.salary_model.predict(user_vector_scaled)[0])
    return round(salary, 2)

def recommend_jobs(payload: RecommendationInput) -> list[RecommendedJob]:
    candidates = _candidate_jobs(payload)
    jobs = retrieve_jobs()
    if candidates.empty:
        return []

    ranked_candidates = candidates.sort_values("relevance_score", ascending=False).head(payload.limit)

    return [
        RecommendedJob(
            job_id=str(row["job_id"]),
            title=_optional_text(row.get("job_title")),
            company=_optional_text(row.get("company_name")),
            location=_optional_text(row.get("location")),
            salary=_optional_float(row.get("salary")),
        )
        for _, row in jobs[jobs["job_id"].isin(ranked_candidates["job_id"])].iterrows()
    ]
