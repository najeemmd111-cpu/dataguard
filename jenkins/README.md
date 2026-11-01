# Jenkins (Phase 5)

A local Jenkins that runs the [`Jenkinsfile`](../Jenkinsfile): the same checks as GitHub Actions, with every test result in Jenkins' test report.

```
docker compose --profile ci up -d --build
        │
        ├── jenkins      http://localhost:8090   (Python 3.12, Node 22, Java 21, Maven, kubeconform built in)
        └── jenkins-db   pgvector/pgvector:pg16  (for the database tests)
```

## Start it

```bash
docker compose --profile ci up -d --build     # the first build takes a few minutes
```

Open http://localhost:8090 and sign in as **admin / admin**. The **dataguard** job is already there: click it, then **Build Now**.

The first build is the slowest (about 5–10 minutes) because it downloads the Python, npm and Maven packages. They are cached in the `jenkins_home` volume, so later builds are much faster. After the first build, Jenkins checks GitHub every 5 minutes and builds new commits by itself.

Stop it with `docker compose --profile ci down` (add `-v` to also delete the Jenkins data and caches).

## Pipeline

| Stage | Commands | Test report |
|---|---|---|
| Rules engine | `ruff check`, `pytest` against `jenkins-db` | `reports/rules-engine.xml` |
| Agent | `ruff check`, `pytest` (offline stand-in models) | `reports/agent.xml` |
| MCP server | `npm ci`, type check, `vitest`, build | `reports/mcp-server.xml` |
| Dashboard | `npm ci`, `eslint`, `vitest`, build | `reports/dashboard.xml` |
| Explainer (Java) | `mvn verify` | Surefire reports |
| Kubernetes manifests | `kubeconform -strict` | |

After a build, open it and click **Tests** for every test case from all stages; **Pipeline Overview** / **Stage View** shows the time per stage.

## How it is set up

- **No setup wizard, nothing to click.** [`casc.yaml`](casc.yaml) (Configuration as Code) creates the admin user, the security settings and, with Job DSL, the `dataguard` pipeline job. It is applied on every start, so the configuration lives in Git, not in the Jenkins UI.
- **The tools are in the image** ([`Dockerfile`](Dockerfile)), so the pipeline doesn't need access to the Docker socket. Giving Jenkins the Docker socket is common, but it effectively gives builds root access to the host. Python 3.12 is installed with `uv`, which also creates each stage's virtual environment.
- **Plugins** are listed in [`plugins.txt`](plugins.txt) and installed when the image is built.
- The job builds from GitHub (`main`), like GitHub Actions. To build a fork or another branch, set `DATAGUARD_REPO` or `DATAGUARD_BRANCH` in `.env` and run `docker compose --profile ci up -d`.

## Result

On a MacBook Air (Apple Silicon, Docker Desktop), the first full build took about 3 minutes with downloads, and later builds about **1 min 17 s**, all six stages green.

One problem found on the way: `uv` downloads 50 packages at once by default, and Docker Desktop's network on a Mac stalled under that (7+ minutes for a small install, sometimes a timeout). The Jenkinsfile limits it to 4 parallel downloads with retries, which brought the install down to seconds.

## Jenkins and GitHub Actions

| | GitHub Actions | Jenkins |
|---|---|---|
| Runs on | GitHub's machines | your own machine (or a company server) |
| Configured in | `.github/workflows/ci.yml` | `Jenkinsfile` + `jenkins/casc.yaml` |
| Database for tests | service container per job | `jenkins-db` next to Jenkins |
| Also runs | Playwright e2e, kind deploy, retrieval evaluation | (these need Docker, so they stay in GitHub Actions) |

## Settings

| Variable | Default |
|---|---|
| `JENKINS_ADMIN_PASSWORD` | `admin` |
| `DATAGUARD_REPO` | `https://github.com/najeemmd111-cpu/dataguard.git` |
| `DATAGUARD_BRANCH` | `main` |

## Troubleshooting

- **Port 8090 in use**: change `"8090:8080"` in `docker-compose.yml`.
- **A stage fails but works in GitHub Actions**: open the build's **Console Output**; the first lines of the *Prepare* stage show the tool versions.
- **Configuration looks wrong after editing `casc.yaml`**: rebuild the image, `docker compose --profile ci up -d --build`.
