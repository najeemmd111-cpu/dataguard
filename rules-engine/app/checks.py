"""One checker per rule type. Each runs SQL and returns a CheckResult.

All identifiers come from validated contracts and are still quoted with
psycopg.sql.Identifier, so no user text is ever pasted into SQL.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

from .models import (
    CompletenessRule,
    Contract,
    FreshnessRule,
    RowCountRule,
    SchemaRule,
    UniquenessRule,
)

# contract type -> Postgres data_type values that satisfy it
TYPE_MAP: dict[str, set[str]] = {
    "integer": {"integer", "bigint", "smallint"},
    "numeric": {"numeric", "double precision", "real", "integer", "bigint", "smallint"},
    "text": {"text", "character varying", "character"},
    "timestamp": {"timestamp with time zone", "timestamp without time zone"},
    "boolean": {"boolean"},
    "date": {"date"},
}


@dataclass
class CheckResult:
    passed: bool
    measured_value: str
    threshold: str
    message: str
    sample_rows: list[dict] = field(default_factory=list)


def _table(contract: Contract) -> sql.Composed:
    schema, name = contract.table_parts
    return sql.SQL("{}.{}").format(sql.Identifier(schema), sql.Identifier(name))


def _jsonable(rows: list[dict]) -> list[dict]:
    return json.loads(json.dumps(rows, default=str))


def check_schema(conn: psycopg.Connection, contract: Contract, rule: SchemaRule, sample_size: int) -> CheckResult:
    schema, name = contract.table_parts
    rows = conn.execute(
        "SELECT column_name, data_type FROM information_schema.columns "
        "WHERE table_schema = %s AND table_name = %s",
        (schema, name),
    ).fetchall()
    actual = {r[0]: r[1] for r in rows}
    if not actual:
        return CheckResult(False, "table missing", contract.table, f"table {contract.table} does not exist")

    problems: list[dict] = []
    for col in contract.schema_:
        if col.name not in actual:
            if col.required:
                problems.append({"column": col.name, "problem": "missing", "expected": col.type})
        elif actual[col.name] not in TYPE_MAP[col.type]:
            problems.append({"column": col.name, "problem": "wrong type",
                             "expected": col.type, "actual": actual[col.name]})
    msg = "schema matches contract" if not problems else "; ".join(
        f"{p['column']}: {p['problem']}" + (f" ({p.get('actual')} != {p['expected']})" if "actual" in p else "")
        for p in problems
    )
    return CheckResult(not problems, f"{len(problems)} mismatches", "0 mismatches", msg, problems[:sample_size])


def check_freshness(conn: psycopg.Connection, contract: Contract, rule: FreshnessRule, sample_size: int) -> CheckResult:
    query = sql.SQL("SELECT max({col}) FROM {tbl}").format(col=sql.Identifier(rule.column), tbl=_table(contract))
    latest = conn.execute(query).fetchone()[0]
    if latest is None:
        return CheckResult(False, "no rows", rule.max_age, "table is empty, cannot measure freshness")
    if latest.tzinfo is None:
        latest = latest.replace(tzinfo=UTC)
    age = datetime.now(UTC) - latest
    hours = age.total_seconds() / 3600
    passed = age <= rule.max_age_delta
    return CheckResult(
        passed,
        f"{hours:.1f}h",
        rule.max_age,
        f"latest {rule.column} is {latest.isoformat()} ({hours:.1f}h old)",
        [{"latest_value": latest.isoformat(), "age_hours": round(hours, 2)}],
    )


def check_completeness(conn: psycopg.Connection, contract: Contract, rule: CompletenessRule, sample_size: int) -> CheckResult:
    col = sql.Identifier(rule.column)
    tbl = _table(contract)
    total, non_null = conn.execute(
        sql.SQL("SELECT count(*), count({col}) FROM {tbl}").format(col=col, tbl=tbl)
    ).fetchone()
    ratio = (non_null / total) if total else 0.0
    passed = total > 0 and ratio >= rule.min_ratio
    samples: list[dict] = []
    if not passed and total:
        cur = conn.cursor(row_factory=dict_row)
        samples = cur.execute(
            sql.SQL("SELECT * FROM {tbl} WHERE {col} IS NULL LIMIT %s").format(tbl=tbl, col=col), (sample_size,)
        ).fetchall()
    return CheckResult(
        passed,
        f"{ratio:.4f}",
        f">= {rule.min_ratio}",
        f"{total - non_null} of {total} rows have NULL {rule.column}",
        _jsonable(samples),
    )


def check_uniqueness(conn: psycopg.Connection, contract: Contract, rule: UniquenessRule, sample_size: int) -> CheckResult:
    cols = sql.SQL(", ").join(sql.Identifier(c) for c in rule.columns)
    tbl = _table(contract)
    dup_groups = conn.execute(
        sql.SQL("SELECT count(*) FROM (SELECT 1 FROM {tbl} GROUP BY {cols} HAVING count(*) > 1) d").format(tbl=tbl, cols=cols)
    ).fetchone()[0]
    samples: list[dict] = []
    if dup_groups:
        cur = conn.cursor(row_factory=dict_row)
        samples = cur.execute(
            sql.SQL("SELECT {cols}, count(*) AS occurrences FROM {tbl} GROUP BY {cols} "
                    "HAVING count(*) > 1 ORDER BY count(*) DESC LIMIT %s").format(cols=cols, tbl=tbl),
            (sample_size,),
        ).fetchall()
    return CheckResult(
        dup_groups == 0,
        f"{dup_groups} duplicate keys",
        "0 duplicate keys",
        f"{dup_groups} values of ({', '.join(rule.columns)}) appear more than once",
        _jsonable(samples),
    )


def check_row_count(conn: psycopg.Connection, contract: Contract, rule: RowCountRule, sample_size: int) -> CheckResult:
    count = conn.execute(sql.SQL("SELECT count(*) FROM {tbl}").format(tbl=_table(contract))).fetchone()[0]
    ok = (rule.min is None or count >= rule.min) and (rule.max is None or count <= rule.max)
    bounds = f"[{rule.min if rule.min is not None else '-'}, {rule.max if rule.max is not None else '-'}]"
    return CheckResult(ok, str(count), bounds, f"{count} rows (expected {bounds})")


CHECKERS = {
    "schema": check_schema,
    "freshness": check_freshness,
    "completeness": check_completeness,
    "uniqueness": check_uniqueness,
    "row_count": check_row_count,
}
