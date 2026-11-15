with source as (
    select distinct currency_code from {{ ref('stg_exchange_rates') }}
)

select
    currency_code,
    case
        when currency_code = 'USD' then 'US Dollar'
        when currency_code = 'EUR' then 'Euro'
        when currency_code = 'GBP' then 'British Pound'
        when currency_code = 'SAR' then 'Saudi Riyal'
        when currency_code = 'AED' then 'UAE Dirham'
        when currency_code = 'CAD' then 'Canadian Dollar'
        when currency_code = 'JPY' then 'Japanese Yen'
        else currency_code
    end as currency_name
from source