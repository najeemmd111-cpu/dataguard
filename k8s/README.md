# Kubernetes on kind (Phase 5)

Runs DataGuard's core (PostgreSQL with pgvector, the sample data, the rules engine and the dashboard) on a real Kubernetes cluster inside Docker, using [kind](https://kind.sigs.k8s.io/).

```
          your Mac                         kind cluster (namespace: dataguard)
  localhost:8880 ──NodePort 30880──▶ dashboard (2 pods, nginx) ──/api──▶ rules-engine Service
  localhost:8800 ──NodePort 30800──▶ rules-engine (1 pod) ──▶ postgres (StatefulSet + 1Gi volume)
                                     seed Job (loads the sample data once)
```

## Run it

```bash
brew install kind kubectl        # once
k8s/deploy.sh                    # creates the cluster, builds and loads the images, deploys, waits
k8s/smoke-test.sh                # checks health, a full run (11 rules, 4 failures) and the dashboard proxy
```

Then open the dashboard at http://localhost:8880 and the engine API at http://localhost:8800/docs. The ports don't clash with the Docker Compose setup (8000 and 5173), so both can run at the same time.

`deploy.sh` is safe to run again after code changes: it rebuilds the images, reloads them, and restarts the apps. Remove everything with `k8s/teardown.sh`.

Useful commands:

```bash
kubectl -n dataguard get pods
kubectl -n dataguard logs deployment/rules-engine -f
kubectl -n dataguard describe pod -l app=rules-engine
```

## What's in it

| File | Kind | Notes |
|---|---|---|
| `kind-config.yaml` | cluster | publishes NodePorts 30800 and 30880 on localhost:8800 and 8880 |
| `namespace.yaml` | Namespace | `dataguard` |
| `secret.yaml` | Secret | database password and URL (local development values only) |
| `postgres.yaml` | StatefulSet + headless Service | pgvector image, 1Gi PersistentVolumeClaim, `pg_isready` probes; `init.sql` runs from a ConfigMap on first start |
| `seed-job.yaml` | Job | waits for PostgreSQL (init container), then loads the sample data |
| `rules-engine.yaml` | Deployment + NodePort Service | contracts mounted from a ConfigMap; readiness = `GET /health` (database reachable), liveness = TCP |
| `dashboard.yaml` | Deployment + NodePort Service | 2 replicas of the production build served by nginx, which proxies `/api` to the engine |
| `kustomization.yaml` | Kustomize | `kubectl apply -k k8s/` |

`deploy.sh` creates two ConfigMaps from the repository files: `db-init` (from `db/init.sql`) and `contracts` (from `contracts/*.yaml`). Editing a contract and running `deploy.sh` again updates the engine.

## Design choices

- **One engine replica, `Recreate` strategy.** The check scheduler runs inside the engine, so two replicas would run every check twice. To scale out, move scheduling to a Kubernetes `CronJob` that calls `POST /runs`, then raise the replica count.
- **Readiness vs liveness.** Readiness checks the database, so traffic stops when it is down. Liveness only checks that the process answers: a database outage should not make Kubernetes restart the engine in a loop.
- **Non-root everywhere.** Every container runs as a numeric non-root user with privilege escalation off and all Linux capabilities dropped. The engine and seed images were changed to numeric users (10001) so Kubernetes can verify this.
- **Resource requests and limits** on every container.
- **Images are built locally** and loaded into kind (`imagePullPolicy: Never`); no registry is needed. For a cloud cluster, push the images to a registry and change the image names.
- **Not included:** the agent, n8n and the explainer, which depend on Ollama running on your Mac. They stay in Docker Compose.

## Checks

- Every manifest is validated against the official Kubernetes schemas with [kubeconform](https://github.com/yannh/kubeconform) in strict mode (unknown fields fail).
- CI creates a kind cluster, runs `deploy.sh` and `smoke-test.sh` on every push, and prints pod status and logs if anything fails.
