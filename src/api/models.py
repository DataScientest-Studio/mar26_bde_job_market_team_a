from datetime import datetime
from decimal import Decimal

from sqlmodel import Field, SQLModel


class Company(SQLModel, table=True):
    __tablename__ = "dim_company"
    __table_args__ = {"schema": "analytics"}

    company_id: str = Field(primary_key=True)
    name: str | None = None
    name_normalized: str | None = None
    size_min: int | None = None
    size_max: int | None = None
    country: str | None = None


class Location(SQLModel, table=True):
    __tablename__ = "dim_location"
    __table_args__ = {"schema": "analytics"}

    location_id: str = Field(primary_key=True)
    city: str | None = None
    region: str | None = None
    country: str | None = None
    postal_code: str | None = None


class Contract(SQLModel, table=True):
    __tablename__ = "dim_contract"
    __table_args__ = {"schema": "analytics"}

    contract_type_id: str = Field(primary_key=True)
    contract_type: str | None = None
    full_time: bool | None = None
    remote: str | None = None
    weekly_hours: Decimal | None = None


class Industry(SQLModel, table=True):
    __tablename__ = "dim_industry"
    __table_args__ = {"schema": "analytics"}

    industry_id: str = Field(primary_key=True)
    industry_name: str | None = None


class Salary(SQLModel, table=True):
    __tablename__ = "dim_salary"
    __table_args__ = {"schema": "analytics"}

    salary_id: str = Field(primary_key=True)
    frequency: str | None = None
    salary_min: Decimal | None = None
    salary_max: Decimal | None = None
    currency: str | None = None


class JobType(SQLModel, table=True):
    __tablename__ = "dim_job_type"
    __table_args__ = {"schema": "analytics"}

    job_type_id: str = Field(primary_key=True)
    title: str | None = None
    category: str | None = None
    rome_code: str | None = None
    rome_family: str | None = None


class Skill(SQLModel, table=True):
    __tablename__ = "dim_skill"
    __table_args__ = {"schema": "analytics"}

    skill_id: str = Field(primary_key=True)
    skill_name: str
    skill_category: str


class JobSkill(SQLModel, table=True):
    __tablename__ = "bridge_job_skill"
    __table_args__ = {"schema": "analytics"}

    job_skill_id: str = Field(primary_key=True)
    job_id: str
    skill_id: str


class JobOffer(SQLModel, table=True):
    __tablename__ = "fct_job_offers"
    __table_args__ = {"schema": "analytics"}

    job_id: str = Field(primary_key=True)
    company_id: str | None = None
    location_id: str | None = None
    contract_type_id: str | None = None
    job_type_id: str | None = None
    industry_id: str | None = None
    salary_id: str | None = None
    education_id: str | None = None
    title_raw: str | None = None
    title_norm: str | None = None
    description_raw: str | None = None
    description_norm: str | None = None
    primary_source_system: str | None = None
    primary_source_offer_id: str | None = None
    primary_source_url: str | None = None
    experience_years: Decimal | None = None
    handicap_friendly: bool | None = None
    driving_license: bool | None = None
    published_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    match_rule: str | None = None
    match_score: Decimal | None = None
