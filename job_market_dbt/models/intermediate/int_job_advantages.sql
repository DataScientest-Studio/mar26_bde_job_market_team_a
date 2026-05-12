-- Bridge préparatoire job <-> avantage
-- Le grain est une ligne par avantage rattaché à une offre
{{
    config(
        indexes=[
            {'columns': ['job_advantage_id'], 'unique': True},
            {'columns': ['job_id']},
            {'columns': ['advantage_id']}
        ]
    )
}}

with advantage_rows as (
    -- Centralise l'extraction des avantages depuis les horaires/contexte de travail FT
    {{ advantage_rows_from_primary_offers() }}
),

cleaned as (
    -- Nettoie les libellés avant de calculer les ids
    select
        job_id,
        {{ clean_display_label('advantage_name') }} as advantage_name
    from advantage_rows
)

select distinct
    md5(advantage_name) as advantage_id,
    md5(job_id || '|' || advantage_name) as job_advantage_id,
    job_id,
    advantage_name
from cleaned
