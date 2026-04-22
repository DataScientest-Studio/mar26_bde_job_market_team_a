"""
Dashboard functions for job market data analytics.
Uses Supabase Python client to execute queries against a PostgreSQL data warehouse.

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

import os
from supabase import create_client, Client

# ---------------------------------------------------------------------------
# Supabase client initialization
# ---------------------------------------------------------------------------
SUPABASE_URL: str = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY: str = os.environ.get("SUPABASE_KEY", "")

supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# ---------------------------------------------------------------------------
# Helper — execute a named Supabase RPC function
# ---------------------------------------------------------------------------

def _run_rpc(fn_name: str, params: dict = None):
    """
    Execute a Supabase RPC function and return the data as a list of dicts.
    Raises a RuntimeError if the response contains an error.
    """
    response = supabase_client.rpc(fn_name, params or {}).execute()
    if hasattr(response, "error") and response.error:
        raise RuntimeError(f"Supabase RPC error on '{fn_name}': {response.error}")
    return response.data


# ---------------------------------------------------------------------------
# Dashboard functions
# Each function calls a named PostgreSQL function exposed via Supabase RPC.
# The SQL body of each function is documented below for reference.
# ---------------------------------------------------------------------------

def get_trends_by_sector() -> list[dict]:
    """
    Returns job offer trends grouped by industry sector and year.

    Equivalent SQL (define as PostgreSQL function 'get_trends_by_sector'):
        SELECT
            i.name        AS sector,
            EXTRACT(YEAR FROM f.published_date)::int AS year,
            COUNT(*)      AS nb_offres
        FROM fact_job_offers f
        JOIN dim_industry i ON f.industry_id = i.industry_id
        GROUP BY i.name, EXTRACT(YEAR FROM f.published_date)
        ORDER BY nb_offres DESC;
    """
    return _run_rpc("get_trends_by_sector")


def get_trends_by_region() -> list[dict]:
    """
    Returns job offer trends grouped by region and year.

    Equivalent SQL (define as PostgreSQL function 'get_trends_by_region'):
        SELECT
            r.name        AS region,
            EXTRACT(YEAR FROM f.published_date)::int AS year,
            COUNT(*)      AS nb_offres
        FROM fact_job_offers f
        JOIN dim_region r ON f.region_id = r.region_id
        GROUP BY r.name, EXTRACT(YEAR FROM f.published_date)
        ORDER BY nb_offres DESC;
    """
    return _run_rpc("get_trends_by_region")


def get_trends_by_contract_type() -> list[dict]:
    """
    Returns job offer trends grouped by contract type and year.

    Equivalent SQL (define as PostgreSQL function 'get_trends_by_contract_type'):
        SELECT
            c.name        AS contract_type,
            EXTRACT(YEAR FROM f.published_date)::int AS year,
            COUNT(*)      AS nb_offres
        FROM fact_job_offers f
        JOIN dim_contract_type c ON f.contract_type_id = c.contract_type_id
        GROUP BY c.name, EXTRACT(YEAR FROM f.published_date)
        ORDER BY nb_offres DESC;
    """
    return _run_rpc("get_trends_by_contract_type")


def get_salary_by_job() -> list[dict]:
    """
    Returns average salary grouped by job title and year.

    Equivalent SQL (define as PostgreSQL function 'get_salary_by_job'):
        SELECT
            j.title       AS job_title,
            EXTRACT(YEAR FROM f.published_date)::int AS year,
            ROUND(AVG(f.salary)::numeric, 2) AS avg_salary
        FROM fact_job_offers f
        JOIN dim_job j ON f.job_id = j.job_id
        GROUP BY j.title, EXTRACT(YEAR FROM f.published_date)
        ORDER BY avg_salary DESC;
    """
    return _run_rpc("get_salary_by_job")
