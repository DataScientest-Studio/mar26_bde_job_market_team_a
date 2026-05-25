select
    coalesce(skill.skill_name, 'Non renseigné') as skill_name,
    coalesce(skill.skill_category, 'Non renseigné') as skill_category,
    count(distinct job_skill.job_id)::integer as nb_offres
from {{ ref('dim_skill') }} as skill
inner join {{ ref('bridge_job_skill') }} as job_skill
    on skill.skill_id = job_skill.skill_id
group by 1, 2
