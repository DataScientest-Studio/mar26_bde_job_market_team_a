import pandas as pd
from sqlalchemy import desc, func
from sqlmodel import select
from src.api.models import JobSkill, Skill

def _encode_experience(x):
    if x <= 2:
        return 0  # junior
    elif x <= 5:
        return 1  # mid
    else:
        return 2  # senior

def _salary_bucket(x):
    if x < 30000:
        return 0
    elif x < 60000:
        return 1
    else:
        return 2

def find_top_skills(engine, limit=50) -> list[str]:
    skill_name = Skill.skill_name.label("skill_name")
    skill_count = func.count().label("skill_count")
    query = (
        select(skill_name, skill_count).select_from(JobSkill)
        .join(Skill, JobSkill.skill_id == Skill.skill_id)
        .group_by(Skill.skill_name)
        .order_by(desc(skill_count))
        .limit(limit)
    )

    # Execute query and load data into DataFrame
    df = pd.read_sql_query(query, engine)
    return df["skill_name"].tolist()


def skill_match_score(user_skills, job_skills) -> float:
    return len(set(user_skills) & set(job_skills)) / len(set(job_skills)) if job_skills else 0

def experience_years_score(user_experience, required_experience) -> float:
    return 1. - abs(user_experience - required_experience) / required_experience if required_experience != 0. else 0.

def location_score(user_location, job_location, user_region, job_region) -> float:
    if user_location == job_location:
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
        + 0.15 * location_score(
            user["location"],
            job["location"],
            user["region"],
            job["region"]
        )
        + 0.15 * salary_match_score(
            job["mid_salary"],
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
