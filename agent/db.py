from __future__ import annotations

import datetime
import decimal

from sqlalchemy import create_engine, inspect, text

from . import config

_DIALECTS = {"postgresql": "postgres", "sqlite": "sqlite", "mysql": "mysql"}


def _jsonable(v):
    if v is None or isinstance(v, (int, float, bool)):
        return v
    if isinstance(v, decimal.Decimal):
        return float(v)
    if isinstance(v, (datetime.datetime, datetime.date)):
        return v.isoformat()
    return str(v)[:200]


class Database:
    def __init__(self, url: str = config.DATABASE_URL, allowed_tables: set[str] | None = None):
        self.engine = create_engine(url)
        self.allowed_tables = {t.lower() for t in (allowed_tables or config.ALLOWED_TABLES)}
        self.dialect = _DIALECTS.get(self.engine.dialect.name)

    def schema_description(self) -> str:
        insp = inspect(self.engine)
        lines = []
        for table in sorted(insp.get_table_names()):
            if table.lower() in self.allowed_tables:
                cols = ", ".join(f"{c['name']} {str(c['type']).lower()}" for c in insp.get_columns(table))
                lines.append(f"{table}({cols})")
        return "\n".join(lines)

    def run_select(self, sql: str) -> dict:
        """Execute an ALREADY-VALIDATED query inside a read-only transaction with a timeout."""
        with self.engine.connect() as conn:
            if self.engine.dialect.name == "postgresql":
                conn.execute(text("SET TRANSACTION READ ONLY"))
                conn.execute(text(f"SET LOCAL statement_timeout = {int(config.STATEMENT_TIMEOUT_MS)}"))
            result = conn.execute(text(sql))
            columns = list(result.keys())
            rows = [[_jsonable(v) for v in row] for row in result.fetchall()]
            conn.rollback()
        return {"columns": columns, "rows": rows, "row_count": len(rows), "sql": sql}

    def table_counts(self) -> dict[str, int]:
        """Row counts per allowed table (used to verify nothing was modified)."""
        insp = inspect(self.engine)
        out = {}
        with self.engine.connect() as conn:
            for t in sorted(insp.get_table_names()):
                if t.lower() in self.allowed_tables:
                    out[t] = conn.execute(text(f'SELECT COUNT(*) FROM "{t}"')).scalar()
        return out
