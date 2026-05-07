-- Une ligne par offre source, avec des libellés nettoyés avant le matching inter-source
with unioned as (
    -- Aligne les deux sources dans un même contrat de colonnes
    select
        raw_offer_id,
        source_system,
        source_offer_id,
        source_url,
        source_file_name,
        source_file_path,
        raw_hash,
        ingested_at,
        raw_payload,
        title_raw,
        description_raw,
        company_raw,
        city_raw,
        postal_code_raw,
        contract_type_raw,
        salary_raw,
        published_at,
        updated_at,
        working_time_raw,
        experience_raw,
        rome_code,
        rome_family_raw,
        job_type_raw,
        industry_raw
    from {{ ref('stg_france_travail_offers') }}

    union all

    select
        raw_offer_id,
        source_system,
        source_offer_id,
        source_url,
        source_file_name,
        source_file_path,
        raw_hash,
        ingested_at,
        raw_payload,
        title_raw,
        description_raw,
        company_raw,
        city_raw,
        postal_code_raw,
        contract_type_raw,
        salary_raw,
        published_at,
        updated_at,
        working_time_raw,
        experience_raw,
        rome_code,
        rome_family_raw,
        job_type_raw,
        industry_raw
    from {{ ref('stg_welcome_to_the_jungle_offers') }}
),

cleaned as (
    -- Les champs *_clean deviennent la base commune pour le matching FT/WTTJ
    select
        *,
        {{ clean_analytics_label('title_raw') }} as title_clean,
        {{ clean_company_label('company_raw') }} as company_clean,
        {{ display_city_label('city_raw') }} as city_clean,
        {{ clean_contract_type_label('contract_type_raw') }} as contract_type_clean,
        {{ clean_analytics_label('description_raw') }} as description_clean
    from unioned
),

prepared as (
    -- Calcule les libellés analytiques et les clés techniques de matching
    select
        md5(source_system || '|' || raw_offer_id::text) as normalized_offer_id,
        raw_offer_id,
        source_system,
        source_offer_id,
        source_url,
        source_file_name,
        source_file_path,
        raw_hash,
        ingested_at,
        raw_payload,
        title_raw,
        title_clean as title_norm,
        {{ normalize_title_match('title_clean') }} as title_match_norm,
        company_raw,
        company_clean as company_norm,
        {{ normalize_company_match('company_clean') }} as company_match_norm,
        city_raw,
        city_clean as city_norm,
        {{ normalize_city_match('city_clean') }} as city_match_norm,
        {{ extract_postal_code('postal_code_raw', 'city_raw') }} as postal_code,
        {{ postal_code_to_region(extract_postal_code('postal_code_raw', 'city_raw')) }} as region_norm,
        'france' as country_norm,
        contract_type_raw,
        contract_type_clean as contract_type_norm,
        case
            when lower(coalesce(city_raw, '') || ' ' || coalesce(description_raw, '') || ' ' || coalesce(working_time_raw, '')) like '%teletravail%' then 'teletravail'
            when lower(coalesce(city_raw, '') || ' ' || coalesce(description_raw, '') || ' ' || coalesce(working_time_raw, '')) like '%remote%' then 'remote'
            else 'non_precise'
        end as remote_raw_norm,
        salary_raw,
        published_at as published_at_norm,
        coalesce(published_at::date, ingested_at::date) as match_reference_date,
        updated_at,
        description_raw,
        description_clean as description_norm,
        working_time_raw,
        experience_raw,
        rome_code,
        rome_family_raw,
        job_type_raw,
        industry_raw,
        current_timestamp as created_at
    from cleaned
),

final as (
    -- Fingerprint exact conservé pour audit et debug du matching
    select
        *,
        {{ clean_analytics_label('remote_raw_norm') }} as remote_norm,
        case
            when title_match_norm is not null
                and company_match_norm is not null
                and city_match_norm is not null
                and match_reference_date is not null
                then md5(
                    title_match_norm
                    || '|'
                    || company_match_norm
                    || '|'
                    || city_match_norm
                    || '|'
                    || to_char(match_reference_date, 'YYYY-MM')
                )
            else null
        end as fingerprint_exact
    from prepared
)

select *
from final
