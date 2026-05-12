-- Bridge préparatoire job <-> skill
-- Le grain est une ligne par compétence rattachée à une offre
{{
    config(
        indexes=[
            {'columns': ['job_skill_id'], 'unique': True},
            {'columns': ['job_id']},
            {'columns': ['skill_id']}
        ]
    )
}}

with skill_rows as (
    -- Centralise l'extraction JSON des compétences FT et WTTJ
    {{ skill_rows_from_primary_offers() }}
),

cleaned as (
    -- Nettoie les libellés avant de calculer les ids, pour éviter les doublons de type "▪ PYTHON"
    select
        job_id,
        {{ clean_display_label('skill_name') }} as skill_name,
        {{ clean_display_label('skill_category') }} as skill_category
    from skill_rows
    where nullif(skill_name, '') is not null
)

select distinct
    md5(skill_category || '|' || skill_name) as skill_id,
    md5(job_id || '|' || skill_category || '|' || skill_name) as job_skill_id,
    job_id,
    skill_name,
    skill_category
from cleaned
