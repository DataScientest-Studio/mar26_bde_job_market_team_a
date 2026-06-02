{{
    config(
        indexes=[
            {'columns': ['job_id'], 'unique': True},
            {'columns': ['normalized_offer_id']},
            {'columns': ['company_id']},
            {'columns': ['location_id']},
            {'columns': ['salary_id']}
        ]
    )
}}

-- Final primary job offer row. Salary parsing stays here so the previous step remains small.
with attributes as (
    select
        *,
        lower(replace(coalesce(salary_raw, ''), '€', ' eur')) as salary_text
    from {{ ref('int_primary_offer_attributes') }}
),

salary_matches as (
    select
        *,
        salary_text ~ '[0-9]\s*k([^a-z0-9]|$)|\bk\s*(eur|euros)\b' as salary_has_k,
        regexp_match(
            salary_text,
            '([0-9]+(?:\s?[0-9]{3})*(?:[,.][0-9]+)?)\s*(?:k|eur|euros)?[^0-9,.]+([0-9]+(?:\s?[0-9]{3})*(?:[,.][0-9]+)?)\s*(?:k|eur|euros)'
        ) as salary_range_match,
        regexp_match(
            salary_text,
            '([0-9]+(?:\s?[0-9]{3})*(?:[,.][0-9]+)?)\s*(?:k|eur|euros)'
        ) as salary_single_match,
        regexp_match(salary_text, 'sur\s+([0-9]+(?:[.,][0-9]+)?)\s+mois') as salary_month_match
    from attributes
),

salary_normalized as (
    select
        *,
        case
            when salary_text like '%annuel%'
                or salary_text like '%annuelle%'
                or salary_text like '% year%'
                or salary_text like '%/year%'
                then 'year'
            when salary_text like '%mensuel%'
                or salary_text like '%mois%'
                or salary_text like '%month%'
                then 'month'
            when salary_text like '%horaire%'
                or salary_text like '%heure%'
                or salary_text like '%/h%'
                then 'hour'
            when salary_text like '%semaine%'
                or salary_text like '%week%'
                then 'week'
            when salary_has_k
                then 'year'
            else null
        end as salary_frequency_norm,
        case
            when salary_month_match is not null
                then replace(salary_month_match[1], ',', '.')::numeric
            else 12
        end as salary_month_count,
        case when salary_has_k then 1000 else 1 end as salary_unit_multiplier,
        case when salary_raw is not null then 'EUR' else null end as salary_currency
    from salary_matches
),

salary_parsed as (
    select
        *,
        case
            when salary_range_match is not null
                then nullif({{ parse_numeric_text('salary_range_match[1]') }} * salary_unit_multiplier, 0)
            when salary_single_match is not null
                then nullif({{ parse_numeric_text('salary_single_match[1]') }} * salary_unit_multiplier, 0)
            else null
        end as salary_min_norm,
        case
            when salary_range_match is not null
                then nullif({{ parse_numeric_text('salary_range_match[2]') }} * salary_unit_multiplier, 0)
            when salary_single_match is not null
                then nullif({{ parse_numeric_text('salary_single_match[1]') }} * salary_unit_multiplier, 0)
            else null
        end as salary_max_norm
    from salary_normalized
),

salary_guarded as (
    select
        *,
        {{ guarded_salary_amount('salary_min_norm', 'salary_frequency_norm') }} as salary_min_guarded,
        {{ guarded_salary_amount('salary_max_norm', 'salary_frequency_norm') }} as salary_max_guarded
    from salary_parsed
),

final as (
    select
        *,
        (
            salary_frequency_norm is not null
            and (
                salary_min_guarded is not null
                or salary_max_guarded is not null
            )
        ) as has_valid_salary
    from salary_guarded
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
    weekly_hours,
    full_time,
    salary_raw,
    case when has_valid_salary then salary_min_guarded else null end as salary_min_norm,
    case when has_valid_salary then salary_max_guarded else null end as salary_max_norm,
    case when has_valid_salary then salary_frequency_norm else null end as salary_frequency_norm,
    case when has_valid_salary then salary_month_count else null end as salary_month_count,
    case when has_valid_salary then salary_currency else null end as salary_currency,
    published_at_norm as published_at,
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
    {{ salary_dimension_id(
        'case when has_valid_salary then salary_min_guarded else null end',
        'case when has_valid_salary then salary_max_guarded else null end',
        'case when has_valid_salary then salary_frequency_norm else null end',
        'case when has_valid_salary then salary_month_count else null end',
        'weekly_hours',
        'case when has_valid_salary then salary_currency else null end'
    ) }} as salary_id,
    created_at
from final
