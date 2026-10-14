# 🛡️ MPLADS FundGuard: Full-Stack Public Procurement Screening Platform

> **AI-Powered System to Detect Irregularities, Ledger Anomalies, and Inefficiencies in MPLAD Scheme Implementation**  
> **MoSPI Problem Statement ID:** 26102 | **Department:** Data Informatics & Innovation Division (DIID)

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.65+-FF4B4B.svg)](https://streamlit.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📌 Overview

The Members of Parliament Local Area Development Scheme (MPLADS) funds thousands of civic development projects across India. **MPLADS FundGuard** is an end-to-end data analytics, machine learning screening, and forensic audit platform covering 2.1 lakh records across 543 Lok Sabha MPs.

### Key Capabilities
- 🚨 **Duplicate Payments & Double Billing** — Identifies exact duplicate `[Work ID + Vendor + Amount + Date]` ledger entries.
- 🚨 **Same-Day Bulk Payments** — Flags 8+ near-equal payments (≤₹5L) to a single vendor on the same date.
- 🚨 **Ghost Projects & Missing Photographic Evidence** — Detects completed projects with ₹0 expenditure, and monitors compliance with the post-May 2026 completion photo mandate.
- 🚨 **Multidimensional Peer Anomaly Screening** — Stratified **Isolation Forest ensemble (10 seeds, max_samples=1024)** benchmarked against localized `[Work Category × State]` peer medians.
- 🚨 **Stalled / Blocked Capital** — Identifies works sanctioned >180 days ago with zero disbursements.
- 📋 **Double-Blind Verification Audit** — A matched-control review workspace with standardized rubric for unbiased manual human field verification.

> ⚠️ **Ethical & Legal Disclaimer:** Flags and anomaly scores are exploratory screening signals for manual audit prioritization. They are not evidence of fraud or wrongdoing.
>
> 🏛️ **Scope:** Covers **Lok Sabha MPLADS only** (543 MPs, 18th Lok Sabha). Rajya Sabha data is not included. No MP or Constituency blame rankings or leaderboards are generated.

---

## 🏗️ Full-Stack System Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Streamlit Frontend (UI)                         │
│   • Overview (Macro KPIs, Pipeline Integrity)                          │
│   • EDA (Catalog, Missingness, Plotly Distributions)                   │
│   • Data Quality (14-Point Check Suite & Irregularity Browser)         │
│   • Fund Utilization (State & Category Allocations)                    │
│   • Anomaly Screening (Interactive Table & Deep Dossier Inspection)    │
│   • Model Evaluation (Seed Stability, Synthetic AUC, Limitations)      │
│   • Blind Audit Tool (Reviewer Sheet, Rubric, SMD Balance Analysis)    │
│   • Sanitized CSV Export (Formula injection neutralized)               │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP / JSON (Typed API Client)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                          FastAPI Backend (API)                         │
│   • Healthcheck & CORS Middleware                                      │
│   • Pydantic v2 Schemas & Data Envelopes                               │
│   • In-Memory Repository with Artifact Caching                         │
│   • Strict Key Protection (Answer key is never served or exposed)      │
│   • Graceful 503 Handling with Rebuild Command Instructions            │
│   • Endpoints: /api/v1/{overview, eda, data-quality, fund-utilization, │
│                          anomalies, model-evaluation, audit}           │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Reads Clean Artifacts
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                      Automated Pipeline Rebuilder                      │
│   • src/rebuild.py (Orchestrates 6 steps sequentially)                 │
│   1. eda/eda_pipeline.py ──► Masks PII & Standardizes IDs              │
│   2. eda/eda_checks.py   ──► Input Quality Gate                        │
│   3. src/build_master.py ──► 360° Master Join & Rule Flags             │
│   4. eda/eda_checks.py   ──► Output Quality Gate                       │
│   5. src/build_ml_features.py ──► Stratified Isolation Forest Scores   │
│   6. src/evaluate_model.py    ──► Evaluation & Blind Audit Matching    │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start Guide

### 1. Local Environment Setup

```bash
git clone https://github.com/v1-n/MpladsFundGuard.git
cd MpladsFundGuard

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Generate Pipeline Data Artifacts

If running on a fresh clone with raw portal exports in `data/raw/`:
```bash
python -m src.rebuild
```
This executes all 6 pipeline stages sequentially and generates verified artifacts in `data/clean/`:
- `mplads_360_master.csv` (84,271 unique works)
- `anomaly_scores.csv` (58,050 scored works with peer tiers and explanations)
- `manual_audit_sample_blind.csv` (100 blind audit works)
- `data_quality_report.json` (14-point audit report)
- `evaluation_results.json` (synthetic benchmark metrics)
- `audit_matching_diagnostics.json` (control balance diagnostics)

### 3. Launch Backend API (FastAPI)

```bash
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
- API Health: `http://127.0.0.1:8000/health`
- Interactive Swagger UI: `http://127.0.0.1:8000/api/v1/docs`

### 4. Launch Frontend App (Streamlit)

In a separate terminal:
```bash
source venv/bin/activate
streamlit run frontend/app.py
```
Open `http://localhost:8501` in your browser.

---

## 🐳 Docker Deployment

Run the entire platform with Docker Compose:

```bash
docker compose up --build
```
- **Streamlit Web UI:** `http://localhost:8501`
- **FastAPI Documentation:** `http://localhost:8000/api/v1/docs`

---

## 🧪 Automated Test Suite

Run unit and integration tests across the backend, schemas, frontend client, and security assertions:

```bash
PYTHONPATH=. pytest -v
```
**Verification Coverage (27 passed tests):**
- System health and disclaimer validation
- Overview KPIs and zero-orphan integrity checks
- EDA distributions and missing-value endpoints
- Data quality rules, flags, and pagination
- State and category fund utilization
- Multi-dimensional anomaly scoring and detailed dossiers
- Synthetic evaluation reproduction and limitation disclosure
- **Strict Blind Audit Security:** Asserts answer key is never accessible, and verifies blind sample contains no score or cohort fields
- **Formula Injection Defense:** Verifies CSV export prepends single quotes to dangerous leading characters (`=`, `+`, `-`, `@`, `\t`, `\r`)
- **Missing Artifacts Behavior:** Verifies 503 response code with exact rebuild instructions

---

## 📊 Summary of Findings

- **84,271 Unique Works** in master dataset across 543 Lok Sabha constituencies
- **454 Duplicate Payment works** detected in transaction records
- **12,529 Same-Day Bulk Payment works** (split disbursements ≤₹5L)
- **75 Ghost Completions** (marked completed with ₹0 settled and ₹0 pending expenditure)
- **21 Post-Cutoff Missing Photos** (completions after May 2026 lacking required photo evidence)
- **10,687 Stalled Unpaid Works** (>180 days idle since sanction)

### ML Benchmark Metrics (Completed Works Cohort)
- **Seed Stability:** Top-300 Jaccard similarity of **0.9355** (Completed) and **0.9672** (In-Progress) across 10 random seeds.
- **Held-Out Synthetic ROC-AUC:** **0.870 ± 0.004** (vs 0.790 for Robust Z-Score baseline).
- **Precision @ 2% Top-Ranked:** **19.9% ± 2.3%** (~7.4× lift over 2.7% base rate).
- **Clean Baseline Agreement:** 64.7% overlap (194/300) with non-parametric Robust Z baseline.
- **Matched-Control Blind Audit:** 100-work balanced sample (50 top-ranked vs 50 matched controls ranked >300).

---

## 🛡️ Security & Privacy Practices

1. **PII Protection:** Phone numbers and sensitive contact details in raw portal extracts are dynamically masked during ingestion. Raw data files are gitignored.
2. **Audit Integrity:** Answer keys (`manual_audit_sample_key.csv`) are strictly quarantined from all API endpoints and frontend views to guarantee unbiased manual review.
3. **Spreadsheet Security:** All CSV downloads neutralize spreadsheet formula injection vulnerabilities (`=`, `+`, `-`, `@`, `\t`, `\r`).
4. **Data Isolation:** Fresh clones without generated data receive HTTP 503 errors pointing to `python -m src.rebuild` without exposing internal filesystem paths.

---

## 📜 License
Distributed under the MIT License. See [LICENSE](LICENSE) for details.
