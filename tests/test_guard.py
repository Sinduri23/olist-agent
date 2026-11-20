import pytest

from agent.guard import GuardError, validate_and_prepare

ALLOWED = {"olist_orders_dataset", "olist_customers_dataset"}


def prep(sql, dialect="postgres", max_rows=100):
    return validate_and_prepare(sql, ALLOWED, max_rows, dialect)


@pytest.mark.parametrize("sql", [
    "SELECT COUNT(*) FROM olist_orders_dataset",
    "select order_status, count(*) from olist_orders_dataset group by 1;",
    "WITH d AS (SELECT * FROM olist_orders_dataset) SELECT COUNT(*) FROM d",
    "SELECT o.order_id FROM olist_orders_dataset o JOIN olist_customers_dataset c ON o.customer_id = c.customer_id",
    "SELECT order_id FROM olist_orders_dataset UNION SELECT customer_id FROM olist_customers_dataset",
    "SELECT * FROM olist_orders_dataset WHERE order_id IN (SELECT order_id FROM olist_orders_dataset)",
])
def test_allows_legit_selects(sql):
    assert prep(sql).upper().startswith(("SELECT", "WITH"))


@pytest.mark.parametrize("sql", [
    "DROP TABLE olist_orders_dataset",
    "DELETE FROM olist_orders_dataset",
    "UPDATE olist_orders_dataset SET order_status = 'x'",
    "INSERT INTO olist_orders_dataset VALUES ('a','b','c')",
    "SELECT 1; DELETE FROM olist_orders_dataset",
    "SELECT 1; SELECT 2",
    "CREATE TABLE t AS SELECT * FROM olist_orders_dataset",
    "SELECT * INTO newt FROM olist_orders_dataset",
    "ALTER TABLE olist_orders_dataset ADD COLUMN x int",
    "TRUNCATE olist_orders_dataset",
    "COPY olist_orders_dataset TO '/tmp/x.csv'",
    "GRANT ALL ON olist_orders_dataset TO public",
    "SELECT * FROM pg_user",
    "SELECT * FROM information_schema.tables",
    "SELECT * FROM pg_catalog.pg_tables",
    "SELECT * FROM secret_table",
    "SELECT pg_sleep(100)",
    "SELECT pg_read_file('/etc/passwd')",
    "SELECT current_setting('server_version')",
])
def test_blocks_attacks(sql):
    with pytest.raises(GuardError):
        prep(sql)


def test_empty_and_garbage():
    for bad in ["", "   ", "this is not sql at all ((("]:
        with pytest.raises(GuardError):
            prep(bad)


def test_limit_added_and_capped():
    assert "LIMIT 100" in prep("SELECT * FROM olist_orders_dataset")
    assert "LIMIT 100" in prep("SELECT * FROM olist_orders_dataset LIMIT 5000")
    assert "LIMIT 5" in prep("SELECT * FROM olist_orders_dataset LIMIT 5")


def test_sqlite_dialect_works():
    assert "LIMIT" in prep("SELECT COUNT(*) FROM olist_orders_dataset", dialect="sqlite")
