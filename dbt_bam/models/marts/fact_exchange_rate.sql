with staging as (
    select * from {{ ref('stg_exchange_rates') }}
)

select
    cast(format(rate_date, 'yyyyMMdd') as int) as date_key,
    currency_code,
    rate_mad
from staging