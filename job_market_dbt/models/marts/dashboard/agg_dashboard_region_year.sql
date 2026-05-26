select
    region,
    published_year as year,
    count(*)::integer as nb_offres
from {{ ref('dashboard_job_offers') }}
where published_year is not null
    and nullif(region, '') is not null
group by region, published_year
