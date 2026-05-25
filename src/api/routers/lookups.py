from typing import Any

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.sql import Select
from sqlmodel import select

from src.api.dependencies import DbSession
from src.api.models import Contract, Education, Industry, JobOffer, JobSkill, JobType, Location, Skill
from src.api.schemas import DashboardLookups, LookupValue

router = APIRouter(prefix="/lookups", tags=["Lookups"])


def _clean_display_text(value: str | None) -> str:
    if value is None:
        return ""
    if not any(marker in value for marker in ("Ã", "Â", "â")):
        return value
    try:
        return value.encode("latin1").decode("utf-8")
    except UnicodeError:
        return value


def _count_jobs():
    return func.count(func.distinct(JobOffer.job_id)).label("count")


def _not_blank(column: Any):
    return func.nullif(column, "").is_not(None)


def _lookup_statement(value_expr: Any, label_expr: Any, count_expr: Any, limit: int | None) -> Select:
    statement = (
        select(
            value_expr.label("value"),
            label_expr.label("label"),
            count_expr,
        )
        .where(_not_blank(value_expr))
        .group_by(value_expr, label_expr)
        .order_by(count_expr.desc().nulls_last(), label_expr)
    )
    if limit is not None:
        statement = statement.limit(limit)
    return statement


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


@router.get("/skills", response_model=list[LookupValue])
def get_skill_values(db: DbSession, limit: int = Query(100, ge=1, le=500)) -> list[LookupValue]:
    count_expr = _count_jobs()
    statement = (
        _lookup_statement(Skill.skill_name, Skill.skill_name, count_expr, limit)
        .join(JobSkill, Skill.skill_id == JobSkill.skill_id)
        .join(JobOffer, JobSkill.job_id == JobOffer.job_id)
    )
    return _fetch_lookup(db, statement)


@router.get("/contracts", response_model=list[LookupValue])
def get_contract_values(db: DbSession, limit: int = Query(100, ge=1, le=500)) -> list[LookupValue]:
    count_expr = _count_jobs()
    statement = (
        _lookup_statement(Contract.contract_type, Contract.contract_type, count_expr, limit)
        .join(JobOffer, Contract.contract_type_id == JobOffer.contract_type_id)
    )
    return _fetch_lookup(db, statement)


@router.get("/remote", response_model=list[LookupValue])
def get_remote_values(db: DbSession, limit: int = Query(100, ge=1, le=500)) -> list[LookupValue]:
    count_expr = _count_jobs()
    statement = (
        _lookup_statement(Contract.remote, Contract.remote, count_expr, limit)
        .join(JobOffer, Contract.contract_type_id == JobOffer.contract_type_id)
    )
    return _fetch_lookup(db, statement)


@router.get("/education", response_model=list[LookupValue])
def get_education_values(db: DbSession, limit: int = Query(100, ge=1, le=500)) -> list[LookupValue]:
    count_expr = _count_jobs()
    statement = (
        _lookup_statement(Education.title, Education.title, count_expr, limit)
        .join(JobOffer, Education.education_id == JobOffer.education_id)
    )
    return _fetch_lookup(db, statement)


@router.get("/industries", response_model=list[LookupValue])
def get_industry_values(db: DbSession, limit: int = Query(100, ge=1, le=500)) -> list[LookupValue]:
    count_expr = _count_jobs()
    statement = (
        _lookup_statement(Industry.industry_name, Industry.industry_name, count_expr, limit)
        .join(JobOffer, Industry.industry_id == JobOffer.industry_id)
    )
    return _fetch_lookup(db, statement)


@router.get("/locations", response_model=list[LookupValue])
def get_location_values(db: DbSession, limit: int = Query(100, ge=1, le=500)) -> list[LookupValue]:
    count_expr = _count_jobs()
    location_expr = func.concat_ws(
        ", ",
        func.nullif(Location.city, ""),
        func.nullif(Location.region, ""),
    )
    statement = (
        _lookup_statement(location_expr, location_expr, count_expr, limit)
        .join(JobOffer, Location.location_id == JobOffer.location_id)
    )
    return _fetch_lookup(db, statement)


@router.get("/job-titles", response_model=list[LookupValue])
def get_job_title_values(
    db: DbSession,
    limit: int | None = Query(default=None, ge=1),
    search: str | None = Query(default=None, min_length=1),
) -> list[LookupValue]:
    count_expr = _count_jobs()
    statement = (
        _lookup_statement(JobType.title, JobType.title, count_expr, limit)
        .join(JobOffer, JobType.job_type_id == JobOffer.job_type_id)
    )
    if search:
        statement = statement.where(JobType.title.ilike(f"%{search.strip()}%"))
    return _fetch_lookup(db, statement)


@router.get("", response_model=DashboardLookups)
def get_all_lookup_values(db: DbSession, limit: int = Query(100, ge=1, le=500)) -> DashboardLookups:
    return DashboardLookups(
        skills=get_skill_values(db, limit),
        contracts=get_contract_values(db, limit),
        remote=get_remote_values(db, limit),
        education=get_education_values(db, limit),
        industries=get_industry_values(db, limit),
        locations=get_location_values(db, limit),
        job_titles=get_job_title_values(db, limit),
    )
