"""End-to-end API tests against a real database."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.db


@pytest.fixture()
def client(database_url):
    from app.main import app
    with TestClient(app) as c:
        yield c


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_full_run_finds_injected_problems(client):
    run = client.post("/runs", json={}).json()
    assert run["status"] == "failed"
    # orders: schema, freshness, uniqueness  +  customers: email completeness
    assert run["failed_rules"] == 4

    failing = {(f["dataset"], f["rule_id"]) for f in client.get("/failures").json()}
    assert ("orders", "orders_fresh") in failing
    assert ("orders", "orders_unique_id") in failing
    assert ("orders", "orders_schema") in failing
    assert ("customers", "customers_email_complete") in failing
    assert not any(ds == "products" for ds, _ in failing)


def test_failures_filter_by_severity(client):
    client.post("/runs", json={})
    critical = client.get("/failures", params={"severity": "critical"}).json()
    assert critical and all(f["severity"] == "critical" for f in critical)


def test_datasets_health(client):
    client.post("/runs", json={})
    health = {d["dataset"]: d["health"] for d in client.get("/datasets").json()}
    assert health["orders"] == "red"
    assert health["products"] == "green"


def test_unknown_dataset_404(client):
    assert client.post("/runs", json={"dataset": "nope"}).status_code == 404
    assert client.get("/datasets/nope").status_code == 404


def test_add_rule_then_run(client, conn):
    body = {"dataset": "products", "rule": {"id": "products_max_rows", "type": "row_count", "max": 10, "severity": "low"}}
    assert client.post("/rules", json=body).status_code == 201
    assert client.post("/rules", json=body).status_code == 409  # duplicate

    client.post("/runs", json={"dataset": "products"})
    ds = client.get("/datasets/products").json()
    assert any(r["rule_id"] == "products_max_rows" and not r["passed"] for r in ds["latest_results"])
    assert ds["health"] == "amber"  # only a low-severity failure

    conn.execute("DELETE FROM dq.custom_rules WHERE rule->>'id' = 'products_max_rows'")
    conn.commit()


def test_add_invalid_rule_422(client):
    r = client.post("/rules", json={"dataset": "orders", "rule": {"id": "bad", "type": "completeness", "column": "x"}})
    assert r.status_code == 422


def test_annotate_result(client):
    client.post("/runs", json={"dataset": "orders"})
    failure = client.get("/failures", params={"dataset": "orders"}).json()[0]
    r = client.post(f"/results/{failure['result_id']}/annotations", json={"note": "ETL job paused", "author": "test"})
    assert r.status_code == 201
    ds = client.get("/datasets/orders").json()
    annotated = next(x for x in ds["latest_results"] if x["result_id"] == failure["result_id"])
    assert annotated["annotations"][0]["note"] == "ETL job paused"
    assert client.post("/results/999999/annotations", json={"note": "x"}).status_code == 404
