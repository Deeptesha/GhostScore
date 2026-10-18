"""
GCP client interfaces with MODE=local|gcp switch.

Every GCP call is wrapped behind a Python function.  When GHOSTSCORE_MODE=local
the function uses a deterministic stub so the app works without credentials.
Stubs are clearly labelled with ⚙ STUB comments.
"""
from __future__ import annotations
import os, uuid, json, math
from typing import Any


# ─── Document AI ─────────────────────────────────────────────────────────────

def process_document(file_bytes: bytes, doc_type: str) -> dict[str, Any]:
    """
    Submit a file to Document AI and return structured entities.
    GCP:   calls the Document AI REST/gRPC API.
    LOCAL: ⚙ STUB — returns plausible synthetic fields.
    """
    from app.config import MODE
    if MODE == "gcp":
        return _gcp_process_document(file_bytes, doc_type)
    return _stub_process_document(doc_type)


def _stub_process_document(doc_type: str) -> dict[str, Any]:
    """⚙ STUB — synthetic Document AI output."""
    stubs = {
        "electricity_bill": [
            {"field": "payer_name",  "value": "Priya Sharma",  "confidence": 0.97},
            {"field": "amount",      "value": "843.00",        "confidence": 0.95},
            {"field": "currency",    "value": "INR",           "confidence": 0.99},
            {"field": "due_date",    "value": "2024-11-15",    "confidence": 0.92},
            {"field": "paid_date",   "value": "2024-11-12",    "confidence": 0.91},
            {"field": "period",      "value": "Oct 2024",      "confidence": 0.98},
            {"field": "biller",      "value": "MSEDCL",        "confidence": 0.96},
        ],
        "rent_receipt": [
            {"field": "payer_name",  "value": "Priya Sharma",  "confidence": 0.95},
            {"field": "amount",      "value": "5500.00",       "confidence": 0.93},
            {"field": "currency",    "value": "INR",           "confidence": 0.99},
            {"field": "due_date",    "value": "2024-11-01",    "confidence": 0.88},
            {"field": "paid_date",   "value": "2024-11-01",    "confidence": 0.90},
            {"field": "period",      "value": "Nov 2024",      "confidence": 0.97},
            {"field": "biller",      "value": "Landlord Patil","confidence": 0.85},
        ],
        "upi_screenshot": [
            {"field": "payer_name",  "value": "Priya Sharma",  "confidence": 0.92},
            {"field": "amount",      "value": "1200.00",       "confidence": 0.90},
            {"field": "currency",    "value": "INR",           "confidence": 0.99},
            {"field": "paid_date",   "value": "2024-11-10",    "confidence": 0.89},
            {"field": "period",      "value": "Nov 2024",      "confidence": 0.94},
            {"field": "biller",      "value": "PhonePe/UPI",   "confidence": 0.88},
        ],
    }
    entities = stubs.get(doc_type, stubs["electricity_bill"])
    return {"entities": entities, "doc_id": str(uuid.uuid4()), "stub": True}


def _gcp_process_document(file_bytes: bytes, doc_type: str) -> dict[str, Any]:
    """GCP — calls Document AI.  Requires GOOGLE_APPLICATION_CREDENTIALS."""
    try:
        from google.cloud import documentai_v1 as documentai
        from app.config import GCP_PROJECT, GCP_REGION
        processor_map = {
            "electricity_bill": os.getenv("DAI_UTILITY_PROCESSOR", ""),
            "rent_receipt":     os.getenv("DAI_CUSTOM_PROCESSOR", ""),
            "upi_screenshot":   os.getenv("DAI_FORM_PROCESSOR", ""),
        }
        processor_id = processor_map.get(doc_type, processor_map["electricity_bill"])
        client = documentai.DocumentProcessorServiceClient()
        name   = client.processor_path(GCP_PROJECT, GCP_REGION, processor_id)
        raw    = documentai.RawDocument(content=file_bytes, mime_type="application/pdf")
        req    = documentai.ProcessRequest(name=name, raw_document=raw)
        result = client.process_document(request=req)
        doc    = result.document
        entities = [
            {"field": e.type_, "value": e.mention_text, "confidence": round(e.confidence, 3)}
            for e in doc.entities
        ]
        return {"entities": entities, "doc_id": str(uuid.uuid4()), "stub": False}
    except Exception as exc:
        raise RuntimeError(f"Document AI error: {exc}") from exc


# ─── Vertex AI Scoring ───────────────────────────────────────────────────────

def score_features(feature_vector: list[float]) -> dict[str, Any]:
    """
    Score a feature vector.
    GCP:   calls the Vertex AI online-prediction endpoint.
    LOCAL: ⚙ STUB — uses the locally trained sklearn GradientBoosting model.
    """
    from app.config import MODE
    if MODE == "gcp":
        return _gcp_score(feature_vector)
    return _local_score(feature_vector)


def _local_score(feature_vector: list[float]) -> dict[str, Any]:
    """⚙ LOCAL — uses the sklearn pipeline trained on UCI data."""
    import joblib, numpy as np
    import pandas as pd
    from pathlib import Path
    model_path = Path(__file__).parents[3] / "ml" / "artifacts" / "model.joblib"
    if not model_path.exists():
        # Return a deterministic stub if model hasn't been trained yet
        return _deterministic_score_stub(feature_vector)
    pipe = joblib.load(model_path)
    feat_names = [
        "payment_consistency", "income_stability", "spending_discipline",
        "digital_footprint", "rental_reliability", "pay_streak",
        "avg_pay_ratio", "bill_variance", "inflow_regularity",
        "max_pay_gap", "limit_utilization", "months_data",
    ]
    arr = np.array(feature_vector, dtype=float).reshape(1, -1)
    X   = pd.DataFrame(arr, columns=feat_names)
    prob = pipe.predict_proba(X)[0]   # probability of default (class 1)
    default_prob = float(prob[1])
    score, band  = _prob_to_score_band(default_prob)
    importances  = _compute_local_importances(pipe, X)
    return {
        "score": score,
        "band": band,
        "band_confidence": round(1.0 - default_prob, 3),
        "feature_importances": importances,
        "stub": False,
        "model": "local-uci-gradient-boosting",
    }


def _deterministic_score_stub(feature_vector: list[float]) -> dict[str, Any]:
    """⚙ STUB — deterministic score before model is trained."""
    avg = sum(feature_vector) / max(len(feature_vector), 1)
    # Map avg of normalized features to a rough score
    score = int(300 + min(avg, 1.0) * 550)
    band  = _score_to_band(score)
    return {
        "score": score,
        "band": band,
        "band_confidence": 0.72,
        "feature_importances": {
            "payment_consistency": 0.35,
            "income_stability":    0.22,
            "rental_reliability":  0.18,
            "spending_discipline": 0.15,
            "digital_footprint":   0.10,
        },
        "stub": True,
        "model": "deterministic-stub",
    }


def _gcp_score(feature_vector: list[float]) -> dict[str, Any]:
    """GCP — Vertex AI online prediction."""
    try:
        from google.cloud import aiplatform
        from app.config import GCP_PROJECT, GCP_REGION, VERTEX_ENDPOINT
        aiplatform.init(project=GCP_PROJECT, location=GCP_REGION)
        endpoint = aiplatform.Endpoint(VERTEX_ENDPOINT)
        result   = endpoint.predict(instances=[{"feature_vector": feature_vector}])
        pred     = result.predictions[0]
        score    = int(pred.get("score", 0))
        band     = pred.get("band", _score_to_band(score))
        return {
            "score": score,
            "band": band,
            "band_confidence": pred.get("confidence", 0.0),
            "feature_importances": pred.get("importances", {}),
            "stub": False,
            "model": "vertex-ai",
        }
    except Exception as exc:
        raise RuntimeError(f"Vertex AI scoring error: {exc}") from exc


def run_what_if(feature_vector: list[float], action_id: str) -> dict[str, Any]:
    """
    Re-score with a hypothetical feature change (what-if analysis).
    Numbers come from here; Gemini only reads and phrases them.
    """
    from app.config import MODE
    delta_map = {
        "add_2mo_upi":     {"payment_consistency": 0.08, "digital_footprint": 0.05},
        "add_rent_docs":   {"rental_reliability": 0.12},
        "reduce_variance": {"income_stability": 0.07},
        "add_utility_6mo": {"payment_consistency": 0.10},
    }
    modifications = delta_map.get(action_id, {})
    feature_names = [
        "payment_consistency", "income_stability", "spending_discipline",
        "digital_footprint", "rental_reliability", "pay_streak",
        "avg_pay_ratio", "bill_variance", "inflow_regularity",
        "max_pay_gap", "limit_utilization", "months_data",
    ]
    modified = list(feature_vector)
    for i, name in enumerate(feature_names):
        if name in modifications and i < len(modified):
            modified[i] = min(1.0, modified[i] + modifications[name])

    base = score_features(feature_vector)
    new  = score_features(modified)
    return {
        "action_id":   action_id,
        "base_score":  base["score"],
        "new_score":   new["score"],
        "new_band":    new["band"],
        "score_delta": new["score"] - base["score"],
        "effort":      _effort_for_action(action_id),
    }


# ─── Vertex AI Search (policy retrieval) ─────────────────────────────────────

def search_policy(query: str, top_k: int = 4) -> list[dict[str, Any]]:
    """
    Retrieve policy passages.
    GCP:   calls Vertex AI Search / Agent Builder.
    LOCAL: ⚙ STUB — returns static RBI/PMMY passages.
    """
    from app.config import MODE
    if MODE == "gcp":
        return _gcp_search(query, top_k)
    return _stub_search(query)


def _stub_search(query: str) -> list[dict[str, Any]]:
    """⚙ STUB — static curated policy passages."""
    passages = [
        {
            "id": "P1",
            "source": "PMMY Guidelines 2023",
            "text": "Mudra Shishu loans cover amounts up to INR 50,000 for non-corporate, non-farm micro enterprises without collateral.",
        },
        {
            "id": "P2",
            "source": "PMMY Guidelines 2023",
            "text": "Mudra Kishore loans cover INR 50,001 to INR 5,00,000. The borrower must demonstrate income-generating activity.",
        },
        {
            "id": "P3",
            "source": "RBI Master Circular — Microfinance 2023",
            "text": "Microfinance institutions may lend to borrowers with annual household income up to INR 3,00,000 in rural areas and INR 3,60,000 in urban areas.",
        },
        {
            "id": "P4",
            "source": "RBI Master Circular — Microfinance 2023",
            "text": "Total loan obligations of a microfinance borrower must not exceed 50% of the monthly household income.",
        },
        {
            "id": "P5",
            "source": "NPCI UPI FAQ 2024",
            "text": "UPI transaction history can serve as proof of digital payment behavior for informal sector participants applying for credit.",
        },
    ]
    q = query.lower()
    if "mudra" in q or "loan" in q or "eligible" in q:
        return passages[:4]
    if "upi" in q or "transaction" in q:
        return [passages[4]] + passages[:2]
    return passages[:3]


def _gcp_search(query: str, top_k: int) -> list[dict[str, Any]]:
    """GCP — Vertex AI Search / Agent Builder."""
    try:
        from google.cloud import discoveryengine_v1 as discoveryengine
        from app.config import GCP_PROJECT
        datastore_id = os.getenv("SEARCH_DATASTORE_ID", "ghostscore-policy")
        client  = discoveryengine.SearchServiceClient()
        request = discoveryengine.SearchRequest(
            serving_config=client.serving_config_path(
                GCP_PROJECT, "global", datastore_id, "default_config"
            ),
            query=query,
            page_size=top_k,
        )
        response = client.search(request=request)
        results  = []
        for i, r in enumerate(response.results):
            doc  = r.document
            data = dict(doc.struct_data)
            results.append({
                "id":     f"P{i+1}",
                "source": data.get("source", "GCP Search"),
                "text":   data.get("text", ""),
            })
        return results
    except Exception as exc:
        raise RuntimeError(f"Vertex AI Search error: {exc}") from exc


# ─── Pub/Sub ─────────────────────────────────────────────────────────────────

def publish_event(event: dict[str, Any]) -> str:
    """
    Publish a scoring event to Pub/Sub.
    GCP:   calls the Pub/Sub publish API.
    LOCAL: ⚙ STUB — logs the event and returns a fake message-id.
    """
    from app.config import MODE
    if MODE == "gcp":
        return _gcp_publish(event)
    import json
    print(f"⚙ STUB Pub/Sub event: {json.dumps(event, default=str)}")
    return f"stub-msg-{uuid.uuid4()}"


def _gcp_publish(event: dict[str, Any]) -> str:
    """GCP — Pub/Sub publisher."""
    try:
        from google.cloud import pubsub_v1
        from app.config import GCP_PROJECT, PUBSUB_TOPIC
        import json
        publisher = pubsub_v1.PublisherClient()
        topic     = publisher.topic_path(GCP_PROJECT, PUBSUB_TOPIC)
        future    = publisher.publish(topic, json.dumps(event, default=str).encode())
        return future.result()
    except Exception as exc:
        raise RuntimeError(f"Pub/Sub error: {exc}") from exc


# ─── Cloud SQL (application state) ───────────────────────────────────────────

# In local mode we use an in-memory dict to simulate the database.
_local_db: dict[str, Any] = {
    "score_history": {},
    "documents": {},
    "audit_log": [],
    "improvement_plans": {},
}


def save_score(user_id: str, score: int, band: str) -> None:
    """⚙ STUB (local) or Cloud SQL INSERT (gcp)."""
    import datetime
    entry = {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "score": score,
        "band":  band,
        "event": "score_computed",
    }
    _local_db["score_history"].setdefault(user_id, []).append(entry)


def get_score_history(user_id: str) -> list[dict[str, Any]]:
    """⚙ STUB (local) or Cloud SQL SELECT (gcp)."""
    return _local_db["score_history"].get(user_id, [])


def save_document(doc_id: str, meta: dict[str, Any]) -> None:
    _local_db["documents"][doc_id] = meta


def get_document(doc_id: str) -> dict[str, Any] | None:
    return _local_db["documents"].get(doc_id)


def append_audit(entry: dict[str, Any]) -> None:
    _local_db["audit_log"].append(entry)


def get_audit_log(limit: int = 50) -> list[dict[str, Any]]:
    return _local_db["audit_log"][-limit:]


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _prob_to_score_band(default_prob: float):
    score = int(850 - default_prob * 550)
    score = max(300, min(850, score))
    return score, _score_to_band(score)


def _score_to_band(score: int) -> str:
    # Cut-offs match the UI scale: 300-579 / 580-669 / 670-739 / 740-850
    if score < 580:   return "Poor"
    if score < 670:   return "Fair"
    if score < 740:   return "Good"
    return "Excellent"


def _compute_local_importances(pipe, X):
    try:
        model = pipe.named_steps.get("clf") or pipe.steps[-1][1]
        imp   = model.feature_importances_
        names = [
            "payment_consistency", "income_stability", "spending_discipline",
            "digital_footprint", "rental_reliability", "pay_streak",
            "avg_pay_ratio", "bill_variance", "inflow_regularity",
            "max_pay_gap", "limit_utilization", "months_data",
        ]
        total = sum(imp) or 1.0
        return {names[i]: round(float(imp[i]) / total, 4) for i in range(len(imp))}
    except Exception:
        return {
            "payment_consistency": 0.35,
            "income_stability":    0.22,
            "rental_reliability":  0.18,
            "spending_discipline": 0.15,
            "digital_footprint":   0.10,
        }


def _effort_for_action(action_id: str) -> str:
    mapping = {
        "add_2mo_upi":     "low",
        "add_rent_docs":   "low",
        "reduce_variance": "high",
        "add_utility_6mo": "medium",
    }
    return mapping.get(action_id, "medium")
