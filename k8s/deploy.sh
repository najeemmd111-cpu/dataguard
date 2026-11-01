#!/usr/bin/env bash
# Deploy DataGuard (database, sample data, rules engine, dashboard) to a local kind cluster.
# Usage: k8s/deploy.sh          (safe to run again after code changes)
set -euo pipefail
cd "$(dirname "$0")/.."

CLUSTER="${CLUSTER:-dataguard}"
NS=dataguard

need() {
  command -v "$1" >/dev/null 2>&1 || { echo "Missing '$1'. Install it with: brew install $2"; exit 1; }
}
need docker "--cask docker"
need kind kind
need kubectl kubectl

if ! kind get clusters 2>/dev/null | grep -qx "$CLUSTER"; then
  echo "==> Creating the kind cluster '$CLUSTER'"
  kind create cluster --name "$CLUSTER" --config k8s/kind-config.yaml
fi
kubectl config use-context "kind-$CLUSTER" >/dev/null

echo "==> Building images"
docker build -q -t dataguard/rules-engine:dev rules-engine
docker build -q -t dataguard/seed:dev db
docker build -q -t dataguard/dashboard:dev dashboard

echo "==> Loading images into the cluster"
kind load docker-image dataguard/rules-engine:dev dataguard/seed:dev dataguard/dashboard:dev --name "$CLUSTER"

echo "==> Applying configuration and manifests"
kubectl apply -f k8s/namespace.yaml
kubectl -n "$NS" create configmap db-init --from-file=init.sql=db/init.sql --dry-run=client -o yaml | kubectl apply -f -
kubectl -n "$NS" create configmap contracts --from-file=contracts/ --dry-run=client -o yaml | kubectl apply -f -
kubectl -n "$NS" delete job seed --ignore-not-found          # Jobs cannot be updated, only re-created
kubectl apply -k k8s/

echo "==> Waiting for PostgreSQL and the sample data"
kubectl -n "$NS" rollout status statefulset/postgres --timeout=300s
kubectl -n "$NS" wait --for=condition=complete job/seed --timeout=300s

echo "==> Restarting the apps so they pick up new images and contracts"
kubectl -n "$NS" rollout restart deployment/rules-engine deployment/dashboard
kubectl -n "$NS" rollout status deployment/rules-engine --timeout=300s
kubectl -n "$NS" rollout status deployment/dashboard --timeout=300s

echo
kubectl -n "$NS" get pods
echo
echo "Rules engine: http://localhost:8800/docs"
echo "Dashboard:    http://localhost:8880"
