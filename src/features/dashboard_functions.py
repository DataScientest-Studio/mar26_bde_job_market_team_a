"""
Dashboard query builders.
"""

from sqlalchemy import case, desc, func
from sqlalchemy.sql import Select
from sqlmodel import select

from src.api.dashboard_models import (
    AggDashboardContractYear,
    AggDashboardRegionYear,
    AggDashboardSalaryJobYear,
    AggDashboardSectorYear,
    AggDashboardSource,
    AggDashboardTopAdvantage,
    AggDashboardTopCompany,
    AggDashboardTopSkill,
    DashboardJobOffer,
    DashboardLookupValue,
)

MIN_DASHBOARD_ANNUAL_SALARY = 10_000
MAX_DASHBOARD_ANNUAL_SALARY = 200_000
MISSING_LABEL = "NON RENSEIGNÉ"


def trends_by_sector_statement() -> Select:
    return select(
        AggDashboardSectorYear.sector,
        AggDashboardSectorYear.year,
        AggDashboardSectorYear.nb_offres,
    ).order_by(desc(AggDashboardSectorYear.nb_offres))


def trends_by_region_statement() -> Select:
    return select(
        AggDashboardRegionYear.region,
        AggDashboardRegionYear.year,
        AggDashboardRegionYear.nb_offres,
    ).order_by(desc(AggDashboardRegionYear.nb_offres))


def trends_by_contract_type_statement() -> Select:
    return select(
        AggDashboardContractYear.contract_type,
        AggDashboardContractYear.year,
        AggDashboardContractYear.nb_offres,
    ).order_by(desc(AggDashboardContractYear.nb_offres))


def salary_by_job_statement() -> Select:
    return select(
        AggDashboardSalaryJobYear.job_title,
        AggDashboardSalaryJobYear.year,
        AggDashboardSalaryJobYear.avg_salary,
        AggDashboardSalaryJobYear.nb_offres,
    ).order_by(desc(AggDashboardSalaryJobYear.avg_salary))


def annual_salary_expression():
    return DashboardJobOffer.annual_salary


def dimension_columns() -> dict[str, object]:
    return {
        "sector": DashboardJobOffer.sector,
        "region": DashboardJobOffer.region,
        "contract_type": DashboardJobOffer.contract_type,
        "job_title": DashboardJobOffer.job_title,
        "source": DashboardJobOffer.source_system,
    }


def analytics_summary_statement(
    dimension: str | None = None,
    values: list[str] | None = None,
    job_titles: list[str] | None = None,
    start_year: int | None = None,
    end_year: int | None = None,
) -> Select:
    statement = select(
        DashboardJobOffer.job_id,
        DashboardJobOffer.sector,
        DashboardJobOffer.region,
        DashboardJobOffer.contract_type,
        DashboardJobOffer.annual_salary,
    )

    if values:
        filter_column = dimension_columns().get(dimension or "")
        if filter_column is not None:
            statement = statement.where(filter_column.in_(values))

    if job_titles:
        statement = statement.where(DashboardJobOffer.job_title.in_(job_titles))

    if start_year is not None:
        statement = statement.where(DashboardJobOffer.published_year >= start_year)
    if end_year is not None:
        statement = statement.where(DashboardJobOffer.published_year <= end_year)

    return statement


def offers_breakdown_statement(
    group_dimension: str = "region",
    filter_dimension: str | None = None,
    filter_values: list[str] | None = None,
    job_titles: list[str] | None = None,
    limit: int = 30,
    start_year: int | None = None,
    end_year: int | None = None,
) -> Select:
    dimension_map = dimension_columns()
    group_column = dimension_map.get(group_dimension, DashboardJobOffer.region)
    label = func.coalesce(group_column, MISSING_LABEL).label("label")
    nb_offres = func.count(func.distinct(DashboardJobOffer.job_id)).label("nb_offres")

    statement = select(label, nb_offres).where(func.nullif(group_column, "").is_not(None))

    if filter_values:
        filter_column = dimension_map.get(filter_dimension or "")
        if filter_column is not None:
            statement = statement.where(filter_column.in_(filter_values))

    if job_titles:
        statement = statement.where(DashboardJobOffer.job_title.in_(job_titles))

    if start_year is not None:
        statement = statement.where(DashboardJobOffer.published_year >= start_year)
    if end_year is not None:
        statement = statement.where(DashboardJobOffer.published_year <= end_year)

    return statement.group_by(label).order_by(desc(nb_offres)).limit(limit)


def salary_breakdown_statement(
    group_dimension: str = "job_title",
    filter_dimension: str | None = None,
    filter_values: list[str] | None = None,
    job_titles: list[str] | None = None,
    limit: int = 30,
    start_year: int | None = None,
    end_year: int | None = None,
) -> Select:
    annual_salary = annual_salary_expression()
    dimension_map = dimension_columns()
    group_column = dimension_map.get(group_dimension, DashboardJobOffer.job_title)
    label = func.coalesce(group_column, MISSING_LABEL).label("label")
    avg_salary = func.round(func.avg(annual_salary), 2).label("avg_salary")
    nb_offres = func.count(func.distinct(DashboardJobOffer.job_id)).label("nb_offres")

    statement = (
        select(label, avg_salary, nb_offres)
        .where(DashboardJobOffer.has_salary.is_(True))
        .where(annual_salary.between(MIN_DASHBOARD_ANNUAL_SALARY, MAX_DASHBOARD_ANNUAL_SALARY))
        .where(func.nullif(group_column, "").is_not(None))
    )

    if filter_values:
        filter_column = dimension_map.get(filter_dimension or "")
        if filter_column is not None:
            statement = statement.where(filter_column.in_(filter_values))

    if job_titles:
        statement = statement.where(DashboardJobOffer.job_title.in_(job_titles))

    if start_year is not None:
        statement = statement.where(DashboardJobOffer.published_year >= start_year)
    if end_year is not None:
        statement = statement.where(DashboardJobOffer.published_year <= end_year)

    return statement.group_by(label).order_by(desc(avg_salary)).limit(limit)


def top_skills_statement(limit: int = 20) -> Select:
    return (
        select(
            AggDashboardTopSkill.skill_name,
            AggDashboardTopSkill.skill_category,
            AggDashboardTopSkill.nb_offres,
        )
        .order_by(desc(AggDashboardTopSkill.nb_offres))
        .limit(limit)
    )


def top_advantages_statement(limit: int = 15) -> Select:
    return (
        select(
            AggDashboardTopAdvantage.advantage_name,
            AggDashboardTopAdvantage.nb_offres,
        )
        .order_by(desc(AggDashboardTopAdvantage.nb_offres))
        .limit(limit)
    )


def top_companies_statement(limit: int = 20) -> Select:
    return (
        select(
            AggDashboardTopCompany.company_name,
            AggDashboardTopCompany.nb_offres,
        )
        .order_by(desc(AggDashboardTopCompany.nb_offres))
        .limit(limit)
    )


def offers_by_source_statement() -> Select:
    return select(
        AggDashboardSource.source_system,
        AggDashboardSource.nb_offres,
    ).order_by(desc(AggDashboardSource.nb_offres))
