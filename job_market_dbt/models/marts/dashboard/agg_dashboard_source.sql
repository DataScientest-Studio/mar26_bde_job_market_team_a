select
    source_system,
    count(*)::integer as nb_offres
from {{ ref('dashboard_job_offers') }}
group by source_system
