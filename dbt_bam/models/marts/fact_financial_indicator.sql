with staging as (
    select * from {{ ref('stg_report_table_rows') }}
),

unpivoted as (
    select
        report_year, language, source_file, page_number, table_title, row_label, header_text,
        1 as column_index, val_1 as indicator_value from staging where val_1 is not null
    union all
    select report_year, language, source_file, page_number, table_title, row_label, header_text,
    2 as column_index, val_2 from staging where val_2 is not null
    union all
    select report_year, language, source_file, page_number, table_title, row_label, header_text,
    3 as column_index, val_3 from staging where val_3 is not null
    union all
    select report_year, language, source_file, page_number, table_title, row_label, header_text,
    4 as column_index, val_4 from staging where val_4 is not null
    union all
    select report_year, language, source_file, page_number, table_title, row_label, header_text,
    5 as column_index, val_5 from staging where val_5 is not null
    union all
    select report_year, language, source_file, page_number, table_title, row_label, header_text,
    6 as column_index, val_6 from staging where val_6 is not null
)

select
    report_year as publication_year,
    language,
    table_title,
    row_label as indicator_name,
    header_text,      -- <--- THE SECRET WEAPON
    column_index,     -- <--- 1, 2, 3...
    indicator_value
from unpivoted