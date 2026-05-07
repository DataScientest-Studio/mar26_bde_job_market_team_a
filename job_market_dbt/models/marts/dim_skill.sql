select distinct
    skill_id,
    skill_name,
    skill_category
from {{ ref('int_job_skills') }}
