"""
Pydantic models for the GhostScore API contract (Section 16 of blueprint).
"""
from __future__ import annotations
from typing import Any, Optional
from pydantic import BaseModel


# ── /documents ──────────────────────────────────────────────────────────────

class DocumentUploadResponse(BaseModel):
    doc_id: str
    status: str                    # "processing" | "done" | "error"
    doc_type: str
    filename: str


class DocumentReviewResponse(BaseModel):
    doc_id: str
    normalized: dict[str, Any]
    status: str                    # "accepted" | "needs_review" | "rejected_unreadable"
    flags: list[dict[str, Any]]
    applicant_message: str


# ── /score ───────────────────────────────────────────────────────────────────

class ScoreRequest(BaseModel):
    user_id: str
    doc_ids: list[str]
    language: Optional[str] = "en"


class ScoreResponse(BaseModel):
    score: int
    band: str                      # "Poor" | "Fair" | "Good" | "Excellent"
    band_confidence: float
    headline: str
    what_helped: list[dict[str, Any]]
    what_held_back: list[dict[str, Any]]
    confidence_note: str
    disclaimer: str
    compliance_pass: bool


# ── /plan ────────────────────────────────────────────────────────────────────

class PlanResponse(BaseModel):
    user_id: str
    actions: list[dict[str, Any]]
    compliance_pass: bool


# ── /options ─────────────────────────────────────────────────────────────────

class OptionsResponse(BaseModel):
    user_id: str
    products: list[dict[str, Any]]
    cannot_confirm: list[str]
    compliance_pass: bool


# ── /chat ────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    user_id: str
    message: str
    language: Optional[str] = "en"


class ChatResponse(BaseModel):
    reply: str
    tool_calls_made: list[str]
    sources: list[str]


# ── /history ─────────────────────────────────────────────────────────────────

class HistoryEntry(BaseModel):
    timestamp: str
    score: int
    band: str
    event: Optional[str] = None


class HistoryResponse(BaseModel):
    user_id: str
    entries: list[HistoryEntry]


# ── /audit ───────────────────────────────────────────────────────────────────

class AuditEntry(BaseModel):
    timestamp: str
    event_type: str
    user_id: str
    model_version: str
    band: str
    top_factors: list[str]
    explanation_id: str


class AuditResponse(BaseModel):
    entries: list[AuditEntry]
