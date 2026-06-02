from fastapi import APIRouter

from src.api.schemas import (
    RecommendationInput,
    RecommendationOutput,
    SalaryPredictionInput,
    SalaryPredictionOutput,
)
from src.models.predict_models import predict_salary_amount, recommend_jobs

router = APIRouter(prefix="/predict", tags=["Prédictions"])


@router.post("/salary", response_model=SalaryPredictionOutput)
def predict_salary(payload: SalaryPredictionInput) -> SalaryPredictionOutput:
    predicted_salary = predict_salary_amount(payload)
    return SalaryPredictionOutput(
        input=payload,
        predicted_salary=predicted_salary,
        message="Salaire estimé à partir des offres similaires issues du modèle ML.",
    )


@router.post("/recommendation", response_model=RecommendationOutput)
def predict_recommendation(payload: RecommendationInput) -> RecommendationOutput:
    recommended_jobs = recommend_jobs(payload)
    return RecommendationOutput(
        input=payload,
        recommended_jobs=recommended_jobs,
        message="Recommandations calculées à partir des offres PostgreSQL similaires.",
    )
