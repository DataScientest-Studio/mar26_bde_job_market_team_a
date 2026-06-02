from functools import lru_cache
import os
import numpy as np
import pandas as pd
from sklearn.preprocessing import MultiLabelBinarizer
from sqlalchemy import func
from sqlmodel import case, select
from src.api.models import Company, Contract, JobOffer, JobType, Location, Salary, JobSkill, Skill
from src.database import get_engine

DEFAULT_ML_SKILL_LIMIT = 100


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value in (None, ""):
        return default
    return int(value)


def encode_experience(years: float) -> int:
    """
    Transforme une variable quantitative en variable ordinale.

    Variable explicative :
    - expérience demandée.

    Encodage :
    - 0 = junior ;
    - 1 = intermédiaire ;
    - 2 = senior.
    """
    if years <= 2:
        return 0
    if years <= 5:
        return 1
    return 2


def salary_bucket(salary: float) -> int:
    """
    Transforme le salaire en tranche.

    Variable explicative :
    - niveau de rémunération de l'offre.

    Encodage :
    - 0 = salaire bas ;
    - 1 = salaire moyen ;
    - 2 = salaire élevé.
    """
    if salary < 30000:
        return 0
    if salary < 60000:
        return 1
    return 2

def encode_user_input(user_input: pd.DataFrame, mlbs: dict[str, MultiLabelBinarizer]) -> pd.DataFrame:
    # Skills
    skills_vec = mlbs["skills"].transform([user_input["skills"]])
    # Experience
    exp = encode_experience(user_input["experience_years"])
    # Salary
    salary_buck = salary_bucket(user_input["expected_salary"])
    # Contract type
    contract_vec = mlbs["contract"].transform([[user_input["contract_preference"]]])
    # Combine
    user_vector = np.concatenate([
        skills_vec[0],
        contract_vec[0],
        [exp, salary_buck]
    ])
    columns = list(mlbs["skills"].classes_) + list(mlbs["contract"].classes_) + ["exp_level", "salary_bucket"]
    return pd.DataFrame(data=[user_vector.flatten()], columns=columns)

@lru_cache(maxsize=1)
def find_top_skills() -> list[str]:
    engine = get_engine()
    skill_count = func.count(func.distinct(JobSkill.job_id)).label("skill_count")
    statement = (
        select(Skill.skill_name, skill_count)
        .join(JobSkill, Skill.skill_id == JobSkill.skill_id)
        .where(func.nullif(Skill.skill_name, "").is_not(None))
        .group_by(Skill.skill_name)
        .order_by(skill_count.desc(), Skill.skill_name)
        .limit(_env_int("ML_SKILL_LIMIT", DEFAULT_ML_SKILL_LIMIT))
    )

    # Execute query and load data into DataFrame
    df = pd.read_sql_query(statement, engine)
    return df["skill_name"].tolist()


@lru_cache(maxsize=1)
def retrieve_jobs() -> pd.DataFrame:
    engine = get_engine()
    job_id = JobOffer.job_id.label("job_id")
    job_title = JobType.title.label("job_title")
    company_name = Company.name.label("company_name")
    experience_years = JobOffer.experience_years.label("experience_years")
    contract_type = Contract.contract_type.label("contract_type")
    salary_amount = (func.coalesce((Salary.salary_min + Salary.salary_max) / 2)).label("salary")
    annual_salary = case(
        (Salary.frequency == "month", salary_amount * 12),
        (Salary.frequency == "week", salary_amount * 52),
        (Salary.frequency == "hour", salary_amount * 35 * 52),
        else_=salary_amount,
    ).label("salary")

    skills = func.array_agg(Skill.skill_name).label("skills")
    location = func.concat(Location.city, ",", Location.region).label("location")

    statement = (
        select(job_id, job_title, company_name, experience_years, contract_type, annual_salary, skills, location)
        .select_from(JobOffer)
        .join(Salary, JobOffer.salary_id == Salary.salary_id)
        .join(Contract, JobOffer.contract_type_id == Contract.contract_type_id)
        .join(JobType, JobOffer.job_type_id == JobType.job_type_id)
        .join(JobSkill, JobOffer.job_id == JobSkill.job_id)
        .join(Skill, JobSkill.skill_id == Skill.skill_id)
        .join(Company, JobOffer.company_id == Company.company_id)
        .join(Location, JobOffer.location_id == Location.location_id)
        .where(annual_salary.between(10000, 200000))
        .group_by(job_id, job_title, company_name, experience_years, contract_type, annual_salary, location)
    )

    # Execute query and load data into DataFrame
    df = pd.read_sql_query(statement, engine)
    return df

def skill_match_score(user_skills, job_skills) -> float:
    return len(set(user_skills) & set(job_skills)) / len(set(job_skills)) if job_skills else 0.

def experience_years_score(user_experience, required_experience) -> float:
    return 1. - abs(user_experience - required_experience) / required_experience if required_experience != 0. else 1.

def location_match_score(user_location, job_location) -> float:
    user_city, user_region = user_location.split(",") if "," in user_location else (user_location, "")
    job_city, job_region = job_location.split(",") if "," in job_location else (job_location, "")
    if user_city == job_city:
        return 1.0
    elif user_region == job_region:
        return 0.5
    else:
        return 0.0

def salary_match_score(job_salary, expected_salary) -> float:
    return 1. - abs(job_salary - expected_salary) / expected_salary if expected_salary != 0. else 0.

def contract_match(user_contract_preference, job_contract_type) -> int:
    return 1 if user_contract_preference == job_contract_type else 0

def remote_match(user_remote_preference, job_remote_option) -> int:
    return 1 if user_remote_preference == job_remote_option else 0

def relevance_score(user, job) -> float:
    return (
        0.5 * skill_match_score(user["skills"], job["skills"])
        + 0.15 * location_match_score(
            user["location"],
            job["location"]
        )
        + 0.15 * salary_match_score(
            job["salary"],
            user["expected_salary"]
        )
        + 0.1 * contract_match(
            user["contract_preference"],
            job["contract_type"]
        )
        + 0.1 * experience_years_score(
            user["experience_years"],
            job["experience_years"]
        )
    )
