{% macro set_statement_timeout() -%}
    {% set timeout = env_var('DBT_STATEMENT_TIMEOUT', '300s') %}
    set statement_timeout to '{{ timeout }}'
{%- endmacro %}
