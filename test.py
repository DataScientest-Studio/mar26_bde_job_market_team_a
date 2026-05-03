from typing import Iterator

import sys
from pathlib import Path


from src.database import get_engine

from sqlalchemy import Integer, desc, func
from sqlalchemy.sql import Select
from sqlmodel import Session, select, table, column, inspect


from src.api.models import Industry, JobOffer, JobSkill, Skill


def get_db_session() -> Iterator[Session]:
    with Session(get_engine()) as session:
        yield session


def trends_by_sector_statement() -> Select:
    sector = func.coalesce(Industry.industry_name, "Non renseigne").label("sector")
    year = func.extract("year", JobOffer.published_at).cast(Integer).label("year")
    nb_offres = func.count().cast(Integer).label("nb_offres")

    return (
        select(sector, year, nb_offres)
        .join(Industry, JobOffer.industry_id == Industry.industry_id)
        .where(JobOffer.published_at.is_not(None))
        .group_by(sector, year)
        .order_by(desc(nb_offres))
    )


def find_top_skills(limit=50):
    skill_name = Skill.skill_name.label("skill_name")
    skill_count = func.count().label("skill_count")
    return (
        select(skill_name, skill_count).select_from(JobSkill)
        .join(Skill, JobSkill.skill_id == Skill.skill_id)
        .group_by(Skill.skill_name)
        .order_by(desc(skill_count))
        .limit(limit)
    )

def get_stats_by_region(db: Session) -> any:
    try:
        return db.exec(trends_by_sector_statement())
    except Exception as exc:
        raise exc


import matplotlib.pyplot as plt

if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parent
    sys.path.insert(0, str(repo_root))

    from src.database import load_project_env

    env_file = repo_root / ".env"
    print(env_file)

    load_project_env(env_file, override=True)
    engine = get_engine()
    print("Testing database connection and query execution...")

    with Session(engine) as session:
        # result = session.exec(trends_by_sector_statement())
        result = session.exec(find_top_skills())
        rows = result.all()
        for row in rows:
            print(f"Skill: {row.skill_name}, Count: {row.skill_count}")

    # sectors, nb_offers, years = [], [], []
    # for row in rows[:10]:
    #     if row.year == 2026:
    #         sectors.append(row.sector[:20])
    #         nb_offers.append(row.nb_offres)
    # plt.figure(figsize=(10, 6))
    # plt.barh(sectors, nb_offers, color="skyblue")
    # plt.xlabel("Number of Job Offers")
    # plt.title("Number of Job Offers by Sector in 2026")
    # plt.gca().invert_yaxis()
    # plt.tight_layout()
    # plt.show()
