select distinct
    education_id,
    education_title_norm as title,
    education_field_norm as education_field
from {{ ref('int_primary_job_offers') }}
where education_id is not null
