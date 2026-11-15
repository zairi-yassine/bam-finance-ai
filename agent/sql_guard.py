import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

# We only want the AI to query the Marts schema
ALLOWED_SCHEMA = "dbt_dev_marts"

_FORBIDDEN_NODES = (
    exp.Insert, exp.Update, exp.Delete, exp.Drop,
    exp.Create, exp.Alter, exp.Merge, exp.Command, exp.Into
)

def validate_sql(sql: str) -> tuple[bool, str]:
    """Returns (is_valid, error_message)."""
    if not sql or not sql.strip():
        return False, "Empty SQL."

    try:
        # Parse the SQL as T-SQL
        statements = [s for s in sqlglot.parse(sql, read="tsql") if s is not None]
    except ParseError as exc:
        return False, f"SQL parse error: {str(exc)[:200]}"
    except Exception as exc:
        return False, f"SQL could not be parsed: {str(exc)[:200]}"

    if len(statements) != 1:
        return False, "Exactly one SQL statement is allowed."

    stmt = statements[0]
    if not isinstance(stmt, (exp.Select, exp.Union)):
        return False, "Only SELECT queries are allowed."

    for node in stmt.walk():
        if isinstance(node, _FORBIDDEN_NODES):
            return False, f"Forbidden SQL operation: {type(node).__name__}."

    # Check that all tables belong to the allowed schema
    cte_names = {cte.alias_or_name.lower() for cte in stmt.find_all(exp.CTE)}
    for table in stmt.find_all(exp.Table):
        name = (table.name or "").lower()
        schema = (table.db or "").lower()
        if name in cte_names and not schema:
            continue
        if schema != ALLOWED_SCHEMA:
            return False, (
                f"Table '{table.sql(dialect='tsql')}' is not allowed. "
                f"Use schema-qualified tables from the '{ALLOWED_SCHEMA}' schema only."
            )

    return True, ""