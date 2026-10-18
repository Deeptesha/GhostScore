-- GhostScore BigQuery Schema
-- Dataset: ghostscore
-- All tables are partitioned/clustered for cost efficiency
-- Section 5.3 of blueprint: feature engineering SQL

-- ─────────────────────────────────────────────────────────────────────────────
-- Raw events table (ingested from Pub/Sub via Dataflow or direct insert)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `{project}.{dataset}.raw_events`
(
  event_id        STRING     NOT NULL,
  user_id         STRING     NOT NULL,
  event_type      STRING     NOT NULL,   -- 'upi_debit'|'upi_credit'|'bill_payment'|'rent_payment'
  amount_inr      FLOAT64,
  merchant        STRING,
  event_date      DATE       NOT NULL,
  doc_id          STRING,                -- for document-sourced events
  ingested_at     TIMESTAMP  NOT NULL    DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY event_date
CLUSTER BY user_id, event_type;


-- ─────────────────────────────────────────────────────────────────────────────
-- Extracted document fields (written by doc-processor after Document AI)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `{project}.{dataset}.extracted_documents`
(
  doc_id            STRING     NOT NULL,
  user_id           STRING     NOT NULL,
  doc_type          STRING     NOT NULL,
  period            STRING,
  biller_or_landlord STRING,
  amount_inr        FLOAT64,
  due_date          DATE,
  paid_date         DATE,
  on_time           BOOL,
  confidence_avg    FLOAT64,
  status            STRING,              -- 'accepted'|'needs_review'|'rejected_unreadable'
  created_at        TIMESTAMP  NOT NULL  DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY created_at
CLUSTER BY user_id, doc_type;


-- ─────────────────────────────────────────────────────────────────────────────
-- Feature store — one row per user per computation window
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `{project}.{dataset}.feature_store`
(
  user_id              STRING    NOT NULL,
  computed_at          TIMESTAMP NOT NULL  DEFAULT CURRENT_TIMESTAMP(),
  window_months        INT64     NOT NULL  DEFAULT 6,
  payment_consistency  FLOAT64,           -- Section 5.3: fraction on-time bills
  income_stability     FLOAT64,           -- 1 - CV(monthly_inflow)
  spending_discipline  FLOAT64,           -- avg(essential/total) over window
  digital_footprint    FLOAT64,           -- normalized UPI frequency/amount
  rental_reliability   FLOAT64,           -- consecutive rent months / window
  pay_streak           INT64,             -- consecutive on-time months
  avg_pay_ratio        FLOAT64,           -- avg(paid / billed)
  bill_variance        FLOAT64,           -- STDDEV(bill amounts) / avg
  inflow_regularity    FLOAT64,           -- 1 / (1 + CV(monthly_inflows))
  max_pay_gap          FLOAT64,           -- max days late, normalized
  limit_utilization    FLOAT64,           -- avg_bill / limit proxy
  months_data          FLOAT64            -- months of data present (0-1)
)
PARTITION BY DATE(computed_at)
CLUSTER BY user_id;


-- ─────────────────────────────────────────────────────────────────────────────
-- Score history (written by api-service after each scoring event)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `{project}.{dataset}.score_history`
(
  score_id        STRING    NOT NULL,
  user_id         STRING    NOT NULL,
  scored_at       TIMESTAMP NOT NULL  DEFAULT CURRENT_TIMESTAMP(),
  score           INT64     NOT NULL,
  band            STRING    NOT NULL,
  band_confidence FLOAT64,
  model_version   STRING,
  feature_hash    STRING,               -- SHA256 of feature vector for dedup
  disclaimer      STRING
)
PARTITION BY DATE(scored_at)
CLUSTER BY user_id;


-- ─────────────────────────────────────────────────────────────────────────────
-- Audit log (immutable, append-only)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `{project}.{dataset}.audit_log`
(
  audit_id        STRING    NOT NULL,
  timestamp       TIMESTAMP NOT NULL  DEFAULT CURRENT_TIMESTAMP(),
  event_type      STRING    NOT NULL,
  user_id         STRING    NOT NULL,
  model_version   STRING,
  band            STRING,
  top_factors     ARRAY<STRING>,
  explanation_id  STRING,
  ip_hash         STRING                -- hashed for privacy
)
PARTITION BY DATE(timestamp);
