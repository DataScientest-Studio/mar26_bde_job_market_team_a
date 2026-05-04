{# Shared patterns for salary strings such as:
   "Mensuel de 1900.0 Euros a 2500.0 Euros sur 12.0 mois"
   "Salaire : 44K a 46K EUR"
#}

{% macro salary_text(salary_expression) -%}
lower(coalesce({{ salary_expression }}, ''))
{%- endmacro %}

{% macro salary_contains_k(salary_expression) -%}
{{ salary_text(salary_expression) }} ~ '(^|[^a-z0-9])k([^a-z0-9]|$)|\bk\s*(eur|euros)\b'
{%- endmacro %}

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

{% macro salary_month_count(salary_expression) -%}
{% set month_count_match = "regexp_match(" ~ salary_text(salary_expression) ~ ", 'sur\\s+([0-9]+(?:[.,][0-9]+)?)\\s+mois')" %}
case
    when {{ month_count_match }} is not null
        then replace(({{ month_count_match }})[1], ',', '.')::numeric
    else 12
end
{%- endmacro %}

{% macro salary_unit_multiplier(salary_expression) -%}
case when {{ salary_contains_k(salary_expression) }} then 1000 else 1 end
{%- endmacro %}

{% macro salary_range_match(salary_expression) -%}
{% set amount = "([0-9]+(?:\\s?[0-9]{3})*(?:[,.][0-9]+)?)" %}
{% set currency = "(?:k|eur|euros)" %}
regexp_match(
    {{ salary_text(salary_expression) }},
    '{{ amount }}\s*{{ currency }}?[^0-9,.]+{{ amount }}\s*{{ currency }}'
)
{%- endmacro %}

{% macro salary_single_match(salary_expression) -%}
{% set amount = "([0-9]+(?:\\s?[0-9]{3})*(?:[,.][0-9]+)?)" %}
{% set currency = "(?:k|eur|euros)" %}
regexp_match(
    {{ salary_text(salary_expression) }},
    '{{ amount }}\s*{{ currency }}'
)
{%- endmacro %}

{% macro parse_salary_min(range_match_expression, single_match_expression, unit_multiplier_expression) -%}
case
    when {{ range_match_expression }} is not null
        then nullif({{ parse_numeric_text(range_match_expression ~ '[1]') }} * {{ unit_multiplier_expression }}, 0)
    when {{ single_match_expression }} is not null
        then nullif({{ parse_numeric_text(single_match_expression ~ '[1]') }} * {{ unit_multiplier_expression }}, 0)
    else null
end
{%- endmacro %}

{% macro parse_salary_max(range_match_expression, single_match_expression, unit_multiplier_expression) -%}
case
    when {{ range_match_expression }} is not null
        then nullif({{ parse_numeric_text(range_match_expression ~ '[2]') }} * {{ unit_multiplier_expression }}, 0)
    when {{ single_match_expression }} is not null
        then nullif({{ parse_numeric_text(single_match_expression ~ '[1]') }} * {{ unit_multiplier_expression }}, 0)
    else null
end
{%- endmacro %}

{% macro annualize_salary(amount_expression, frequency_expression, month_count_expression, weekly_hours_expression) -%}
case
    when {{ frequency_expression }} = 'month' then {{ amount_expression }} * {{ month_count_expression }}
    when {{ frequency_expression }} = 'week' then {{ amount_expression }} * 52
    when {{ frequency_expression }} = 'hour' then {{ amount_expression }} * coalesce({{ weekly_hours_expression }}, 35) * 52
    when {{ frequency_expression }} = 'year' then {{ amount_expression }}
    else {{ amount_expression }}
end
{%- endmacro %}

{% macro salary_dimension_id(min_expression, max_expression, frequency_expression, month_count_expression, weekly_hours_expression, currency_expression) -%}
case
    when {{ min_expression }} is not null
        or {{ max_expression }} is not null
        or {{ frequency_expression }} is not null
        or {{ currency_expression }} is not null
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
