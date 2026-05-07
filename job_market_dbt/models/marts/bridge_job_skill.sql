select distinct
    job_skill_id,
    job_id,
    skill_id
from {{ ref('int_job_skills') }}
