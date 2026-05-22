"""
Helpers utilisés par l'API de prédiction.

Important : on garde ici une V0 volontairement simple. L'API appelle le modèle
entraîné depuis PostgreSQL dans features_preparation.py.
"""

from __future__ import annotations


import pandas as pd

from src.api.schemas import PredictInput, RecommendedJob, RecommendationInput, SalaryPredictionInput
from src.models.features_preparation import (
    get_features_for_job,
    load_job_market_artifacts,
    get_model_dir
)
from src.models.train_models import ml_train_pipeline
from src.models.utils import retrieve_jobs, encode_user_input



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


def _payload_to_user_input(payload: PredictInput | RecommendationInput | SalaryPredictionInput) -> dict:
    salary = getattr(payload, "expected_salary", None)
    if salary is None:
        # TODO : use average salary 
        salary = 0.0

    return {
        "skills": [skill.lower() for skill in payload.skills],
        "experience_years": float(payload.experience_years),
        "salary": float(salary or 0),
        "job_title": getattr(payload, "job_title", None),
        "location": getattr(payload, "location", None),
        "contract_type": getattr(payload, "contract_type", None),
        "remote": getattr(payload, "remote", None),
        "education_level": getattr(payload, "education_level", None),
        "industry": getattr(payload, "industry", None),
    }


def get_model_stats() -> dict:
    artifacts = load_model_artifacts()
    return {
        "training_rows": len(artifacts.training_df),
        "encoded_skills": len(artifacts.mlb.classes_),
        "recommendation_features": len(artifacts.recommendation_columns),
        "salary_features": len(artifacts.salary_columns),
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


def _candidate_jobs(payload: RecommendationInput) -> tuple[dict, pd.DataFrame]:
    artifacts = load_model_artifacts()
    user_input = _payload_to_user_input(payload)
    candidate_limit = max(getattr(payload, "limit", 100), 100)

    encoded_user_input = encode_user_input(user_input, artifacts.mlb, artifacts.kmeans_scaler, artifacts.kmeans_model)
    cluster_id = artifacts.kmeans_model.predict(encoded_user_input)[0]

    jobs = retrieve_jobs()
    reduced_jobs_ids = artifacts.training_df[artifacts.training_df["cluster"] == cluster_id]["job_id"].to_list()
    reduced_jobs = jobs[jobs["job_id"].isin(reduced_jobs_ids)]

    ranked_candidates = _rank_jobs_for_user(artifacts.ranking_model, user_input, reduced_jobs)

    return user_input, ranked_candidates.limit(candidate_limit)


def _rank_jobs_for_user(model, user: dict, jobs: pd.DataFrame) -> pd.DataFrame:
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
    scores = model.predict_proba(df_features[feature_columns])[:, 1]

    df_features["relevance_score"] = scores

    return df_features.sort_values(
        by="relevance_score",
        ascending=False
    )


def predict_salary_amount(payload: SalaryPredictionInput) -> float | None:
    artifacts = load_model_artifacts()
    if artifacts.training_df.empty:
        return None
    user_input = _payload_to_user_input(payload)
    user_vector = encode_user_input(user_input, artifacts.mlb)[:-1]
    user_vector_scaled = artifacts.salary_scaler.transform(user_vector)
    salary = float(artifacts.salary_model.predict(user_vector_scaled)[0])
    return round(salary, 2)


def recommend_jobs(payload: RecommendationInput) -> list[RecommendedJob]:
    _, candidates = _candidate_jobs(payload)
    if candidates.empty:
        return []

    ranked_candidates = candidates.sort_values("relevance_score", ascending=False).head(payload.limit)

    return [
        RecommendedJob(
            job_id=str(row["id"]),
            title=_optional_text(row.get("title")),
            company=_optional_text(row.get("company")),
            location=_optional_text(row.get("location"))
        )
        for _, row in ranked_candidates.iterrows()
    ]
