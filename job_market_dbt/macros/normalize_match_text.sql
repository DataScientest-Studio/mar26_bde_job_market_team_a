-- Normalisation agressive pour les comparaisons : minuscules, sans accents,
-- sans ponctuation, sans puces de liste
{% macro normalize_match_text(expression) -%}
nullif(
    trim(
        regexp_replace(
            regexp_replace(
                regexp_replace(
                    lower(
                        translate(
                            coalesce({{ expression }}, ''),
                            'àâäáãåçèéêëìíîïñòóôöõùúûüýÿ',
                            'aaaaaaceeeeiiiinooooouuuuyy'
                        )
                    ),
                    '[▪•◦‣⁃]',
                    ' ',
                    'g'
                ),
                '[^a-z0-9]+',
                ' ',
                'g'
            ),
            '\s+',
            ' ',
            'g'
        )
    ),
    ''
)
{%- endmacro %}

-- Nettoyage d'affichage : conserve les mots d'origine mais harmonise les espaces,
-- retire les puces et passe en majuscules
{% macro clean_display_label(expression) -%}
nullif(
    upper(
        trim(
            regexp_replace(
                regexp_replace(
                    coalesce({{ expression }}, ''),
                    '[▪•◦‣⁃]',
                    ' ',
                    'g'
                ),
                '\s+',
                ' ',
                'g'
            )
        )
    ),
    ''
)
{%- endmacro %}

-- Retire les suffixes H/F courants afin de mieux matcher les titres FT/WTTJ
{% macro normalize_title_match(expression) -%}
nullif(
    trim(
        regexp_replace(
            regexp_replace(
                regexp_replace(
                    coalesce({{ normalize_match_text(expression) }}, ''),
                    '\b(h f|f h|hf)\b',
                    '',
                    'g'
                ),
                '\b(h|f)\b',
                '',
                'g'
            ),
            '\s+',
            ' ',
            'g'
        )
    ),
    ''
)
{%- endmacro %}

-- Clé de rapprochement entreprise : retire formes juridiques et mots parasites
{% macro normalize_company_match(expression) -%}
nullif(
    trim(
        regexp_replace(
            regexp_replace(
                regexp_replace(
                    regexp_replace(
                        regexp_replace(
                            coalesce({{ normalize_match_text(expression) }}, ''),
                            '\b(sas|sasu|sarl|sa|eurl|cfa|groupe|group|france|holding|inc|ltd|llc|corp|corporation)\b',
                            '',
                            'g'
                        ),
                        '\b(emploi|interim|interimaire|interimaires|staffing|recrutement|recruitment|cabinet|consulting|conseil)\b',
                        '',
                        'g'
                    ),
                    '\b(the|le|la|les|de|du|des|d|and|et)\b',
                    '',
                    'g'
                ),
                '[0-9]+',
                '',
                'g'
            ),
            '\s+',
            ' ',
            'g'
        )
    ),
    ''
)
{%- endmacro %}

-- Libellé entreprise final : lisible pour dashboard/API, pas pour le matching
{% macro clean_company_label(expression) -%}
{% set company_label %}
regexp_replace(
    coalesce({{ expression }}, ''),
    '[.-]+',
    ' ',
    'g'
)
{% endset %}
{{ clean_display_label(company_label) }}
{%- endmacro %}

-- Libellé analytique générique : version uppercase/sans accents
{% macro clean_analytics_label(expression) -%}
upper({{ normalize_match_text(expression) }})
{%- endmacro %}

-- Harmonise les types de contrat avant publication et création des ids
{% macro clean_contract_type_label(expression) -%}
{% set normalized_expression = normalize_match_text(expression) %}
{% set tokenized_expression = "' ' || " ~ normalized_expression ~ " || ' '" %}
case
    when {{ normalized_expression }} is null then null
    when {{ tokenized_expression }} like '% alternance %'
        or {{ tokenized_expression }} like '% alternant %'
        or {{ tokenized_expression }} like '% apprentissage %'
        or {{ tokenized_expression }} like '% apprenti %'
        or {{ tokenized_expression }} like '% professionnalisation %'
        then 'ALTERNANCE'
    when {{ tokenized_expression }} like '% stage %'
        or {{ tokenized_expression }} like '% stagiaire %'
        then 'STAGE'
    when {{ tokenized_expression }} like '% interim %'
        or {{ tokenized_expression }} like '% interimaire %'
        or {{ tokenized_expression }} like '% mis %'
        then 'INTERIM'
    when {{ tokenized_expression }} like '% saisonnier %'
        or {{ tokenized_expression }} like '% sai %'
        then 'SAISONNIER'
    when {{ tokenized_expression }} like '% cdi %'
        then 'CDI'
    when {{ tokenized_expression }} like '% cdd %'
        or {{ normalized_expression }} like '%temporaire%'
        then 'CDD'
    when {{ tokenized_expression }} like '% freelance %'
        or {{ tokenized_expression }} like '% independant %'
        or {{ tokenized_expression }} like '% liberal %'
        or {{ tokenized_expression }} like '% lib %'
        or {{ tokenized_expression }} like '% cce %'
        then 'FREELANCE'
    when {{ tokenized_expression }} like '% franchise %'
        or {{ tokenized_expression }} like '% fra %'
        then 'FRANCHISE'
    when {{ tokenized_expression }} like '% benevole %'
        or {{ tokenized_expression }} like '% benevolat %'
        then 'BENEVOLE'
    else 'AUTRE'
end
{%- endmacro %}

-- Retire les préfixes code postal/département souvent présents dans les villes FT
{% macro clean_city_label(expression) -%}
nullif(
    trim(
        regexp_replace(
            regexp_replace(
                coalesce({{ expression }}, ''),
                '^\s*[0-9]{2,3}\s*-\s*',
                ''
            ),
            '^\s*[0-9]{5}\s+',
            ''
        )
    ),
    ''
)
{%- endmacro %}

-- Version affichée de la ville, basée sur la normalisation de matching
{% macro display_city_label(expression) -%}
upper({{ normalize_city_text(expression) }})
{%- endmacro %}

-- Utilise le code postal explicite, ou l'extrait du libellé de ville si besoin
{% macro extract_postal_code(postal_code_expression, city_expression) -%}
coalesce(
    nullif(trim({{ postal_code_expression }}), ''),
    case
        when coalesce({{ city_expression }}, '') ~ '^\s*[0-9]{5}\s+'
            then substring(coalesce({{ city_expression }}, '') from '^\s*([0-9]{5})')
        else null
    end
)
{%- endmacro %}

-- Ville normalisée pour regroupement analytique
{% macro normalize_city_text(expression) -%}
{{ normalize_match_text(clean_city_label(expression)) }}
{%- endmacro %}

-- Ville normalisée pour matching : retire remote, arrondissements et codes résiduels
{% macro normalize_city_match(expression) -%}
nullif(
    trim(
        regexp_replace(
            regexp_replace(
                regexp_replace(
                    regexp_replace(
                        regexp_replace(
                            regexp_replace(
                                coalesce({{ normalize_city_text(expression) }}, ''),
                                '(^[0-9]{5}\s+)|((\s+)?\(?[0-9]{2,5}\)?)$',
                                '',
                                'g'
                            ),
                            '\bteletravail\b|\bpartiel\b|\bremote\b|\bhybride\b',
                            '',
                            'g'
                        ),
                        '\b[0-9]{1,2}e\b',
                        '',
                        'g'
                    ),
                    '\b[0-9]{1,5}\b',
                    '',
                    'g'
                ),
                '\b(a|au|aux)\b',
                '',
                'g'
            ),
            '\s+',
            ' ',
            'g'
        )
    ),
    ''
)
{%- endmacro %}
