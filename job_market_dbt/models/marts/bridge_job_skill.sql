select distinct
    job_skills.job_skill_id,
    job_skills.job_id,
    job_skills.skill_id
from {{ ref('int_job_skills') }} as job_skills
inner join {{ ref('fact_job_offers') }} as fact_jobs
    on job_skills.job_id = fact_jobs.job_id
