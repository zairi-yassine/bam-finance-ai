with source as (
    select * from {{ source('landing', 'report_table_rows') }}
),

cleaned as (
    select
        report_year,
        language,
        source_file,
        page_number,
        table_title,
        row_label,
        header_text,

        -- Clean the text: remove spaces, replace comma with dot, then cast to decimal
        try_cast(replace(replace(col_1, ' ', ''), ',', '.') as decimal(18, 4)) as val_1,
        try_cast(replace(replace(col_2, ' ', ''), ',', '.') as decimal(18, 4)) as val_2,
        try_cast(replace(replace(col_3, ' ', ''), ',', '.') as decimal(18, 4)) as val_3,
        try_cast(replace(replace(col_4, ' ', ''), ',', '.') as decimal(18, 4)) as val_4,
        try_cast(replace(replace(col_5, ' ', ''), ',', '.') as decimal(18, 4)) as val_5,
        try_cast(replace(replace(col_6, ' ', ''), ',', '.') as decimal(18, 4)) as val_6

    from source
    where row_label is not null
      and len(trim(row_label)) > 0
),

filtered as (
    select * from cleaned
    -- THE MAGIC FILTER:
    -- Keep only rows where AT LEAST one of the value columns is not null.
    -- This removes the Table of Contents and paragraphs of text instantly.
    where val_1 is not null
       or val_2 is not null
       or val_3 is not null
       or val_4 is not null
       or val_5 is not null
       or val_6 is not null
)

select * from filtered