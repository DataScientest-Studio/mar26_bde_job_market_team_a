from pydantic import BaseModel, ConfigDict


class SectorTrend(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sector: str
    year: int
    nb_offres: int


class RegionTrend(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    region: str
    year: int
    nb_offres: int


class ContractTrend(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    contract_type: str
    year: int
    nb_offres: int


class SalaryByJob(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_title: str
    year: int
    avg_salary: float
    nb_offres: int


class DashboardStats(BaseModel):
    sector: list[SectorTrend]
    region: list[RegionTrend]
    contract: list[ContractTrend]
    salary: list[SalaryByJob]
