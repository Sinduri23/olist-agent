"""Interactive CLI: python -m agent.cli"""
from __future__ import annotations

from .agent import DataAgent
from .db import Database


def main() -> None:
    agent = DataAgent(Database())
    print("Olist data agent (read-only). Ctrl-C to quit.")
    while True:
        try:
            q = input("\n> ").strip()
        except (KeyboardInterrupt, EOFError):
            break
        if not q:
            continue
        r = agent.run(q)
        for s in r.successful_queries:
            print(f"\n[SQL] {s['sql']}")
        print(f"\n{r.answer}\n(blocked={r.blocked_count}, sql_errors={r.sql_error_count}, {r.latency_ms:.0f} ms)")


if __name__ == "__main__":
    main()
