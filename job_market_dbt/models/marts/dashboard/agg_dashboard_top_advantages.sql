select
    coalesce(advantage.advantage_name, 'Non renseigné') as advantage_name,
    count(distinct job_advantage.job_id)::integer as nb_offres
from {{ ref('dim_advantage') }} as advantage
inner join {{ ref('bridge_job_advantage') }} as job_advantage
    on advantage.advantage_id = job_advantage.advantage_id
group by 1
