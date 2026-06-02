select distinct
    advantage_id,
    advantage_name
from {{ ref('int_job_advantages') }}
