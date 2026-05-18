select
    industry_id,
    max(industry_norm) as industry_name
from {{ ref('int_primary_job_offers') }}
where industry_id is not null
group by 1
