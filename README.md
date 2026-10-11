# 🛡️ MpladsFundGuard

> **AI-Powered System to Detect Anomalies, Fraud, and Inefficiencies in MPLAD Scheme Implementation**  
> **MoSPI Problem Statement ID:** 26102 | **Department:** Data Informatics & Innovation Division (DIID)

---

## 📌 Overview
The Members of Parliament Local Area Development Scheme (MPLADS) involves large-scale fund utilization and execution of thousands of civic works. **MpladsFundGuard** is an end-to-end AI and forensic data analytics platform designed to detect:
- 🚨 **Duplicate Payments & Double Billing** — identical [Work ID + Vendor + Amount + Date] rows in the ledger
- 🚨 **Same-Day Bulk Payments** — 8+ near-equal payments to one vendor on the same day, all ≤₹5L
- 🚨 **Ghost Projects & Missing Photographic Evidence** — completed works lacking geo-tagged images (photos appear required after 15 May 2026)
- 🚨 **Multidimensional Cost & Delay Anomalies** — via Unsupervised **Isolation Forest** & **Peer Normalization**
- 🚨 **Stalled / Blocked Capital** — sanctioned works idle for >180 days with ₹0 disbursed
- 📈 **Scale** — built an audit pipeline over 2.1 lakh MPLADS records for 543 Lok Sabha MPs

> **Scope:** This project covers **Lok Sabha MPLADS only** (543 MPs). Rajya Sabha members are out of scope, meaning these figures do not represent the entirety of Parliament.

---

## 🏗️ Architecture & Data Pipeline

```
┌─────────────────────────────────────────────────────────┐
│ 1. Data Cleaning & Standardization                      │
│    📄 eda/eda_pipeline.py                               │
│    • Normalizes Work IDs (removes backticks/tabs/noise) │
│    • Preserves missing values (blanks ≠ zero)           │
│    • Masks PII (phone numbers) dynamically              │
│    • Strict ISO Date parsing with fallback              │
└───────────────────────────┬─────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│ 1b. Data Quality Gate (Input)                           │
│    📄 eda/eda_checks.py                                 │
│    • Validates columns, Work ID format, join coverage   │
│    • Payment status audit, NaN vs zero, PII scan        │
│    • Financial reconciliation totals                    │
└───────────────────────────┬─────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│ 2. 360° Master Lifecycle Join & Forensic Indicators     │
│    📄 src/build_master.py                               │
│    • Collapses 1-to-many payment transactions (1-to-1)  │
│    • Merges Sanction ──► Expenditure ──► Completion     │
│    • Flags duplicate payments & bulk payments           │
│    • Exports data/clean/mplads_360_master.csv (45 cols) │
└───────────────────────────┬─────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│ 2b. Data Quality Gate (Output)                          │
│    📄 eda/eda_checks.py (re-run)                        │
│    • Rule-firing prevalence diagnostics                 │
│    • Missing-photo flag rate over time                  │
└───────────────────────────┬─────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│ 3. Machine Learning Anomaly Engine                      │
│    📄 src/build_ml_features.py                          │
│    • Peer benchmarking: log(paid) - log(peer_median)    │
│    • Unsupervised Isolation Forest (300 estimators)     │
│    • Scores only works with settled payments            │
│    • Outputs data/clean/anomaly_scores.csv              │
└─────────────────────────────────────────────────────────┘
```

---

## 📥 Data

The raw data must be downloaded manually from the [MPLADS Portal](https://www.mplads.gov.in/) before running the pipeline. Place these files in `data/raw/`:

| File | Portal Export |
|------|-------------|
| `Works Sanctioned.csv` | Works Sanctioned report |
| `Expenditure on Completed and On-going Works as on Date.csv` | Expenditure report |
| `Works Completed.csv` | Works Completed report |
| `mplads_mp_summary_*.csv` | MP Summary report |

> **PII note:** Raw files contain phone numbers. The pipeline masks them automatically in `data/clean/`. Raw files are `.gitignore`d and never tracked.

---

## 🚀 Quick Start

### 1. Setup Environment
```bash
git clone https://github.com/v1-n/MpladsFundGuard.git
cd MpladsFundGuard

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Run the Complete Pipeline
```bash
# Step 1: Clean raw data and mask PII
python3 eda/eda_pipeline.py

# Step 2: Data Quality Gate (Input — validates clean files)
python3 eda/eda_checks.py

# Step 3: Build the 360° Forensic Master Dataset
python3 src/build_master.py

# Step 4: Data Quality Gate (Output — validates flags and master)
python3 eda/eda_checks.py

# Step 5: Train Stratified Isolation Forest & Generate Anomaly Rankings
python3 src/build_ml_features.py

# Step 6: Run Comprehensive Model Evaluation & Stability Suite
python3 src/evaluate_model.py
```

---

## 📊 Key Findings

- **84,271 Unique Works** in the master dataset (Lok Sabha only)
- **454 Duplicate Payment works** detected using the key [Work ID + Vendor + Amount + Date]
- **12,529 Same-Day Bulk Payment works** — 8+ near-equal payments to one vendor on the same day, all ≤₹5L each
- **75 Ghost Completions** — works reported as completed with ₹0 reported disbursement and ₹0 ledger settled
- **21 Post-Cutoff Missing Photos** — completions after 15 May 2026 lacking photo proof (photos appear required after that date; 9,279 earlier completions predate the requirement)
- **10,687 Stalled Unpaid** — sanctioned >180 days ago with zero payments

### ML Anomaly Scoring & Synthetic Benchmark
Because no ground-truth fraud labels exist in public procurement datasets, the model is evaluated via **reproducibility across random seeds, controlled synthetic outlier injection, non-parametric baseline comparison, and blind human review**:

1. **Stratified Scoring Architecture:** Works are split into separate Completed (36,989) and In-Progress (21,061) cohorts to avoid duration and partial-spend confounding.
2. **Fine-Grained Peer Benchmarks:** Costs are benchmarked against the median for specific `[Work, State]` pairs (91.6% tier 1, 8.0% national work tier 2, 0.4% global fallback).
3. **Run-to-Run Stability:** 10-seed ensemble averaging with `max_samples=1024` achieves a **0.9355 Jaccard overlap** on Completed works and **0.9672** on In-Progress works for the top-300 works across independent seed ensembles.
4. **Synthetic Outlier Injection Benchmark (5 Independent Held-Out Trials):** Evaluated strictly on a 70% clean train / 30% held-out test split with 300 planted multi-dimensional anomalies (cost surges, vendor fragmentation, timeline anomalies):
   - **Isolation Forest:** ROC-AUC **0.870 ± 0.004** | Precision@2% **19.9% ± 2.3%** | Recall@2% **14.7% ± 1.7%** (Type A Cost: 9.0%, Type B Count: 33.4%, Type C Timeline: 1.6%).
   - **Robust Z-Score Baseline:** ROC-AUC **0.790 ± 0.011** | Precision@2% **16.5% ± 1.5%** | Recall@2% **12.1% ± 1.1%** (Type A Cost: 7.8%, Type B Count: 27.0%, Type C Timeline: 1.6%).
   - *Base Rate Context:* The injected test base rate is 2.7%; Precision@2% of 19.9% represents a **~7.4× lift over random guessing**.
   - *Timeline Limitation:* Both models show low recall (~1.6%) on injected timeline compression because single-feature values (0-day payment lag, 1-day approval) already appear naturally in 3–4% of legitimate works.
5. **Clean Data Baseline Agreement:** Top-300 works share **64.7% overlap (194/300)** with non-parametric Robust Z-Scores on clean untouched data. The two methods rank ~35% of their top works differently, reflecting different sensitivity to multi-variable geometry versus marginal extremes.
6. **Interpretability & De-biased Blind Audit:** Top anomalies are tagged with extreme feature indicators (≥98th percentile). A de-biased 100-work blind audit sheet (100 distinct works, political and regional identifiers removed) is exported to `data/clean/manual_audit_sample_blind.csv` alongside a standardized audit rubric in `data/clean/manual_audit_rubric.md` (classifying works as *Routine*, *Needs document check*, or *Inconsistent data*).

---

## 📜 License
MIT License — see [LICENSE](LICENSE)
