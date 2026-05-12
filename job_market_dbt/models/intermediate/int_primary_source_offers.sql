{{
    config(
        indexes=[
            {'columns': ['job_id'], 'unique': True},
            {'columns': ['normalized_offer_id']}
        ]
    )
}}

-- One row per canonical job, with the selected primary source payload.
with primary_matches as (
    select
        job_id,
        match_rule,
        match_score,
        normalized_offer_id
    from {{ ref('int_job_offer_matches') }}
    where is_primary_source
)

select
    matches.job_id,
    matches.match_rule,
    matches.match_score,
    normalized.normalized_offer_id,
    normalized.raw_offer_id,
    normalized.source_system,
    normalized.source_offer_id,
    normalized.source_url,
    normalized.title_raw,
    normalized.title_norm,
    normalized.company_raw,
    normalized.company_norm,
    normalized.company_match_norm,
    normalized.city_raw,
    normalized.city_norm,
    normalized.region_norm,
    normalized.country_norm,
    normalized.postal_code,
    normalized.contract_type_raw,
    normalized.contract_type_norm,
    normalized.remote_norm,
    normalized.salary_raw,
    normalized.published_at_norm,
    normalized.updated_at,
    normalized.working_time_raw,
    normalized.experience_raw,
    normalized.rome_code,
    normalized.rome_family_raw,
    normalized.job_type_raw,
    normalized.industry_raw,
    normalized.created_at,
    normalized.raw_payload ->> 'trancheEffectifEtab' as company_size_raw,
    case
        when normalized.raw_payload ? 'entrepriseAdaptee'
            then (normalized.raw_payload ->> 'entrepriseAdaptee')::boolean
        when normalized.raw_payload ? 'employeurHandiEngage'
            then (normalized.raw_payload ->> 'employeurHandiEngage')::boolean
        when lower(coalesce(normalized.description_raw, '')) like '%rqth%'
            or lower(coalesce(normalized.description_raw, '')) like '%travailleur handicape%'
            then true
        else null
    end as handicap_friendly,
    case
        when jsonb_typeof(coalesce(normalized.raw_payload -> 'permis', '[]'::jsonb)) = 'array'
            and jsonb_array_length(coalesce(normalized.raw_payload -> 'permis', '[]'::jsonb)) > 0
            then true
        when lower(coalesce(normalized.description_raw, '')) like '%permis b%'
            then true
        else false
    end as driving_license,
    schedule_context.schedule_context_raw,
    coalesce(
        nullif(normalized.raw_payload ->> 'education', ''),
        primary_formation.education_title
    ) as education_title,
    primary_formation.education_field
from primary_matches as matches
inner join {{ ref('int_job_offers_normalized') }} as normalized
    on matches.normalized_offer_id = normalized.normalized_offer_id
left join lateral (
    select string_agg(trim(schedule_value.value), ' | ') as schedule_context_raw
    from jsonb_array_elements_text(
        coalesce(normalized.raw_payload -> 'contexteTravail' -> 'horaires', '[]'::jsonb)
    ) as schedule_value(value)
) as schedule_context on true
left join lateral (
    select
        formation.value ->> 'niveauLibelle' as education_title,
        coalesce(formation.value ->> 'domaineLibelle', formation.value ->> 'domaine') as education_field
    from jsonb_array_elements(coalesce(normalized.raw_payload -> 'formations', '[]'::jsonb)) as formation(value)
    order by case when formation.value ->> 'exigence' = 'E' then 1 else 2 end
    limit 1
) as primary_formation on true
