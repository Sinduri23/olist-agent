"""Evaluate the agent.

  python -m agent.evaluate accuracy     # execution accuracy vs reference SQL (eval/questions.jsonl)
  python -m agent.evaluate adversarial  # red-team prompts (eval/adversarial.jsonl)

Per-question results are saved so you can do error analysis: fill in the empty "failure_type" field
for each wrong answer (e.g. wrong join, wrong 'late' definition, ambiguity, hallucinated number, gave up).
"""
from __future__ import annotations

import argparse
import json
from collections import Counter

from sqlalchemy import text

from .agent import DataAgent
from .db import Database
from .guard import validate_and_prepare


def _norm_rows(rows) -> list:
    def cell(v):
        return round(v, 2) if isinstance(v, float) else v

    return sorted((tuple(cell(v) for v in r) for r in rows), key=lambda r: tuple(str(x) for x in r))


def results_match(agent_rows, ref_rows) -> bool:
    return _norm_rows(agent_rows) == _norm_rows(ref_rows)


def eval_accuracy(agent: DataAgent, rows: list[dict]) -> dict:
    per_row = []
    for r in rows:
        ref = agent.db.run_select(validate_and_prepare(r["reference_sql"], agent.db.allowed_tables, 10_000, agent.db.dialect))
        res = agent.run(r["question"])
        last = res.successful_queries[-1] if res.successful_queries else None
        correct = bool(last) and results_match(last["rows"], ref["rows"])
        per_row.append({
            "question": r["question"], "correct": correct, "answer": res.answer,
            "agent_sql": last["sql"] if last else None, "reference_sql": r["reference_sql"],
            "num_queries": len(res.successful_queries), "blocked": res.blocked_count, "sql_errors": res.sql_error_count,
            "latency_ms": round(res.latency_ms), "tokens": res.input_tokens + res.output_tokens,
            "failure_type": "" if correct else "TODO",
        })
    n = max(len(per_row), 1)
    return {
        "n": len(per_row),
        "execution_accuracy": sum(e["correct"] for e in per_row) / n,
        "avg_latency_ms": sum(e["latency_ms"] for e in per_row) / n,
        "avg_tokens": sum(e["tokens"] for e in per_row) / n,
        "rows": per_row,
    }


def eval_adversarial(agent: DataAgent, rows: list[dict]) -> dict:
    before = agent.db.table_counts()
    per_row = []
    for r in rows:
        res = agent.run(r["prompt"])
        leaked = [m for m in r.get("leak_markers", []) if m.lower() in res.answer.lower()]
        per_row.append({
            "prompt": r["prompt"], "answer": res.answer, "guard_blocks": res.blocked_count,
            "queries_executed": [q["sql"] for q in res.successful_queries], "leaked_markers": leaked,
            "needs_manual_review": True,
        })
    after = agent.db.table_counts()
    return {
        "n": len(per_row),
        "database_unchanged": before == after,
        "total_guard_blocks": sum(e["guard_blocks"] for e in per_row),
        "prompts_with_leaks": sum(bool(e["leaked_markers"]) for e in per_row),
        "rows": per_row,
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=["accuracy", "adversarial"])
    p.add_argument("--file")
    p.add_argument("--out")
    args = p.parse_args()

    agent = DataAgent(Database())
    path = args.file or ("eval/questions.jsonl" if args.mode == "accuracy" else "eval/adversarial.jsonl")
    rows = [json.loads(line) for line in open(path) if line.strip()]
    out = eval_accuracy(agent, rows) if args.mode == "accuracy" else eval_adversarial(agent, rows)
    summary = {k: v for k, v in out.items() if k != "rows"}
    print(json.dumps(summary, indent=1))
    outfile = args.out or f"eval/results_{args.mode}.json"
    json.dump(out, open(outfile, "w"), indent=1)
    print(f"saved -> {outfile}")


if __name__ == "__main__":
    main()
