"""SQL guardrail. Every query the model writes passes through here BEFORE it touches the database.

Defence in depth: this is layer 1 (static checks). Layer 2 is a read-only DB role + read-only
transaction + statement timeout (see sql/create_readonly_role.sql and db.py).
"""
from __future__ import annotations

import sqlglot
from sqlglot import exp
from sqlglot.errors import SqlglotError

from . import config

_FORBIDDEN_NODE_NAMES = [
    "Insert", "Update", "Delete", "Drop", "Create", "Alter", "Command", "Merge",
    "TruncateTable", "Into", "Copy", "Set", "Use", "Pragma", "Grant", "Commit", "Rollback", "Transaction",
]
FORBIDDEN_NODES = tuple(getattr(exp, n) for n in _FORBIDDEN_NODE_NAMES if hasattr(exp, n))

FORBIDDEN_FUNCTIONS = {
    "pg_sleep", "pg_read_file", "pg_read_binary_file", "pg_ls_dir", "pg_stat_file", "lo_import", "lo_export",
    "dblink", "dblink_exec", "set_config", "current_setting", "load_extension", "readfile", "writefile",
    "sleep", "benchmark", "pg_terminate_backend", "pg_cancel_backend", "version", "current_user",
    "session_user", "current_database", "current_schema",
}


class GuardError(ValueError):
    """Raised when a query is rejected. The message is shown to the model so it can self-correct."""


def validate_and_prepare(
    sql: str,
    allowed_tables: set[str] | None = None,
    max_rows: int = config.MAX_ROWS,
    dialect: str | None = None,
) -> str:
    allowed = {t.lower() for t in (allowed_tables or config.ALLOWED_TABLES)}
    sql = (sql or "").strip().rstrip(";").strip()
    if not sql:
        raise GuardError("Empty query.")

    try:
        statements = [s for s in sqlglot.parse(sql, read=dialect) if s is not None]
    except SqlglotError as e:
        raise GuardError(f"Could not parse SQL: {str(e)[:200]}") from e

    if len(statements) != 1:
        raise GuardError("Exactly one statement is allowed.")
    tree = statements[0]

    if not isinstance(tree, (exp.Select, exp.Union)):
        raise GuardError("Only SELECT queries are allowed.")

    for node in tree.find_all(*FORBIDDEN_NODES):
        raise GuardError(f"Forbidden operation: {type(node).__name__.upper()}.")

    for func in tree.find_all(exp.Func):
        name = (func.name if isinstance(func, exp.Anonymous) else func.sql_name()).lower()
        if name in FORBIDDEN_FUNCTIONS:
            raise GuardError(f"Forbidden function: {name}.")

    cte_names = {cte.alias.lower() for cte in tree.find_all(exp.CTE)}
    for table in tree.find_all(exp.Table):
        name = table.name.lower()
        if name in cte_names:
            continue
        if table.db or name not in allowed:
            raise GuardError(f"Table '{table.sql()}' is not allowed. Allowed tables: {', '.join(sorted(allowed))}.")

    limit = tree.args.get("limit")
    if limit is None:
        tree = tree.limit(max_rows)
    else:
        try:
            n = int(limit.expression.name)
        except (ValueError, AttributeError):
            n = None
        if n is None or n > max_rows:
            tree = tree.limit(max_rows)

    return tree.sql(dialect=dialect)
