from fastapi import APIRouter, Query

from src.api.schemas import (
    PredictInput,
    PredictionDetails,
    PredictOutput,
    RecommendationInput,
    RecommendationOutput,
    SalaryPredictionInput,
    SalaryPredictionOutput,
)

router = APIRouter(prefix="/predict", tags=["Machine Learning"])


def split_skills(skills: str | None) -> list[str]:
    if not skills:
        return []
    return [skill.strip().lower() for skill in skills.split(",") if skill.strip()]


@router.post("", response_model=PredictOutput)
def predict(payload: PredictInput) -> PredictOutput:
    return PredictOutput(
        input=payload,
        prediction=PredictionDetails(
            score=None,
            message="Endpoint pret. Branchez ici le modele ML quand il sera entraine.",
        ),
    )


@router.get("", response_model=PredictOutput)
def predict_from_query(
    skills: str = Query(..., description="Competences separees par des virgules. Exemple: python,sql,airflow"),
    experience: float = Query(..., ge=0, description="Nombre d'annees d'experience"),
    expected_salary: float | None = Query(None, ge=0, description="Salaire annuel attendu en euros"),
    job_title: str | None = Query(None, description="Intitule de poste cible"),
    location: str | None = Query(None, description="Localisation souhaitee"),
    contract_type: str | None = Query(None, description="Type de contrat souhaite"),
    remote: str | None = Query(None, description="Preference teletravail"),
    education_level: str | None = Query(None, description="Niveau de formation"),
    industry: str | None = Query(None, description="Secteur cible"),
) -> PredictOutput:
    return predict(
        PredictInput(
            skills=split_skills(skills),
            experience_years=experience,
            expected_salary=expected_salary,
            job_title=job_title,
            location=location,
            contract_type=contract_type,
            remote=remote,
            education_level=education_level,
            industry=industry,
        )
    )


@router.post("/salary", response_model=SalaryPredictionOutput)
def predict_salary(payload: SalaryPredictionInput) -> SalaryPredictionOutput:
    return SalaryPredictionOutput(
        input=payload,
        predicted_salary=None,
        message="Prediction salaire a connecter au modele ML.",
    )


@router.get("/salary", response_model=SalaryPredictionOutput)
def predict_salary_from_query(
    job_title: str = Query(..., description="Intitule du poste"),
    experience: float = Query(..., ge=0, description="Nombre d'annees d'experience"),
    skills: str | None = Query(None, description="Competences separees par des virgules"),
    location: str | None = Query(None, description="Localisation du poste"),
    contract_type: str | None = Query(None, description="Type de contrat"),
    remote: str | None = Query(None, description="Modalite teletravail"),
    education_level: str | None = Query(None, description="Niveau de formation"),
    industry: str | None = Query(None, description="Secteur d'activite"),
) -> SalaryPredictionOutput:
    return predict_salary(
        SalaryPredictionInput(
            job_title=job_title,
            experience_years=experience,
            skills=split_skills(skills),
            location=location,
            contract_type=contract_type,
            remote=remote,
            education_level=education_level,
            industry=industry,
        )
    )


@router.post("/recommendation", response_model=RecommendationOutput)
def predict_recommendation(payload: RecommendationInput) -> RecommendationOutput:
    return RecommendationOutput(
        input=payload,
        recommended_jobs=[],
        message="Recommendations a connecter au modele de matching.",
    )


@router.get("/recommendation", response_model=RecommendationOutput)
def predict_recommendation_from_query(
    skills: str = Query(..., description="Competences separees par des virgules"),
    experience: float = Query(..., ge=0, description="Nombre d'annees d'experience"),
    expected_salary: float | None = Query(None, ge=0, description="Salaire annuel attendu en euros"),
    job_title: str | None = Query(None, description="Intitule de poste recherche"),
    location: str | None = Query(None, description="Localisation souhaitee"),
    contract_type: str | None = Query(None, description="Type de contrat souhaite"),
    remote: str | None = Query(None, description="Preference teletravail"),
    education_level: str | None = Query(None, description="Niveau de formation"),
    industry: str | None = Query(None, description="Secteur cible"),
    limit: int = Query(10, ge=1, le=50, description="Nombre maximum de recommandations"),
) -> RecommendationOutput:
    return predict_recommendation(
        RecommendationInput(
            skills=split_skills(skills),
            experience_years=experience,
            expected_salary=expected_salary,
            job_title=job_title,
            location=location,
            contract_type=contract_type,
            remote=remote,
            education_level=education_level,
            industry=industry,
            limit=limit,
        )
    )
