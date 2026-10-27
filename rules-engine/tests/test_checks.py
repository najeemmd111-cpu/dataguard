"""Each checker against the seeded data (bad) and against a clean table (good)."""

from __future__ import annotations

import pytest

from app.checks import check_completeness, check_freshness, check_row_count, check_schema, check_uniqueness
from app.contracts import load_contracts, parse_rule
from app.models import Contract

pytestmark = pytest.mark.db


@pytest.fixture()
def contracts(database_url):
    import os
    from pathlib import Path
    return load_contracts(Path(os.environ["CONTRACTS_DIR"]))


def rule(contract: Contract, rule_id: str):
    return next(r for r in contract.rules if r.id == rule_id)


# --- the injected problems are found ---------------------------------------

def test_schema_detects_text_amount(conn, contracts):
    c = contracts["orders"]
    res = check_schema(conn, c, rule(c, "orders_schema"), 5)
    assert not res.passed
    assert "amount" in res.message and "text" in res.message


def test_freshness_detects_stale_orders(conn, contracts):
    c = contracts["orders"]
    res = check_freshness(conn, c, rule(c, "orders_fresh"), 5)
    assert not res.passed
    assert float(res.measured_value.rstrip("h")) >= 71


def test_completeness_detects_null_emails(conn, contracts):
    c = contracts["customers"]
    res = check_completeness(conn, c, rule(c, "customers_email_complete"), 5)
    assert not res.passed
    assert 0 < len(res.sample_rows) <= 5
    assert all(r["email"] is None for r in res.sample_rows)


def test_uniqueness_detects_duplicate_orders(conn, contracts):
    c = contracts["orders"]
    res = check_uniqueness(conn, c, rule(c, "orders_unique_id"), 5)
    assert not res.passed
    assert res.measured_value.startswith("25 ")
    assert res.sample_rows[0]["occurrences"] == 2


# --- healthy data passes ----------------------------------------------------

def test_completeness_passes_when_ratio_met(conn, contracts):
    c = contracts["orders"]  # ~0.5% NULL customer_id, threshold 0.99
    assert check_completeness(conn, c, rule(c, "orders_no_null_customer"), 5).passed


def test_products_contract_all_green(conn, contracts):
    c = contracts["products"]
    assert check_schema(conn, c, rule(c, "products_schema"), 5).passed
    assert check_freshness(conn, c, rule(c, "products_fresh"), 5).passed
    assert check_uniqueness(conn, c, rule(c, "products_unique_id"), 5).passed


def test_row_count_bounds(conn, contracts):
    c = contracts["orders"]
    assert check_row_count(conn, c, rule(c, "orders_min_rows"), 5).passed
    too_small = parse_rule({"id": "x", "type": "row_count", "max": 10})
    assert not check_row_count(conn, c, too_small, 5).passed
