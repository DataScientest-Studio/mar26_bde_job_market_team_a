from collections import Counter

from fastapi import APIRouter, HTTPException, Query

from src.api.dependencies import DbSession
from src.api.schemas import (
    AdvantageTrend,
    AnalyticsSummary,
    CompanyTrend,
    ContractTrend,
    DashboardStats,
    MLModelStats,
    OfferBreakdown,
    RegionTrend,
    SalaryBreakdown,
    SalaryByJob,
    SectorTrend,
    SkillTrend,
    SourceTrend,
)
from src.features.dashboard_functions import (
    analytics_summary_statement,
    offers_breakdown_statement,
    offers_by_source_statement,
    salary_breakdown_statement,
    salary_by_job_statement,
    top_advantages_statement,
    top_companies_statement,
    top_skills_statement,
    trends_by_contract_type_statement,
    trends_by_region_statement,
    trends_by_sector_statement,
)
from src.models.predict_models import get_model_stats

router = APIRouter(prefix="/stats", tags=["Dashboard"])


@router.get("", response_model=DashboardStats)
def get_all_stats(db: DbSession) -> DashboardStats:
    try:
        return DashboardStats(
            sector=_get_stats_by_sector(db),
            region=_get_stats_by_region(db),
            contract=_get_stats_by_contract(db),
            salary=_get_stats_by_salary(db),
            skill=_get_stats_by_skill(db),
            advantage=_get_stats_by_advantage(db),
            company=_get_stats_by_company(db),
            source=_get_stats_by_source(db),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/ml", response_model=MLModelStats)
def get_ml_model_stats() -> MLModelStats:
    try:
        return MLModelStats(**get_model_stats())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/summary", response_model=AnalyticsSummary)
def get_analytics_summary(
    db: DbSession,
    dimension: str | None = Query(None, pattern="^(sector|region|contract_type|job_title|source)$"),
    values: list[str] = Query(default=[]),
    job_titles: list[str] = Query(default=[]),
    start_year: int | None = Query(None, ge=1900, le=2100),
    end_year: int | None = Query(None, ge=1900, le=2100),
) -> AnalyticsSummary:
    try:
        rows = db.exec(analytics_summary_statement(dimension, values, job_titles, start_year, end_year)).all()
        total_offers = len({row.job_id for row in rows})

        sector_counts = Counter(row.sector for row in rows if row.sector and row.sector != "Non renseigné")
        region_counts = Counter(row.region for row in rows if row.region and row.region != "Non renseigné")
        contract_counts = Counter(
            row.contract_type for row in rows if row.contract_type and row.contract_type != "Non renseigné"
        )
        salaries = [
            float(row.annual_salary)
            for row in rows
            if row.annual_salary is not None and 10_000 <= float(row.annual_salary) <= 200_000
        ]

        return AnalyticsSummary(
            total_offers=total_offers,
            top_sector=sector_counts.most_common(1)[0][0] if sector_counts else None,
            top_region=region_counts.most_common(1)[0][0] if region_counts else None,
            top_contract=contract_counts.most_common(1)[0][0] if contract_counts else None,
            avg_salary=round(sum(salaries) / len(salaries), 2) if salaries else None,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/salary_breakdown", response_model=list[SalaryBreakdown])
def get_salary_breakdown(
    db: DbSession,
    group_dimension: str = Query("job_title", pattern="^(sector|region|contract_type|job_title|source)$"),
    filter_dimension: str | None = Query(None, pattern="^(sector|region|contract_type|job_title|source)$"),
    values: list[str] = Query(default=[]),
    job_titles: list[str] = Query(default=[]),
    limit: int = Query(30, ge=1, le=100),
    start_year: int | None = Query(None, ge=1900, le=2100),
    end_year: int | None = Query(None, ge=1900, le=2100),
) -> list[SalaryBreakdown]:
    try:
        return [
            SalaryBreakdown(label=row.label, avg_salary=row.avg_salary, nb_offres=row.nb_offres)
            for row in db.exec(
                salary_breakdown_statement(
                    group_dimension, filter_dimension, values, job_titles, limit, start_year, end_year
                )
            )
        ]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/breakdown", response_model=list[OfferBreakdown])
def get_offer_breakdown(
    db: DbSession,
    group_dimension: str = Query("region", pattern="^(sector|region|contract_type|job_title|source)$"),
    filter_dimension: str | None = Query(None, pattern="^(sector|region|contract_type|job_title|source)$"),
    values: list[str] = Query(default=[]),
    job_titles: list[str] = Query(default=[]),
    limit: int = Query(30, ge=1, le=100),
    start_year: int | None = Query(None, ge=1900, le=2100),
    end_year: int | None = Query(None, ge=1900, le=2100),
) -> list[OfferBreakdown]:
    try:
        return [
            OfferBreakdown(label=row.label, nb_offres=row.nb_offres)
            for row in db.exec(
                offers_breakdown_statement(
                    group_dimension, filter_dimension, values, job_titles, limit, start_year, end_year
                )
            )
        ]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def _get_stats_by_sector(db: DbSession) -> list[SectorTrend]:
    try:
        return [
            SectorTrend(sector=row.sector, year=row.year, nb_offres=row.nb_offres)
            for row in db.exec(trends_by_sector_statement())
        ]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def _get_stats_by_region(db: DbSession) -> list[RegionTrend]:
    try:
        return [
            RegionTrend(region=row.region, year=row.year, nb_offres=row.nb_offres)
            for row in db.exec(trends_by_region_statement())
        ]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def _get_stats_by_contract(db: DbSession) -> list[ContractTrend]:
    try:
        return [
            ContractTrend(contract_type=row.contract_type, year=row.year, nb_offres=row.nb_offres)
            for row in db.exec(trends_by_contract_type_statement())
        ]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def _get_stats_by_salary(db: DbSession) -> list[SalaryByJob]:
    try:
        return [
            SalaryByJob(
                job_title=row.job_title,
                year=row.year,
                avg_salary=row.avg_salary,
                nb_offres=row.nb_offres,
            )
            for row in db.exec(salary_by_job_statement())
        ]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def _get_stats_by_skill(db: DbSession) -> list[SkillTrend]:
    try:
        return [
            SkillTrend(
                skill_name=row.skill_name,
                skill_category=row.skill_category,
                nb_offres=row.nb_offres,
            )
            for row in db.exec(top_skills_statement())
        ]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def _get_stats_by_advantage(db: DbSession) -> list[AdvantageTrend]:
    try:
        return [
            AdvantageTrend(
                advantage_name=row.advantage_name,
                nb_offres=row.nb_offres,
            )
            for row in db.exec(top_advantages_statement())
        ]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def _get_stats_by_company(db: DbSession) -> list[CompanyTrend]:
    try:
        return [
            CompanyTrend(
                company_name=row.company_name,
                nb_offres=row.nb_offres,
            )
            for row in db.exec(top_companies_statement())
        ]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def _get_stats_by_source(db: DbSession) -> list[SourceTrend]:
    try:
        return [
            SourceTrend(
                source_system=row.source_system,
                nb_offres=row.nb_offres,
            )
            for row in db.exec(offers_by_source_statement())
        ]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
