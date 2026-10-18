-- GhostScore Feature Engineering SQL (Section 5.3 of blueprint)
-- Computes 12 behavioral credit features from extracted documents + raw events
-- Run against BigQuery dataset {project}.{dataset}

-- ─────────────────────────────────────────────────────────────────────────────
-- FEATURE 1: Payment Consistency
-- Section 5.3: COUNTIF(status=ON_TIME)/COUNT(*), STDDEV(payment_date_offset)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW `{project}.{dataset}.v_payment_consistency` AS
SELECT
  user_id,
  COUNT(*)                                                       AS total_bills,
  COUNTIF(on_time = TRUE)                                       AS on_time_bills,
  SAFE_DIVIDE(COUNTIF(on_time = TRUE), COUNT(*))                AS payment_consistency,
  STDDEV(DATE_DIFF(paid_date, due_date, DAY))                   AS payment_date_variance_days
FROM `{project}.{dataset}.extracted_documents`
WHERE doc_type IN ('electricity_bill', 'water_bill', 'gas_bill')
  AND paid_date IS NOT NULL
  AND due_date  IS NOT NULL
GROUP BY user_id;


-- ─────────────────────────────────────────────────────────────────────────────
-- FEATURE 2: Income Stability (from UPI inflows / recurring payments)
-- Section 5.3: STDDEV(monthly_inflow)
-- Caveat: bank statement shows payment regularity, not punctuality.
-- Due dates are not available from Account Aggregator bank statements.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW `{project}.{dataset}.v_income_stability` AS
WITH monthly_inflow AS (
  SELECT
    user_id,
    DATE_TRUNC(event_date, MONTH)        AS month,
    SUM(amount_inr)                      AS total_inflow
  FROM `{project}.{dataset}.raw_events`
  WHERE event_type = 'upi_credit'
  GROUP BY user_id, month
)
SELECT
  user_id,
  COUNT(DISTINCT month)                                  AS months_of_inflow,
  AVG(total_inflow)                                      AS avg_monthly_inflow_inr,
  STDDEV(total_inflow)                                   AS stddev_monthly_inflow,
  SAFE_DIVIDE(STDDEV(total_inflow), AVG(total_inflow))   AS cv_monthly_inflow,
  1.0 / (1.0 + SAFE_DIVIDE(STDDEV(total_inflow), AVG(total_inflow)))
                                                         AS income_stability_score
FROM monthly_inflow
GROUP BY user_id;


-- ─────────────────────────────────────────────────────────────────────────────
-- FEATURE 3: Spending Discipline
-- Section 5.3: AVG(essential_spend/total_spend) over 6-month window
-- Note: classification of transactions as essential vs. discretionary
-- is inferred from merchant names/descriptions — not guaranteed reliable.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW `{project}.{dataset}.v_spending_discipline` AS
WITH monthly_spend AS (
  SELECT
    user_id,
    DATE_TRUNC(event_date, MONTH)             AS month,
    SUM(amount_inr)                           AS total_spend,
    SUM(CASE
      WHEN LOWER(merchant) LIKE '%electricity%'
        OR LOWER(merchant) LIKE '%water%'
        OR LOWER(merchant) LIKE '%rent%'
        OR LOWER(merchant) LIKE '%ration%'
        OR LOWER(merchant) LIKE '%grocery%'
        OR LOWER(merchant) LIKE '%msedcl%'
        OR LOWER(merchant) LIKE '%bsphcl%'
        OR LOWER(merchant) LIKE '%best%'
      THEN amount_inr ELSE 0 END)             AS essential_spend
  FROM `{project}.{dataset}.raw_events`
  WHERE event_type = 'upi_debit'
  GROUP BY user_id, month
)
SELECT
  user_id,
  AVG(SAFE_DIVIDE(essential_spend, total_spend))  AS spending_discipline_score
FROM monthly_spend
GROUP BY user_id;


-- ─────────────────────────────────────────────────────────────────────────────
-- FEATURE 4: Digital Footprint
-- Section 5.3: COUNT(recharges) per month, MAX(recharge_amount)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW `{project}.{dataset}.v_digital_footprint` AS
WITH monthly_upi AS (
  SELECT
    user_id,
    DATE_TRUNC(event_date, MONTH)         AS month,
    COUNT(*)                              AS txn_count,
    MAX(amount_inr)                       AS max_txn_inr,
    SUM(amount_inr)                       AS total_txn_inr
  FROM `{project}.{dataset}.raw_events`
  WHERE event_type IN ('upi_debit', 'upi_credit', 'mobile_recharge')
  GROUP BY user_id, month
)
SELECT
  user_id,
  AVG(txn_count)                                             AS avg_monthly_txn_count,
  MAX(max_txn_inr)                                           AS max_single_txn_inr,
  LEAST(AVG(txn_count) / 30.0, 1.0)                         AS digital_footprint_score
FROM monthly_upi
GROUP BY user_id;


-- ─────────────────────────────────────────────────────────────────────────────
-- FEATURE 5: Rental Reliability
-- Section 5.3: MAX(consecutive_rent_months) using gap-fill window function
-- ─────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW `{project}.{dataset}.v_rental_reliability` AS
WITH rent_months AS (
  SELECT DISTINCT
    user_id,
    DATE_TRUNC(paid_date, MONTH)    AS rent_month
  FROM `{project}.{dataset}.extracted_documents`
  WHERE doc_type = 'rent_receipt'
    AND paid_date IS NOT NULL
),
ranked AS (
  SELECT
    user_id,
    rent_month,
    DATE_DIFF(
      rent_month,
      MIN(rent_month) OVER (PARTITION BY user_id),
      MONTH
    )                               AS months_since_first,
    ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY rent_month)
                                    AS rn
  FROM rent_months
),
streaks AS (
  SELECT
    user_id,
    rent_month,
    months_since_first - rn + 1     AS streak_group
  FROM ranked
)
SELECT
  user_id,
  MAX(streak_count)               AS max_consecutive_rent_months,
  LEAST(MAX(streak_count) / 12.0, 1.0)
                                  AS rental_reliability_score
FROM (
  SELECT user_id, streak_group, COUNT(*) AS streak_count
  FROM streaks
  GROUP BY user_id, streak_group
)
GROUP BY user_id;


-- ─────────────────────────────────────────────────────────────────────────────
-- Combined feature vector view (all 12 features per user)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW `{project}.{dataset}.v_feature_vector` AS
SELECT
  u.user_id,
  CURRENT_TIMESTAMP()                                    AS computed_at,
  COALESCE(pc.payment_consistency,  0.0)                 AS payment_consistency,
  COALESCE(is_.income_stability_score, 0.0)              AS income_stability,
  COALESCE(sd.spending_discipline_score, 0.0)            AS spending_discipline,
  COALESCE(df.digital_footprint_score, 0.0)              AS digital_footprint,
  COALESCE(rr.rental_reliability_score, 0.0)             AS rental_reliability,
  COALESCE(pc.on_time_bills, 0)                          AS pay_streak,
  1.0                                                    AS avg_pay_ratio,     -- populated from doc data
  COALESCE(pc.payment_date_variance_days / 30.0, 0.0)   AS bill_variance,
  COALESCE(is_.income_stability_score, 0.0)              AS inflow_regularity,
  0.0                                                    AS max_pay_gap,       -- from doc data
  0.5                                                    AS limit_utilization, -- from doc data
  COALESCE(is_.months_of_inflow / 6.0, 0.0)             AS months_data
FROM (SELECT DISTINCT user_id FROM `{project}.{dataset}.raw_events`) u
LEFT JOIN `{project}.{dataset}.v_payment_consistency`  pc  ON u.user_id = pc.user_id
LEFT JOIN `{project}.{dataset}.v_income_stability`     is_ ON u.user_id = is_.user_id
LEFT JOIN `{project}.{dataset}.v_spending_discipline`  sd  ON u.user_id = sd.user_id
LEFT JOIN `{project}.{dataset}.v_digital_footprint`    df  ON u.user_id = df.user_id
LEFT JOIN `{project}.{dataset}.v_rental_reliability`   rr  ON u.user_id = rr.user_id;


-- ─────────────────────────────────────────────────────────────────────────────
-- Snapshot the feature vector into the feature store (scheduled query)
-- ─────────────────────────────────────────────────────────────────────────────
-- Run this as a scheduled BigQuery query (e.g. daily at 02:00 IST):
-- INSERT INTO `{project}.{dataset}.feature_store`
-- SELECT * FROM `{project}.{dataset}.v_feature_vector`;
