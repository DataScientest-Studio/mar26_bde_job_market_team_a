{{
    config(
        indexes=[
            {'columns': ['lookup_type', 'value'], 'unique': True},
            {'columns': ['lookup_type', 'nb_offres']}
        ]
    )
}}

select
    'skills' as lookup_type,
    skill.skill_name as value,
    skill.skill_name as label,
    count(distinct job_skill.job_id)::integer as nb_offres
from {{ ref('dim_skill') }} as skill
inner join {{ ref('bridge_job_skill') }} as job_skill
    on skill.skill_id = job_skill.skill_id
where nullif(skill.skill_name, '') is not null
group by skill.skill_name

union all

select
    'contracts' as lookup_type,
    contract.contract_type as value,
    contract.contract_type as label,
    count(distinct fact.job_id)::integer as nb_offres
from {{ ref('dim_contract') }} as contract
inner join {{ ref('fact_job_offers') }} as fact
    on contract.contract_type_id = fact.contract_type_id
where nullif(contract.contract_type, '') is not null
group by contract.contract_type

union all

select
    'remote' as lookup_type,
    contract.remote as value,
    contract.remote as label,
    count(distinct fact.job_id)::integer as nb_offres
from {{ ref('dim_contract') }} as contract
inner join {{ ref('fact_job_offers') }} as fact
    on contract.contract_type_id = fact.contract_type_id
where nullif(contract.remote, '') is not null
group by contract.remote

union all

select
    'education' as lookup_type,
    education.title as value,
    education.title as label,
    count(distinct fact.job_id)::integer as nb_offres
from {{ ref('dim_education') }} as education
inner join {{ ref('fact_job_offers') }} as fact
    on education.education_id = fact.education_id
where nullif(education.title, '') is not null
group by education.title

union all

select
    'industries' as lookup_type,
    offers.sector as value,
    offers.sector as label,
    count(distinct offers.job_id)::integer as nb_offres
from {{ ref('dashboard_job_offers') }} as offers
where nullif(offers.sector, '') is not null
group by offers.sector

union all

select
    'locations' as lookup_type,
    concat_ws(', ', nullif(location.city, ''), nullif(location.region, '')) as value,
    concat_ws(', ', nullif(location.city, ''), nullif(location.region, '')) as label,
    count(distinct fact.job_id)::integer as nb_offres
from {{ ref('dim_location') }} as location
inner join {{ ref('fact_job_offers') }} as fact
    on location.location_id = fact.location_id
where nullif(concat_ws(', ', nullif(location.city, ''), nullif(location.region, '')), '') is not null
group by concat_ws(', ', nullif(location.city, ''), nullif(location.region, ''))
