-- Regroupe les offres FT/WTTJ qui semblent représenter le même poste
-- La source primaire reste France Travail quand une paire est détectée
with base as (
    -- Petite normalisation de synonymes courts pour le fuzzy matching du titre
    select
        *,
        nullif(regexp_replace(coalesce(title_match_norm, ''), '\balt\b', 'alternance', 'g'), '') as title_fuzzy_norm
    from {{ ref('int_job_offers_normalized') }}
),

candidate_pairs as (
    -- Cherche uniquement des paires inter-source avec entreprise, ville et dates compatibles
    select
        a.normalized_offer_id as offer_a,
        b.normalized_offer_id as offer_b,
        md5(a.normalized_offer_id || '|' || b.normalized_offer_id) as candidate_key,
        case
            when a.title_match_norm = b.title_match_norm
                then 'fingerprint_exact_inter_source'
            else 'title_fuzzy_inter_source'
        end as match_rule,
        case
            when a.title_match_norm = b.title_match_norm
                then 1.00::numeric
            else round(0.70 + least(title_score.token_containment, 1.00) * 0.25, 2)
        end as match_score
    from base as a
    inner join base as b
        on a.source_system <> b.source_system
        and a.normalized_offer_id < b.normalized_offer_id
        and a.company_match_norm = b.company_match_norm
        and a.city_match_norm = b.city_match_norm
        and a.match_reference_date is not null
        and b.match_reference_date is not null
        and abs(a.match_reference_date - b.match_reference_date) <= 30
    cross join lateral (
        -- Score fuzzy simple : part de tokens communs entre les deux titres
        with a_tokens as (
            select distinct token
            from unnest(regexp_split_to_array(a.title_fuzzy_norm, '\s+')) as token
            where length(token) > 1
        ),

        b_tokens as (
            select distinct token
            from unnest(regexp_split_to_array(b.title_fuzzy_norm, '\s+')) as token
            where length(token) > 1
        ),

        common_tokens as (
            select token from a_tokens
            intersect
            select token from b_tokens
        )

        select
            count(*) as common_token_count,
            count(*)::numeric / nullif(
                least(
                    (select count(*) from a_tokens),
                    (select count(*) from b_tokens)
                ),
                0
            ) as token_containment
        from common_tokens
    ) as title_score
    where a.company_match_norm is not null
        and a.city_match_norm is not null
        and a.title_fuzzy_norm is not null
        and b.title_fuzzy_norm is not null
        and (
            a.title_match_norm = b.title_match_norm
            or (
                a.title_match_norm <> b.title_match_norm
                and title_score.common_token_count >= 2
                and title_score.token_containment >= 0.66
            )
        )
),

mutual_best_pairs as (
    -- Évite les doublons en gardant seulement les paires où chaque offre est le meilleur choix de l'autre
    select
        offer_a,
        offer_b,
        candidate_key,
        match_rule,
        match_score
    from (
        select
            *,
            row_number() over (partition by offer_a order by match_score desc, candidate_key) as rank_for_a,
            row_number() over (partition by offer_b order by match_score desc, candidate_key) as rank_for_b
        from candidate_pairs
    ) as ranked_pairs
    where rank_for_a = 1
        and rank_for_b = 1
),

matches as (
    -- Repasse de la paire vers une ligne par offre source matchée
    select
        matched_offer.normalized_offer_id,
        mutual_best_pairs.candidate_key,
        mutual_best_pairs.match_rule,
        mutual_best_pairs.match_score
    from mutual_best_pairs
    cross join lateral (
        values (offer_a), (offer_b)
    ) as matched_offer(normalized_offer_id)
),

scored as (
    -- Attribue le job_id canonique et marque la ligne source primaire
    select
        md5(coalesce(matches.candidate_key, base.normalized_offer_id)) as job_id,
        base.normalized_offer_id,
        base.raw_offer_id,
        base.source_system,
        base.source_offer_id,
        base.source_url,
        coalesce(matches.match_rule, 'single_source') as match_rule,
        coalesce(matches.match_score, 0.50) as match_score,
        row_number() over (
            partition by coalesce(matches.candidate_key, base.normalized_offer_id)
            order by
                case when base.source_system = 'france_travail' then 1 else 2 end,
                base.published_at_norm desc nulls last,
                base.ingested_at desc,
                base.raw_offer_id desc
        ) = 1 as is_primary_source
    from base
    left join matches
        on base.normalized_offer_id = matches.normalized_offer_id
)

select
    md5(job_id || '|' || normalized_offer_id) as job_source_id,
    job_id,
    normalized_offer_id,
    raw_offer_id,
    source_system,
    source_offer_id,
    source_url,
    match_rule,
    match_score,
    is_primary_source,
    current_timestamp as matched_at
from scored
