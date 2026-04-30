from fastapi import APIRouter, HTTPException

from src.api.dependencies import DbSession
from src.api.schemas import ContractTrend, DashboardStats, RegionTrend, SalaryByJob, SectorTrend
from src.features.dashboard_functions import (
    salary_by_job_statement,
    trends_by_contract_type_statement,
    trends_by_region_statement,
    trends_by_sector_statement,
)

router = APIRouter(prefix="/stats", tags=["Dashboard"])


@router.get("", response_model=DashboardStats)
def get_all_stats(db: DbSession) -> DashboardStats:
    try:
        return DashboardStats(
            sector=get_stats_by_sector(db),
            region=get_stats_by_region(db),
            contract=get_stats_by_contract(db),
            salary=get_stats_by_salary(db),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/sector", response_model=list[SectorTrend])
def get_stats_by_sector(db: DbSession) -> list[SectorTrend]:
    try:
        return [
            SectorTrend(sector=row.sector, year=row.year, nb_offres=row.nb_offres)
            for row in db.exec(trends_by_sector_statement())
        ]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/region", response_model=list[RegionTrend])
def get_stats_by_region(db: DbSession) -> list[RegionTrend]:
    try:
        return [
            RegionTrend(region=row.region, year=row.year, nb_offres=row.nb_offres)
            for row in db.exec(trends_by_region_statement())
        ]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/contract", response_model=list[ContractTrend])
def get_stats_by_contract(db: DbSession) -> list[ContractTrend]:
    try:
        return [
            ContractTrend(contract_type=row.contract_type, year=row.year, nb_offres=row.nb_offres)
            for row in db.exec(trends_by_contract_type_statement())
        ]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/by_salary", response_model=list[SalaryByJob])
def get_stats_by_salary(db: DbSession) -> list[SalaryByJob]:
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
