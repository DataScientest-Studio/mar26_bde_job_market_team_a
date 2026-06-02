select
    job_type_id,
    max(coalesce(job_type_raw, title_raw)) as title,
    max(job_category_norm) as category,
    max(rome_code) as rome_code,
    max(rome_family_norm) as rome_family
from {{ ref('int_primary_job_offers') }}
group by 1
