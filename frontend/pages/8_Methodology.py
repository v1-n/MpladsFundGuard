import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import streamlit as st
from frontend.theme import inject_css
from frontend.components.disclaimer import render_disclaimer_banner
from frontend.components.cards import section_header, info_card
from frontend.components.progress import pipeline_tracker

st.set_page_config(
    page_title="Methodology & Governance | MPLADS FundGuard",
    page_icon="📖",
    layout="wide",
)

inject_css()

st.title("📖 Platform Methodology & Governance Framework")
render_disclaimer_banner(include_scope=True)

st.markdown(
    """
    **MPLADS FundGuard** provides reproducible, data-driven screening of public procurement records under the
    **Members of Parliament Local Area Development Scheme (MPLADS)** for the **18th Lok Sabha**.
    This document outlines the end-to-end data processing architecture, validation gates, statistical models,
    and governance safeguards governing the platform.
    """
)

# Pipeline Architecture Overview
section_header(
    title="1. End-to-End Processing Architecture",
    subtitle="The 8-stage data pipeline from raw portal records to double-blind verification",
)
pipeline_tracker()

# Detailed Sections
section_header(
    title="2. Scope & Public Ledger Provenance",
    subtitle="Coverage and data boundaries",
)
c1, c2 = st.columns(2)
with c1:
    info_card(
        title="Lok Sabha Scope (543 MPs)",
        content="The system monitors public expenditure across all 543 Lok Sabha parliamentary constituencies of the 18th Lok Sabha. Data is derived directly from the official Ministry of Statistics and Programme Implementation (MoSPI) public ledger.",
        icon="🏛️",
    )
with c2:
    info_card(
        title="Ledger Cleanliness & Foreign Key Integrity",
        content="The raw portal data contains 86,527 work entries. The normalization pipeline enforces strict relational constraints: foreign-key integrity between payment vouchers and sanction orders, deduplication of portal submissions, and timestamp validation.",
        icon="🛡️",
    )

section_header(
    title="3. 14-Point Pipeline Quality Gates",
    subtitle="Distinguishing input data realities from output integrity gates",
)
st.markdown(
    """
    The data pipeline executes a 14-point audit before generating model inputs:
    - **Input Quality Audits (Checks 1–10):** Document real-world reporting patterns in public data, including legacy missing photographs (prior to the May 2026 geotagging mandate), missing contractor start dates, and unrecorded vendor entities.
    - **Output Integrity Gates (Checks 11–14):** Enforce strict database invariants. If any output integrity gate fails (e.g. orphan payment records without matching sanction orders, or settled expenditure exceeding sanctioned budgets by >1%), the pipeline flags an error to prevent corrupted data from reaching the scoring models.
    """
)

section_header(
    title="4. Deterministic Ledger Screening Rules",
    subtitle="8 canonical deterministic checks applied across all records",
)
st.markdown(
    """
    1. **Same-Day Bulk Payments:** Identifies instances where ≥8 works (each ≤₹5 Lakh) are disbursed to a single contractor on the exact same date. While often representing administrative batch processing by district treasuries, it serves as a screening signal for potential contract splitting.
    2. **Stalled Unpaid Works:** Projects sanctioned >180 days ago with zero expenditure recorded in the ledger, indicating procurement bottlenecks or retendering delays.
    3. **Duplicate Payment Rows:** Exact matching records sharing identical `[Work ID + Vendor + Amount + Date]`, surfacing potential double-entry portal clerical errors.
    4. **Ghost Completions:** Works marked complete on the portal with ₹0 settled and ₹0 pending expenditure.
    5. **Missing Photos (Post-Cutoff):** Completed works after May 2026 lacking required geotagged physical asset proof.
    6. **Missing Photos (Pre-Cutoff):** Historical completions prior to the photographic mandate.
    7. **Orphan Payments:** Expenditure rows lacking a parent administrative sanction record.
    8. **Cost Cap Violations:** Disbursed amounts exceeding approved budget by >1%.
    """
)

section_header(
    title="5. Unsupervised Anomaly Screening & Peer Normalization",
    subtitle="Ensemble Isolation Forest and Robust Z-score methodology",
)
m1, m2 = st.columns(2)
with m1:
    info_card(
        title="Stratified Peer Benchmarking",
        content="Raw expenditure comparisons across different project types (e.g. handpumps vs school buildings) produce misleading anomalies. FundGuard groups works into peer cohorts based on Sectoral Category and State. Deviation metrics are computed relative to the peer group median.",
        icon="⚖️",
        variant="purple",
    )
with m2:
    info_card(
        title="Multi-Seed Ensemble Isolation Forest",
        content="To eliminate instability from random forest partitioning, the system trains an ensemble across 10 random seeds with max_samples=1024. Anomaly scores represent multidimensional deviation from normal peer behavior.",
        icon="🌲",
        variant="purple",
    )

section_header(
    title="6. Double-Blind Manual Audit Protocol",
    subtitle="Scientific ground-truth collection and SMD balance diagnostics",
)
st.markdown(
    """
    Because public expenditure datasets do not contain pre-existing ground-truth labels for fraudulent transactions:
    - **Circular Bias Elimination:** Reviewers evaluating projects must not be shown model scores, ranks, or cohort labels.
    - **Balanced Control Matching:** 50 top-ranked outliers are paired with 50 matched control works selected strictly outside the top-300 (`controls_min_rank >= 300`) within the same work categories.
    - **Covariate Balance (SMD):** Standardized Mean Differences are monitored to ensure controls share comparable project scopes and budgets.
    - **Standardized Rubric:** Auditors inspect official completion photos, contractor invoices, and execution timelines against a published rubric.
    """
)

section_header(
    title="7. Legal, Ethical & Screening Safeguards",
    subtitle="Principles governing responsible use of screening tools",
)
st.markdown(
    """
    - **Screening, Not Accusation:** Anomaly scores and rule flags are signals designed to optimize manual audit resources. They do not constitute evidence of wrongdoing or fraud.
    - **No Public Blaming or Rankings:** The platform strictly prohibits generating comparative rank lists, competitive MP standings, or blame scorecards.
    - **Defense in Depth:** All tabular data exports sanitize cells against spreadsheet formula injection (`=`, `+`, `-`, `@`, `\t`, `\r`).
    - **Transparent Limitations:** Synthetic benchmark metrics are clearly documented as measures of artificial perturbation recovery, and no real-world precision is asserted prior to human field verification.
    """
)
