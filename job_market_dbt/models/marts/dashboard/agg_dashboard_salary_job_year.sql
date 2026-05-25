select
    job_title,
    published_year as year,
    round(avg(annual_salary), 2) as avg_salary,
    count(*)::integer as nb_offres
from {{ ref('dashboard_job_offers') }}
where published_year is not null
    and annual_salary between 10000 and 200000
group by job_title, published_year
