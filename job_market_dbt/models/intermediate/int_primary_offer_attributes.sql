{{
    config(
        indexes=[
            {'columns': ['job_id'], 'unique': True},
            {'columns': ['normalized_offer_id']},
            {'columns': ['company_id']},
            {'columns': ['location_id']}
        ]
    )
}}

-- Business attributes derived from the selected primary source, excluding salary parsing.
with source_offers as (
    select
        *,
        lower(
            coalesce(contract_type_raw, '')
            || ' '
            || coalesce(working_time_raw, '')
            || ' '
            || coalesce(schedule_context_raw, '')
        ) as work_context_lower
    from {{ ref('int_primary_source_offers') }}
),

labeled as (
    select
        source_offers.*,
        {{ clean_analytics_label('industry_raw') }} as industry_norm,
        {{ clean_analytics_label('coalesce(rome_family_raw, industry_raw)') }} as job_category_norm,
        {{ clean_analytics_label('rome_family_raw') }} as rome_family_norm,
        {{ clean_analytics_label('education_title') }} as education_title_norm,
        {{ clean_analytics_label('education_field') }} as education_field_norm,
        {{ company_size_min('company_size_raw') }} as company_size_min,
        {{ company_size_max('company_size_raw') }} as company_size_max,
        {{ weekly_hours_from_text("coalesce(working_time_raw, '') || ' ' || coalesce(schedule_context_raw, '')") }} as weekly_hours,
        {{ experience_years_from_text('experience_raw') }} as experience_years
    from source_offers
),

features as (
    select
        labeled.*,
        case
            when work_context_lower like '%temps plein%'
                or work_context_lower like '%full time%'
                then true
            when work_context_lower like '%temps partiel%'
                or work_context_lower like '%part time%'
                then false
            when weekly_hours is not null
                then weekly_hours >= 35
            else null
        end as full_time,
        case
            when coalesce(education_title_norm, education_field_norm) is not null
                then md5(coalesce(education_title_norm, '') || '|' || coalesce(education_field_norm, ''))
            else null
        end as education_id,
        case
            when company_match_norm is not null then md5(company_match_norm)
            else null
        end as company_id,
        md5(
            coalesce(city_norm, '')
            || '|'
            || coalesce(postal_code, '')
            || '|'
            || coalesce(region_norm, '')
            || '|'
            || coalesce(country_norm, '')
        ) as location_id,
        md5(
            coalesce(contract_type_norm, '')
            || '|'
            || coalesce(remote_norm, '')
            || '|'
            || coalesce(weekly_hours::text, '')
            || '|'
            || coalesce(
                case
                    when work_context_lower like '%temps plein%' or work_context_lower like '%full time%' then true
                    when work_context_lower like '%temps partiel%' or work_context_lower like '%part time%' then false
                    when weekly_hours is not null then weekly_hours >= 35
                    else null
                end::text,
                ''
            )
        ) as contract_type_id,
        md5(
            coalesce(title_norm, '')
            || '|'
            || coalesce(rome_code, '')
            || '|'
            || coalesce(rome_family_norm, '')
        ) as job_type_id,
        case
            when industry_norm is not null then md5(industry_norm)
            else null
        end as industry_id
    from labeled
)

select
    job_id,
    match_rule,
    match_score,
    normalized_offer_id,
    raw_offer_id,
    source_system,
    source_offer_id,
    source_url,
    title_raw,
    title_norm,
    company_raw,
    company_norm,
    city_raw,
    city_norm,
    region_norm,
    country_norm,
    postal_code,
    contract_type_raw,
    contract_type_norm,
    remote_norm,
    working_time_raw,
    schedule_context_raw,
    weekly_hours,
    full_time,
    salary_raw,
    published_at_norm,
    updated_at,
    experience_raw,
    experience_years,
    handicap_friendly,
    driving_license,
    rome_code,
    rome_family_raw,
    rome_family_norm,
    job_type_raw,
    job_category_norm,
    industry_raw,
    industry_norm,
    company_size_raw,
    company_size_min,
    company_size_max,
    education_title,
    education_field,
    education_title_norm,
    education_field_norm,
    education_id,
    company_id,
    location_id,
    contract_type_id,
    job_type_id,
    industry_id,
    created_at
from features
