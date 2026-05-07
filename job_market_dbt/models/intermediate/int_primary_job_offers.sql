-- Une ligne par offre canonique, construite à partir de la source primaire
with primary_matches as (
    select *
    from {{ ref('int_job_offer_matches') }}
    where is_primary_source
),

primary_source_offers as (
    -- Récupère le payload complet de la source choisie pour enrichir l'offre canonique
    select
        matches.job_id,
        matches.match_rule,
        matches.match_score,
        normalized.normalized_offer_id,
        normalized.raw_offer_id,
        normalized.source_system,
        normalized.source_offer_id,
        normalized.source_url,
        normalized.source_file_name,
        normalized.source_file_path,
        normalized.raw_hash,
        normalized.ingested_at,
        normalized.raw_payload,
        normalized.title_raw,
        normalized.title_norm,
        normalized.description_raw,
        normalized.description_norm,
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
        array_to_string(
            array(
                select trim(value)
                from jsonb_array_elements_text(
                    coalesce(normalized.raw_payload -> 'contexteTravail' -> 'horaires', '[]'::jsonb)
                ) as value
            ),
            ' | '
        ) as schedule_context_raw,
        coalesce(
            nullif(normalized.raw_payload ->> 'education', ''),
            (
            select formation ->> 'niveauLibelle'
            from jsonb_array_elements(coalesce(normalized.raw_payload -> 'formations', '[]'::jsonb)) as formation
            order by case when formation ->> 'exigence' = 'E' then 1 else 2 end
            limit 1
            )
        ) as education_title,
        (
            select coalesce(formation ->> 'domaineLibelle', formation ->> 'domaine')
            from jsonb_array_elements(coalesce(normalized.raw_payload -> 'formations', '[]'::jsonb)) as formation
            order by case when formation ->> 'exigence' = 'E' then 1 else 2 end
            limit 1
        ) as education_field
    from primary_matches as matches
    inner join {{ ref('int_job_offers_normalized') }} as normalized
        on matches.normalized_offer_id = normalized.normalized_offer_id
),

enriched_offers as (
    -- Ajoute les attributs métier dérivés : temps de travail, salaire, formation, secteur
    select
        primary_source_offers.*,
        {{ clean_analytics_label('industry_raw') }} as industry_norm,
        {{ clean_analytics_label('coalesce(rome_family_raw, industry_raw)') }} as job_category_norm,
        {{ clean_analytics_label('rome_family_raw') }} as rome_family_norm,
        {{ clean_analytics_label('education_title') }} as education_title_norm,
        {{ clean_analytics_label('education_field') }} as education_field_norm,
        {{ company_size_min('company_size_raw') }} as company_size_min,
        {{ company_size_max('company_size_raw') }} as company_size_max,
        {{ weekly_hours_from_text("coalesce(working_time_raw, '') || ' ' || coalesce(schedule_context_raw, '')") }} as weekly_hours,
        {{ full_time_from_context('contract_type_raw', 'working_time_raw', 'schedule_context_raw') }} as full_time,
        case
            when raw_payload ? 'entrepriseAdaptee'
                then (raw_payload ->> 'entrepriseAdaptee')::boolean
            when raw_payload ? 'employeurHandiEngage'
                then (raw_payload ->> 'employeurHandiEngage')::boolean
            when lower(coalesce(description_raw, '')) like '%rqth%'
                or lower(coalesce(description_raw, '')) like '%travailleur handicape%'
                then true
            else null
        end as handicap_friendly,
        case
            when jsonb_typeof(coalesce(raw_payload -> 'permis', '[]'::jsonb)) = 'array'
                and jsonb_array_length(coalesce(raw_payload -> 'permis', '[]'::jsonb)) > 0
                then true
            when lower(coalesce(description_raw, '')) like '%permis b%'
                then true
            else false
        end as driving_license,
        case when salary_raw is not null then 'EUR' else null end as salary_currency,
        {{ normalize_salary_frequency('salary_raw') }} as salary_frequency_norm,
        {{ salary_month_count('salary_raw') }} as salary_month_count,
        {{ salary_unit_multiplier('salary_raw') }} as salary_unit_multiplier,
        {{ salary_range_match('salary_raw') }} as salary_range_match,
        {{ salary_single_match('salary_raw') }} as salary_single_match,
        {{ experience_years_from_text('experience_raw') }} as experience_years
    from primary_source_offers
),

parsed_offers as (
    -- Convertit les valeurs extraites en champs analytiques directement exploitables
    select
        job_id,
        match_rule,
        match_score,
        normalized_offer_id,
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
        title_norm,
        description_raw,
        description_norm,
        company_raw,
        company_norm,
        company_match_norm,
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
        salary_frequency_norm,
        salary_month_count,
        {{ parse_salary_min('salary_range_match', 'salary_single_match', 'salary_unit_multiplier') }} as salary_min_norm,
        {{ parse_salary_max('salary_range_match', 'salary_single_match', 'salary_unit_multiplier') }} as salary_max_norm,
        salary_currency,
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
        created_at
    from enriched_offers
),

cleaned_offers as (
    -- Écarte les salaires absurdes tout en conservant l'offre dans la fact
    select
        *,
        {{ guarded_salary_amount('salary_min_norm', 'salary_frequency_norm') }} as salary_min_guarded,
        {{ guarded_salary_amount('salary_max_norm', 'salary_frequency_norm') }} as salary_max_guarded,
        {{ has_guarded_salary('salary_min_norm', 'salary_max_norm', 'salary_frequency_norm') }} as has_guarded_salary,
        contract_type_norm as contract_type_clean
    from parsed_offers
),

final as (
    -- Calcule les clés de dimensions à partir des valeurs déjà nettoyées
    select
        job_id,
        match_rule,
        match_score,
        normalized_offer_id,
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
        title_norm,
        description_raw,
        description_norm,
        company_raw,
        company_norm,
        city_raw,
        city_norm,
        region_norm,
        country_norm,
        postal_code,
        contract_type_raw,
        contract_type_clean as contract_type_norm,
        remote_norm,
        working_time_raw,
        weekly_hours,
        full_time,
        salary_raw,
        salary_min_guarded as salary_min_norm,
        salary_max_guarded as salary_max_norm,
        case when has_guarded_salary then salary_frequency_norm else null end as salary_frequency_norm,
        case when has_guarded_salary then salary_month_count else null end as salary_month_count,
        case when has_guarded_salary then salary_currency else null end as salary_currency,
        published_at,
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
            coalesce(contract_type_clean, '')
            || '|'
            || coalesce(remote_norm, '')
            || '|'
            || coalesce(weekly_hours::text, '')
            || '|'
            || coalesce(full_time::text, '')
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
        end as industry_id,
        {{ salary_dimension_id(
            'salary_min_guarded',
            'salary_max_guarded',
            'case when has_guarded_salary then salary_frequency_norm else null end',
            'case when has_guarded_salary then salary_month_count else null end',
            'weekly_hours',
            'case when has_guarded_salary then salary_currency else null end'
        ) }} as salary_id,
        created_at
    from cleaned_offers
)

select *
from final
