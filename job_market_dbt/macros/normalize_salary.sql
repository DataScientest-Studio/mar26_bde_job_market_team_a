-- Parse les salaires texte FT/WTTJ
-- Exemples couverts : "Mensuel de 1900 Euros a 2500 Euros", "44K a 46K EUR"

-- Texte salaire standardisé pour les regex
{% macro salary_text(salary_expression) -%}
lower(replace(replace(coalesce({{ salary_expression }}, ''), '€', ' eur'), 'â‚¬', ' eur'))
{%- endmacro %}

-- Détecte les salaires en milliers : 44K, 44 k EUR, etc
{% macro salary_contains_k(salary_expression) -%}
{{ salary_text(salary_expression) }} ~ '[0-9]\s*k([^a-z0-9]|$)|\bk\s*(eur|euros)\b'
{%- endmacro %}

-- Fréquence explicite, avec fallback annuel pour les montants en K
{% macro normalize_salary_frequency(salary_expression) -%}
case
    when {{ salary_text(salary_expression) }} like '%annuel%'
        or {{ salary_text(salary_expression) }} like '%annuelle%'
        or {{ salary_text(salary_expression) }} like '% year%'
        or {{ salary_text(salary_expression) }} like '%/year%'
        then 'year'
    when {{ salary_text(salary_expression) }} like '%mensuel%'
        or {{ salary_text(salary_expression) }} like '%mois%'
        or {{ salary_text(salary_expression) }} like '%month%'
        then 'month'
    when {{ salary_text(salary_expression) }} like '%horaire%'
        or {{ salary_text(salary_expression) }} like '%heure%'
        or {{ salary_text(salary_expression) }} like '%/h%'
        then 'hour'
    when {{ salary_text(salary_expression) }} like '%semaine%'
        or {{ salary_text(salary_expression) }} like '%week%'
        then 'week'
    when {{ salary_contains_k(salary_expression) }}
        then 'year'
    else null
end
{%- endmacro %}

-- Nombre de mois payés, 12 par défaut
{% macro salary_month_count(salary_expression) -%}
{% set month_count_match = "regexp_match(" ~ salary_text(salary_expression) ~ ", 'sur\\s+([0-9]+(?:[.,][0-9]+)?)\\s+mois')" %}
case
    when {{ month_count_match }} is not null
        then replace(({{ month_count_match }})[1], ',', '.')::numeric
    else 12
end
{%- endmacro %}

-- Multiplie par 1000 quand le montant est exprimé en K
{% macro salary_unit_multiplier(salary_expression) -%}
case when {{ salary_contains_k(salary_expression) }} then 1000 else 1 end
{%- endmacro %}

-- Capture une fourchette de salaire
{% macro salary_range_match(salary_expression) -%}
{% set amount = "([0-9]+(?:\\s?[0-9]{3})*(?:[,.][0-9]+)?)" %}
{% set currency = "(?:k|eur|euros)" %}
regexp_match(
    {{ salary_text(salary_expression) }},
    '{{ amount }}\s*{{ currency }}?[^0-9,.]+{{ amount }}\s*{{ currency }}'
)
{%- endmacro %}

-- Capture un salaire unique
{% macro salary_single_match(salary_expression) -%}
{% set amount = "([0-9]+(?:\\s?[0-9]{3})*(?:[,.][0-9]+)?)" %}
{% set currency = "(?:k|eur|euros)" %}
regexp_match(
    {{ salary_text(salary_expression) }},
    '{{ amount }}\s*{{ currency }}'
)
{%- endmacro %}

-- Borne basse parsée depuis une fourchette ou un montant unique
{% macro parse_salary_min(range_match_expression, single_match_expression, unit_multiplier_expression) -%}
case
    when {{ range_match_expression }} is not null
        then nullif({{ parse_numeric_text(range_match_expression ~ '[1]') }} * {{ unit_multiplier_expression }}, 0)
    when {{ single_match_expression }} is not null
        then nullif({{ parse_numeric_text(single_match_expression ~ '[1]') }} * {{ unit_multiplier_expression }}, 0)
    else null
end
{%- endmacro %}

-- Borne haute parsée depuis une fourchette ou un montant unique
{% macro parse_salary_max(range_match_expression, single_match_expression, unit_multiplier_expression) -%}
case
    when {{ range_match_expression }} is not null
        then nullif({{ parse_numeric_text(range_match_expression ~ '[2]') }} * {{ unit_multiplier_expression }}, 0)
    when {{ single_match_expression }} is not null
        then nullif({{ parse_numeric_text(single_match_expression ~ '[1]') }} * {{ unit_multiplier_expression }}, 0)
    else null
end
{%- endmacro %}

-- Garde-fous simples pour rejeter les montants manifestement mal classés
{% macro guarded_salary_amount(amount_expression, frequency_expression) -%}
case
    when {{ amount_expression }} is null then null
    when {{ frequency_expression }} = 'hour'
        and {{ amount_expression }} between 5 and 250
        then {{ amount_expression }}
    when {{ frequency_expression }} = 'week'
        and {{ amount_expression }} between 150 and 10000
        then {{ amount_expression }}
    when {{ frequency_expression }} = 'month'
        and {{ amount_expression }} between 500 and 30000
        then {{ amount_expression }}
    when {{ frequency_expression }} = 'year'
        and {{ amount_expression }} between 8000 and 500000
        then {{ amount_expression }}
    else null
end
{%- endmacro %}

-- La frequence est obligatoire pour exposer un salaire dans les marts
{% macro salary_dimension_id(min_expression, max_expression, frequency_expression, month_count_expression, weekly_hours_expression, currency_expression) -%}
case
    when {{ frequency_expression }} is not null
        and (
            {{ min_expression }} is not null
            or {{ max_expression }} is not null
        )
        then md5(
            coalesce({{ min_expression }}::text, '')
            || '|'
            || coalesce({{ max_expression }}::text, '')
            || '|'
            || coalesce({{ frequency_expression }}, '')
            || '|'
            || coalesce({{ month_count_expression }}::text, '')
            || '|'
            || coalesce({{ weekly_hours_expression }}::text, '')
            || '|'
            || coalesce({{ currency_expression }}, '')
        )
    else null
end
{%- endmacro %}
