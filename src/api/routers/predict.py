from fastapi import APIRouter, Query

router = APIRouter(prefix="/predict", tags=["Machine Learning"])


@router.get("")
def predict(
    skills: str = Query(..., description="Competences separees par des virgules. Exemple: python,sql,airflow"),
    experience_years: int = Query(..., ge=0, description="Nombre d'annees d'experience_years"),
    expected_salary: float = Query(..., ge=0, description="Salaire attendu"),
    location: str | None = Query(None, description="Localisation souhaitee"),
    contract: str | None = Query(None, description="Type de contrat souhaite"),
) -> dict:
    skill_list = [skill.strip().lower() for skill in skills.split(",") if skill.strip()]

    return {
        "input": {
            "skills": skill_list,
            "experience_years": experience_years,
            "expected_salary": expected_salary,
            "location": location,
            "contract": contract,
        },
        "prediction": {
            "score": None,
            "message": "Endpoint pret. Branchez ici le modele ML quand il sera entraine.",
        },
    }


@router.get("/salary")
def predict_salary(
    job_title: str = Query(..., description="Intitule du poste"),
    experience_years: int = Query(..., ge=0, description="Nombre d'annees d'experience_years"),
    skills: str | None = Query(None, description="Competences separees par des virgules"),
) -> dict:
    skill_list = []
    if skills:
        skill_list = [skill.strip().lower() for skill in skills.split(",") if skill.strip()]

    return {
        "input": {
            "job_title": job_title,
            "experience_years": experience_years,
            "skills": skill_list,
        },
        "predicted_salary": None,
        "message": "Prediction salaire a connecter au modele ML.",
    }


@router.get("/recommendation")
def predict_recommendation(
    skills: str = Query(..., description="Competences separees par des virgules"),
    experience_years: int = Query(..., ge=0),
    location: str | None = None,
) -> dict:
    skill_list = [skill.strip().lower() for skill in skills.split(",") if skill.strip()]

    return {
        "input": {
            "skills": skill_list,
            "experience_years": experience_years,
            "location": location,
        },
        "recommended_jobs": [],
        "message": "Recommendations a connecter au modele de matching.",
    }
