-- Offre canonique finale enrichie avec les clés de dimensions
select
    job_id,
    company_id,
    location_id,
    contract_type_id,
    job_type_id,
    industry_id,
    salary_id,
    education_id,
    source_system as primary_source_system,
    source_offer_id as primary_source_offer_id,
    source_url as primary_source_url,
    experience_years,
    handicap_friendly,
    driving_license,
    published_at,
    created_at,
    updated_at,
    match_rule,
    match_score
from {{ ref('int_primary_job_offers') }}
