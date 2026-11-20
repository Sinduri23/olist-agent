# Olist Data Agent: a guarded, read-only text-to-SQL agent

A tool-calling agent (Claude) that answers natural-language questions about the
[Olist Brazilian e-commerce dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)
(~100k orders) by writing and running SQL on PostgreSQL, with layered guardrails, an execution-accuracy
benchmark and a red-team suite.

## Architecture

```mermaid
flowchart TD
  U[User question] --> A[Agent loop: Claude + tools, max N steps]
  A -->|get_schema| S[Allowed tables and columns only]
  A -->|run_sql| G{SQL guard: sqlglot AST checks}
  G -->|blocked: error returned to model| A
  G -->|valid SELECT + LIMIT| D[(PostgreSQL: read-only role, read-only txn, timeout)]
  D -->|rows| A
  A --> R[Answer + SQL + trace]
```

### Guardrails (defence in depth)
1. **Static SQL guard** (`agent/guard.py`): parses SQL into an AST; exactly one statement; top level must be `SELECT`; rejects
   DML/DDL/`COPY`/`INTO`/`SET`; table allow-list (blocks `pg_catalog`, `information_schema`, other schemas); function deny-list
   (`pg_sleep`, `pg_read_file`, `current_setting`, ...); forces a `LIMIT` cap.
2. **Database layer**: dedicated read-only role (`sql/create_readonly_role.sql`), `SET TRANSACTION READ ONLY`, statement timeout.
3. **Agent layer**: system prompt refuses writes, credential/system-info requests and off-topic questions; tool results are treated as untrusted data; step limit; blocked queries are fed back so the model self-corrects but never bypasses.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env     # set ANTHROPIC_API_KEY, DATABASE_URL (export them or use direnv)

# 1. Download the Olist CSVs from Kaggle into ./olist_csvs
# 2. Create DB `olist` in PostgreSQL, then load with an ADMIN url:
python -m agent.load_data --csv-dir olist_csvs --url postgresql+psycopg2://postgres:PASSWORD@localhost/olist
# 3. Create the read-only role used by the agent:
psql -d olist -f sql/create_readonly_role.sql

python -m agent.cli
```

## Evaluation

```bash
python -m agent.evaluate accuracy      # execution accuracy vs reference SQL
python -m agent.evaluate adversarial   # red-team prompts; checks DB unchanged + leak markers
pytest -q                              # 30+ unit tests incl. a parametrised SQL-attack suite (no API key needed)
```

- **Execution accuracy**: the result set of the agent's last successful query is compared (order-insensitive, floats rounded) with the reference SQL's result set.
- **Adversarial**: `database_unchanged` is verified by comparing table row counts before/after, and `leak_markers` are searched for in answers. Read `eval/results_adversarial.json` by hand too.
- Extend `eval/questions.jsonl` to 30+ questions (include multi-join, date logic and ambiguous wording) and **verify every reference SQL yourself**.

### Results

> TODO: fill from YOUR runs. Do not copy numbers you did not measure.

| Metric | Value |
|---|---|
| Questions (n) | |
| Execution accuracy | |
| Avg latency / tokens per question | |
| Adversarial prompts (n) / database unchanged / leaks | |
| SQL attack payloads blocked by guard (unit tests) | |

### Error analysis

> TODO: fill `failure_type` for every wrong row in `eval/results_accuracy.json`, then summarise
> (e.g. wrong 'late' definition, wrong join grain / double-counting, hallucinated number, ambiguity) and what you changed.

## Limitations
- Text-to-SQL is brittle on ambiguous metrics ("late", "seller handling time"); the agent states assumptions but can still be wrong.
- The guard is static: it cannot judge whether a valid query is *expensive*; the timeout and row cap handle that.
- Public, anonymised dataset only; do not point this at sensitive production data without a security review.
