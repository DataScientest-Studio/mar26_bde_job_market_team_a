/* rapproche les offres apres normalisation, uniquement entre sources differentes */
with base as (
    select *
    from {{ ref('int_job_offers_normalized') }}
),

/* un candidat de match doit rapprocher deux sources dans une fenetre de 30 jours glissants */
candidate_pairs as (
    select
        a.normalized_offer_id as normalized_offer_id_a,
        b.normalized_offer_id as normalized_offer_id_b,
        md5(
            a.fingerprint_exact
            || '|'
            || b.fingerprint_exact
            || '|'
            || to_char(least(a.match_reference_date, b.match_reference_date), 'YYYY-MM-DD')
            || '|'
            || to_char(greatest(a.match_reference_date, b.match_reference_date), 'YYYY-MM-DD')
        ) as candidate_key
    from base as a
    inner join base as b
        on a.source_system <> b.source_system
        and a.normalized_offer_id < b.normalized_offer_id
        and a.title_match_norm = b.title_match_norm
        and a.company_match_norm = b.company_match_norm
        and a.city_match_norm = b.city_match_norm
        and a.match_reference_date is not null
        and b.match_reference_date is not null
        and abs(a.match_reference_date - b.match_reference_date) <= 30
    where a.fingerprint_exact is not null
        and b.fingerprint_exact is not null
),

matches as (
    select
        normalized_offer_id,
        min(candidate_key) as candidate_key
    from (
        select normalized_offer_id_a as normalized_offer_id, candidate_key
        from candidate_pairs

        union all

        select normalized_offer_id_b as normalized_offer_id, candidate_key
        from candidate_pairs
    ) as matched_offers
    group by 1
),

/* on fusionne seulement les offres qui ont un candidat de match */
enriched as (
    select
        base.*,
        matches.candidate_key,
        case
            when matches.candidate_key is not null
                then matches.candidate_key
            else base.normalized_offer_id
        end as match_key
    from base
    left join matches
        on base.normalized_offer_id = matches.normalized_offer_id
),

/* France Travail reste prioritaire si les deux sources matchent */
scored as (
    select
        md5(match_key) as job_id,
        normalized_offer_id,
        raw_offer_id,
        source_system,
        source_offer_id,
        source_url,
        ingested_at,
        published_at_norm,
        case
            when candidate_key is not null
                then 'fingerprint_exact_inter_source'
            else 'single_source'
        end as match_rule,
        case
            when candidate_key is not null
                then 1.00
            else 0.50
        end as match_score,
        row_number() over (
            partition by match_key
            order by
                case when source_system = 'france_travail' then 1 else 2 end,
                published_at_norm desc nulls last,
                ingested_at desc,
                raw_offer_id desc
        ) as source_rank
    from enriched
)

select
    job_id,
    normalized_offer_id,
    raw_offer_id,
    source_system,
    source_offer_id,
    source_url,
    match_rule,
    match_score,
    source_rank = 1 as is_primary_source,
    current_timestamp as matched_at
from scored
