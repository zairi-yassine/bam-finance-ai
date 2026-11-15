with source as (
    select * from {{ source('landing', 'report_pages') }}
)

select
    report_year,
    language,
    source_file,
    page_number,
    text_content,
    n_chars
from source
-- Filter out pages that have almost no text (like blank pages or images)
where n_chars > 50