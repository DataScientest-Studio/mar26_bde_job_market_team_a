select distinct
    job_advantages.job_advantage_id,
    job_advantages.job_id,
    job_advantages.advantage_id
from {{ ref('int_job_advantages') }} as job_advantages
inner join {{ ref('fact_job_offers') }} as fact_jobs
    on job_advantages.job_id = fact_jobs.job_id
