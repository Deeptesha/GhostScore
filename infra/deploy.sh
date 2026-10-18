#!/usr/bin/env bash
# GhostScore — Cloud Run deployment
#
# Builds the repo-root Dockerfile with Cloud Build (no local Docker needed) and
# deploys it to Cloud Run. Run from the repository root, e.g. in Cloud Shell:
#
#   GCP_PROJECT=my-project ./infra/deploy.sh
#
# GHOSTSCORE_MODE (default: local)
#   local : all Google Cloud calls are stubbed; model = sklearn pipeline on UCI data.
#           Needs only Cloud Run + Cloud Build + Artifact Registry. This is the demo path.
#   gcp   : uses Vertex AI / Gemini / Document AI / BigQuery etc. The GCP-mode code and
#           setup_gcp.sh have NOT been run end-to-end. Run infra/setup_gcp.sh first and
#           expect to debug.

set -euo pipefail

: "${GCP_PROJECT:?Set GCP_PROJECT to your Google Cloud project ID}"
REGION=${GCP_REGION:-"us-central1"}
SERVICE=${SERVICE_NAME:-"ghostscore"}
MODE=${GHOSTSCORE_MODE:-"local"}

cd "$(dirname "$0")/.."

# Ensure the model artifact exists (the image copies ml/artifacts/)
if [ ! -f "ml/artifacts/model.joblib" ]; then
  echo "ml/artifacts/model.joblib missing. Train it first: python ml/train.py" >&2
  exit 1
fi

EXTRA_ARGS=()
if [ "$MODE" = "gcp" ]; then
  EXTRA_ARGS+=(--service-account="ghostscore-sa@${GCP_PROJECT}.iam.gserviceaccount.com")
fi

echo "=== Deploying ${SERVICE} (mode=${MODE}) to ${GCP_PROJECT}/${REGION} ==="
gcloud run deploy "$SERVICE" \
  --source . \
  --project="$GCP_PROJECT" \
  --region="$REGION" \
  --allow-unauthenticated \
  --memory=1Gi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=3 \
  --set-env-vars="GHOSTSCORE_MODE=${MODE},GCP_PROJECT=${GCP_PROJECT},GCP_REGION=${REGION}" \
  ${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"}

URL=$(gcloud run services describe "$SERVICE" --region="$REGION" --project="$GCP_PROJECT" --format="value(status.url)")
echo ""
echo "=== Deployed: ${URL} ==="
echo "Health: ${URL}/health"
echo "UI:     ${URL}/ui/"
