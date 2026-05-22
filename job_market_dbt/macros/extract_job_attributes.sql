-- Extrait les compétences depuis les structures France Travail et WTTJ
-- Les libellés sont nettoyés plus tard dans int_job_skills
{% macro skill_rows_from_primary_offers() -%}
select
    primary_payload.job_id,
    extracted_skill.skill_name,
    extracted_skill.skill_category
from (
    select
        primary_offer.job_id,
        normalized.raw_payload
    from {{ ref('int_primary_source_offers') }} as primary_offer
    inner join {{ ref('int_job_offers_normalized') }} as normalized
        on primary_offer.normalized_offer_id = normalized.normalized_offer_id
) as primary_payload
cross join lateral (
    select
        trim(skill.value ->> 'libelle') as skill_name,
        'competence' as skill_category
    from jsonb_array_elements(coalesce(primary_payload.raw_payload -> 'competences', '[]'::jsonb)) as skill(value)

    union all

    select
        trim(skill.value ->> 'libelle') as skill_name,
        'soft_skill' as skill_category
    from jsonb_array_elements(coalesce(primary_payload.raw_payload -> 'qualitesProfessionnelles', '[]'::jsonb)) as skill(value)

    union all

    select
        trim(coalesce(skill.value ->> 'libelle', skill.value ->> 'langueLibelle', skill.value ->> 'name')) as skill_name,
        'language' as skill_category
    from jsonb_array_elements(coalesce(primary_payload.raw_payload -> 'langues', '[]'::jsonb)) as skill(value)

    union all

    select
        trim(skill.value ->> 'libelle') as skill_name,
        'license' as skill_category
    from jsonb_array_elements(coalesce(primary_payload.raw_payload -> 'permis', '[]'::jsonb)) as skill(value)

    union all

    select
        trim(skill.value #>> '{}') as skill_name,
        'competence' as skill_category
    from jsonb_array_elements(coalesce(primary_payload.raw_payload -> 'skills', '[]'::jsonb)) as skill(value)
) as extracted_skill
{%- endmacro %}

-- Extrait les avantages depuis le contexte de travail
-- Les horaires purs sont filtrés ici pour ne garder que des avantages lisibles
{% macro advantage_rows_from_primary_offers() -%}
select
    primary_offer.job_id,
    trim(split_value) as advantage_name
from {{ ref('int_primary_source_offers') }} as primary_offer
inner join {{ ref('int_job_offers_normalized') }} as normalized
    on primary_offer.normalized_offer_id = normalized.normalized_offer_id
cross join lateral jsonb_array_elements_text(
    coalesce(normalized.raw_payload -> 'contexteTravail' -> 'horaires', '[]'::jsonb)
) as raw_advantage(raw_advantage_name)
cross join lateral regexp_split_to_table(raw_advantage_name, E'\\n+') as split_value
where nullif(trim(split_value), '') is not null
    and lower(split_value) !~ '(^|\s)temps partiel'
    and lower(split_value) !~ '(^|\s)temps plein'
    and lower(split_value) !~ '([0-9]+(?:[.,][0-9]+)?)\s*h'
    and lower(split_value) !~ '([0-9]+(?:[.,][0-9]+)?)h\/semaine'
{%- endmacro %}
