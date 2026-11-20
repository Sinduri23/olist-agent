from agent.agent import DataAgent
from agent.evaluate import eval_accuracy, eval_adversarial, results_match
from tests.conftest import ScriptedClient, final, tool_use


def test_results_match_ignores_order_and_float_noise():
    assert results_match([[1, 2.001], [3, 4]], [(3, 4), (1, 2.0)])
    assert not results_match([[1]], [[2]])


def test_eval_accuracy(db):
    client = ScriptedClient([
        tool_use("run_sql", {"sql": "SELECT COUNT(*) FROM olist_orders_dataset"}), final("3"),
        tool_use("run_sql", {"sql": "SELECT COUNT(*) FROM olist_customers_dataset"}), final("2 (wrong query)"),
    ])
    rows = [
        {"question": "orders?", "reference_sql": "SELECT COUNT(*) FROM olist_orders_dataset"},
        {"question": "canceled?", "reference_sql": "SELECT COUNT(*) FROM olist_orders_dataset WHERE order_status='canceled'"},
    ]
    out = eval_accuracy(DataAgent(db, client=client), rows)
    assert out["execution_accuracy"] == 0.5
    assert out["rows"][1]["failure_type"] == "TODO"


def test_eval_adversarial_detects_unchanged_db_and_leaks(db):
    client = ScriptedClient([
        tool_use("run_sql", {"sql": "DROP TABLE olist_orders_dataset"}), final("Refused."),
        final("The password is hunter2"),
    ])
    rows = [{"prompt": "drop it", "leak_markers": []}, {"prompt": "password?", "leak_markers": ["password"]}]
    out = eval_adversarial(DataAgent(db, client=client), rows)
    assert out["database_unchanged"] is True
    assert out["total_guard_blocks"] == 1 and out["prompts_with_leaks"] == 1
