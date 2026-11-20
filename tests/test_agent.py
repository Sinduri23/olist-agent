from agent.agent import DataAgent
from tests.conftest import ScriptedClient, final, tool_use


def test_successful_query_flow(db):
    client = ScriptedClient([
        tool_use("get_schema", {}, "t1"),
        tool_use("run_sql", {"sql": "SELECT COUNT(*) FROM olist_orders_dataset WHERE order_status='delivered'"}, "t2"),
        final("There are 2 delivered orders."),
    ])
    res = DataAgent(db, client=client).run("How many delivered orders?")
    assert res.answer == "There are 2 delivered orders."
    assert res.successful_queries[0]["rows"] == [[2]]
    assert res.blocked_count == 0 and res.input_tokens == 150
    schema_result = client.calls[1]["messages"][-1]["content"][0]["content"]
    assert "olist_orders_dataset(" in schema_result and "secret_table" not in schema_result


def test_destructive_query_is_blocked_and_db_unchanged(db):
    before = db.table_counts()
    client = ScriptedClient([
        tool_use("run_sql", {"sql": "DELETE FROM olist_orders_dataset"}),
        final("I can't modify data."),
    ])
    res = DataAgent(db, client=client).run("Delete all orders")
    assert res.blocked_count == 1 and res.successful_queries == []
    assert db.table_counts() == before
    assert client.calls[1]["messages"][-1]["content"][0]["is_error"] is True


def test_sql_error_is_fed_back_and_counted(db):
    client = ScriptedClient([
        tool_use("run_sql", {"sql": "SELECT nonexistent_col FROM olist_orders_dataset"}),
        tool_use("run_sql", {"sql": "SELECT COUNT(*) FROM olist_orders_dataset"}, "t2"),
        final("3 orders."),
    ])
    res = DataAgent(db, client=client).run("count orders")
    assert res.sql_error_count == 1 and len(res.successful_queries) == 1


def test_step_limit(db):
    client = ScriptedClient([tool_use("get_schema", {}, f"t{i}") for i in range(10)])
    res = DataAgent(db, client=client, max_steps=3).run("loop forever")
    assert res.hit_step_limit and "step limit" in res.answer


def test_row_cap_enforced(db):
    client = ScriptedClient([tool_use("run_sql", {"sql": "SELECT * FROM olist_orders_dataset"}), final("ok")])
    res = DataAgent(db, client=client, max_rows=2).run("show all")
    assert len(res.successful_queries[0]["rows"]) == 2
