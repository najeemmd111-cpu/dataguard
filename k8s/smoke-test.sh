#!/usr/bin/env bash
# Check the deployed stack end to end: engine health, a full check run, and the dashboard proxy.
set -euo pipefail
ENGINE="${ENGINE:-http://localhost:8800}"
DASHBOARD="${DASHBOARD:-http://localhost:8880}"

fail() { echo "FAIL: $*"; exit 1; }

for i in $(seq 1 30); do curl -sf "$ENGINE/health" >/dev/null && break; sleep 2; done
curl -sf "$ENGINE/health" | grep -q '"ok"' || fail "engine /health"
echo "ok   engine is healthy"

run=$(curl -sf -X POST "$ENGINE/runs" -H 'content-type: application/json' -d '{}') || fail "POST /runs"
echo "$run" | grep -q '"total_rules":11' || fail "expected 11 rules, got: $run"
echo "$run" | grep -q '"failed_rules":4' || fail "expected the 4 seeded failures, got: $run"
echo "ok   a full run checks 11 rules and finds the 4 seeded failures"

curl -sf "$DASHBOARD/" | grep -q "<title>DataGuard</title>" || fail "dashboard index.html"
curl -sf "$DASHBOARD/datasets/orders" | grep -q '<div id="app">' || fail "dashboard single-page routing"
echo "ok   dashboard serves the app, including deep links"

datasets=$(curl -sf "$DASHBOARD/api/datasets") || fail "dashboard /api proxy"
for d in orders customers products; do echo "$datasets" | grep -q "\"dataset\":\"$d\"" || fail "dataset $d missing via proxy"; done
echo "ok   dashboard /api proxies to the engine (3 datasets)"

echo "Smoke test passed."
