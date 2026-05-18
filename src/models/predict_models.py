"""
Helpers utilisés par l'API de prédiction.

Important : on garde ici une V0 volontairement simple. L'API appelle le modèle
entraîné depuis PostgreSQL dans features_preparation.py.
"""

from __future__ import annotations

from functools import lru_cache

import pandas as pd

from src.api.schemas import PredictInput, RecommendedJob, RecommendationInput, SalaryPredictionInput
from src.models.features_preparation import (
    get_model_dir,
    get_recommendation_candidates,
    load_job_market_artifacts,
    predict_relevance_for_jobs,
    predict_salary_from_profile,
    train_job_market_models,
)


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
        return train_job_market_models(model_dir=get_model_dir())


def _payload_to_user_input(payload: PredictInput | RecommendationInput | SalaryPredictionInput) -> dict:
    salary = getattr(payload, "expected_salary", None)
    if salary is None:
        _, avg_salary = _training_context()
        salary = avg_salary

    return {
        "skills": [skill.lower() for skill in payload.skills],
        "experience": float(payload.experience_years),
        "salary": float(salary or 0),
        "job_title": getattr(payload, "job_title", None),
        "location": getattr(payload, "location", None),
        "contract_type": getattr(payload, "contract_type", None),
        "remote": getattr(payload, "remote", None),
        "education_level": getattr(payload, "education_level", None),
        "industry": getattr(payload, "industry", None),
    }


def _training_context():
    artifacts = load_model_artifacts()
    avg_salary = float(artifacts.training_df["salary"].mean()) if not artifacts.training_df.empty else 0.0
    return artifacts, avg_salary


def get_model_stats() -> dict:
    artifacts = load_model_artifacts()
    return {
        "training_rows": len(artifacts.training_df),
        "encoded_skills": len(artifacts.mlb.classes_),
        "recommendation_features": len(artifacts.recommendation_columns),
        "salary_features": len(artifacts.salary_columns),
        "recommendation_model": type(artifacts.recommendation_model).__name__,
        "salary_model": type(artifacts.salary_model).__name__,
        "candidate_prefilter": type(artifacts.similarity_model).__name__,
        "metrics": artifacts.metrics,
    }


def _optional_text(value) -> str | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    return text or None


def _candidate_jobs(payload: PredictInput | RecommendationInput | SalaryPredictionInput) -> tuple[dict, pd.DataFrame]:
    artifacts, _ = _training_context()
    user_input = _payload_to_user_input(payload)
    candidate_limit = max(getattr(payload, "limit", 100), 100)
    candidates = get_recommendation_candidates(user_input, artifacts, limit=candidate_limit)
    scored_candidates = predict_relevance_for_jobs(user_input, candidates, artifacts)
    if user_input.get("job_title") and not scored_candidates.empty and scored_candidates["title_match"].max() >= 0.75:
        scored_candidates = scored_candidates[scored_candidates["title_match"] >= 0.75]
    return user_input, scored_candidates


def predict_market_score(payload: PredictInput) -> float | None:
    _, candidates = _candidate_jobs(payload)
    if candidates.empty:
        return None
    return round(float(candidates["score"].max()), 4)


def predict_salary_amount(payload: SalaryPredictionInput) -> float | None:
    artifacts, _ = _training_context()
    if artifacts.training_df.empty:
        return None
    user_input = _payload_to_user_input(payload)
    return round(predict_salary_from_profile(user_input, artifacts), 2)


def recommend_jobs(payload: RecommendationInput) -> list[RecommendedJob]:
    _, candidates = _candidate_jobs(payload)
    if candidates.empty:
        return []

    ranked_candidates = candidates.sort_values("score", ascending=False).head(payload.limit)

    return [
        RecommendedJob(
            job_id=str(row["id"]),
            title=_optional_text(row.get("title")),
            company=_optional_text(row.get("company")),
            location=_optional_text(row.get("location")),
            score=round(float(row["score"]), 4),
        )
        for _, row in ranked_candidates.iterrows()
    ]
