"""Contract parsing tests. No database needed."""

from datetime import timedelta
from pathlib import Path

import pytest

from app.contracts import ContractError, load_contract_file, load_contracts, merge_custom_rules, parse_rule
from app.models import parse_duration

CONTRACTS_DIR = Path(__file__).resolve().parents[2] / "contracts"


def test_shipped_contracts_are_valid():
    contracts = load_contracts(CONTRACTS_DIR)
    assert {"orders", "customers", "products"} <= set(contracts)
    assert contracts["orders"].table_parts == ("public", "orders")


@pytest.mark.parametrize("text,expected", [
    ("30m", timedelta(minutes=30)), ("24h", timedelta(hours=24)),
    ("7d", timedelta(days=7)), ("45s", timedelta(seconds=45)),
])
def test_parse_duration(text, expected):
    assert parse_duration(text) == expected


@pytest.mark.parametrize("bad", ["24", "1w", "h24", ""])
def test_parse_duration_rejects_bad_input(bad):
    with pytest.raises(ValueError):
        parse_duration(bad)


def _write(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "c.yaml"
    path.write_text(body)
    return path


def test_unknown_rule_type_fails_loudly(tmp_path):
    path = _write(tmp_path, """
dataset: x
table: x
owner: me
rules:
  - { id: r1, type: magic }
""")
    with pytest.raises(ContractError):
        load_contract_file(path)


def test_sql_injection_in_column_is_rejected(tmp_path):
    path = _write(tmp_path, """
dataset: x
table: x
owner: me
rules:
  - { id: r1, type: completeness, column: "id; DROP TABLE x", min_ratio: 0.9 }
""")
    with pytest.raises(ContractError):
        load_contract_file(path)


def test_duplicate_rule_ids_rejected(tmp_path):
    path = _write(tmp_path, """
dataset: x
table: x
owner: me
rules:
  - { id: r1, type: row_count, min: 1 }
  - { id: r1, type: row_count, min: 2 }
""")
    with pytest.raises(ContractError, match="duplicate"):
        load_contract_file(path)


def test_unknown_field_rejected(tmp_path):
    path = _write(tmp_path, "dataset: x\ntable: x\nowner: me\ncolour: blue\n")
    with pytest.raises(ContractError):
        load_contract_file(path)


def test_row_count_needs_bounds():
    with pytest.raises(ContractError):
        parse_rule({"id": "r", "type": "row_count"})


def test_merge_custom_rules_appends_and_yaml_wins():
    contracts = load_contracts(CONTRACTS_DIR)
    merged = merge_custom_rules(contracts, [
        ("orders", {"id": "orders_new", "type": "row_count", "max": 1_000_000}),
        ("orders", {"id": "orders_fresh", "type": "row_count", "min": 1}),  # clashes with YAML -> ignored
        ("ghost", {"id": "x", "type": "row_count", "min": 1}),             # unknown dataset -> ignored
    ])
    ids = [r.id for r in merged["orders"].rules]
    assert "orders_new" in ids
    assert ids.count("orders_fresh") == 1
    assert next(r for r in merged["orders"].rules if r.id == "orders_fresh").type == "freshness"
    assert len(contracts["orders"].rules) == len(merged["orders"].rules) - 1  # original untouched
