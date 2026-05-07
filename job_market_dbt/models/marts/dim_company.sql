select
    company_id,
    max(company_norm) as name,
    min(company_size_min) as size_min,
    max(company_size_max) as size_max,
    max(country_norm) as country
from {{ ref('int_primary_job_offers') }}
where company_id is not null
group by 1
