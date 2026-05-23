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


class SkillTrend(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    skill_name: str
    skill_category: str
    nb_offres: int


class AdvantageTrend(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    advantage_name: str
    nb_offres: int


class SourceTrend(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source_system: str
    nb_offres: int


class MLModelStats(BaseModel):
    training_rows: int
    encoded_skills: int
    recommendation_features: int
    salary_features: int
    recommendation_model: str
    salary_model: str
    candidate_prefilter: str
    metrics: dict[str, float]


class AnalyticsSummary(BaseModel):
    total_offers: int
    top_sector: str | None = None
    top_region: str | None = None
    top_contract: str | None = None
    avg_salary: float | None = None


class SalaryBreakdown(BaseModel):
    label: str
    avg_salary: float
    nb_offres: int


class OfferBreakdown(BaseModel):
    label: str
    nb_offres: int


class DashboardStats(BaseModel):
    sector: list[SectorTrend]
    region: list[RegionTrend]
    contract: list[ContractTrend]
    salary: list[SalaryByJob]
    skill: list[SkillTrend]
    advantage: list[AdvantageTrend]
    source: list[SourceTrend]


class LookupValue(BaseModel):
    value: str
    label: str
    count: int | None = None


class DashboardLookups(BaseModel):
    skills: list[LookupValue]
    contracts: list[LookupValue]
    remote: list[LookupValue]
    education: list[LookupValue]
    industries: list[LookupValue]
    locations: list[LookupValue]
    job_titles: list[LookupValue]


class CandidateProfileInput(BaseModel):
    skills: list[str] = Field(
        default_factory=list,
        description="Compétences du candidat. Valeurs disponibles via GET /lookups/skills.",
    )
    experience_years: int = Field(ge=0, description="Nombre d'années d'expérience.")
    expected_salary: float | None = Field(default=None, ge=0, description="Salaire annuel attendu en euros.")
    location: str | None = Field(default=None, description="Localisation souhaitee. Valeurs via GET /lookups/locations.")
    contract_type: str | None = Field(default=None, description="Type de contrat. Valeurs via GET /lookups/contracts.")
    remote: str | None = Field(default=None, description="Préférence télétravail. Valeurs via GET /lookups/remote.")
    education_level: str | None = Field(default=None, description="Niveau de formation. Valeurs via GET /lookups/education.")
    industry: str | None = Field(default=None, description="Secteur cible. Valeurs via GET /lookups/industries.")


class PredictInput(CandidateProfileInput):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "skills": ["faire preuve d'autonomie", "travailler en équipe"],
                "experience_years": 2,
                "expected_salary": 28000,
                "job_title": "Aide-soignant / Aide-soignante",
                "location": "CAEN, normandie",
                "contract_type": "CDI",
                "remote": "Non précisé",
                "education_level": "Bac",
                "industry": "Santé",
            }
        }
    )

    job_title: str | None = Field(default=None, description="Intitulé de poste cible. Valeurs via GET /lookups/job-titles.")


class SalaryPredictionInput(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "job_title": "Aide-soignant / Aide-soignante",
                "experience_years": 2,
                "skills": ["faire preuve d'autonomie", "travailler en équipe"],
                "location": "CAEN, normandie",
                "contract_type": "CDI",
                "remote": "Non précisé",
                "education_level": "Bac",
                "industry": "Santé",
            }
        }
    )

    job_title: str = Field(description="Intitulé du poste. Valeurs via GET /lookups/job-titles.")
    experience_years: float = Field(ge=0, description="Nombre d'années d'expérience.")
    skills: list[str] = Field(default_factory=list, description="Compétences utiles. Valeurs via GET /lookups/skills.")
    location: str | None = Field(default=None, description="Localisation du poste. Valeurs via GET /lookups/locations.")
    contract_type: str | None = Field(default=None, description="Type de contrat. Valeurs via GET /lookups/contracts.")
    remote: str | None = Field(default=None, description="Modalité télétravail. Valeurs via GET /lookups/remote.")
    education_level: str | None = Field(default=None, description="Niveau de formation. Valeurs via GET /lookups/education.")
    industry: str | None = Field(default=None, description="Secteur d'activité. Valeurs via GET /lookups/industries.")


class RecommendationInput(CandidateProfileInput):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "skills": ["faire preuve d'autonomie", "travailler en équipe"],
                "experience_years": 2,
                "expected_salary": 28000,
                "job_title": "Aide-soignant / Aide-soignante",
                "location": "CAEN, normandie",
                "contract_type": "CDI",
                "remote": "Non précisé",
                "education_level": "Bac",
                "industry": "Santé",
                "limit": 10,
            }
        }
    )

    job_title: str | None = Field(default=None, description="Intitulé de poste recherché. Valeurs via GET /lookups/job-titles.")
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


class RecommendationOutput(BaseModel):
    input: RecommendationInput
    recommended_jobs: list[RecommendedJob]
    message: str