from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, text

from agent.db import Database


@pytest.fixture
def db(tmp_path):
    url = f"sqlite:///{tmp_path/'olist.db'}"
    eng = create_engine(url)
    with eng.begin() as c:
        c.execute(text("CREATE TABLE olist_orders_dataset (order_id TEXT, customer_id TEXT, order_status TEXT)"))
        c.execute(text("CREATE TABLE olist_customers_dataset (customer_id TEXT, customer_state TEXT)"))
        c.execute(text("CREATE TABLE secret_table (id INTEGER, token TEXT)"))
        c.execute(text("INSERT INTO olist_orders_dataset VALUES ('o1','c1','delivered'),('o2','c2','delivered'),('o3','c1','canceled')"))
        c.execute(text("INSERT INTO olist_customers_dataset VALUES ('c1','SP'),('c2','RJ')"))
        c.execute(text("INSERT INTO secret_table VALUES (1,'s3cr3t')"))
    return Database(url)


def tool_use(name, tool_input, id="t1"):
    return SimpleNamespace(
        stop_reason="tool_use",
        content=[SimpleNamespace(type="tool_use", id=id, name=name, input=tool_input)],
        usage=SimpleNamespace(input_tokens=50, output_tokens=10),
    )


def final(text_):
    return SimpleNamespace(
        stop_reason="end_turn",
        content=[SimpleNamespace(type="text", text=text_)],
        usage=SimpleNamespace(input_tokens=50, output_tokens=10),
    )


class ScriptedClient:
    """Returns pre-scripted model responses in order; records what the agent sent."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.messages = self

    def create(self, **kwargs):
        self.calls.append({**kwargs, "messages": list(kwargs["messages"])})  # snapshot: agent mutates the list
        return self.responses.pop(0)
