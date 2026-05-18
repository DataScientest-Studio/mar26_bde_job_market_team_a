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

from src.api.models import Advantage, Contract, Industry, JobAdvantage, JobOffer, JobSkill, JobType, Location, Salary, Skill

MIN_DASHBOARD_ANNUAL_SALARY = 10_000
MAX_DASHBOARD_ANNUAL_SALARY = 200_000


def trends_by_sector_statement() -> Select:
    sector = func.coalesce(Industry.industry_name, "Non renseigné").label("sector")
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
    region = func.coalesce(Location.region, "Non renseigné").label("region")
    year = func.extract("year", JobOffer.published_at).cast(Integer).label("year")
    nb_offres = func.count().cast(Integer).label("nb_offres")

    return (
        select(region, year, nb_offres)
        .join(Location, JobOffer.location_id == Location.location_id)
        .where(JobOffer.published_at.is_not(None))
        .where(func.nullif(Location.region, "").is_not(None))
        .group_by(region, year)
        .order_by(desc(nb_offres))
    )


def trends_by_contract_type_statement() -> Select:
    contract_type = func.coalesce(Contract.contract_type, "Non renseigné").label("contract_type")
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
    job_title = func.coalesce(JobType.title, "Non renseigné").label("job_title")
    year = func.extract("year", JobOffer.published_at).cast(Integer).label("year")
    salary_amount = (
        (func.coalesce(Salary.salary_min, Salary.salary_max) + func.coalesce(Salary.salary_max, Salary.salary_min)) / 2
    )
    annual_salary_amount = (
        case(
            (Salary.frequency == "month", salary_amount * 12),
            (Salary.frequency == "week", salary_amount * 52),
            (Salary.frequency == "hour", salary_amount * 35 * 52),
            else_=salary_amount,
        )
    )
    avg_salary = func.round(func.avg(annual_salary_amount), 2).label("avg_salary")
    nb_offres = func.count().cast(Integer).label("nb_offres")

    return (
        select(job_title, year, avg_salary, nb_offres)
        .join(JobType, JobOffer.job_type_id == JobType.job_type_id)
        .join(Salary, JobOffer.salary_id == Salary.salary_id)
        .where((Salary.salary_min.is_not(None) | Salary.salary_max.is_not(None)))
        .where(annual_salary_amount.between(MIN_DASHBOARD_ANNUAL_SALARY, MAX_DASHBOARD_ANNUAL_SALARY))
        .where(JobOffer.published_at.is_not(None))
        .group_by(job_title, year)
        .order_by(desc(avg_salary))
    )


def annual_salary_expression():
    salary_amount = (
        (func.coalesce(Salary.salary_min, Salary.salary_max) + func.coalesce(Salary.salary_max, Salary.salary_min)) / 2
    )
    return case(
        (Salary.frequency == "month", salary_amount * 12),
        (Salary.frequency == "week", salary_amount * 52),
        (Salary.frequency == "hour", salary_amount * 35 * 52),
        else_=salary_amount,
    )


def dimension_columns() -> dict[str, object]:
    return {
        "sector": Industry.industry_name,
        "region": Location.region,
        "contract_type": Contract.contract_type,
        "job_title": JobType.title,
        "source": JobOffer.primary_source_system,
    }


def analytics_summary_statement(
    dimension: str | None = None,
    values: list[str] | None = None,
    job_titles: list[str] | None = None,
) -> Select:
    sector = func.coalesce(Industry.industry_name, "Non renseigné").label("sector")
    region = func.coalesce(Location.region, "Non renseigné").label("region")
    contract_type = func.coalesce(Contract.contract_type, "Non renseigné").label("contract_type")
    annual_salary = annual_salary_expression().label("annual_salary")

    statement = (
        select(
            JobOffer.job_id,
            sector,
            region,
            contract_type,
            annual_salary,
        )
        .outerjoin(Industry, JobOffer.industry_id == Industry.industry_id)
        .outerjoin(Location, JobOffer.location_id == Location.location_id)
        .outerjoin(Contract, JobOffer.contract_type_id == Contract.contract_type_id)
        .outerjoin(JobType, JobOffer.job_type_id == JobType.job_type_id)
        .outerjoin(Salary, JobOffer.salary_id == Salary.salary_id)
        .where(JobOffer.published_at.is_not(None))
    )

    if values:
        filter_column = dimension_columns().get(dimension or "")
        if filter_column is not None:
            statement = statement.where(filter_column.in_(values))

    if job_titles:
        statement = statement.where(JobType.title.in_(job_titles))

    return statement


def offers_breakdown_statement(
    group_dimension: str = "region",
    filter_dimension: str | None = None,
    filter_values: list[str] | None = None,
    job_titles: list[str] | None = None,
    limit: int = 30,
) -> Select:
    dimension_map = dimension_columns()
    group_column = dimension_map.get(group_dimension, Location.region)
    label = func.coalesce(group_column, "Non renseigné").label("label")
    nb_offres = func.count(func.distinct(JobOffer.job_id)).cast(Integer).label("nb_offres")

    statement = (
        select(label, nb_offres)
        .outerjoin(Industry, JobOffer.industry_id == Industry.industry_id)
        .outerjoin(Location, JobOffer.location_id == Location.location_id)
        .outerjoin(Contract, JobOffer.contract_type_id == Contract.contract_type_id)
        .outerjoin(JobType, JobOffer.job_type_id == JobType.job_type_id)
        .where(JobOffer.published_at.is_not(None))
        .where(func.nullif(group_column, "").is_not(None))
    )

    if filter_values:
        filter_column = dimension_map.get(filter_dimension or "")
        if filter_column is not None:
            statement = statement.where(filter_column.in_(filter_values))

    if job_titles:
        statement = statement.where(JobType.title.in_(job_titles))

    return (
        statement.group_by(label)
        .order_by(desc(nb_offres))
        .limit(limit)
    )


def salary_breakdown_statement(
    group_dimension: str = "job_title",
    filter_dimension: str | None = None,
    filter_values: list[str] | None = None,
    job_titles: list[str] | None = None,
    limit: int = 30,
) -> Select:
    annual_salary = annual_salary_expression()
    dimension_map = dimension_columns()
    group_column = dimension_map.get(group_dimension, JobType.title)
    label = func.coalesce(group_column, "Non renseigné").label("label")
    avg_salary = func.round(func.avg(annual_salary), 2).label("avg_salary")
    nb_offres = func.count(func.distinct(JobOffer.job_id)).cast(Integer).label("nb_offres")

    statement = (
        select(label, avg_salary, nb_offres)
        .outerjoin(Industry, JobOffer.industry_id == Industry.industry_id)
        .outerjoin(Location, JobOffer.location_id == Location.location_id)
        .outerjoin(Contract, JobOffer.contract_type_id == Contract.contract_type_id)
        .outerjoin(JobType, JobOffer.job_type_id == JobType.job_type_id)
        .outerjoin(Salary, JobOffer.salary_id == Salary.salary_id)
        .where(JobOffer.published_at.is_not(None))
        .where((Salary.salary_min.is_not(None) | Salary.salary_max.is_not(None)))
        .where(annual_salary.between(MIN_DASHBOARD_ANNUAL_SALARY, MAX_DASHBOARD_ANNUAL_SALARY))
        .where(func.nullif(group_column, "").is_not(None))
    )

    if filter_values:
        filter_column = dimension_map.get(filter_dimension or "")
        if filter_column is not None:
            statement = statement.where(filter_column.in_(filter_values))

    if job_titles:
        statement = statement.where(JobType.title.in_(job_titles))

    return (
        statement.group_by(label)
        .order_by(desc(avg_salary))
        .limit(limit)
    )


def top_skills_statement(limit: int = 20) -> Select:
    skill_name = func.coalesce(Skill.skill_name, "Non renseigné").label("skill_name")
    skill_category = func.coalesce(Skill.skill_category, "Non renseigné").label("skill_category")
    nb_offres = func.count(func.distinct(JobSkill.job_id)).cast(Integer).label("nb_offres")

    return (
        select(skill_name, skill_category, nb_offres)
        .join(JobSkill, Skill.skill_id == JobSkill.skill_id)
        .group_by(skill_name, skill_category)
        .order_by(desc(nb_offres))
        .limit(limit)
    )


def top_advantages_statement(limit: int = 15) -> Select:
    advantage_name = func.coalesce(Advantage.advantage_name, "Non renseigné").label("advantage_name")
    nb_offres = func.count(func.distinct(JobAdvantage.job_id)).cast(Integer).label("nb_offres")

    return (
        select(advantage_name, nb_offres)
        .join(JobAdvantage, Advantage.advantage_id == JobAdvantage.advantage_id)
        .group_by(advantage_name)
        .order_by(desc(nb_offres))
        .limit(limit)
    )


def offers_by_source_statement() -> Select:
    source_system = func.coalesce(JobOffer.primary_source_system, "Non renseigné").label("source_system")
    nb_offres = func.count().cast(Integer).label("nb_offres")

    return (
        select(source_system, nb_offres)
        .group_by(source_system)
        .order_by(desc(nb_offres))
    )
