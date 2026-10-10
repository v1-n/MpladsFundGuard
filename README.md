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

> **Scope:** Current data extracts cover **Lok Sabha MPs only** (543 of 774 MPs in the summary). The MP summary lists 231 Rajya Sabha MPs with ₹1,232 cr of spend that is not covered by the sanction/expenditure/completion files.

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

# Step 5: Train Isolation Forest & Generate Anomaly Rankings
python3 src/build_ml_features.py
```

---

## 📊 Key Findings

- **84,271 Unique Works** in the master dataset (Lok Sabha only)
- **454 Duplicate Payment works** detected using the key [Work ID + Vendor + Amount + Date]
- **12,529 Same-Day Bulk Payment works** — 8+ near-equal payments to one vendor on the same day, all ≤₹5L each
- **75 Ghost Completions** — works reported as completed with ₹0 reported disbursement and ₹0 ledger settled
- **21 Post-Cutoff Missing Photos** — completions after 15 May 2026 lacking photo proof (photos appear required after that date; 9,279 earlier completions predate the requirement)
- **10,687 Stalled Unpaid** — sanctioned >180 days ago with zero payments

### ML Anomaly Scoring (Isolation Forest)
- **58,050 works scored** (works with at least one settled payment)
- **1,939 pending-only works excluded** (trivial outliers with zero settled amounts)

*Note on structural overlaps:* The top 500 statistically anomalous works have a higher concentration of Duplicate Payment flags (4.0% vs 0.8% base) and Same-Day Bulk Payment flags (31.4% vs 21.6% base). However, these flags apply to works with multiple payment installments, and the Isolation Forest naturally scores works with many installments as structural outliers. Therefore, this overlap reflects the model's sensitivity to multi-transaction works rather than independent validation of fraud.

The top 500 anomalies also differ structurally from the cohort:
- **Fewer completions**: 18.4% completed vs 63.7% in the base cohort.
- **More installments**: Average 4.8 installments vs 1.5.
- **More vendors**: Average 3.1 vendors vs 1.2.

---

## 📜 License
MIT License — see [LICENSE](LICENSE)
