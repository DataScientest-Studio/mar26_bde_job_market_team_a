{% macro postal_code_to_region(postal_code_expr) %}
    {% set postal_code_regions = var('postal_code_regions') %}
    case
        when {{ postal_code_expr }} is null then null
        {% for region, prefixes in postal_code_regions.items() %}
        when (
            {% for prefix in prefixes %}
                left({{ postal_code_expr }}, {{ prefix | length }}) = '{{ prefix }}'
                {% if not loop.last %}or{% endif %}
            {% endfor %}
        ) then '{{ region }}'
        {% endfor %}
        else null
    end
{% endmacro %}
