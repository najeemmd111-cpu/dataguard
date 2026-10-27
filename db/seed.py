"""Seed the sample dataset with realistic rows AND deliberate data-quality problems.

Injected problems (so the rules engine has something to find):
  1. ~4% of customers have a NULL email                 -> completeness rule fails
  2. 25 order_id values appear twice                    -> uniqueness rule fails
  3. orders.updated_at stopped moving 3 days ago        -> freshness rule fails
  4. orders.amount is stored as TEXT, not NUMERIC        -> schema rule fails
  5. ~0.5% of orders have a NULL customer_id             -> completeness (passes at 0.99)

Usage:
    DATABASE_URL=postgresql://dataguard:dataguard@localhost:5432/dataguard python seed.py
"""

from __future__ import annotations

import os
import random
from datetime import datetime, timedelta, timezone

import psycopg

N_CUSTOMERS = 1_000
N_PRODUCTS = 50
N_ORDERS = 10_000
N_DUPLICATE_ORDERS = 25

COUNTRIES = ["FR", "DE", "ES", "IT", "BE", "NL", "PT", "GB"]
CATEGORIES = ["books", "electronics", "garden", "kitchen", "sports", "toys"]
STATUSES = ["pending", "paid", "shipped", "delivered", "cancelled"]


def main() -> None:
    url = os.environ.get("DATABASE_URL", "postgresql://dataguard:dataguard@localhost:5432/dataguard")
    rng = random.Random(42)  # deterministic, so test expectations stay stable
    now = datetime.now(timezone.utc)
    stale_cutoff = now - timedelta(days=3)  # the "ETL stopped" moment

    with psycopg.connect(url) as conn, conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM orders")
        if cur.fetchone()[0] > 0 and os.environ.get("RESEED") != "1":
            print("Data already present, skipping (set RESEED=1 to force).")
            return
        cur.execute("TRUNCATE orders, customers, products RESTART IDENTITY")

        customers = []
        for cid in range(1, N_CUSTOMERS + 1):
            email = None if rng.random() < 0.04 else f"customer{cid}@example.com"
            created = now - timedelta(days=rng.randint(30, 900))
            customers.append((cid, email, rng.choice(COUNTRIES), created, created))
        with cur.copy("COPY customers (customer_id, email, country, created_at, updated_at) FROM STDIN") as cp:
            for row in customers:
                cp.write_row(row)

        products = []
        for pid in range(1, N_PRODUCTS + 1):
            price = round(rng.uniform(3, 400), 2)
            products.append((pid, f"Product {pid}", rng.choice(CATEGORIES), price, now))
        with cur.copy("COPY products (product_id, name, category, price, updated_at) FROM STDIN") as cp:
            for row in products:
                cp.write_row(row)

        prices = {p[0]: p[3] for p in products}
        orders = []
        for oid in range(1, N_ORDERS + 1):
            pid = rng.randint(1, N_PRODUCTS)
            qty = rng.randint(1, 5)
            customer_id = None if rng.random() < 0.005 else rng.randint(1, N_CUSTOMERS)
            created = stale_cutoff - timedelta(minutes=rng.randint(0, 60 * 24 * 60))
            updated = min(created + timedelta(hours=rng.randint(0, 72)), stale_cutoff)
            orders.append((oid, customer_id, pid, qty, f"{prices[pid] * qty:.2f}",
                           rng.choice(STATUSES), created, updated))

        for row in rng.sample(orders, N_DUPLICATE_ORDERS):
            orders.append(row)  # same order_id twice

        with cur.copy(
            "COPY orders (order_id, customer_id, product_id, quantity, amount, status, created_at, updated_at) FROM STDIN"
        ) as cp:
            for row in orders:
                cp.write_row(row)

        conn.commit()
        print(f"Seeded {N_CUSTOMERS} customers, {N_PRODUCTS} products, {len(orders)} orders.")


if __name__ == "__main__":
    main()
