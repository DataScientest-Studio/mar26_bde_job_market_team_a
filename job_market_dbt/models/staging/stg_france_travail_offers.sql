-- Expose les champs France Travail utiles au reste du pipeline
-- Cette couche reste proche du JSON source : extraction et typage léger uniquement
with source as (
    select *
    from {{ source('landing', 'raw_france_travail_offers') }}
),

renamed as (
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
        raw_payload ->> 'intitule' as title_raw,
        raw_payload ->> 'description' as description_raw,
        raw_payload #>> '{entreprise,nom}' as company_raw,
        {{ clean_city_label("raw_payload #>> '{lieuTravail,libelle}'") }} as city_raw,
        raw_payload #>> '{lieuTravail,codePostal}' as postal_code_raw,
        raw_payload #>> '{lieuTravail,commune}' as commune_code_raw,
        raw_payload ->> 'typeContratLibelle' as contract_type_raw,
        coalesce(
            nullif(raw_payload #>> '{salaire,libelle}', ''),
            nullif(raw_payload #>> '{salaire,commentaire}', '')
        ) as salary_raw,
        nullif(raw_payload ->> 'dateCreation', '')::timestamptz as published_at,
        nullif(raw_payload ->> 'dateActualisation', '')::timestamptz as updated_at,
        raw_payload ->> 'dureeTravailLibelleConverti' as working_time_raw,
        raw_payload ->> 'experienceLibelle' as experience_raw,
        raw_payload ->> 'romeCode' as rome_code,
        raw_payload ->> 'romeLibelle' as rome_family_raw,
        raw_payload ->> 'appellationlibelle' as job_type_raw,
        raw_payload ->> 'secteurActiviteLibelle' as industry_raw
    from source
)

select *
from renamed
