"""Shared SQLAlchemy engine factory for Azure SQL Database (with serverless-resume retry)."""
from __future__ import annotations

import os
import time
import urllib.parse

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DBAPIError, OperationalError

load_dotenv()

ODBC_DRIVER = os.getenv("ODBC_DRIVER", "ODBC Driver 18 for SQL Server")


def _odbc_connection_string(user: str, password: str) -> str:
    server = os.environ["SQL_SERVER"]
    database = os.environ["SQL_DATABASE"]
    # Braces around the password allow special characters (except '}').
    return (
        f"Driver={{{ODBC_DRIVER}}};"
        f"Server=tcp:{server},1433;"
        f"Database={database};"
        f"Uid={user};"
        f"Pwd={{{password}}};"
        "Encrypt=yes;TrustServerCertificate=no;Connection Timeout=60;"
    )


def make_engine(readonly: bool = False) -> Engine:
    """Create an engine. readonly=True uses the least-privilege agent account."""
    if readonly:
        user, password = os.environ["SQL_RO_USER"], os.environ["SQL_RO_PASSWORD"]
    else:
        user, password = os.environ["SQL_ADMIN_USER"], os.environ["SQL_ADMIN_PASSWORD"]

    url = "mssql+pyodbc:///?odbc_connect=" + urllib.parse.quote_plus(
        _odbc_connection_string(user, password)
    )
    return create_engine(
        url,
        fast_executemany=True,
        pool_pre_ping=True,
        pool_recycle=1800,
        future=True,
    )


def wait_for_db(engine: Engine, tries: int = 6, delay: float = 15.0) -> None:
    """Block until the (possibly auto-paused) serverless database answers."""
    last_exc: Exception | None = None
    for attempt in range(1, tries + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return
        except (OperationalError, DBAPIError) as exc:
            last_exc = exc
            print(f"[db] not ready (attempt {attempt}/{tries}), retrying in {delay:.0f}s ...")
            time.sleep(delay)
    raise RuntimeError(f"Database unreachable after {tries} attempts: {last_exc}")