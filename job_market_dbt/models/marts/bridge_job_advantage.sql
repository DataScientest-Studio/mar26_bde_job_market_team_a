select distinct
    job_advantage_id,
    job_id,
    advantage_id
from {{ ref('int_job_advantages') }}
