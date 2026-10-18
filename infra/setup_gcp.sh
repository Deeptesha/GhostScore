#!/usr/bin/env bash
# GhostScore — GCP Infrastructure Deployment Script
# Section 8 of blueprint: Hours 0-4 (GCP project setup)
#
# IMPORTANT: This script sets up real GCP resources.
# Review each section before running. You need:
#   - gcloud CLI authenticated: gcloud auth application-default login
#   - Billing account linked to the project
#   - APIs enabled (handled below)
#
# Do NOT run this against production without a dry-run review.

set -euo pipefail

PROJECT=${GCP_PROJECT:-"ghostscore-demo"}
REGION=${GCP_REGION:-"us-central1"}
DATASET=${BQ_DATASET:-"ghostscore"}
PUBSUB_TOPIC=${PUBSUB_TOPIC:-"gs-events"}
PUBSUB_SUB=${PUBSUB_SUB:-"gs-events-sub"}
REPO=${AR_REPO:-"ghostscore"}
SQL_INSTANCE=${SQL_INSTANCE:-"ghostscore-db"}
SQL_DB=${SQL_DB:-"ghostscore"}
SEARCH_DS=${SEARCH_DS:-"ghostscore-policy"}

echo "=== GhostScore GCP Setup ==="
echo "Project: $PROJECT  Region: $REGION"
echo ""

# ─── 1. Enable APIs ───────────────────────────────────────────────────────────
echo "1. Enabling APIs..."
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  bigquery.googleapis.com \
  pubsub.googleapis.com \
  documentai.googleapis.com \
  aiplatform.googleapis.com \
  discoveryengine.googleapis.com \
  sqladmin.googleapis.com \
  secretmanager.googleapis.com \
  --project="$PROJECT"

# ─── 2. Artifact Registry ────────────────────────────────────────────────────
echo "2. Creating Artifact Registry repository..."
gcloud artifacts repositories create "$REPO" \
  --repository-format=docker \
  --location="$REGION" \
  --description="GhostScore Docker images" \
  --project="$PROJECT" || echo "  (already exists)"

# ─── 3. BigQuery Dataset ─────────────────────────────────────────────────────
echo "3. Creating BigQuery dataset..."
bq --project_id="$PROJECT" mk \
  --dataset \
  --location="$REGION" \
  --description="GhostScore feature store and audit logs" \
  "$PROJECT:$DATASET" || echo "  (already exists)"

echo "   Creating tables..."
bq --project_id="$PROJECT" query --use_legacy_sql=false \
  "$(sed "s/{project}/$PROJECT/g; s/{dataset}/$DATASET/g" sql/schema.sql)"

# ─── 4. Pub/Sub Topic and Subscription ───────────────────────────────────────
echo "4. Creating Pub/Sub topic and subscription..."
gcloud pubsub topics create "$PUBSUB_TOPIC" --project="$PROJECT" || echo "  (already exists)"
gcloud pubsub subscriptions create "$PUBSUB_SUB" \
  --topic="$PUBSUB_TOPIC" \
  --ack-deadline=60 \
  --project="$PROJECT" || echo "  (already exists)"

# ─── 5. Cloud SQL (PostgreSQL) ───────────────────────────────────────────────
echo "5. Creating Cloud SQL instance (this takes ~5 minutes)..."
gcloud sql instances create "$SQL_INSTANCE" \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region="$REGION" \
  --project="$PROJECT" || echo "  (already exists)"

gcloud sql databases create "$SQL_DB" \
  --instance="$SQL_INSTANCE" \
  --project="$PROJECT" || echo "  (already exists)"

# ─── 6. Document AI Processors ───────────────────────────────────────────────
echo "6. Creating Document AI processors..."
echo "   NOTE: Create these manually in the GCP Console > Document AI"
echo "   - Form Parser (for utility bills, rent receipts)"
echo "   - Bank Statement Parser (for bank statements)"
echo "   - Identity Document Parser (for KYC)"
echo "   - Custom Document Extractor (for rental agreements)"
echo "   Then set env vars: DAI_UTILITY_PROCESSOR, DAI_CUSTOM_PROCESSOR, etc."

# ─── 7. Vertex AI Search Datastore ───────────────────────────────────────────
echo "7. Setting up Vertex AI Search datastore..."
echo "   NOTE: Create the datastore manually in GCP Console > Agent Builder"
echo "   Datastore ID: $SEARCH_DS"
echo "   Upload policy documents: RBI microfinance guidelines, PMMY tiers, FAQs"
echo "   Then set env var: SEARCH_DATASTORE_ID=$SEARCH_DS"

# ─── 8. IAM Service Account ──────────────────────────────────────────────────
echo "8. Creating service account..."
SA_NAME="ghostscore-sa"
SA_EMAIL="${SA_NAME}@${PROJECT}.iam.gserviceaccount.com"
gcloud iam service-accounts create "$SA_NAME" \
  --description="GhostScore API service account" \
  --display-name="GhostScore SA" \
  --project="$PROJECT" || echo "  (already exists)"

# Grant necessary roles
for ROLE in \
  roles/bigquery.dataEditor \
  roles/bigquery.jobUser \
  roles/pubsub.publisher \
  roles/pubsub.subscriber \
  roles/documentai.apiUser \
  roles/aiplatform.user \
  roles/cloudsql.client \
  roles/discoveryengine.viewer; do
  gcloud projects add-iam-policy-binding "$PROJECT" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="$ROLE" --quiet
done

echo ""
echo "=== Infrastructure setup complete ==="
echo "Next: run deploy.sh to build and deploy Cloud Run services."
