{{
    config(
        indexes=[
            {'columns': ['job_id'], 'unique': True},
            {'columns': ['published_year']},
            {'columns': ['job_title']},
            {'columns': ['source_system']},
            {'columns': ['region']},
            {'columns': ['sector']},
            {'columns': ['contract_type']},
            {'columns': ['job_title', 'source_system']},
            {'columns': ['job_title', 'region']},
            {'columns': ['job_title', 'sector']}
        ]
    )
}}

with offers as (
    select
        fact.job_id,
        extract(year from fact.published_at)::integer as published_year,
        job_type.title as job_title,
        industry.industry_name as sector,
        location.region,
        contract.contract_type,
        fact.primary_source_system as source_system,
        case
            when salary.frequency = 'month'
                then (
                    (coalesce(salary.salary_min, salary.salary_max)
                    + coalesce(salary.salary_max, salary.salary_min)) / 2
                ) * 12
            when salary.frequency = 'week'
                then (
                    (coalesce(salary.salary_min, salary.salary_max)
                    + coalesce(salary.salary_max, salary.salary_min)) / 2
                ) * 52
            when salary.frequency = 'hour'
                then (
                    (coalesce(salary.salary_min, salary.salary_max)
                    + coalesce(salary.salary_max, salary.salary_min)) / 2
                ) * 35 * 52
            else (
                (coalesce(salary.salary_min, salary.salary_max)
                + coalesce(salary.salary_max, salary.salary_min)) / 2
            )
        end as annual_salary
    from {{ ref('fact_job_offers') }} as fact
    left join {{ ref('dim_job_type') }} as job_type
        on fact.job_type_id = job_type.job_type_id
    left join {{ ref('dim_industry') }} as industry
        on fact.industry_id = industry.industry_id
    left join {{ ref('dim_location') }} as location
        on fact.location_id = location.location_id
    left join {{ ref('dim_contract') }} as contract
        on fact.contract_type_id = contract.contract_type_id
    left join {{ ref('dim_salary') }} as salary
        on fact.salary_id = salary.salary_id
    where fact.published_at is not null
)

select
    job_id,
    published_year,
    coalesce(job_title, 'Non renseigné') as job_title,
    coalesce(sector, 'Non renseigné') as sector,
    coalesce(region, 'Non renseigné') as region,
    coalesce(contract_type, 'Non renseigné') as contract_type,
    coalesce(source_system, 'Non renseigné') as source_system,
    annual_salary,
    annual_salary is not null as has_salary
from offers
