with numbers as (
    select top (10958) -- 30 years of days
        row_number() over (order by (select null)) - 1 as n
    from sys.all_objects a
    cross join sys.all_objects b
),

days as (
    select dateadd(day, n, cast('1996-01-01' as date)) as full_date
    from numbers
)

select
    cast(format(full_date, 'yyyyMMdd') as int) as date_key,
    full_date,
    year(full_date) as year_num,
    month(full_date) as month_num,
    datename(month, full_date) as month_name,
    day(full_date) as day_of_month
from days