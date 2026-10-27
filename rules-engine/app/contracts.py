"""Load YAML contracts from disk and merge runtime rules from dq.custom_rules."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import TypeAdapter, ValidationError

from .models import Contract, Rule

_rule_adapter = TypeAdapter(Rule)


class ContractError(Exception):
    pass


def load_contract_file(path: Path) -> Contract:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ContractError(f"{path.name}: invalid YAML: {exc}") from exc
    if not isinstance(raw, dict):
        raise ContractError(f"{path.name}: top level must be a mapping")
    try:
        return Contract.model_validate(raw)
    except ValidationError as exc:
        raise ContractError(f"{path.name}: {exc}") from exc


def load_contracts(directory: Path) -> dict[str, Contract]:
    contracts: dict[str, Contract] = {}
    for path in sorted(directory.glob("*.y*ml")):
        contract = load_contract_file(path)
        if contract.dataset in contracts:
            raise ContractError(f"dataset {contract.dataset!r} defined twice")
        contracts[contract.dataset] = contract
    return contracts


def parse_rule(data: dict) -> Rule:
    try:
        return _rule_adapter.validate_python(data)
    except ValidationError as exc:
        raise ContractError(str(exc)) from exc


def merge_custom_rules(contracts: dict[str, Contract], rows: list[tuple[str, dict]]) -> dict[str, Contract]:
    """Return copies of the contracts with runtime rules appended (YAML rules win on id clash)."""
    merged = {name: c.model_copy(deep=True) for name, c in contracts.items()}
    for dataset, rule_data in rows:
        contract = merged.get(dataset)
        if contract is None:
            continue
        rule = parse_rule(rule_data)
        if all(r.id != rule.id for r in contract.rules):
            contract.rules.append(rule)
    return merged
