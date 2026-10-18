"""
GhostScore Backend — configuration and mode switching.

MODE=local   runs entirely offline using the trained sklearn GradientBoosting model.
MODE=gcp     uses real Google Cloud services (requires valid ADC credentials).
"""
import os

MODE = os.getenv("GHOSTSCORE_MODE", "local")   # "local" | "gcp"

GCP_PROJECT   = os.getenv("GCP_PROJECT", "ghostscore-demo")
GCP_REGION    = os.getenv("GCP_REGION", "us-central1")
BQ_DATASET    = os.getenv("BQ_DATASET", "ghostscore")
PUBSUB_TOPIC  = os.getenv("PUBSUB_TOPIC", "gs-events")
MODEL_PATH    = os.getenv("MODEL_PATH", "ml/artifacts/model.joblib")
CONF_THRESHOLD = float(os.getenv("CONF_THRESHOLD", "0.75"))

# Vertex AI endpoint (populated after deployment)
VERTEX_ENDPOINT = os.getenv("VERTEX_ENDPOINT", "")
