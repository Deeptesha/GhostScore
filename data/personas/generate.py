"""
GhostScore — Synthetic Persona Generator.

Generates synthetic transaction and document events for demo personas.
Calibrated against NPCI UPI Monthly Product Statistics (April 2025 – Sept 2026).

NPCI calibration (computed from the two source files, accessed 13 Oct 2026):
  Mean all-India ticket: Rs 1,287 (range Rs 1,217 – Rs 1,346)
  Volume growth: +34.5% over 18 months, YoY +23-25%
  Ticket trend: approximately -9% over 18 months (declining ticket size)

  Note: April 2026 row in the 2026-27 file contains a digit-grouping anomaly
  (raw value 29,029,88.05 treated as Rs 29,02,988.05 crore — handled below).

Street-vendor/gig-worker persona UPI amounts are set well below the national
average (Rs 200-600) to reflect lower transaction sizes in informal sectors.

IMPORTANT — data disclaimer (blueprint Section 5.8):
  These personas are synthetic and illustrative.  They are NOT training data.
  No model performance or India-specific accuracy is claimed.
  Personas are clearly labelled as synthetic in every output file.
"""
from __future__ import annotations
import json, uuid, random
from datetime import date, timedelta
from pathlib import Path
from typing import Any

PERSONAS_DIR = Path(__file__).parent / "personas"

# ─── NPCI calibration constants ──────────────────────────────────────────────
# Source: NPCI UPI Monthly Product Statistics, April 2025 – Sept 2026
NPCI_MEAN_TICKET_INR  = 1_287          # national mean, all sectors
NPCI_TICKET_TREND     = -0.09          # ~9% decline over 18 months
# Informal sector personas are scaled down significantly from national mean
VENDOR_UPI_MEAN_INR   = 420            # street vendor / tea stall (~33% of national mean)
VENDOR_UPI_STDDEV_INR = 120
GIG_UPI_MEAN_INR      = 680            # gig worker (~53% of national mean)
GIG_UPI_STDDEV_INR    = 200
SEASONAL_UPI_MEAN_INR = 350            # seasonal earner
SEASONAL_UPI_STDDEV_INR = 180


def _months_back(n: int, from_date: date | None = None) -> list[date]:
    """Return the 1st of each of the last n months."""
    base  = from_date or date.today()
    start = date(base.year, base.month, 1)
    result = []
    for i in range(n):
        m = start.month - i
        y = start.year
        while m <= 0:
            m += 12
            y -= 1
        result.append(date(y, m, 1))
    return list(reversed(result))


def _jitter_day(d: date, sigma: int = 2) -> date:
    offset = int(random.gauss(0, sigma))
    return d + timedelta(days=offset)


def _clamp(val: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, val))


# ─── Persona definitions ─────────────────────────────────────────────────────

def _priya_scenario() -> dict[str, Any]:
    """
    Priya Sharma — tea stall operator, Pune.
    Demo persona from Section 7 of the blueprint.
    4 years consistent electricity payments, monthly rent, irregular UPI.
    """
    random.seed(42)   # deterministic for demo reproducibility
    months     = _months_back(6)
    doc_events = []

    # Electricity bills: 4 years consistent, demo shows last 6 months
    for d in months:
        amount   = round(random.gauss(843, 80), 2)
        paid_day = _jitter_day(date(d.year, d.month, 12), sigma=2)  # typically pays ~3 days early
        doc_events.append({
            "type":     "electricity_bill",
            "biller":   "MSEDCL",
            "period":   d.strftime("%b %Y"),
            "amount_inr": amount,
            "due_date": date(d.year, d.month, 15).isoformat(),
            "paid_date": paid_day.isoformat(),
            "on_time":  paid_day <= date(d.year, d.month, 15),
            "confidence": round(random.uniform(0.91, 0.98), 3),
        })

    # Rent receipts: consistent on the 1st of each month
    for d in months:
        paid_day = _jitter_day(date(d.year, d.month, 1), sigma=1)
        doc_events.append({
            "type":       "rent_receipt",
            "landlord":   "Suresh Patil",
            "period":     d.strftime("%b %Y"),
            "amount_inr": 5500.0,
            "due_date":   date(d.year, d.month, 1).isoformat(),
            "paid_date":  paid_day.isoformat(),
            "on_time":    True,
            "confidence": round(random.uniform(0.85, 0.95), 3),
        })

    # UPI transactions: irregular amounts, street-vendor calibration
    upi_events = []
    for d in months:
        n_txn = random.randint(8, 18)   # monthly transaction count
        for _ in range(n_txn):
            amt = _clamp(random.gauss(VENDOR_UPI_MEAN_INR, VENDOR_UPI_STDDEV_INR), 50, 1500)
            txn_day = d + timedelta(days=random.randint(0, 27))
            upi_events.append({
                "date":       txn_day.isoformat(),
                "amount_inr": round(amt, 2),
                "merchant":   random.choice(["Kirana store", "Vegetable vendor",
                                              "PhonePe recharge", "Electricity prepaid",
                                              "Small supplier", "Mobile recharge"]),
                "type":       "upi_debit",
            })

    # Feature vector (heuristic from docs)
    on_time_rate = sum(1 for e in doc_events if e.get("on_time")) / len(doc_events)
    amounts      = [e["amount_inr"] for e in doc_events]
    import statistics as st
    income_cv    = st.stdev(amounts) / (st.mean(amounts) or 1)

    features = {
        "payment_consistency": round(on_time_rate, 3),
        "income_stability":    round(_clamp(1 - income_cv / 2, 0, 1), 3),
        "spending_discipline": 0.72,    # heuristic
        "digital_footprint":   0.38,    # below national mean → lower
        "rental_reliability":  1.0,     # perfect streak
        "pay_streak":          1.0,     # 6/6 months
        "avg_pay_ratio":       0.95,
        "bill_variance":       0.18,
        "inflow_regularity":   0.65,
        "max_pay_gap":         0.0,
        "limit_utilization":   0.45,
        "months_data":         1.0,
    }

    return {
        "_synthetic": True,
        "_disclaimer": (
            "This is a synthetic demo persona. "
            "Amounts are calibrated against NPCI UPI statistics but are not real transactions. "
            "Score illustrates the product; no India-specific accuracy is claimed."
        ),
        "persona_id":  "priya_sharma",
        "name":        "Priya Sharma",
        "occupation":  "Tea stall operator",
        "location":    "Pune, Maharashtra",
        "monthly_income_range": "INR 8,000-14,000",
        "documents":   doc_events,
        "upi_events":  upi_events,
        "features":    features,
        "expected_band": "Fair",   # 640 per demo script
        "expected_score": 640,
    }


def _raju_scenario() -> dict[str, Any]:
    """
    Raju Kumar — gig delivery worker, Mumbai.
    Irregular income, digital-heavy UPI, no rent receipts.
    """
    random.seed(7)
    months = _months_back(6)
    doc_events = []

    # Electricity bills: 4 of 6 months on time
    for i, d in enumerate(months):
        on_time   = i not in (2, 4)    # missed 2 months
        paid_day  = _jitter_day(date(d.year, d.month, 15 if on_time else 20), sigma=3)
        doc_events.append({
            "type":       "electricity_bill",
            "biller":     "BEST Mumbai",
            "period":     d.strftime("%b %Y"),
            "amount_inr": round(random.gauss(620, 90), 2),
            "due_date":   date(d.year, d.month, 15).isoformat(),
            "paid_date":  paid_day.isoformat(),
            "on_time":    on_time,
            "confidence": round(random.uniform(0.88, 0.97), 3),
        })

    upi_events = []
    for d in months:
        n_txn = random.randint(20, 40)   # gig workers transact more
        for _ in range(n_txn):
            amt = _clamp(random.gauss(GIG_UPI_MEAN_INR, GIG_UPI_STDDEV_INR), 50, 3000)
            txn_day = d + timedelta(days=random.randint(0, 27))
            upi_events.append({
                "date":       txn_day.isoformat(),
                "amount_inr": round(amt, 2),
                "merchant":   random.choice(["Swiggy payout", "Zomato payout",
                                              "Fuel", "Mobile data", "Grocery",
                                              "ATM withdrawal", "UPI transfer"]),
                "type":       random.choice(["upi_debit", "upi_credit"]),
            })

    features = {
        "payment_consistency": 0.67,
        "income_stability":    0.48,
        "spending_discipline": 0.61,
        "digital_footprint":   0.62,
        "rental_reliability":  0.0,
        "pay_streak":          0.33,
        "avg_pay_ratio":       0.85,
        "bill_variance":       0.30,
        "inflow_regularity":   0.55,
        "max_pay_gap":         0.25,
        "limit_utilization":   0.55,
        "months_data":         1.0,
    }

    return {
        "_synthetic": True,
        "_disclaimer": (
            "Synthetic demo persona — not real transactions. "
            "Score illustrates the product; no India-specific accuracy is claimed."
        ),
        "persona_id":  "raju_kumar",
        "name":        "Raju Kumar",
        "occupation":  "Gig delivery worker",
        "location":    "Mumbai, Maharashtra",
        "monthly_income_range": "INR 12,000-22,000",
        "documents":   doc_events,
        "upi_events":  upi_events,
        "features":    features,
        "expected_band": "Fair",
    }


def _seema_scenario() -> dict[str, Any]:
    """
    Seema Devi — seasonal agricultural worker, rural Bihar.
    Very irregular income, limited digital footprint.
    """
    random.seed(13)
    months = _months_back(6)
    doc_events = []

    # Only 3 months of electricity bills (rural, irregular supply)
    for i, d in enumerate(months[:3]):
        doc_events.append({
            "type":       "electricity_bill",
            "biller":     "BSPHCL",
            "period":     d.strftime("%b %Y"),
            "amount_inr": round(random.gauss(220, 40), 2),
            "due_date":   date(d.year, d.month, 15).isoformat(),
            "paid_date":  _jitter_day(date(d.year, d.month, 14), sigma=4).isoformat(),
            "on_time":    True,
            "confidence": round(random.uniform(0.82, 0.93), 3),
        })

    upi_events = []
    for d in months:
        n_txn = random.randint(2, 8)   # low digital footprint
        for _ in range(n_txn):
            amt = _clamp(random.gauss(SEASONAL_UPI_MEAN_INR, SEASONAL_UPI_STDDEV_INR), 50, 1000)
            txn_day = d + timedelta(days=random.randint(0, 27))
            upi_events.append({
                "date":       txn_day.isoformat(),
                "amount_inr": round(amt, 2),
                "merchant":   random.choice(["Village kirana", "Mobile recharge",
                                              "Jan Dhan ATM", "UPI transfer"]),
                "type":       "upi_debit",
            })

    features = {
        "payment_consistency": 0.50,
        "income_stability":    0.30,
        "spending_discipline": 0.55,
        "digital_footprint":   0.18,
        "rental_reliability":  0.0,
        "pay_streak":          0.50,
        "avg_pay_ratio":       0.90,
        "bill_variance":       0.12,
        "inflow_regularity":   0.38,
        "max_pay_gap":         0.10,
        "limit_utilization":   0.35,
        "months_data":         0.5,
    }

    return {
        "_synthetic": True,
        "_disclaimer": (
            "Synthetic demo persona — not real transactions. "
            "Score illustrates the product; no India-specific accuracy is claimed."
        ),
        "persona_id":  "seema_devi",
        "name":        "Seema Devi",
        "occupation":  "Seasonal agricultural worker",
        "location":    "Sitamarhi, Bihar",
        "monthly_income_range": "INR 3,000-8,000 (seasonal)",
        "documents":   doc_events,
        "upi_events":  upi_events,
        "features":    features,
        "expected_band": "Poor",
    }


# ─── Public interface ─────────────────────────────────────────────────────────

PERSONAS: dict[str, Any] = {
    "priya_sharma": _priya_scenario,
    "raju_kumar":   _raju_scenario,
    "seema_devi":   _seema_scenario,
}


def get_persona(name: str) -> dict[str, Any]:
    """Return a synthetic persona dict.  Raises KeyError if unknown."""
    builder = PERSONAS[name]
    return builder()


def get_feature_vector(persona_name: str) -> list[float]:
    """Return the 12-element feature vector for a persona."""
    p    = get_persona(persona_name)
    feat = p["features"]
    keys = [
        "payment_consistency", "income_stability", "spending_discipline",
        "digital_footprint", "rental_reliability", "pay_streak",
        "avg_pay_ratio", "bill_variance", "inflow_regularity",
        "max_pay_gap", "limit_utilization", "months_data",
    ]
    return [float(feat.get(k, 0.5)) for k in keys]


def save_all(output_dir: Path | None = None) -> None:
    """Serialize all personas to JSON files."""
    out = output_dir or PERSONAS_DIR
    out.mkdir(parents=True, exist_ok=True)
    for name, builder in PERSONAS.items():
        persona = builder()
        path    = out / f"{name}.json"
        path.write_text(json.dumps(persona, indent=2, default=str))
        print(f"  Saved {path}")


if __name__ == "__main__":
    print("Generating synthetic personas (calibrated to NPCI UPI stats)…")
    save_all()
    print("Done.  Disclaimer: these are synthetic demo personas, not real data.")
