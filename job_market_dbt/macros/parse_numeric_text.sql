-- Convertit un nombre texte français/anglais en numeric
{% macro parse_numeric_text(expression) -%}
nullif(
    regexp_replace(
        replace(replace({{ expression }}, ' ', ''), ',', '.'),
        '[^0-9.]',
        '',
        'g'
    ),
    ''
)::numeric
{%- endmacro %}
