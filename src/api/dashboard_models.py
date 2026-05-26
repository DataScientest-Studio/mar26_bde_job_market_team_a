from decimal import Decimal

from sqlmodel import Field, SQLModel


class DashboardJobOffer(SQLModel, table=True):
    __tablename__ = "dashboard_job_offers"
    __table_args__ = {"schema": "analytics"}

    job_id: str = Field(primary_key=True)
    published_year: int | None = None
    job_title: str | None = None
    sector: str | None = None
    region: str | None = None
    contract_type: str | None = None
    source_system: str | None = None
    annual_salary: Decimal | None = None
    has_salary: bool | None = None


class AggDashboardSectorYear(SQLModel, table=True):
    __tablename__ = "agg_dashboard_sector_year"
    __table_args__ = {"schema": "analytics"}

    sector: str = Field(primary_key=True)
    year: int = Field(primary_key=True)
    nb_offres: int


class AggDashboardRegionYear(SQLModel, table=True):
    __tablename__ = "agg_dashboard_region_year"
    __table_args__ = {"schema": "analytics"}

    region: str = Field(primary_key=True)
    year: int = Field(primary_key=True)
    nb_offres: int


class AggDashboardContractYear(SQLModel, table=True):
    __tablename__ = "agg_dashboard_contract_year"
    __table_args__ = {"schema": "analytics"}

    contract_type: str = Field(primary_key=True)
    year: int = Field(primary_key=True)
    nb_offres: int


class AggDashboardSalaryJobYear(SQLModel, table=True):
    __tablename__ = "agg_dashboard_salary_job_year"
    __table_args__ = {"schema": "analytics"}

    job_title: str = Field(primary_key=True)
    year: int = Field(primary_key=True)
    avg_salary: Decimal
    nb_offres: int


class AggDashboardSource(SQLModel, table=True):
    __tablename__ = "agg_dashboard_source"
    __table_args__ = {"schema": "analytics"}

    source_system: str = Field(primary_key=True)
    nb_offres: int


class AggDashboardTopSkill(SQLModel, table=True):
    __tablename__ = "agg_dashboard_top_skills"
    __table_args__ = {"schema": "analytics"}

    skill_name: str = Field(primary_key=True)
    skill_category: str = Field(primary_key=True)
    nb_offres: int


class AggDashboardTopAdvantage(SQLModel, table=True):
    __tablename__ = "agg_dashboard_top_advantages"
    __table_args__ = {"schema": "analytics"}

    advantage_name: str = Field(primary_key=True)
    nb_offres: int


class AggDashboardTopCompany(SQLModel, table=True):
    __tablename__ = "agg_dashboard_top_companies"
    __table_args__ = {"schema": "analytics"}

    company_name: str = Field(primary_key=True)
    nb_offres: int


class DashboardLookupValue(SQLModel, table=True):
    __tablename__ = "dashboard_lookup_values"
    __table_args__ = {"schema": "analytics"}

    lookup_type: str = Field(primary_key=True)
    value: str = Field(primary_key=True)
    label: str
    nb_offres: int
