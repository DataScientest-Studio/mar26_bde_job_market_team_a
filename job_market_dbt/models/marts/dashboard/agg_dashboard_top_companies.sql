{{
    config(
        indexes=[
            {'columns': ['company_name'], 'unique': True},
            {'columns': ['nb_offres']}
        ]
    )
}}

select
    company.name as company_name,
    count(distinct fact.job_id)::integer as nb_offres
from {{ ref('fact_job_offers') }} as fact
inner join {{ ref('dim_company') }} as company
    on fact.company_id = company.company_id
where nullif(company.name, '') is not null
group by company.name
