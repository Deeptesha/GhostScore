"""
GhostScore Gemini Prompt Chain — P1 through P7.

Design rule (Section 13 of blueprint):
  Gemini NEVER calculates scores and NEVER invents numbers.
  All numeric deltas and scores come from Vertex AI (gcp.run_what_if /
  gcp.score_features).  Gemini only validates, explains and phrases them.

In local mode every call returns a deterministic JSON stub labelled ⚙ STUB.
"""
from __future__ import annotations
import json
from typing import Any

from app.config import MODE, GCP_PROJECT, GCP_REGION


# ─── Gemini client factory ────────────────────────────────────────────────────

def _gemini_generate(system_prompt: str, user_content: str,
                     temperature: float = 0.2,
                     response_mime_type: str = "application/json") -> str:
    """
    Call Gemini via Vertex AI SDK.
    LOCAL: ⚙ STUB — returns the user_content dict with a stub flag.
    """
    if MODE == "local":
        # ⚙ STUB: echo back a stub marker so tests can verify no numbers invented
        return json.dumps({"_stub": True, "_input": json.loads(user_content)})
    try:
        import vertexai
        from vertexai.generative_models import GenerativeModel, GenerationConfig
        vertexai.init(project=GCP_PROJECT, location=GCP_REGION)
        model = GenerativeModel(
            "gemini-1.5-pro",
            system_instruction=system_prompt,
        )
        config = GenerationConfig(
            temperature=temperature,
            response_mime_type=response_mime_type,
        )
        response = model.generate_content(user_content, generation_config=config)
        return response.text
    except Exception as exc:
        raise RuntimeError(f"Gemini API error: {exc}") from exc


# ─── P1 — Intake Verifier ─────────────────────────────────────────────────────

SYSTEM_P1 = """You are a document-intake analyst for a credit-scoring service. \
You receive structured output from Document AI, the applicant's declared details \
and the document type. Your job is to normalize fields and flag inconsistencies.

Rules:
- Use only the data provided; use null for a missing value, never guess.
- Never accuse anyone of fraud; use status "needs_review" with a neutral, \
  factual reason.
- Flag: field confidence below {CONF_THRESHOLD}, impossible or out-of-sequence \
  billing dates, amounts inconsistent with other months, duplicate documents, \
  and a payer name that differs from the declared name.
- Output valid JSON matching the schema, with no prose outside the JSON.

Output schema:
{
  "normalized": {"payer_name":"","amount":"","currency":"","due_date":"",
                 "paid_date":"","period":"","biller_or_landlord":""},
  "status": "accepted|needs_review|rejected_unreadable",
  "flags": [{"code":"","field":"","plain_reason":""}],
  "applicant_message": "one neutral sentence on what to re-upload, if anything"
}"""


def p1_intake_verifier(doc_type: str, declared_name: str,
                       entities: list[dict[str, Any]],
                       conf_threshold: float = 0.75) -> dict[str, Any]:
    """
    P1 — normalize and quality-check Document AI output.
    Returns accepted/needs_review/rejected_unreadable with flags.
    """
    system = SYSTEM_P1.replace("{CONF_THRESHOLD}", str(conf_threshold))
    user   = json.dumps({
        "doc_type":           doc_type,
        "declared_name":      declared_name,
        "document_ai_entities": entities,
    })
    raw    = _gemini_generate(system, user, temperature=0.1)
    result = _safe_parse(raw)

    if result.get("_stub"):
        # ⚙ STUB: build a deterministic P1 response from the entity list
        return _stub_p1(entities, declared_name, conf_threshold)
    return result


def _stub_p1(entities: list[dict], declared_name: str, threshold: float) -> dict:
    """⚙ STUB P1 — deterministic intake verification."""
    normalized: dict[str, Any] = {
        "payer_name": None, "amount": None, "currency": None,
        "due_date": None, "paid_date": None, "period": None,
        "biller_or_landlord": None,
    }
    flags = []
    field_map = {
        "payer_name": "payer_name", "amount": "amount", "currency": "currency",
        "due_date": "due_date", "paid_date": "paid_date", "period": "period",
        "biller": "biller_or_landlord", "biller_or_landlord": "biller_or_landlord",
    }
    for e in entities:
        field = e.get("field", "")
        value = e.get("value", "")
        conf  = e.get("confidence", 1.0)
        mapped = field_map.get(field)
        if mapped:
            normalized[mapped] = value
        if conf < threshold:
            flags.append({
                "code": "LOW_CONFIDENCE",
                "field": field,
                "plain_reason": f"Confidence {conf:.0%} is below threshold {threshold:.0%}.",
            })

    payer = normalized.get("payer_name") or ""
    if declared_name and payer and declared_name.lower() not in payer.lower():
        flags.append({
            "code": "NAME_MISMATCH",
            "field": "payer_name",
            "plain_reason": (
                f"The name on the document ({payer!r}) does not "
                f"match the declared name ({declared_name!r}). "
                "Please check and re-upload if this is incorrect."
            ),
        })

    status = "needs_review" if flags else "accepted"
    msg    = ("No action needed." if not flags
               else "Please re-upload the document with clearer details.")
    return {
        "normalized": normalized,
        "status": status,
        "flags": flags,
        "applicant_message": msg,
    }


# ─── P2 — Score Explainer ─────────────────────────────────────────────────────

SYSTEM_P2 = """You explain a credit-band result to a first-time borrower with \
no credit history. Be warm, direct and non-judgmental. Write at about grade 6 \
reading level. Avoid jargon.

Rules:
- Use ONLY the numbers and factors in the input; do not add factors or figures.
- Never mention or infer religion, caste, gender, age or location as a reason.
- Do not promise a loan or approval.
- State plainly if data coverage is thin, because that lowers confidence.
- Output JSON only.

Output schema:
{
  "headline": "max 12 words",
  "what_helped": [{"feature":"","plain_label":"","contribution":0.0}],
  "what_held_back": [{"feature":"","plain_label":"","contribution":0.0}],
  "confidence_note": "one sentence"
}"""


def p2_score_explainer(band: str, band_confidence: float,
                        feature_importances: dict[str, float],
                        data_coverage: dict[str, Any],
                        language: str = "en") -> dict[str, Any]:
    """P2 — explain score band to applicant in plain language."""
    sorted_feats = sorted(feature_importances.items(), key=lambda x: -x[1])
    pos = [{"feature": k, "plain_label": _plain_label(k), "contribution": v}
           for k, v in sorted_feats[:3] if v > 0.1]
    neg = [{"feature": k, "plain_label": _plain_label(k), "contribution": v}
           for k, v in sorted_feats[-2:] if v < 0.15]

    user = json.dumps({
        "band": band,
        "band_confidence": band_confidence,
        "positive_factors": pos[:2],
        "negative_factors": neg[:2],
        "data_coverage": data_coverage,
    })
    raw    = _gemini_generate(SYSTEM_P2, user, temperature=0.5)
    result = _safe_parse(raw)

    if result.get("_stub"):
        return _stub_p2(band, band_confidence, pos, neg)
    return result


def _stub_p2(band, conf, pos, neg) -> dict:
    """⚙ STUB P2."""
    top_pos = pos[0]["plain_label"] if pos else "payment history"
    top_neg = neg[0]["plain_label"] if neg else "income stability"
    return {
        "headline": f"Your payments earned you a {band} credit band.",
        "what_helped": pos[:2],
        "what_held_back": neg[:2],
        "confidence_note": (
            f"This is a model estimate with {conf:.0%} confidence, "
            "not a lender decision. More months of data would increase accuracy."
        ),
    }


# ─── P3 — Improvement Planner ─────────────────────────────────────────────────

SYSTEM_P3 = """You turn tested what-if results into a short action plan. \
The backend has already re-scored the applicant for each action. \
You choose and phrase actions.

Rules:
- Pick the 1-3 actions with the largest score_delta that the user can actually do.
- State a point change ONLY if it appears in the input; never estimate.
- Each action must be concrete (what to upload or do, and by when).
- Output JSON only.

Output schema:
{
  "actions": [
    {"action_id":"","title":"","why_it_helps":"",
     "steps":[""],"expected_change":"copied from score_delta"}
  ]
}"""


def p3_improvement_planner(what_if_results: list[dict[str, Any]]) -> dict[str, Any]:
    """
    P3 — build an improvement plan from what-if scores.
    score_delta values MUST come from Vertex AI what-if re-scores.
    Gemini picks and phrases; it does NOT invent numbers.
    """
    user   = json.dumps({"what_if_results": what_if_results})
    raw    = _gemini_generate(SYSTEM_P3, user, temperature=0.5)
    result = _safe_parse(raw)

    if result.get("_stub"):
        return _stub_p3(what_if_results)
    return result


def _stub_p3(what_if_results: list[dict]) -> dict:
    """⚙ STUB P3 — picks the top 2 by score_delta."""
    sorted_actions = sorted(what_if_results, key=lambda x: -x.get("score_delta", 0))
    actions = []
    for r in sorted_actions[:2]:
        delta = r.get("score_delta", 0)
        actions.append({
            "action_id":       r["action_id"],
            "title":           _action_title(r["action_id"]),
            "why_it_helps":    _action_why(r["action_id"]),
            "steps":           _action_steps(r["action_id"]),
            "expected_change": f"+{delta} points" if delta > 0 else f"{delta} points",
        })
    return {"actions": actions}


# ─── P4 — Grounded Eligibility ────────────────────────────────────────────────

SYSTEM_P4 = """You match an applicant to financial products using ONLY the \
retrieved policy passages. If the passages do not support an answer, say you \
cannot confirm.

Rules:
- Cite the passage id for every claim, for example [P2].
- Use "may be eligible", never "you qualify" or "you will get".
- Do not state loan limits, rates or criteria from memory; quote the passage.
- State that the final decision belongs to the lender.
- Output JSON only.

Output schema:
{
  "products": [
    {"name":"","why_it_may_fit":"","limits_from_passage":"","citations":[""]}
  ],
  "cannot_confirm": ["topics not covered by the passages"]
}"""


def p4_grounded_eligibility(band: str, occupation: str,
                              monthly_income_range: str,
                              passages: list[dict[str, Any]]) -> dict[str, Any]:
    """P4 — map applicant to loan products using only retrieved passages."""
    user   = json.dumps({
        "band": band,
        "declared_occupation": occupation,
        "monthly_income_range": monthly_income_range,
        "passages": passages,
    })
    raw    = _gemini_generate(SYSTEM_P4, user, temperature=0.2)
    result = _safe_parse(raw)

    if result.get("_stub"):
        return _stub_p4(band, passages)
    return result


def _stub_p4(band: str, passages: list[dict]) -> dict:
    """⚙ STUB P4."""
    products = []
    if band in ("Fair", "Good", "Excellent"):
        products.append({
            "name": "Mudra Shishu",
            "why_it_may_fit": "You may be eligible for a Mudra Shishu loan [P1].",
            "limits_from_passage": "Up to INR 50,000 without collateral [P1].",
            "citations": ["P1"],
        })
    if band in ("Good", "Excellent"):
        products.append({
            "name": "Mudra Kishore",
            "why_it_may_fit": "With a Good or better band you may be eligible for Mudra Kishore [P2].",
            "limits_from_passage": "INR 50,001 to INR 5,00,000 with income-generating activity evidence [P2].",
            "citations": ["P2"],
        })
    return {
        "products": products,
        "cannot_confirm": [] if products else ["No matching product found in the retrieved passages."],
    }


# ─── P5 — Compliance Reviewer ─────────────────────────────────────────────────

SYSTEM_P5 = """You are a strict reviewer. You receive draft outputs from the \
explainer, planner and eligibility steps, plus the source data they were based on. \
Check the draft against the checklist and fix anything that fails.

Checklist:
1. Every number in the draft appears in the source data.
2. No promise or guarantee of approval, rate or amount.
3. No protected attribute (religion, caste, gender, age, location) used as a reason.
4. Every eligibility claim has a citation.
5. Tone is respectful and does not blame the applicant.
6. The text states the result is a model estimate, not a lender decision.

Output: {"pass": true|false, "failed_checks": [...], "corrected_draft": {...}}"""


def p5_compliance_reviewer(drafts: dict[str, Any],
                             source_data: dict[str, Any]) -> dict[str, Any]:
    """P5 — compliance gate before response reaches the UI."""
    user   = json.dumps({"drafts": drafts, "source_data": source_data})
    raw    = _gemini_generate(SYSTEM_P5, user, temperature=0.1)
    result = _safe_parse(raw)

    if result.get("_stub"):
        return _stub_p5(drafts)
    return result


def _stub_p5(drafts: dict) -> dict:
    """⚙ STUB P5 — always passes; a real implementation would verify each check."""
    return {
        "pass": True,
        "failed_checks": [],
        "corrected_draft": drafts,
    }


# ─── P6 — Chat Advisor ────────────────────────────────────────────────────────

SYSTEM_P6 = """You are GhostScore's credit advisor. You help people understand \
their score and improve it. You are not a lender and you do not decide loans.

Tools available: get_score_summary(user_id), run_what_if(user_id, action_id), \
search_policy(query), request_human_review(reason).

Behavior:
- For questions about the user's own score, call get_score_summary first.
- For what-if questions, call run_what_if and quote only the returned delta.
- For loan or policy questions, call search_policy and answer only from results.
- If a tool returns nothing useful, say so; do not guess.
- Refuse requests to game the score; offer legitimate steps instead.
- For complaints, call request_human_review.
- Reply in the user's language, under 80 words, end with one next step."""


def p6_chat_advisor(user_id: str, message: str, language: str,
                     tool_results: dict[str, Any]) -> dict[str, Any]:
    """
    P6 — conversational advisor with tool results pre-fetched.
    Tool results (score, what-if deltas, policy passages) are computed by the
    backend before this call; Gemini reads and phrases them only.
    """
    user   = json.dumps({
        "user_id":      user_id,
        "message":      message,
        "language":     language,
        "tool_results": tool_results,
    })
    raw    = _gemini_generate(SYSTEM_P6, user, temperature=0.5,
                               response_mime_type="text/plain")

    if MODE == "local":
        return _stub_p6(message, tool_results)
    return {"reply": raw, "tool_calls_made": list(tool_results.keys()), "sources": []}


def _stub_p6(message: str, tool_results: dict) -> dict:
    """⚙ STUB P6."""
    score_info = tool_results.get("score_summary", {})
    band       = score_info.get("band", "Fair")
    score      = score_info.get("score", 640)
    reply      = (
        f"⚙ [STUB] Your current band is {band} (score {score}). "
        "To improve, consider uploading more months of utility bills or UPI history. "
        "Would you like to see what-if estimates for specific actions?"
    )
    return {
        "reply": reply,
        "tool_calls_made": list(tool_results.keys()),
        "sources": [],
    }


# ─── P7 — Localizer ───────────────────────────────────────────────────────────

SYSTEM_P7_TEMPLATE = """Translate the following text into {language} for a reader \
with limited financial literacy. Keep all numbers, rupee amounts, scheme names \
(such as Mudra Shishu) and citation tags exactly unchanged. Use simple, \
spoken-style wording. Return only the translation."""

SUPPORTED_LANGUAGES = {"en": "English", "hi": "Hindi", "mr": "Marathi"}


def p7_localizer(text: str, language: str) -> str:
    """P7 — translate the assembled response into the user's language."""
    if language == "en":
        return text   # no-op for English
    lang_name = SUPPORTED_LANGUAGES.get(language, language)
    system    = SYSTEM_P7_TEMPLATE.replace("{language}", lang_name)
    raw       = _gemini_generate(system, json.dumps({"text": text}),
                                  temperature=0.3,
                                  response_mime_type="text/plain")
    if MODE == "local":
        # ⚙ LOCAL: fixed translation table for known stub strings only.
        from app.i18n import tr
        return tr(text, language)
    return raw


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _safe_parse(raw: str) -> dict[str, Any]:
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {"_parse_error": True, "_raw": raw}


_PLAIN_LABELS = {
    "payment_consistency": "Regular bill payments",
    "income_stability":    "Steady monthly income",
    "spending_discipline": "Responsible spending",
    "digital_footprint":   "Digital payment activity",
    "rental_reliability":  "Consistent rent payments",
    "pay_streak":          "Recent on-time streak",
    "avg_pay_ratio":       "Share of bills paid in full",
    "bill_variance":       "Bill amount swings",
    "inflow_regularity":   "Regular money coming in",
    "max_pay_gap":         "Longest payment delay",
    "limit_utilization":   "Credit line usage",
    "months_data":         "Months of history provided",
}


def _plain_label(feature: str) -> str:
    return _PLAIN_LABELS.get(feature, feature.replace("_", " ").title())


def _action_title(action_id: str) -> str:
    titles = {
        "add_2mo_upi":     "Add 2 more months of UPI history",
        "add_rent_docs":   "Upload missing rent receipts",
        "reduce_variance": "Show more consistent monthly income",
        "add_utility_6mo": "Upload 6 months of utility bills",
    }
    return titles.get(action_id, action_id.replace("_", " ").title())


def _action_why(action_id: str) -> str:
    reasons = {
        "add_2mo_upi":     "More UPI transactions confirm your digital payment habit.",
        "add_rent_docs":   "Rental receipts prove consistent housing-expense reliability.",
        "reduce_variance": "Lower income swings signal a more predictable repayment capacity.",
        "add_utility_6mo": "Six months of utility bills gives the model stronger payment data.",
    }
    return reasons.get(action_id, "This action improves a key feature in your score.")


def _action_steps(action_id: str) -> list[str]:
    steps = {
        "add_2mo_upi":     ["Open your UPI app", "Export or screenshot the last 2 months", "Upload on the Documents screen"],
        "add_rent_docs":   ["Collect receipts from your landlord", "Photograph clearly", "Upload on the Documents screen"],
        "reduce_variance": ["Consider stable side income sources", "Keep monthly inflow more consistent over 3 months"],
        "add_utility_6mo": ["Collect electricity/water bills for the last 6 months", "Upload on the Documents screen"],
    }
    return steps.get(action_id, ["Follow up with your GhostScore advisor."])
