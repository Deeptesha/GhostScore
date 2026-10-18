"""
GhostScore API — Section 16 contract (blueprint).

Endpoints:
  POST /documents
  GET  /documents/{doc_id}/review
  POST /score
  GET  /score/latest
  GET  /plan
  GET  /options
  POST /chat
  GET  /history
  GET  /audit
"""
from __future__ import annotations
import uuid, datetime
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query

from app import gcp, gemini as gem
from app.config import MODE
from app.i18n import localize
from app.models import (
    DocumentUploadResponse, DocumentReviewResponse,
    ScoreRequest, ScoreResponse,
    PlanResponse, OptionsResponse,
    ChatRequest, ChatResponse,
    HistoryResponse, HistoryEntry,
    AuditResponse, AuditEntry,
)

router = APIRouter()


def _loc(model, lang):
    """Local mode: translate known stub strings in a response model.
    In gcp mode Gemini P7 is the translator and this is a no-op."""
    if MODE != "local" or lang not in ("hi", "mr"):
        return model
    return type(model)(**localize(model.model_dump(), lang))

# In local mode these dicts act as ephemeral storage between requests.
_doc_store: dict[str, dict] = {}       # doc_id → {entities, doc_type, filename}
_score_store: dict[str, dict] = {}     # user_id → latest score result


# ─── POST /documents ─────────────────────────────────────────────────────────

@router.post("/documents", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    doc_type: str = Form("electricity_bill"),
    user_id: str = Form("priya"),
):
    """
    Upload a document.  Calls Document AI (or stub) to extract entities.
    No Gemini step at this point.
    """
    content  = await file.read()
    result   = gcp.process_document(content, doc_type)
    doc_id   = result.get("doc_id", str(uuid.uuid4()))

    meta = {
        "doc_id":   doc_id,
        "doc_type": doc_type,
        "filename": file.filename or "upload",
        "user_id":  user_id,
        "entities": result.get("entities", []),
        "stub":     result.get("stub", False),
        "status":   "done",
    }
    _doc_store[doc_id] = meta
    gcp.save_document(doc_id, meta)

    return DocumentUploadResponse(
        doc_id=doc_id,
        status="done",
        doc_type=doc_type,
        filename=meta["filename"],
    )


# ─── GET /documents/{doc_id}/review ──────────────────────────────────────────

@router.get("/documents/{doc_id}/review", response_model=DocumentReviewResponse)
async def review_document(
    doc_id: str,
    declared_name: str = Query("Priya Sharma"),
    conf_threshold: float = Query(0.75),
    language: str = Query("en"),
):
    """
    Run P1 Intake Verifier on a previously uploaded document.
    """
    doc = _doc_store.get(doc_id) or gcp.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document {doc_id!r} not found")

    p1 = gem.p1_intake_verifier(
        doc_type=doc["doc_type"],
        declared_name=declared_name,
        entities=doc["entities"],
        conf_threshold=conf_threshold,
    )
    return _loc(DocumentReviewResponse(
        doc_id=doc_id,
        normalized=p1["normalized"],
        status=p1["status"],
        flags=p1["flags"],
        applicant_message=p1["applicant_message"],
    ), language)


# ─── POST /score ──────────────────────────────────────────────────────────────

@router.post("/score", response_model=ScoreResponse)
async def compute_score(req: ScoreRequest):
    """
    Compute credit score for a user.
    Chain: feature engineering → Vertex AI score → P2 explainer → P5 compliance.
    """
    feature_vector = _build_feature_vector(req.doc_ids)
    score_result   = gcp.score_features(feature_vector)

    # coverage info for P2
    data_coverage = {
        "months_of_data":   len(req.doc_ids),
        "doc_types_present": list({_doc_store.get(d, {}).get("doc_type","unknown")
                                    for d in req.doc_ids}),
        "doc_types_missing": [],
    }

    p2 = gem.p2_score_explainer(
        band=score_result["band"],
        band_confidence=score_result["band_confidence"],
        feature_importances=score_result["feature_importances"],
        data_coverage=data_coverage,
        language=req.language or "en",
    )
    p5 = gem.p5_compliance_reviewer(
        drafts={"p2": p2},
        source_data={"score_result": score_result},
    )
    corrected_p2 = p5.get("corrected_draft", {}).get("p2", p2)

    # Persist
    gcp.save_score(req.user_id, score_result["score"], score_result["band"])
    _score_store[req.user_id] = {**score_result, "feature_vector": feature_vector}
    gcp.append_audit({
        "timestamp":     datetime.datetime.utcnow().isoformat() + "Z",
        "event_type":    "score_computed",
        "user_id":       req.user_id,
        "model_version": score_result.get("model", "local"),
        "band":          score_result["band"],
        "top_factors":   list(score_result["feature_importances"].keys())[:3],
        "explanation_id": str(uuid.uuid4()),
    })
    gcp.publish_event({
        "event": "score_computed",
        "user_id": req.user_id,
        "band": score_result["band"],
    })

    return _loc(ScoreResponse(
        score=score_result["score"],
        band=score_result["band"],
        band_confidence=score_result["band_confidence"],
        headline=corrected_p2.get("headline", "Your score has been calculated."),
        what_helped=corrected_p2.get("what_helped", []),
        what_held_back=corrected_p2.get("what_held_back", []),
        confidence_note=corrected_p2.get("confidence_note", "This is a model estimate."),
        disclaimer="Model estimate — not a lender decision.",
        compliance_pass=p5["pass"],
    ), req.language or "en")


# ─── GET /score/latest ────────────────────────────────────────────────────────

@router.get("/score/latest", response_model=ScoreResponse)
async def get_latest_score(
    user_id: str = Query("priya"),
    language: str = Query("en"),
):
    """Return the latest computed score for a user."""
    cached = _score_store.get(user_id)
    if not cached:
        raise HTTPException(status_code=404, detail="No score found for this user")

    p2 = gem.p2_score_explainer(
        band=cached["band"],
        band_confidence=cached["band_confidence"],
        feature_importances=cached["feature_importances"],
        data_coverage={"months_of_data": 6, "doc_types_present": [], "doc_types_missing": []},
        language=language,
    )
    return _loc(ScoreResponse(
        score=cached["score"],
        band=cached["band"],
        band_confidence=cached["band_confidence"],
        headline=p2.get("headline", "Your score is ready."),
        what_helped=p2.get("what_helped", []),
        what_held_back=p2.get("what_held_back", []),
        confidence_note=p2.get("confidence_note", ""),
        disclaimer="Model estimate — not a lender decision.",
        compliance_pass=True,
    ), language)


# ─── GET /plan ────────────────────────────────────────────────────────────────

@router.get("/plan", response_model=PlanResponse)
async def get_improvement_plan(
    user_id: str = Query("priya"),
    language: str = Query("en"),
):
    """
    Build an improvement plan.
    Chain: Vertex AI what-if re-scores → P3 planner → P5 compliance.
    Numbers come from Vertex AI what-if; Gemini only phrases them.
    """
    cached = _score_store.get(user_id)
    fv     = cached["feature_vector"] if cached else [0.5] * 12

    action_ids = ["add_2mo_upi", "add_rent_docs", "reduce_variance", "add_utility_6mo"]
    what_if_results = [gcp.run_what_if(fv, aid) for aid in action_ids]

    p3 = gem.p3_improvement_planner(what_if_results)
    p5 = gem.p5_compliance_reviewer(
        drafts={"p3": p3},
        source_data={"what_if_results": what_if_results},
    )
    corrected_p3 = p5.get("corrected_draft", {}).get("p3", p3)

    return _loc(PlanResponse(
        user_id=user_id,
        actions=corrected_p3.get("actions", []),
        compliance_pass=p5["pass"],
    ), language)


# ─── GET /options ─────────────────────────────────────────────────────────────

@router.get("/options", response_model=OptionsResponse)
async def get_options(
    user_id: str = Query("priya"),
    occupation: str = Query("street vendor"),
    monthly_income_range: str = Query("INR 5,000-15,000"),
    language: str = Query("en"),
):
    """
    Return eligible loan products.
    Chain: Vertex AI Search → P4 eligibility → P5 compliance.
    """
    cached   = _score_store.get(user_id)
    band     = cached["band"] if cached else "Fair"
    passages = gcp.search_policy(f"loan eligibility {occupation} {band}")

    p4 = gem.p4_grounded_eligibility(band, occupation, monthly_income_range, passages)
    p5 = gem.p5_compliance_reviewer(
        drafts={"p4": p4},
        source_data={"passages": passages, "band": band},
    )
    corrected_p4 = p5.get("corrected_draft", {}).get("p4", p4)

    return _loc(OptionsResponse(
        user_id=user_id,
        products=corrected_p4.get("products", []),
        cannot_confirm=corrected_p4.get("cannot_confirm", []),
        compliance_pass=p5["pass"],
    ), language)


# ─── POST /chat ───────────────────────────────────────────────────────────────

@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """
    Conversational advisor (P6).
    The backend pre-fetches tool results; Gemini reads and phrases them.
    """
    tool_results: dict = {}

    msg_lower = req.message.lower()

    # Pre-fetch score summary if needed
    if any(w in msg_lower for w in ["score", "band", "result", "मेरा"]):
        cached = _score_store.get(req.user_id)
        if cached:
            tool_results["score_summary"] = {
                "score": cached["score"],
                "band":  cached["band"],
                "confidence": cached["band_confidence"],
            }

    # Pre-fetch what-if if needed
    if any(w in msg_lower for w in ["improve", "what if", "upload", "add", "better"]):
        cached = _score_store.get(req.user_id)
        fv     = cached["feature_vector"] if cached else [0.5] * 12
        wi     = gcp.run_what_if(fv, "add_2mo_upi")
        tool_results["what_if"] = wi

    # Pre-fetch policy if needed
    if any(w in msg_lower for w in ["loan", "mudra", "eligible", "product", "lender"]):
        passages = gcp.search_policy(req.message)
        tool_results["policy_passages"] = passages

    result = gem.p6_chat_advisor(req.user_id, req.message, req.language or "en", tool_results)

    # P7 localization
    reply = result["reply"]
    if req.language and req.language != "en":
        reply = gem.p7_localizer(reply, req.language)

    return ChatResponse(
        reply=reply,
        tool_calls_made=result.get("tool_calls_made", []),
        sources=result.get("sources", []),
    )


# ─── GET /history ─────────────────────────────────────────────────────────────

@router.get("/history", response_model=HistoryResponse)
async def get_history(user_id: str = Query("priya")):
    """Return score history from Cloud SQL (local: in-memory)."""
    raw     = gcp.get_score_history(user_id)
    entries = [
        HistoryEntry(
            timestamp=e["timestamp"],
            score=e["score"],
            band=e["band"],
            event=e.get("event"),
        )
        for e in raw
    ]
    return HistoryResponse(user_id=user_id, entries=entries)


# ─── GET /audit ───────────────────────────────────────────────────────────────

@router.get("/audit", response_model=AuditResponse)
async def get_audit(limit: int = Query(50)):
    """Return audit log (judges view)."""
    raw     = gcp.get_audit_log(limit)
    entries = [
        AuditEntry(
            timestamp=e["timestamp"],
            event_type=e["event_type"],
            user_id=e["user_id"],
            model_version=e["model_version"],
            band=e["band"],
            top_factors=e["top_factors"],
            explanation_id=e["explanation_id"],
        )
        for e in raw
    ]
    return AuditResponse(entries=entries)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _build_feature_vector(doc_ids: list[str]) -> list[float]:
    """
    Build a 12-dimensional feature vector from uploaded documents.
    In local mode this is a heuristic from the extracted entity values.
    In production this would be BigQuery SQL computed features.
    """
    totals: dict[str, float] = {
        "payment_consistency": 0.0,
        "income_stability":    0.0,
        "spending_discipline": 0.0,
        "digital_footprint":   0.0,
        "rental_reliability":  0.0,
    }
    n_docs = 0
    for did in doc_ids:
        doc = _doc_store.get(did) or gcp.get_document(did)
        if not doc:
            continue
        entities = {e["field"]: e for e in doc.get("entities", [])}
        amt = _parse_amount(entities.get("amount", {}).get("value", "0"))
        conf_avg = (
            sum(e.get("confidence", 0.8) for e in doc.get("entities", [])) /
            max(len(doc.get("entities", [])), 1)
        )
        dt = doc.get("doc_type", "")
        if dt in ("electricity_bill", "water_bill"):
            totals["payment_consistency"] += conf_avg
        elif dt == "rent_receipt":
            totals["rental_reliability"]  += conf_avg
        elif dt == "upi_screenshot":
            totals["digital_footprint"]   += min(amt / 5000.0, 1.0)
        totals["income_stability"]    += conf_avg * 0.6
        totals["spending_discipline"] += conf_avg * 0.5
        n_docs += 1

    n = max(n_docs, 1)
    base = [
        min(totals["payment_consistency"] / n, 1.0),
        min(totals["income_stability"]    / n, 1.0),
        min(totals["spending_discipline"] / n, 1.0),
        min(totals["digital_footprint"]   / n, 1.0),
        min(totals["rental_reliability"]  / n, 1.0),
    ]
    # Remaining 7 model inputs, derived from the 5 above with the same
    # local heuristic (order matches ml/train.py FEATURE_NAMES):
    # pay_streak, avg_pay_ratio, bill_variance, inflow_regularity,
    # max_pay_gap, limit_utilization, months_data.
    pc, inc, spend = base[0], base[1], base[2]
    derived = [
        pc,                      # pay_streak
        spend,                   # avg_pay_ratio
        1.0 - inc,               # bill_variance
        inc,                     # inflow_regularity
        1.0 - pc,                # max_pay_gap (higher = worse)
        0.3,                     # limit_utilization: no credit line, neutral
        min(n_docs / 6.0, 1.0),  # months_data
    ]
    return base + derived


def _parse_amount(val: str) -> float:
    try:
        return float(val.replace(",", "").replace("INR", "").strip())
    except (ValueError, AttributeError):
        return 0.0
