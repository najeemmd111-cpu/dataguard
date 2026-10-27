"""Database fixtures.

If DATABASE_URL is set (CI service container, or your docker-compose Postgres),
tests use it. Otherwise they start a throwaway Postgres with Testcontainers.
If neither is possible, DB tests are skipped.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import psycopg
import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def database_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
    container = None
    if not url:
        try:
            from testcontainers.postgres import PostgresContainer

            container = PostgresContainer("pgvector/pgvector:pg16", driver=None)
            container.start()
            url = container.get_connection_url()
        except Exception as exc:  # noqa: BLE001
            pytest.skip(f"no database available: {exc}")

    # Fresh schema + deterministic seed every session.
    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute("DROP SCHEMA IF EXISTS dq CASCADE")
        conn.execute("DROP TABLE IF EXISTS orders, customers, products CASCADE")
        conn.execute((ROOT / "db" / "init.sql").read_text())
    subprocess.run([sys.executable, str(ROOT / "db" / "seed.py")], check=True,
                   env={**os.environ, "DATABASE_URL": url, "RESEED": "1"})

    os.environ["DATABASE_URL"] = url
    os.environ["CONTRACTS_DIR"] = str(ROOT / "contracts")
    yield url
    if container:
        container.stop()


@pytest.fixture()
def conn(database_url):
    with psycopg.connect(database_url) as c:
        yield c
        c.rollback()
