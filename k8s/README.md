# Kubernetes on kind (Phase 5)

```bash
kind create cluster --name dataguard
docker build -t dataguard/rules-engine:dev ../rules-engine
docker build -t dataguard/seed:dev ../db
kind load docker-image dataguard/rules-engine:dev dataguard/seed:dev --name dataguard

kubectl create namespace dataguard
kubectl -n dataguard create secret generic db --from-literal=password=dataguard
kubectl -n dataguard create configmap contracts --from-file=../contracts
kubectl -n dataguard create configmap db-init --from-file=../db/init.sql
kubectl apply -n dataguard -f .
kubectl -n dataguard port-forward svc/rules-engine 8000:8000
```

## Manifests to write

| File | Contents |
|---|---|
| `postgres.yaml` | StatefulSet (pgvector/pgvector:pg16) + PVC + headless Service; mount `db-init` at `/docker-entrypoint-initdb.d` |
| `seed-job.yaml` | Job running `dataguard/seed:dev` once |
| `rules-engine.yaml` | Deployment + Service; mount `contracts` at `/contracts`; readiness/liveness probe on `/health` |
| `dashboard.yaml` | Deployment + Service (phase 2 image) |

Remember `imagePullPolicy: IfNotPresent` for images loaded with `kind load`.
