"""Create landing tables and load Parquet files into Azure SQL idempotently (per source_file)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from common.db import make_engine, wait_for_db

DDL = """
IF SCHEMA_ID('landing') IS NULL EXEC('CREATE SCHEMA landing');

IF OBJECT_ID('landing.report_pages', 'U') IS NULL
CREATE TABLE landing.report_pages (
    report_year   INT           NOT NULL,
    language      CHAR(2)       NOT NULL,
    source_file   NVARCHAR(255) NOT NULL,
    page_number   INT           NOT NULL,
    text_content  NVARCHAR(MAX) NULL,
    n_chars       INT           NULL,
    loaded_at     DATETIME2     NOT NULL DEFAULT SYSUTCDATETIME()
);

IF OBJECT_ID('landing.report_table_rows', 'U') IS NULL
CREATE TABLE landing.report_table_rows (
    table_title   NVARCHAR(500)   NULL,
    report_year   INT           NOT NULL,
    language      CHAR(2)       NOT NULL,
    source_file   NVARCHAR(255) NOT NULL,
    page_number   INT           NOT NULL,
    table_index   INT           NOT NULL,
    row_index     INT           NOT NULL,
    row_label     NVARCHAR(500) NULL,
    header_text   NVARCHAR(1000) NULL,
    n_cols        INT           NULL,
    col_1 NVARCHAR(200) NULL, col_2 NVARCHAR(200) NULL, col_3 NVARCHAR(200) NULL,
    col_4 NVARCHAR(200) NULL, col_5 NVARCHAR(200) NULL, col_6 NVARCHAR(200) NULL,
    loaded_at     DATETIME2     NOT NULL DEFAULT SYSUTCDATETIME()
);

IF OBJECT_ID('landing.exchange_rates', 'U') IS NULL
CREATE TABLE landing.exchange_rates (
    rate_date     DATE          NOT NULL,
    currency_code VARCHAR(10)   NOT NULL,
    unit          INT           NOT NULL,
    rate_mad      DECIMAL(18,6) NOT NULL,
    source_file   NVARCHAR(255) NOT NULL,
    loaded_at     DATETIME2     NOT NULL DEFAULT SYSUTCDATETIME()
);
"""

TARGETS = {
    "report_pages_": "landing.report_pages",
    "report_table_rows_": "landing.report_table_rows",
    "exchange_rates_": "landing.exchange_rates",
}


def create_landing_tables(engine: Engine) -> None:
    with engine.begin() as conn:
        for statement in [s for s in DDL.split(";\n\n") if s.strip()]:
            conn.exec_driver_sql(statement)


def _resolve_target(path: Path) -> str:
    for prefix, table in TARGETS.items():
        if path.name.startswith(prefix):
            return table
    raise ValueError(f"No target table for {path.name}")


def load_parquet(engine: Engine, path: Path, chunksize: int = 500) -> int:
    table = _resolve_target(path)
    schema, name = table.split(".")
    df = pd.read_parquet(path)
    if df.empty:
        print(f"  {path.name}: empty, skipped")
        return 0

    df = df.astype(object).where(pd.notnull(df), None)
    source_file = df["source_file"].iloc[0]

    with engine.begin() as conn:
        conn.execute(text(f"DELETE FROM {table} WHERE source_file = :sf"), {"sf": source_file})
        df.to_sql(name, conn, schema=schema, if_exists="append", index=False, chunksize=chunksize)
    return len(df)


def load_directory(silver_dir: Path) -> None:
    engine = make_engine()
    wait_for_db(engine)
    create_landing_tables(engine)
    for path in sorted(silver_dir.glob("*.parquet")):
        n = load_parquet(engine, path)
        print(f"  {path.name} -> {_resolve_target(path)}: {n} rows")


if __name__ == "__main__":
    load_directory(Path("data/silver"))