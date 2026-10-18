"""
GhostScore ML — Feature mapping from public datasets to GhostScore features.

Design note (Section 5.8 of blueprint):
  The model is trained on UCI Default of Credit Card Clients (Taiwan 2009).
  This is NOT Indian data.  The mapping below is an explicit assumption:
  we treat repayment-status columns (PAY_0…PAY_6) as proxies for payment
  regularity, and the bill/payment amount columns as proxies for income
  stability and spending discipline.

  This assumption has NOT been validated on Indian lending data.
  Do NOT present model accuracy as India-specific.

Swapping datasets:
  To use Home Credit Default Risk 2018 (or the 2024 benchmark), replace the
  `_map_uci_features()` function with `_map_homecredit_features()` below
  and point DATA_PATH at the relevant CSV.  The feature names and
  normalization must be updated to match the real column names after
  inspecting them.
"""
from __future__ import annotations
import os, sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.ensemble import GradientBoostingClassifier
import joblib

DATA_PATH    = Path(__file__).parents[2] / "ghostscore-data" / "raw" / "uci_default_credit_card.csv"
ARTIFACT_DIR = Path(__file__).parent / "artifacts"
MODEL_PATH   = ARTIFACT_DIR / "model.joblib"

FEATURE_NAMES = [
    "payment_consistency",   # derived from PAY_0…PAY_6
    "income_stability",      # derived from BILL_AMT stddev
    "spending_discipline",   # derived from pay-to-bill ratio
    "digital_footprint",     # proxy: LIMIT_BAL normalized
    "rental_reliability",    # proxy: payment-streak derived
    "pay_streak",            # consecutive on-time payments
    "avg_pay_ratio",         # AVG(PAY_AMTi / max(BILL_AMTi, 1))
    "bill_variance",         # STDDEV of bill amounts
    "inflow_regularity",     # 1 / (1 + cv of pay amounts)
    "max_pay_gap",           # max(PAY_0…PAY_6) — worst lateness
    "limit_utilization",     # avg bill / LIMIT_BAL
    "months_data",           # always 6 for UCI; varies for personas
]

TARGET_COL = "default payment next month"


# Column name mapping: UCI uses X1-X23 notation
_UCI_RENAME = {
    "X1": "LIMIT_BAL",
    "X6": "PAY_0", "X7": "PAY_2", "X8": "PAY_3", "X9": "PAY_4",
    "X10": "PAY_5", "X11": "PAY_6",
    "X12": "BILL_AMT1", "X13": "BILL_AMT2", "X14": "BILL_AMT3",
    "X15": "BILL_AMT4", "X16": "BILL_AMT5", "X17": "BILL_AMT6",
    "X18": "PAY_AMT1", "X19": "PAY_AMT2", "X20": "PAY_AMT3",
    "X21": "PAY_AMT4", "X22": "PAY_AMT5", "X23": "PAY_AMT6",
    "Y": "default payment next month",
}


def load_uci_data() -> pd.DataFrame:
    path = DATA_PATH
    if not path.exists():
        alt = Path("../ghostscore-data/raw/uci_default_credit_card.csv")
        if alt.exists():
            path = alt
        else:
            raise FileNotFoundError(f"UCI data not found at {DATA_PATH}")
    df = pd.read_csv(path, header=0)
    df = df.rename(columns=_UCI_RENAME)
    return df


def _map_uci_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Map UCI columns to GhostScore feature vector.

    This mapping is an explicit assumption documented in Section 5.8:
    - PAY_0…PAY_6 (repayment status, -1=on-time, 0=min, 1=1mo late…)
      → payment_consistency, pay_streak, max_pay_gap
    - BILL_AMT1…6 → bill_variance, limit_utilization
    - PAY_AMT1…6 → spending_discipline, avg_pay_ratio, inflow_regularity
    - LIMIT_BAL → digital_footprint proxy
    """
    pay_cols  = [f"PAY_{i}" for i in range(7) if f"PAY_{i}" in df.columns]
    bill_cols = [f"BILL_AMT{i}" for i in range(1, 7) if f"BILL_AMT{i}" in df.columns]
    pamt_cols = [f"PAY_AMT{i}" for i in range(1, 7) if f"PAY_AMT{i}" in df.columns]

    pay_arr  = df[pay_cols].values.astype(float)
    bill_arr = df[bill_cols].values.astype(float)
    pamt_arr = df[pamt_cols].values.astype(float)

    # payment_consistency: fraction of months that were on-time (PAY <= 0)
    on_time = (pay_arr <= 0).mean(axis=1)

    # pay_streak: count of consecutive on-time months from most recent
    def streak(row):
        s = 0
        for v in row:
            if v <= 0: s += 1
            else:      break
        return s
    streaks = np.apply_along_axis(streak, 1, pay_arr)

    # max_pay_gap: worst lateness value (higher = worse)
    max_gap = np.clip(pay_arr.max(axis=1) / 8.0, 0, 1)   # normalize to [0,1]

    # bill_variance (lower = more stable) — normalized by LIMIT_BAL
    limit = np.clip(df["LIMIT_BAL"].values.astype(float), 1, None)
    bill_std = bill_arr.std(axis=1)
    bill_var  = np.clip(bill_std / limit, 0, 1)

    # limit_utilization: avg bill / LIMIT_BAL
    avg_bill = bill_arr.mean(axis=1)
    util     = np.clip(avg_bill / limit, 0, 1)

    # pay-to-bill ratios
    ratio_arr = pamt_arr / np.clip(bill_arr, 1, None)
    avg_ratio = ratio_arr.mean(axis=1)

    # inflow_regularity: 1 / (1 + CV of pay amounts)
    pamt_std  = pamt_arr.std(axis=1)
    pamt_mean = np.clip(pamt_arr.mean(axis=1), 1, None)
    cv        = pamt_std / pamt_mean
    inflow_reg = 1.0 / (1.0 + cv)

    # digital_footprint proxy: normalized LIMIT_BAL (higher credit limit = more formal access)
    max_limit = limit.max() or 1.0
    dig_fp    = limit / max_limit

    # income_stability proxy: 1 - bill_var
    income_stab = 1.0 - bill_var

    # spending_discipline: avg pay-to-bill ratio capped at 1
    spend_disc = np.clip(avg_ratio, 0, 1)

    # rental_reliability: proxy from pay_streak / 6
    rental_rel = np.clip(streaks / 6.0, 0, 1)

    features = pd.DataFrame({
        "payment_consistency": on_time,
        "income_stability":    income_stab,
        "spending_discipline": spend_disc,
        "digital_footprint":   dig_fp,
        "rental_reliability":  rental_rel,
        "pay_streak":          np.clip(streaks / 6.0, 0, 1),
        "avg_pay_ratio":       np.clip(avg_ratio, 0, 2),
        "bill_variance":       bill_var,
        "inflow_regularity":   inflow_reg,
        "max_pay_gap":         max_gap,
        "limit_utilization":   util,
        "months_data":         np.ones(len(df)) * (len(bill_cols) / 6.0),
    })
    return features


def train():
    """Train a sklearn GradientBoosting pipeline on UCI data and save to ml/artifacts/model.joblib."""
    print("Loading UCI data…")
    df = load_uci_data()
    print(f"  Loaded {len(df):,} rows. Default rate: {df[TARGET_COL].mean():.2%}")
    print("  Note: UCI is Taiwan 2009 credit-card data — NOT Indian data.")
    print("  Model is a pipeline baseline; no India-specific accuracy is claimed.")

    print("Engineering features…")
    X = _map_uci_features(df)
    y = df[TARGET_COL].values.astype(int)

    from sklearn.model_selection import train_test_split
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42)

    pipe = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler",  StandardScaler()),
        ("clf",     GradientBoostingClassifier(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.1,
            subsample=0.8,
            random_state=42,
        )),
    ])

    print("Training…")
    pipe.fit(X_tr, y_tr)

    from sklearn.metrics import roc_auc_score, classification_report
    probs = pipe.predict_proba(X_te)[:, 1]
    auc   = roc_auc_score(y_te, probs)
    print(f"  Test AUC: {auc:.4f}  (Taiwan 2009 CC data — not India-validated)")
    preds = pipe.predict(X_te)
    print(classification_report(y_te, preds, target_names=["No default", "Default"]))

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipe, MODEL_PATH)
    print(f"  Model saved → {MODEL_PATH}")

    # Save feature names for downstream use
    import json
    (ARTIFACT_DIR / "feature_names.json").write_text(
        json.dumps(FEATURE_NAMES, indent=2)
    )
    print("Done.")


# ─── Home Credit 2018 feature mapping (swap-in template) ─────────────────────

def _map_homecredit_features(df_app: pd.DataFrame,
                              df_install: pd.DataFrame) -> pd.DataFrame:
    """
    Template for mapping Home Credit Default Risk 2018 installments_payments
    to GhostScore features (Section 5.8 of blueprint).

    This has NOT been run — it is a template for when the dataset is available.
    Field names and availability at prediction cutoff must be verified.

    Parameters
    ----------
    df_app     : application_train.csv
    df_install : installments_payments.csv
    """
    raise NotImplementedError(
        "Home Credit mapping not yet implemented. "
        "Download application_train.csv and installments_payments.csv from Kaggle, "
        "verify field names and prediction-time availability, then implement this function. "
        "See blueprint Section 5.8 for the mapping assumptions."
    )


if __name__ == "__main__":
    train()
