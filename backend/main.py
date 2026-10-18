"""
GhostScore FastAPI application entry point.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.api import router
from app.config import MODE

app = FastAPI(
    title="GhostScore API",
    description=(
        "Alternative credit scoring for India's credit-invisible population. "
        "Uses non-traditional signals (UPI, utility, rent) processed through "
        "Google Cloud Document AI, Vertex AI and Gemini. "
        f"Running in MODE={MODE} ({'offline local model' if MODE == 'local' else 'Google Cloud'})."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="")

# Serve the Stitch frontend if available
_frontend_dir = Path(__file__).parent.parent / "frontend"
if _frontend_dir.exists():
    app.mount("/ui", StaticFiles(directory=str(_frontend_dir), html=True), name="ui")


@app.get("/", include_in_schema=False)
def root():
    """Send visitors to the app's welcome screen."""
    return RedirectResponse("/ui/stitch/stitch_ghostscore_credit_advisor_app/ghostscore_welcome_consent/code.html")


@app.get("/health")
def health():
    return {"status": "ok", "mode": MODE}
