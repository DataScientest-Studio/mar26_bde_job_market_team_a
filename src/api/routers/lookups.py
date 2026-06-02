from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import desc, func
from sqlalchemy.sql import Select
from sqlmodel import select

from src.api.dependencies import DbSession
from src.api.dashboard_models import DashboardJobOffer, DashboardLookupValue
from src.api.schemas import LookupValue

router = APIRouter(prefix="/lookups", tags=["Lookups"])


def _clean_display_text(value: str | None) -> str:
    if value is None:
        return ""
    if not any(marker in value for marker in ("Ãƒ", "Ã‚", "Ã¢")):
        return value
    try:
        return value.encode("latin1").decode("utf-8")
    except UnicodeError:
        return value


def _fetch_lookup(db: DbSession, statement: Select) -> list[LookupValue]:
    try:
        rows = db.exec(statement).all()
        return [
            LookupValue(
                value=_clean_display_text(row.value),
                label=_clean_display_text(row.label),
                count=row.count,
            )
            for row in rows
        ]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def dashboard_lookup_statement(lookup_type: str, limit: int | None) -> Select:
    statement = (
        select(
            DashboardLookupValue.value,
            DashboardLookupValue.label,
            DashboardLookupValue.nb_offres.label("count"),
        )
        .where(DashboardLookupValue.lookup_type == lookup_type)
        .order_by(desc(DashboardLookupValue.nb_offres), DashboardLookupValue.label)
    )
    if limit is not None:
        statement = statement.limit(limit)
    return statement


@router.get("/skills", response_model=list[LookupValue])
def get_skill_values(db: DbSession, limit: int = Query(100, ge=1, le=500)) -> list[LookupValue]:
    return _fetch_lookup(db, dashboard_lookup_statement("skills", limit))


@router.get("/contracts", response_model=list[LookupValue])
def get_contract_values(db: DbSession, limit: int = Query(100, ge=1, le=500)) -> list[LookupValue]:
    return _fetch_lookup(db, dashboard_lookup_statement("contracts", limit))


@router.get("/remote", response_model=list[LookupValue])
def get_remote_values(db: DbSession, limit: int = Query(100, ge=1, le=500)) -> list[LookupValue]:
    return _fetch_lookup(db, dashboard_lookup_statement("remote", limit))


@router.get("/education", response_model=list[LookupValue])
def get_education_values(db: DbSession, limit: int = Query(100, ge=1, le=500)) -> list[LookupValue]:
    return _fetch_lookup(db, dashboard_lookup_statement("education", limit))


@router.get("/industries", response_model=list[LookupValue])
def get_industry_values(db: DbSession, limit: int = Query(100, ge=1, le=500)) -> list[LookupValue]:
    return _fetch_lookup(db, dashboard_lookup_statement("industries", limit))


@router.get("/locations", response_model=list[LookupValue])
def get_location_values(db: DbSession, limit: int = Query(100, ge=1, le=500)) -> list[LookupValue]:
    return _fetch_lookup(db, dashboard_lookup_statement("locations", limit))


@router.get("/job-titles", response_model=list[LookupValue])
def get_job_title_values(
    db: DbSession,
    limit: int | None = Query(default=None, ge=1),
    search: str | None = Query(default=None, min_length=1),
) -> list[LookupValue]:
    count_expr = func.count(func.distinct(DashboardJobOffer.job_id)).label("count")
    statement = (
        select(
            DashboardJobOffer.job_title.label("value"),
            DashboardJobOffer.job_title.label("label"),
            count_expr,
        )
        .where(func.nullif(DashboardJobOffer.job_title, "").is_not(None))
    )
    if search:
        statement = statement.where(DashboardJobOffer.job_title.ilike(f"%{search.strip()}%"))
    statement = statement.group_by(DashboardJobOffer.job_title).order_by(desc(count_expr), DashboardJobOffer.job_title)
    if limit is not None:
        statement = statement.limit(limit)
    return _fetch_lookup(db, statement)
