from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row

from .config import get_settings


@contextmanager
def connect(autocommit: bool = False) -> Iterator[psycopg.Connection]:
    with psycopg.connect(get_settings().database_url, autocommit=autocommit) as conn:
        yield conn


def fetch_all(query: str, params: tuple | dict = ()) -> list[dict]:
    with connect() as conn, conn.cursor(row_factory=dict_row) as cur:
        return cur.execute(query, params).fetchall()


def fetch_one(query: str, params: tuple | dict = ()) -> dict | None:
    with connect() as conn, conn.cursor(row_factory=dict_row) as cur:
        return cur.execute(query, params).fetchone()
