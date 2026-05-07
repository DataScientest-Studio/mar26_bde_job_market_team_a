-- Expose les champs WTTJ dans le même contrat de colonnes que France Travail
-- L'identifiant source est extrait de l'URL quand WTTJ ne fournit qu'un lien complet
with source as (
    select *
    from {{ source('landing', 'raw_welcome_to_the_jungle_offers') }}
),

renamed as (
    select
        raw_offer_id,
        source_system,
        case
            when coalesce(source_offer_id, '') ~ '^https?://'
                then regexp_replace(
                    regexp_replace(split_part(source_offer_id, '?', 1), '/$', ''),
                    '^.*/',
                    ''
                )
            when nullif(source_offer_id, '') is not null
                then source_offer_id
            when coalesce(raw_payload ->> 'id', '') ~ '^https?://'
                then regexp_replace(
                    regexp_replace(split_part(raw_payload ->> 'id', '?', 1), '/$', ''),
                    '^.*/',
                    ''
                )
            else raw_payload ->> 'id'
        end as source_offer_id,
        coalesce(
            source_url,
            case when coalesce(raw_payload ->> 'id', '') ~ '^https?://' then raw_payload ->> 'id' end
        ) as source_url,
        source_file_name,
        source_file_path,
        raw_hash,
        ingested_at,
        raw_payload,
        raw_payload ->> 'title' as title_raw,
        raw_payload ->> 'description' as description_raw,
        raw_payload ->> 'company' as company_raw,
        raw_payload ->> 'location' as city_raw,
        null::text as postal_code_raw,
        null::text as commune_code_raw,
        raw_payload ->> 'contract_type' as contract_type_raw,
        raw_payload ->> 'salary' as salary_raw,
        case
            when coalesce(raw_payload ->> 'published_at', '') ~ '^\d{4}-\d{2}-\d{2}'
                then (raw_payload ->> 'published_at')::timestamptz
            else null
        end as published_at,
        null::timestamptz as updated_at,
        raw_payload ->> 'remote' as working_time_raw,
        raw_payload ->> 'experience' as experience_raw,
        null::text as rome_code,
        null::text as rome_family_raw,
        raw_payload ->> 'title' as job_type_raw,
        raw_payload ->> 'industry' as industry_raw
    from source
)

select *
from renamed
