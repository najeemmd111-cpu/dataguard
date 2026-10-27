"""Pydantic models for data contracts. A malformed YAML file fails loudly here."""

from __future__ import annotations

import re
from datetime import timedelta
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
Severity = Literal["low", "medium", "high", "critical"]
ColumnType = Literal["integer", "numeric", "text", "timestamp", "boolean", "date"]


def _check_ident(value: str) -> str:
    if not IDENT.match(value):
        raise ValueError(f"invalid identifier: {value!r}")
    return value


def parse_duration(text: str) -> timedelta:
    """'30m', '24h', '7d' -> timedelta."""
    match = re.fullmatch(r"\s*(\d+)\s*([smhd])\s*", text)
    if not match:
        raise ValueError(f"invalid duration {text!r}; use e.g. 30m, 24h, 7d")
    amount, unit = int(match.group(1)), match.group(2)
    return {"s": timedelta(seconds=amount), "m": timedelta(minutes=amount),
            "h": timedelta(hours=amount), "d": timedelta(days=amount)}[unit]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ColumnSpec(Strict):
    name: str
    type: ColumnType
    required: bool = True

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        return _check_ident(v)


class BaseRule(Strict):
    id: str
    severity: Severity = "medium"
    description: str | None = None

    @field_validator("id")
    @classmethod
    def _id(cls, v: str) -> str:
        if not re.fullmatch(r"[a-z0-9_\-]+", v):
            raise ValueError("rule id must be lowercase letters, digits, '_' or '-'")
        return v


class SchemaRule(BaseRule):
    type: Literal["schema"]


class FreshnessRule(BaseRule):
    type: Literal["freshness"]
    column: str
    max_age: str

    @field_validator("column")
    @classmethod
    def _column(cls, v: str) -> str:
        return _check_ident(v)

    @field_validator("max_age")
    @classmethod
    def _age(cls, v: str) -> str:
        parse_duration(v)
        return v

    @property
    def max_age_delta(self) -> timedelta:
        return parse_duration(self.max_age)


class CompletenessRule(BaseRule):
    type: Literal["completeness"]
    column: str
    min_ratio: float = Field(ge=0, le=1)

    @field_validator("column")
    @classmethod
    def _column(cls, v: str) -> str:
        return _check_ident(v)


class UniquenessRule(BaseRule):
    type: Literal["uniqueness"]
    columns: list[str] = Field(min_length=1)

    @field_validator("columns")
    @classmethod
    def _cols(cls, v: list[str]) -> list[str]:
        return [_check_ident(c) for c in v]


class RowCountRule(BaseRule):
    type: Literal["row_count"]
    min: int | None = Field(default=None, ge=0)
    max: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _bounds(self) -> RowCountRule:
        if self.min is None and self.max is None:
            raise ValueError("row_count needs min, max or both")
        return self


Rule = Annotated[
    SchemaRule | FreshnessRule | CompletenessRule | UniquenessRule | RowCountRule,
    Field(discriminator="type"),
]


class Contract(Strict):
    dataset: str
    table: str
    owner: str
    description: str | None = None
    schedule: str | None = None  # cron expression
    schema_: list[ColumnSpec] = Field(default_factory=list, alias="schema")
    rules: list[Rule] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    @field_validator("table")
    @classmethod
    def _table(cls, v: str) -> str:
        parts = v.split(".")
        if len(parts) > 2:
            raise ValueError("table must be 'name' or 'schema.name'")
        for p in parts:
            _check_ident(p)
        return v

    @model_validator(mode="after")
    def _unique_rule_ids(self) -> Contract:
        ids = [r.id for r in self.rules]
        dupes = {i for i in ids if ids.count(i) > 1}
        if dupes:
            raise ValueError(f"duplicate rule ids: {sorted(dupes)}")
        if any(r.type == "schema" for r in self.rules) and not self.schema_:
            raise ValueError("a schema rule needs a 'schema' section")
        return self

    @property
    def table_parts(self) -> tuple[str, str]:
        parts = self.table.split(".")
        return (parts[0], parts[1]) if len(parts) == 2 else ("public", parts[0])
