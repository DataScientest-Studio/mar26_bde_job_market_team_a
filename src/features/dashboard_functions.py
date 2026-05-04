"""
Dashboard functions for job market data analytics.
Builds SQLModel/SQLAlchemy statements executed by the API layer.

Planned analytics:
- tendances par secteur => statistiques généraux
- tendances par région
- tendances par type de contrat
- salaires par métier
- quelles recos on fait (ML):
    par critère on recommande telle ou telle offre à un utilisateur
    prédiction salaires
    prédiction du marché de l'emploi de l'individu
    compétences de l'utilisateur => recommandation sur quels métiers correspondent le mieux
"""

from sqlalchemy import Integer, case, desc, func
from sqlalchemy.sql import Select
from sqlmodel import select

from src.api.models import Contract, Industry, JobOffer, JobType, Location, Salary

MIN_DASHBOARD_ANNUAL_SALARY = 10_000
MAX_DASHBOARD_ANNUAL_SALARY = 200_000


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


def trends_by_region_statement() -> Select:
    region = func.coalesce(Location.region, "Non renseigne").label("region")
    year = func.extract("year", JobOffer.published_at).cast(Integer).label("year")
    nb_offres = func.count().cast(Integer).label("nb_offres")

    return (
        select(region, year, nb_offres)
        .join(Location, JobOffer.location_id == Location.location_id)
        .where(JobOffer.published_at.is_not(None))
        .group_by(region, year)
        .order_by(desc(nb_offres))
    )


def trends_by_contract_type_statement() -> Select:
    contract_type = func.coalesce(Contract.contract_type, "Non renseigne").label("contract_type")
    year = func.extract("year", JobOffer.published_at).cast(Integer).label("year")
    nb_offres = func.count().cast(Integer).label("nb_offres")

    return (
        select(contract_type, year, nb_offres)
        .join(Contract, JobOffer.contract_type_id == Contract.contract_type_id)
        .where(JobOffer.published_at.is_not(None))
        .group_by(contract_type, year)
        .order_by(desc(nb_offres))
    )


def salary_by_job_statement() -> Select:
    job_title = func.coalesce(JobType.title, JobOffer.title_norm, JobOffer.title_raw, "Non renseigne").label(
        "job_title"
    )
    year = func.extract("year", JobOffer.published_at).cast(Integer).label("year")
    annual_salary_amount = (
        (
            func.coalesce(Salary.annual_salary_min, Salary.annual_salary_max)
            + func.coalesce(Salary.annual_salary_max, Salary.annual_salary_min)
        )
        / 2
    )
    avg_salary = func.round(func.avg(annual_salary_amount), 2).label("avg_salary")
    nb_offres = func.count().cast(Integer).label("nb_offres")

    return (
        select(job_title, year, avg_salary, nb_offres)
        .join(JobType, JobOffer.job_type_id == JobType.job_type_id)
        .join(Salary, JobOffer.salary_id == Salary.salary_id)
        .where((Salary.annual_salary_min.is_not(None) | Salary.annual_salary_max.is_not(None)))
        .where(annual_salary_amount.between(MIN_DASHBOARD_ANNUAL_SALARY, MAX_DASHBOARD_ANNUAL_SALARY))
        .where(JobOffer.published_at.is_not(None))
        .group_by(job_title, year)
        .order_by(desc(avg_salary))
    )
