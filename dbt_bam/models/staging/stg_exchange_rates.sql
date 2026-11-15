with source as (
    select * from {{ source('landing', 'exchange_rates') }}
),

cleaned as (
    select
        cast(rate_date as date) as rate_date,
        upper(trim(currency_code)) as currency_code,
        cast(rate_mad as decimal(18, 6)) as rate_mad
    from source
    where rate_mad is not null
)

select * from cleaned