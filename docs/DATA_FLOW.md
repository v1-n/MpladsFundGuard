# MPLADS FundGuard — Data Flow & Architecture Specification

## 1. Pipeline Overview & Execution Sequence

The data pipeline processes raw public extracts from the [MPLADS Portal](https://www.mplads.gov.in/) (restricted to Lok Sabha, 543 MPs) and produces cleaned, reconciled, anomaly-scored, and audit-ready datasets.

```text
[data/raw/*.csv]
       │
       ▼
 1. eda/eda_pipeline.py ──────► [data/clean/clean_*.csv]
                                       │
       ┌───────────────────────────────┤
       ▼                               ▼
 2. eda/eda_checks.py (Input Gate)  3. src/build_master.py
                                       │
                                       ▼
                              [data/clean/mplads_360_master.csv]
                                       │
       ┌───────────────────────────────┤
       ▼                               ▼
 2b. eda/eda_checks.py (Output Gate) 4. src/build_ml_features.py
                                       │
                                       ▼
                              [data/clean/ml_features.csv]
                              [data/clean/anomaly_scores.csv]
                                       │
                                       ▼
                              5. src/evaluate_model.py
                                       │
                                       ▼
                              [data/clean/manual_audit_sample_blind.csv]
                              [data/clean/manual_audit_sample_key.csv]
                              [data/clean/manual_audit_rubric.md]
                              [data/clean/evaluation_results.json] (Phase 1)
                              [data/clean/audit_matching_diagnostics.json] (Phase 1)
                              [data/clean/data_quality_report.json] (Phase 1)
```

Execution command order:
```bash
python3 eda/eda_pipeline.py
python3 eda/eda_checks.py
python3 src/build_master.py
python3 eda/eda_checks.py
python3 src/build_ml_features.py
python3 src/evaluate_model.py
```

---

## 2. Raw Input Files (`data/raw/`)

*Note: Raw files contain personal identifiable information (PII such as phone numbers) and are gitignored.*

| Raw Filename | Source Portal Report | Key Content |
|---|---|---|
| `Works Sanctioned.csv` | Works Sanctioned Report | Recommended and Sanction dates, Work description, Sanction amount |
| `Expenditure on Completed and On-going Works as on Date.csv` | Expenditure Ledger Report | Multi-transaction disbursement rows, payment dates, vendor names, payment status |
| `Works Completed.csv` | Works Completed Report | Completion date, reported disbursed amount, completion image status |
| `mplads_mp_summary_2026-10-09.csv` | MP Summary Report | 543 Lok Sabha MPs (Rajya Sabha rows dropped during cleaning), allocated budget, aggregate spend |

---

## 3. Step-by-Step Data Flow & Schemas

### Step 1: Cleaning & Standardization (`eda/eda_pipeline.py`)
- **Inputs:** `data/raw/*.csv` (fallback to `data/` or `data/clean/` if raw missing)
- **Transformations:**
  - Standardizes canonical `Work ID` regex: `^WS/[A-Z0-9]+/\d{4}-\d{4}/\d+$`.
  - Preserves blanks as `NaN` (does not convert blank currency to ₹0, preventing false ghost completions).
  - Explicit ISO format date parsing (`%Y-%m-%d`) with portal fallback (`%d-%b-%Y`), avoiding `dayfirst=True` month swaps.
  - Masks 10-digit Indian mobile numbers (`[6-9]\d{9}`) to `[PHONE_REDACTED]` in all text fields.
  - Drops Rajya Sabha members from MP Summary, restricting scope strictly to Lok Sabha (`House == 'Lok Sabha'`).
- **Outputs:**
  - `data/clean/clean_works_sanctioned.csv`
    - Columns: `Work ID`, `Sr. No.`, `Work category`, `Work`, `State`, `IDA`, `Hon'ble Members of Parliament`, `Constituency`, `Work description`, `Recommended date`, `Sanction Date`, `Sanction Amount ( ₹ )`, `Work Status`
  - `data/clean/clean_expenditure.csv`
    - Columns: `Sr. No.`, `State`, `Work`, `Work ID`, `IDA`, `Hon'ble Members of Parliament`, `Constituency`, `Expenditure Date`, `Vendor Name`, `Payment Status`, `Fund Disbursed Amount ( ₹ )`
  - `data/clean/clean_works_completed.csv`
    - Columns: `Work ID`, `Sr. No.`, `Work Category`, `Work`, `State`, `IDA`, `Work Description`, `Hon'ble Members of Parliament`, `Constituency`, `Image`, `Completion Date`, `Amount Disbursed ( ₹ )`
  - `data/clean/clean_mp_summary.csv`
    - Columns: `MP Name`, `Constituency`, `State`, `House`, `Allocated Amount (₹)`, `Amount Recommended (₹)`, `Total Expenditure (₹)`, `Utilization %`, `Completed Works`, `Recommended Works`, `Completion Rate %`, `Balance Not Yet Paid to Vendors (₹)`, `Transaction Count`, `Successful Payments`, `Pending Payments`, `Average Rating`

---

### Step 2: Quality Gate Checks (`eda/eda_checks.py`)
- **Inputs:** 4 clean datasets (Input Gate) and `mplads_360_master.csv` (Output Gate).
- **Checks:**
  1. Required columns presence.
  2. Work ID format and null rate (<1% null, >90% format match).
  3. Cross-file join coverage (identifies orphan payments, scope match).
  4. Stale sanction export detection (sequence analysis).
  5. Blank vs Zero amount validation.
  6. Payment status decomposition (`Payment Success` vs `Payment In-Progress`).
  7. Tail outlier and unit error detection (>10x P99, < ₹1,000).
  8. Duplicate payment forensics (identical `[Work ID + Vendor + Amount + Date]`).
  9. Master rule-firing prevalence diagnostics (flags firing rate, dead rules).
  10. Missing-photo flag rate over time (pre vs post 15 May 2026 cutoff).
  11. PII scan confirmation (0 phone numbers remaining).
  12. Snapshot freshness (<30 days lag across files).
  13. Cross-file financial reconciliation.
- **Outputs:** Console output; `data/clean/data_quality_report.json` (Phase 1 addition).

---

### Step 3: 360° Master Dataset Generation (`src/build_master.py`)
- **Inputs:** Cleaned Sanctioned, Expenditure, and Completed CSVs.
- **Transformations:**
  - Multi-transaction collapse: Groups expenditure rows by `Work ID` to compute `Total_Exp_Disbursed`, `Total_Exp_Settled` (Success only), and `Total_Exp_In_Progress`.
  - Normalizes vendor names to `vendor_key` (uppercase alphanumeric).
  - Outer joins Sanctioned ──► Expenditure (Aggregated) ──► Completed.
  - Coalesces geographical and MP metadata across sources.
  - Evaluates rule-based screening indicators (see Section 4 for column list).
- **Output:** `data/clean/mplads_360_master.csv` (84,271 unique works, 45 columns)
  - Canonical Columns:
    - Identifiers: `Work ID`, `Lifecycle_Stage`, `Work_Status`, `State`, `Constituency`, `IDA`, `Hon'ble Members of Parliament`, `Work category`, `Work`, `Work_Description_Final`
    - Financials: `Sanction_Amount`, `Total_Exp_Settled`, `Total_Exp_In_Progress`, `Total_Exp_Disbursed`, `Cost_Variance`, `Utilization_Ratio`, `Comp_Reported_Disbursed`
    - Dates: `Recommended date`, `Sanction Date`, `Completion Date`, `First_Payment_Date`, `Last_Payment_Date`
    - Transaction Metrics: `Payment_Installments_Count`, `Settled_Count`, `In_Progress_Count`, `Unique_Vendors_Count`, `Primary_Vendor`, `Dup_Payment_Count`, `Dup_Payment_Amount`
    - Durations: `Sanction_Approval_Days`, `Execution_Duration_Days`, `First_Payment_Lag_Days`
    - Provenance: `Is_Sanctioned`, `Has_Payments`, `Is_Completed`, `Post_Photo_Cutoff`, `Has_Pending_Payment`
    - Rule & Integrity Flags: `Integrity_Cost_Cap_Violation`, `Integrity_Date_Sequence_Violation`, `Flag_Orphan_Payment`, `Flag_Ghost_Completion`, `Flag_Duplicate_Payment`, `Flag_Stalled_Unpaid`, `Flag_Same_Day_Bulk_Payment`, `Missing_Photo_Proof`

---

### Step 4: ML Feature Building & Anomaly Scoring (`src/build_ml_features.py`)
- **Inputs:** `data/clean/mplads_360_master.csv`
- **Scored Cohort:** Works with active settled expenditure (`Total_Exp_Settled > 0`), totaling 58,050 works. (24,282 works with 0 payments and 1,939 pending-only works excluded from scoring).
- **Transformations:**
  - 3-Tier Peer Benchmarking:
    - Tier 1: `[Work, State]` category median (n ≥ 20) -> 91.6% coverage.
    - Tier 2: National `[Work]` median (n ≥ 20) -> 8.0% coverage.
    - Tier 3: Global national fallback median -> 0.4% coverage.
    - `paid_vs_peer_log = log1p(Total_Exp_Settled) - log1p(peer_median)`.
  - Feature Engineering: Log-transformed budget, utilization ratio (capped at 5.0), installment and vendor counts, approval and execution durations. (`log_paid` intentionally dropped to avoid 0.98 collinearity with `log_sanction`).
  - Stratified 10-Seed Ensemble Isolation Forest:
    - Completed Cohort (36,989 works): 8 features (includes execution duration).
    - In-Progress Cohort (21,061 works): 9 features (includes pending expenditure, excludes duration).
  - Heuristic extreme feature indicator attribution (≥98th percentile).
- **Outputs:**
  - `data/clean/ml_features.csv`
    - Columns: `Work ID`, `Is_Completed`, `execution_duration_days`, `first_payment_lag_days`, `log_in_progress`, `log_sanction`, `n_in_progress`, `n_settled`, `n_vendors`, `paid_vs_peer_log`, `sanction_approval_days`, `utilization`
  - `data/clean/anomaly_scores.csv`
    - Columns: `Work ID`, `Stage`, `rank_in_stage`, `anomaly_score`, `extreme_feature_indicators` (aliased to `top_anomalous_factors`), `State`, `Constituency`, `Hon'ble Members of Parliament`, `Work`, `Sanction_Amount`, `Total_Exp_Settled`, `Total_Exp_In_Progress`, `paid_vs_peer_log`, `n_rule_flags`, and all individual rule flags.

---

### Step 5: Model Evaluation & Blind Audit Generation (`src/evaluate_model.py`)
- **Inputs:** `ml_features.csv`, `mplads_360_master.csv`, `anomaly_scores.csv`
- **Methodologies:**
  1. Seed Stability: Top-300 Jaccard overlap across seeds 0–9 vs 10–19 (Completed: 0.9355, In-Progress: 0.9672).
  2. 5-Trial Held-out Synthetic Injection: 70% clean train, 30% held-out test with 300 planted anomalies (ROC-AUC 0.870 ± 0.004 vs 0.790 ± 0.011 Robust Z baseline).
  3. Clean Data Agreement: 64.7% top-300 agreement on unperturbed data.
  4. Matched-Control Audit Sampling: 50 top-ranked completed works paired with 50 controls drawn strictly from `rank_in_stage > 300` using nearest-neighbor profile matching on installments, vendors, and budget.
- **Outputs:**
  - `data/clean/manual_audit_sample_blind.csv` (100 distinct works, no model features or scores, public for reviewers).
    - Columns: `Work ID`, `Work`, `State`, `Constituency`, `Portal_URL`, `Audit_Verdict`, `Auditor_Notes`
  - `data/clean/manual_audit_sample_key.csv` (PRIVATE backend answer key, never exposed in API or git).
    - Columns: `Work ID`, `Cohort`, `rank_in_stage`, `anomaly_score`, `Settled_Count`, `Unique_Vendors_Count`, `Sanction_Amount`
  - `data/clean/manual_audit_rubric.md` (Standardized auditor instructions and classification definitions).
  - `data/clean/evaluation_results.json` (Phase 1 addition: machine-readable metrics for API/frontend).
  - `data/clean/audit_matching_diagnostics.json` (Phase 1 addition: standardized mean differences).

---

## 4. Rule-Based Screening Indicators Definition

| Flag Name | Type | Logical Definition | Intended Interpretation |
|---|---|---|---|
| `Flag_Duplicate_Payment` | Screening Indicator | Identical `[Work ID + Vendor + Amount + Date]` rows in ledger | Potential double billing or unmerged installment repeat; requires voucher review. |
| `Flag_Same_Day_Bulk_Payment` | Screening Indicator | ≥8 near-equal works (CV ≤ 0.15) to same vendor on same day, all ≤ ₹5 Lakh | Vendor payment concentration across identical small works; tender-splitting screening. |
| `Flag_Ghost_Completion` | Screening Indicator | `Is_Completed == 1` with ₹0 settled, ₹0 pending, and ₹0 reported | Project certified complete with zero recorded fund movement. |
| `Flag_Stalled_Unpaid` | Efficiency Indicator | Sanctioned > 180 days ago with ₹0 payments | Blocked capital sitting idle in sanctioned status. |
| `Missing_Photo_Proof` | Compliance Indicator | Missing completion image on completed project | After 15 May 2026: compliance gap. Before 15 May 2026: legacy record predating requirement. |
| `Flag_Orphan_Payment` | Integrity Check | Payment row with no matching Sanction record | Expected: 0. Stale export artifact check. |
| `Integrity_Cost_Cap_Violation` | Integrity Check | `Total_Exp_Settled > Sanction_Amount * 1.01` | Expected: 0. Validates portal budget enforcement. |
| `Integrity_Date_Sequence_Violation` | Integrity Check | Recommended > Sanction, Sanction > Completion, or Sanction > First Payment | Expected: 0. Validates administrative date sequence consistency. |
