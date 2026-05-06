from pydantic import BaseModel, ConfigDict, Field


class SectorTrend(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sector: str
    year: int
    nb_offres: int


class RegionTrend(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    region: str
    year: int
    nb_offres: int


class ContractTrend(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    contract_type: str
    year: int
    nb_offres: int


class SalaryByJob(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_title: str
    year: int
    avg_salary: float
    nb_offres: int


class DashboardStats(BaseModel):
    sector: list[SectorTrend]
    region: list[RegionTrend]
    contract: list[ContractTrend]
    salary: list[SalaryByJob]


class CandidateProfileInput(BaseModel):
    skills: list[str] = Field(
        default_factory=list,
        description="Competences du candidat, par exemple ['python', 'sql', 'airflow'].",
    )
    experience_years: float = Field(ge=0, description="Nombre d'annees d'experience.")
    expected_salary: float | None = Field(default=None, ge=0, description="Salaire annuel attendu en euros.")
    location: str | None = Field(default=None, description="Localisation souhaitee.")
    contract_type: str | None = Field(default=None, description="Type de contrat souhaite, par exemple CDI.")
    remote: str | None = Field(default=None, description="Preference teletravail.")
    education_level: str | None = Field(default=None, description="Niveau de formation.")
    industry: str | None = Field(default=None, description="Secteur cible.")


class PredictInput(CandidateProfileInput):
    job_title: str | None = Field(default=None, description="Intitule de poste cible.")


class SalaryPredictionInput(BaseModel):
    job_title: str = Field(description="Intitule du poste.")
    experience_years: float = Field(ge=0, description="Nombre d'annees d'experience.")
    skills: list[str] = Field(default_factory=list, description="Competences utiles pour le poste.")
    location: str | None = Field(default=None, description="Localisation du poste.")
    contract_type: str | None = Field(default=None, description="Type de contrat.")
    remote: str | None = Field(default=None, description="Modalite teletravail.")
    education_level: str | None = Field(default=None, description="Niveau de formation.")
    industry: str | None = Field(default=None, description="Secteur d'activite.")


class RecommendationInput(CandidateProfileInput):
    job_title: str | None = Field(default=None, description="Intitule de poste recherche.")
    limit: int = Field(default=10, ge=1, le=50, description="Nombre maximum de recommandations.")


class PredictionDetails(BaseModel):
    score: float | None = None
    message: str


class PredictOutput(BaseModel):
    input: PredictInput
    prediction: PredictionDetails


class SalaryPredictionOutput(BaseModel):
    input: SalaryPredictionInput
    predicted_salary: float | None = None
    message: str


class RecommendedJob(BaseModel):
    job_id: str
    title: str | None = None
    company: str | None = None
    location: str | None = None
    score: float | None = None


class RecommendationOutput(BaseModel):
    input: RecommendationInput
    recommended_jobs: list[RecommendedJob]
    message: str
