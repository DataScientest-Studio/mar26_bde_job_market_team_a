-- Contexte texte commun pour déduire temps plein/partiel
{% macro text_context(contract_expression, working_time_expression, schedule_expression) -%}
lower(
    coalesce({{ contract_expression }}, '')
    || ' '
    || coalesce({{ working_time_expression }}, '')
    || ' '
    || coalesce({{ schedule_expression }}, '')
)
{%- endmacro %}

-- Extrait un nombre d'heures hebdomadaire depuis un libellé libre
{% macro weekly_hours_from_text(expression) -%}
case
    when lower(coalesce({{ expression }}, '')) ~ '([0-9]+(?:[.,][0-9]+)?)\s*h'
        then replace(
            (
                regexp_match(
                    lower(coalesce({{ expression }}, '')),
                    '([0-9]+(?:[.,][0-9]+)?)\s*h'
                )
            )[1],
            ',',
            '.'
        )::numeric
    else null
end
{%- endmacro %}

-- Détermine full_time à partir du contrat, des horaires et du nombre d'heures
{% macro full_time_from_context(contract_expression, working_time_expression, schedule_expression) -%}
case
    when {{ text_context(contract_expression, working_time_expression, schedule_expression) }} like '%temps plein%'
        or {{ text_context(contract_expression, working_time_expression, schedule_expression) }} like '%full time%'
        then true
    when {{ text_context(contract_expression, working_time_expression, schedule_expression) }} like '%temps partiel%'
        or {{ text_context(contract_expression, working_time_expression, schedule_expression) }} like '%part time%'
        then false
    when {{ weekly_hours_from_text("coalesce(" ~ working_time_expression ~ ", '') || ' ' || coalesce(" ~ schedule_expression ~ ", '')") }} is not null
        then {{ weekly_hours_from_text("coalesce(" ~ working_time_expression ~ ", '') || ' ' || coalesce(" ~ schedule_expression ~ ", '')") }} >= 35
    else null
end
{%- endmacro %}

-- Extrait le premier nombre d'années d'expérience trouvé dans le libellé
{% macro experience_years_from_text(expression) -%}
{% set experience_match = "regexp_match(lower(coalesce(" ~ expression ~ ", '')), '([0-9]+(?:[.,][0-9]+)?)')" %}
case
    when {{ experience_match }} is not null
        then replace(({{ experience_match }})[1], ',', '.')::numeric
    else null
end
{%- endmacro %}

-- Vrai si au moins une borne salaire passe les garde-fous par fréquence
{% macro has_guarded_salary(min_expression, max_expression, frequency_expression) -%}
(
    {{ guarded_salary_amount(min_expression, frequency_expression) }} is not null
    or {{ guarded_salary_amount(max_expression, frequency_expression) }} is not null
)
{%- endmacro %}

-- Borne basse d'effectif entreprise à partir de tranches textuelles
{% macro company_size_min(expression) -%}
case
    when lower(coalesce({{ expression }}, '')) ~ '([0-9]+)\s*[^0-9]+\s*([0-9]+)'
        then (regexp_match(lower({{ expression }}), '([0-9]+)\s*[^0-9]+\s*([0-9]+)'))[1]::integer
    when lower(coalesce({{ expression }}, '')) ~ 'moins de\s*([0-9]+)'
        then 0
    when lower(coalesce({{ expression }}, '')) ~ 'plus de\s*([0-9]+)'
        then (regexp_match(lower({{ expression }}), 'plus de\s*([0-9]+)'))[1]::integer
    else null
end
{%- endmacro %}

-- Borne haute d'effectif entreprise à partir de tranches textuelles
{% macro company_size_max(expression) -%}
case
    when lower(coalesce({{ expression }}, '')) ~ '([0-9]+)\s*[^0-9]+\s*([0-9]+)'
        then (regexp_match(lower({{ expression }}), '([0-9]+)\s*[^0-9]+\s*([0-9]+)'))[2]::integer
    when lower(coalesce({{ expression }}, '')) ~ 'moins de\s*([0-9]+)'
        then greatest((regexp_match(lower({{ expression }}), 'moins de\s*([0-9]+)'))[1]::integer - 1, 0)
    else null
end
{%- endmacro %}
