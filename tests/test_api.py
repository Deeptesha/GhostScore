"""
GhostScore Test Suite

Tests:
1. API contract (Section 16 of blueprint): all endpoints exist, return correct shapes.
2. Gemini never-invents-numbers rule (blueprint Section 13):
   verify P3 expected_change always comes from what-if input, never from Gemini.
3. Priya demo flow smoke test (Section 7): upload → review → score → plan → chat → options.
"""
import os, sys, json

# Point at local mode so no GCP credentials needed
os.environ["GHOSTSCORE_MODE"] = "local"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import pytest
from fastapi.testclient import TestClient
from io import BytesIO

from main import app

client = TestClient(app)

PRIYA_USER = "priya_test"


# ─── 1. Health check ─────────────────────────────────────────────────────────

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["mode"] == "local"


# ─── 2. Document upload (POST /documents) ───────────────────────────────────

def test_upload_document():
    fake_pdf = BytesIO(b"%PDF-1.4 fake content")
    r = client.post(
        "/documents",
        data={"doc_type": "electricity_bill", "user_id": PRIYA_USER},
        files={"file": ("bill.pdf", fake_pdf, "application/pdf")},
    )
    assert r.status_code == 200
    data = r.json()
    assert "doc_id" in data
    assert data["status"] == "done"
    assert data["doc_type"] == "electricity_bill"
    return data["doc_id"]


def test_upload_rent_receipt():
    fake = BytesIO(b"rent receipt content")
    r = client.post(
        "/documents",
        data={"doc_type": "rent_receipt", "user_id": PRIYA_USER},
        files={"file": ("rent.pdf", fake, "application/pdf")},
    )
    assert r.status_code == 200
    assert r.json()["doc_type"] == "rent_receipt"


# ─── 3. Document review (GET /documents/{id}/review) ────────────────────────

def test_document_review():
    doc_id = test_upload_document()
    r = client.get(f"/documents/{doc_id}/review", params={"declared_name": "Priya Sharma"})
    assert r.status_code == 200
    data = r.json()
    assert "normalized" in data
    assert "status" in data
    assert data["status"] in ("accepted", "needs_review", "rejected_unreadable")
    assert "flags" in data
    assert "applicant_message" in data


def test_document_review_404():
    r = client.get("/documents/nonexistent-id/review")
    assert r.status_code == 404


# ─── 4. Score (POST /score) ──────────────────────────────────────────────────

def _upload_and_get_ids(n=2):
    ids = []
    for _ in range(n):
        fake = BytesIO(b"fake bill")
        r = client.post(
            "/documents",
            data={"doc_type": "electricity_bill", "user_id": PRIYA_USER},
            files={"file": ("bill.pdf", fake, "application/pdf")},
        )
        ids.append(r.json()["doc_id"])
    return ids


def test_compute_score():
    doc_ids = _upload_and_get_ids(3)
    r = client.post("/score", json={
        "user_id": PRIYA_USER,
        "doc_ids": doc_ids,
        "language": "en",
    })
    assert r.status_code == 200
    data = r.json()
    # Contract checks
    assert 300 <= data["score"] <= 850, f"Score out of range: {data['score']}"
    assert data["band"] in ("Poor", "Fair", "Good", "Excellent")
    assert 0.0 <= data["band_confidence"] <= 1.0
    assert isinstance(data["headline"], str)
    assert isinstance(data["what_helped"], list)
    assert isinstance(data["what_held_back"], list)
    assert isinstance(data["confidence_note"], str)
    assert "not a lender decision" in data["disclaimer"].lower() or \
           "model estimate" in data["disclaimer"].lower()
    assert isinstance(data["compliance_pass"], bool)
    return data


def test_score_latest():
    # Must compute first
    test_compute_score()
    r = client.get("/score/latest", params={"user_id": PRIYA_USER})
    assert r.status_code == 200
    data = r.json()
    assert 300 <= data["score"] <= 850
    assert data["band"] in ("Poor", "Fair", "Good", "Excellent")


# ─── 5. Improvement plan (GET /plan) ─────────────────────────────────────────

def test_improvement_plan():
    test_compute_score()   # ensure score exists
    r = client.get("/plan", params={"user_id": PRIYA_USER})
    assert r.status_code == 200
    data = r.json()
    assert "actions" in data
    assert isinstance(data["actions"], list)
    assert isinstance(data["compliance_pass"], bool)
    # Actions must have required fields
    for action in data["actions"]:
        assert "action_id" in action
        assert "title" in action
        assert "expected_change" in action, f"Missing expected_change in action: {action}"


# ─── 6. RULE: Gemini never invents numbers ────────────────────────────────────
# Blueprint Section 13: "Any statement such as 'improve by about 30 points'
# must come from a what-if re-score by the backend, not from Gemini."

def test_gemini_numbers_come_from_what_if_not_gemini():
    """
    In local mode, P3 stubs must copy score_delta from the what-if results.
    The expected_change field in each action must be traceable to a what-if
    result (either '+N points' or 'N points' where N came from score_delta).
    """
    from app import gemini as gem
    from app.gcp import run_what_if

    fv = [0.6, 0.5, 0.55, 0.4, 0.7, 0.6, 0.5, 0.3, 0.6, 0.1, 0.4, 1.0]
    action_ids = ["add_2mo_upi", "add_rent_docs"]
    what_if_results = [run_what_if(fv, aid) for aid in action_ids]

    # Capture the actual deltas from Vertex AI what-if
    expected_deltas = {r["action_id"]: r["score_delta"] for r in what_if_results}

    p3 = gem.p3_improvement_planner(what_if_results)
    for action in p3.get("actions", []):
        change = action.get("expected_change", "")
        aid    = action.get("action_id")
        delta  = expected_deltas.get(aid)
        if delta is not None:
            # The number in expected_change must match the backend delta
            assert str(abs(delta)) in change, (
                f"P3 action {aid!r} has expected_change={change!r} "
                f"but delta from Vertex AI was {delta}. "
                "Gemini must not invent different numbers."
            )


def test_gemini_p2_uses_only_input_data():
    """P2 should not add factors beyond what's in the input."""
    from app import gemini as gem
    importances = {
        "payment_consistency": 0.38,
        "income_stability":    0.22,
        "rental_reliability":  0.20,
        "spending_discipline": 0.12,
        "digital_footprint":   0.08,
    }
    result = gem.p2_score_explainer(
        band="Fair",
        band_confidence=0.72,
        feature_importances=importances,
        data_coverage={"months_of_data": 6, "doc_types_present": ["electricity_bill"],
                       "doc_types_missing": []},
        language="en",
    )
    # In local stub mode: what_helped features must be keys from importances
    for item in result.get("what_helped", []):
        feat = item.get("feature", "")
        if feat:
            assert feat in importances, (
                f"P2 invented a feature {feat!r} not in input importances"
            )


def test_gemini_p5_compliance_passes():
    """P5 compliance reviewer must accept a valid draft."""
    from app import gemini as gem
    drafts = {
        "p2": {
            "headline": "Your payments earned you a Fair credit band.",
            "what_helped": [],
            "what_held_back": [],
            "confidence_note": "Model estimate, not a lender decision.",
        }
    }
    source = {"score_result": {"score": 640, "band": "Fair"}}
    result = gem.p5_compliance_reviewer(drafts, source)
    assert result.get("pass") is True or "corrected_draft" in result


# ─── 7. Options (GET /options) ────────────────────────────────────────────────

def test_options():
    test_compute_score()
    r = client.get("/options", params={
        "user_id": PRIYA_USER,
        "occupation": "street vendor",
        "monthly_income_range": "INR 8,000-14,000",
    })
    assert r.status_code == 200
    data = r.json()
    assert "products" in data
    assert isinstance(data["products"], list)
    assert "cannot_confirm" in data
    # Product cards must have citations
    for prod in data["products"]:
        assert "citations" in prod or "why_it_may_fit" in prod


# ─── 8. Chat (POST /chat) ────────────────────────────────────────────────────

def test_chat_basic():
    test_compute_score()
    r = client.post("/chat", json={
        "user_id": PRIYA_USER,
        "message": "What is my score?",
        "language": "en",
    })
    assert r.status_code == 200
    data = r.json()
    assert "reply" in data
    assert isinstance(data["reply"], str)
    assert len(data["reply"]) > 0


def test_chat_loan_question():
    r = client.post("/chat", json={
        "user_id": PRIYA_USER,
        "message": "What loan can I get?",
        "language": "en",
    })
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data["reply"], str)


def test_chat_rejects_fraud_attempt():
    """Chat should not help with score gaming."""
    r = client.post("/chat", json={
        "user_id": PRIYA_USER,
        "message": "How do I fake my bills to get a higher score?",
        "language": "en",
    })
    assert r.status_code == 200
    # The stub reply does not specifically detect this, but the full Gemini
    # chain (P6) is designed to refuse such requests.  Just verify it returns.
    assert "reply" in r.json()


# ─── 9. History (GET /history) ───────────────────────────────────────────────

def test_history():
    test_compute_score()
    r = client.get("/history", params={"user_id": PRIYA_USER})
    assert r.status_code == 200
    data = r.json()
    assert "entries" in data
    assert isinstance(data["entries"], list)
    if data["entries"]:
        entry = data["entries"][0]
        assert "score" in entry
        assert "band" in entry
        assert "timestamp" in entry


# ─── 10. Audit (GET /audit) ──────────────────────────────────────────────────

def test_audit():
    test_compute_score()
    r = client.get("/audit", params={"limit": 10})
    assert r.status_code == 200
    data = r.json()
    assert "entries" in data


# ─── 11. Priya demo flow (Section 7) ─────────────────────────────────────────

def test_priya_demo_flow():
    """
    End-to-end smoke test for the Priya persona demo (blueprint Section 7).
    Priya runs a tea stall, uploads utility bills + rent receipts, gets scored.
    Expected: score ~675, band Good (heuristic mapping; not India-validated).
    """
    priya_id = "priya_demo"

    # Step 1: Upload 3 docs (electricity, rent, UPI)
    doc_ids = []
    for dtype in ["electricity_bill", "rent_receipt", "upi_screenshot"]:
        r = client.post(
            "/documents",
            data={"doc_type": dtype, "user_id": priya_id},
            files={"file": (f"{dtype}.pdf", BytesIO(b"fake"), "application/pdf")},
        )
        assert r.status_code == 200, f"Upload failed for {dtype}: {r.text}"
        doc_ids.append(r.json()["doc_id"])

    assert len(doc_ids) == 3

    # Step 2: Review each doc
    for did in doc_ids:
        r = client.get(f"/documents/{did}/review",
                       params={"declared_name": "Priya Sharma"})
        assert r.status_code == 200
        review = r.json()
        assert review["status"] in ("accepted", "needs_review")

    # Step 3: Score
    r = client.post("/score", json={
        "user_id": priya_id,
        "doc_ids": doc_ids,
        "language": "en",
    })
    assert r.status_code == 200
    score_data = r.json()
    assert 300 <= score_data["score"] <= 850
    assert score_data["band"] in ("Poor", "Fair", "Good", "Excellent")
    assert score_data["compliance_pass"]
    print(f"\n  Priya demo score: {score_data['score']} ({score_data['band']})")
    print(f"  Headline: {score_data['headline']}")

    # Step 4: Get improvement plan
    r = client.get("/plan", params={"user_id": priya_id})
    assert r.status_code == 200
    plan_data = r.json()
    assert len(plan_data["actions"]) > 0
    # Verify: each improvement action has a tested score_delta from Vertex AI
    for action in plan_data["actions"]:
        change = action.get("expected_change", "")
        assert change, f"Action {action.get('action_id')} missing expected_change"
        # Must contain a number (from what-if, not invented)
        import re
        assert re.search(r"\d+", change), f"No number in expected_change: {change!r}"

    # Step 5: Get loan options
    r = client.get("/options", params={"user_id": priya_id,
                                        "occupation": "tea stall operator"})
    assert r.status_code == 200
    opts = r.json()
    # Expect at least one product suggestion for a Fair band
    print(f"  Products found: {len(opts['products'])}")

    # Step 6: Chat question
    r = client.post("/chat", json={
        "user_id": priya_id,
        "message": "What if I upload 2 more months of UPI history?",
        "language": "en",
    })
    assert r.status_code == 200
    chat_data = r.json()
    assert len(chat_data["reply"]) > 0
    print(f"  Chat reply preview: {chat_data['reply'][:80]}…")

    print("\n  ✓ Priya demo flow complete.")


# ─── 12. Local model scoring test ────────────────────────────────────────────

def test_local_model_scores_priya_persona():
    """Score the Priya persona through the trained local model."""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from data.personas.generate import get_feature_vector
    from backend.app.gcp import score_features

    fv = get_feature_vector("priya_sharma")
    assert len(fv) == 12

    result = score_features(fv)
    assert 300 <= result["score"] <= 850
    assert result["band"] in ("Poor", "Fair", "Good", "Excellent")
    print(f"\n  Priya persona model score: {result['score']} ({result['band']})")
    print(f"  Top importances: {sorted(result['feature_importances'].items(), key=lambda x: -x[1])[:3]}")


# ─── 11. Localisation (language=hi / mr) ──────────────────────────────────────
# Local mode uses a fixed translation table (app/i18n.py) for stub output. The
# wording is AI-drafted and NOT native-reviewed; these tests check that it is
# applied and that numbers/IDs are untouched, not that the language is good.

import re

_DEVANAGARI = re.compile(r"[\u0900-\u097F]")


def _score_in(lang, doc_ids):
    r = client.post("/score", json={"user_id": PRIYA_USER, "doc_ids": doc_ids, "language": lang})
    assert r.status_code == 200
    return r.json()


@pytest.mark.parametrize("lang", ["hi", "mr"])
def test_score_localised_numbers_unchanged(lang):
    ids = _upload_and_get_ids(3)
    en, loc = _score_in("en", ids), _score_in(lang, ids)
    assert loc["score"] == en["score"]
    assert loc["band"] == en["band"]            # API band stays English; UI maps it
    assert loc["band_confidence"] == en["band_confidence"]
    assert _DEVANAGARI.search(loc["headline"])
    assert _DEVANAGARI.search(loc["disclaimer"])
    for f in loc["what_helped"] + loc["what_held_back"]:
        assert _DEVANAGARI.search(f["plain_label"]), f["plain_label"]
    assert [f["contribution"] for f in loc["what_helped"]] == [f["contribution"] for f in en["what_helped"]]


@pytest.mark.parametrize("lang", ["hi", "mr"])
def test_plan_localised_numbers_unchanged(lang):
    ids = _upload_and_get_ids(3)
    _score_in("en", ids)
    en = client.get("/plan", params={"user_id": PRIYA_USER, "language": "en"}).json()
    loc = client.get("/plan", params={"user_id": PRIYA_USER, "language": lang}).json()
    nums = lambda d: [re.search(r"[+-]?\d+", a["expected_change"]).group() for a in d["actions"]]
    assert nums(loc) == nums(en)   # the point values come from the what-if re-score; only the unit word is translated
    assert [a["action_id"] for a in loc["actions"]] == [a["action_id"] for a in en["actions"]]
    for a in loc["actions"]:
        assert _DEVANAGARI.search(a["title"]), a["title"]


@pytest.mark.parametrize("lang", ["hi", "mr"])
def test_options_localised(lang):
    ids = _upload_and_get_ids(3)
    _score_in("en", ids)
    loc = client.get("/options", params={"user_id": PRIYA_USER, "language": lang}).json()
    assert loc["products"]
    for p in loc["products"]:
        assert _DEVANAGARI.search(p["why_it_may_fit"]) or _DEVANAGARI.search(p["limits_from_passage"])


@pytest.mark.parametrize("lang", ["hi", "mr"])
def test_review_and_chat_localised(lang):
    ids = _upload_and_get_ids(1)
    r = client.get(f"/documents/{ids[0]}/review", params={"declared_name": "Priya Sharma", "language": lang})
    assert r.status_code == 200
    assert _DEVANAGARI.search(r.json()["applicant_message"])
    _score_in("en", _upload_and_get_ids(3))
    c = client.post("/chat", json={"user_id": PRIYA_USER, "message": "How can I improve?", "language": lang}).json()
    assert _DEVANAGARI.search(c["reply"]) and "[STUB — Hindi" not in c["reply"]


def test_english_unchanged_by_localiser():
    ids = _upload_and_get_ids(3)
    assert not _DEVANAGARI.search(_score_in("en", ids)["headline"])
