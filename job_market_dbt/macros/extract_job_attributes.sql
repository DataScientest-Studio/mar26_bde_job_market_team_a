-- Extrait les compétences depuis les structures France Travail et WTTJ
-- Les libellés sont nettoyés plus tard dans int_job_skills
{% macro skill_rows_from_primary_offers() -%}
select
    job_id,
    trim(skill ->> 'libelle') as skill_name,
    'competence' as skill_category
from {{ ref('int_primary_job_offers') }}
cross join lateral jsonb_array_elements(coalesce(raw_payload -> 'competences', '[]'::jsonb)) as skill

union all

select
    job_id,
    trim(skill ->> 'libelle') as skill_name,
    'soft_skill' as skill_category
from {{ ref('int_primary_job_offers') }}
cross join lateral jsonb_array_elements(coalesce(raw_payload -> 'qualitesProfessionnelles', '[]'::jsonb)) as skill

union all

select
    job_id,
    trim(coalesce(skill ->> 'libelle', skill ->> 'langueLibelle', skill ->> 'name')) as skill_name,
    'language' as skill_category
from {{ ref('int_primary_job_offers') }}
cross join lateral jsonb_array_elements(coalesce(raw_payload -> 'langues', '[]'::jsonb)) as skill

union all

select
    job_id,
    trim(skill ->> 'libelle') as skill_name,
    'license' as skill_category
from {{ ref('int_primary_job_offers') }}
cross join lateral jsonb_array_elements(coalesce(raw_payload -> 'permis', '[]'::jsonb)) as skill

union all

select
    job_id,
    trim(skill #>> '{}') as skill_name,
    'competence' as skill_category
from {{ ref('int_primary_job_offers') }}
cross join lateral jsonb_array_elements(coalesce(raw_payload -> 'skills', '[]'::jsonb)) as skill
{%- endmacro %}

-- Extrait les avantages depuis le contexte de travail
-- Les horaires purs sont filtrés ici pour ne garder que des avantages lisibles
{% macro advantage_rows_from_primary_offers() -%}
select
    job_id,
    trim(split_value) as advantage_name
from {{ ref('int_primary_job_offers') }}
cross join lateral jsonb_array_elements_text(
    coalesce(raw_payload -> 'contexteTravail' -> 'horaires', '[]'::jsonb)
) as raw_advantage(raw_advantage_name)
cross join lateral regexp_split_to_table(raw_advantage_name, E'\\n+') as split_value
where nullif(trim(split_value), '') is not null
    and lower(split_value) !~ '(^|\s)temps partiel'
    and lower(split_value) !~ '(^|\s)temps plein'
    and lower(split_value) !~ '([0-9]+(?:[.,][0-9]+)?)\s*h'
    and lower(split_value) !~ '([0-9]+(?:[.,][0-9]+)?)h\/semaine'
{%- endmacro %}
