# Cloud Run deployment (Phase 5)

**Before anything else:** Billing → Budgets & alerts → create a budget (e.g. €10) with email alerts.

```bash
PROJECT=your-project-id
REGION=europe-west1
gcloud config set project $PROJECT
gcloud services enable run.googleapis.com artifactregistry.googleapis.com
gcloud artifacts repositories create dataguard --repository-format=docker --location=$REGION
gcloud auth configure-docker $REGION-docker.pkg.dev

IMG=$REGION-docker.pkg.dev/$PROJECT/dataguard/rules-engine:v1
docker build -t $IMG ../../rules-engine && docker push $IMG

gcloud run deploy rules-engine --image $IMG --region $REGION \
  --set-env-vars DATABASE_URL="postgresql://...",SCHEDULER_ENABLED=false \
  --allow-unauthenticated
```

Notes:

- Database: Neon or Supabase (free tier, pgvector included) is cheaper than Cloud SQL. Run `db/init.sql` and `db/seed.py` against it once.
- Contracts: bake them into the image for the cloud (`COPY contracts /contracts`) or mount from a Cloud Storage volume.
- Cloud Run scales to zero, so use **Cloud Scheduler** calling `POST /runs` instead of the in-process scheduler.
- Put the DB URL in **Secret Manager** (`--set-secrets`) rather than a plain env var once it works.

## Teardown

```bash
gcloud run services delete rules-engine --region $REGION --quiet
gcloud artifacts repositories delete dataguard --location $REGION --quiet
```
