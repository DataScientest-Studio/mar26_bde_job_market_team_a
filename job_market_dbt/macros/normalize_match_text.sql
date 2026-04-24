{% macro normalize_match_text(expression) -%}
nullif(
    trim(
        regexp_replace(
            regexp_replace(
                lower(
                    translate(
                        coalesce({{ expression }}, ''),
                        'àâäáãåçèéêëìíîïñòóôöõùúûüýÿ',
                        'aaaaaaceeeeiiiinooooouuuuyy'
                    )
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

{% macro normalize_company_match(expression) -%}
nullif(
    trim(
        regexp_replace(
            regexp_replace(
                regexp_replace(
                    regexp_replace(
                        coalesce({{ normalize_match_text(expression) }}, ''),
                        '\b(sas|sasu|sarl|sa|eurl|cfa|groupe|group|france)\b',
                        '',
                        'g'
                    ),
                    '\b(emploi|interim|interimaire|interimaires|staffing|recrutement)\b',
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

{% macro normalize_city_text(expression) -%}
{{ normalize_match_text(clean_city_label(expression)) }}
{%- endmacro %}

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
