import sys
from pathlib import Path

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pandas as pd
import streamlit as st
from frontend.api_client import api_client, APIError
from frontend.theme import inject_css
from frontend.components.disclaimer import render_disclaimer_banner
from frontend.components.formatters import lakh_crore, pct, compact
from frontend.components.metrics import metric_grid
from frontend.components.cards import section_header, info_card, empty_state
from frontend.components.progress import pipeline_tracker
from frontend.components.dataframe import styled_table

st.set_page_config(
    page_title="MPLADS FundGuard | Public Expenditure Screening",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Apply global styling & typography
inject_css()

# Sidebar
with st.sidebar:
    st.title("🛡️ MPLADS FundGuard")
    st.caption("v2.0 • Public Procurement Screening & Anomaly Auditing")

    try:
        health = api_client.check_health()
        st.success("🟢 Backend API Connected", icon="✅")
    except APIError as e:
        if e.is_rebuild_needed:
            st.error("⚠️ Data Artifacts Missing")
            st.code("python -m src.rebuild", language="bash")
        else:
            st.error("🔴 Backend Disconnected")
            st.caption(f"{e.message}")
    except Exception as e:
        st.error(f"🔴 Connection Error: {e}")

    st.divider()
    st.markdown("### 📌 Navigation")
    st.caption("Select a page above to start:")
    st.markdown(
        """
        - **1. Overview:** Macro statistics & pipeline integrity
        - **2. EDA:** Dataset shapes, missingness, distributions
        - **3. Data Quality:** 14-point ledger rules & flagged works
        - **4. Fund Utilization:** State & category allocations
        - **5. Anomaly Screening:** Outlier scoring & deep-dives
        - **6. Model Evaluation:** Seed stability & synthetic benchmark
        - **7. Blind Audit:** Unbiased manual verification tool
        - **8. Methodology:** Platform architecture & governance
        """
    )
    st.divider()
    st.caption("Lok Sabha procurement data • 543 Constituencies")

# Hero Title
st.title("🛡️ MPLADS FundGuard")
st.subheader("Public Expenditure Screening & Anomaly Prioritization Platform")
render_disclaimer_banner(include_scope=True)

# Fetch overview data
overview = {}
try:
    overview = api_client.get_overview()
except Exception as e:
    st.error(f"Failed to load pipeline overview metrics: {e}")

if overview:
    # Row 1: Pipeline & Expenditure Scale
    section_header(
        title="1. Pipeline Scale & Financial Scope",
        subtitle="18th Lok Sabha public procurement ledger coverage",
        badge="Scope: Lok Sabha",
    )
    scale_items = [
        {
            "label": "Unique Works in Master",
            "value": compact(overview.get("total_works")),
            "subtext": f"{overview.get('completed_works', 0):,} completed • {overview.get('in_progress_works', 0):,} in-progress",
            "badge": "360° Master",
            "badge_variant": "neutral",
        },
        {
            "label": "ML-Scored Works",
            "value": compact(overview.get("pipeline_counts", {}).get("ml_scored_works") or 58050),
            "subtext": "Active spending projects with peer baselines",
            "badge": "Scored Cohort",
            "badge_variant": "purple",
        },
        {
            "label": "Total Sanctioned",
            "value": lakh_crore(overview.get("total_sanctioned_amount")),
            "subtext": "Approved allocations across 543 MPs",
            "badge": "Sanctioned",
            "badge_variant": "neutral",
        },
        {
            "label": "Settled Expenditure",
            "value": lakh_crore(overview.get("total_settled_expenditure")),
            "subtext": f"Unspent: {lakh_crore(overview.get('remaining_unspent_amount'))}",
            "badge": "Disbursed",
            "badge_variant": "pass",
        },
    ]
    metric_grid(scale_items, cols=4)

    # Row 2: Screening Signals & Integrity
    integ = overview.get("integrity_checks", {})
    integ_status = integ.get("status", "NOT VERIFIED")
    integ_variant = "pass" if integ_status == "PASS" else ("warn" if integ_status == "WARN" else "fail")

    section_header(
        title="2. Screening Signals & Ledger Integrity",
        subtitle="Automated ledger rule alerts and pipeline validation status",
        badge="Automated Screening",
    )
    screening_items = [
        {
            "label": "Stalled Unpaid Works",
            "value": compact(overview.get("stalled_unpaid_works")),
            "subtext": "Sanctioned > 180 days with ₹0 paid",
            "badge": "Review Signal",
            "badge_variant": "warn",
        },
        {
            "label": "Same-Day Bulk Payments",
            "value": compact(overview.get("same_day_bulk_payment_works")),
            "subtext": "≥8 works to one vendor on same date",
            "badge": "Review Signal",
            "badge_variant": "warn",
        },
        {
            "label": "Ghost Completions",
            "value": compact(overview.get("ghost_completion_works")),
            "subtext": "Reported complete with ₹0 settled",
            "badge": "Review Signal",
            "badge_variant": "fail",
        },
        {
            "label": "Ledger Accounting Status",
            "value": integ_status,
            "subtext": f"{integ.get('orphan_payments', 0)} orphans • {integ.get('cost_cap_violations', 0)} cost cap breaches",
            "badge": "Integrity Gate",
            "badge_variant": integ_variant,
        },
    ]
    metric_grid(screening_items, cols=4)

# Methodology Pipeline Tracker
section_header(
    title="3. Automated Audit & Screening Methodology",
    subtitle="Reproducible 8-stage data pipeline from public ingestion to double-blind verification",
)
pipeline_tracker(overview.get("pipeline_stages"))

# Quick Navigation Launch Cards
section_header(
    title="4. Platform Modules",
    subtitle="Direct access to analysis, data quality auditing, and verification tools",
)
c1, c2, c3 = st.columns(3)
with c1:
    info_card(
        title="📊 Executive Overview",
        content="Macro portfolio figures, lifecycle stage distribution, financial burn down, and data provenance.",
        icon="📊",
    )
    info_card(
        title="🔍 Data Quality Audit",
        content="14-point zero-defect pipeline verification gates and canonical 8-rule browser for flagged works.",
        icon="🔍",
    )
with c2:
    info_card(
        title="📈 Exploratory Data Analysis",
        content="Empirical feature distributions with log toggles, missingness diagnostics, and category allocations.",
        icon="📈",
    )
    info_card(
        title="💳 Fund Utilization",
        content="Inter-state and category utilization distributions, expenditure timelines, and peer benchmarks.",
        icon="💳",
    )
with c3:
    info_card(
        title="🎯 Anomaly Screening",
        content="Unsupervised Isolation Forest + Robust Z-scores benchmarked against peer cohorts for audit prioritization.",
        icon="🎯",
        variant="purple",
    )
    info_card(
        title="⚖️ Blind Audit & Evaluation",
        content="Scientifically balanced double-blind reviewer sheet and SMD diagnostics for manual human ground truth.",
        icon="⚖️",
    )

# Neutral Top Review Priority Preview
section_header(
    title="5. Review Priority Preview (Completed Works Cohort)",
    subtitle="Top multi-dimensional outliers flagged for audit resource prioritization",
    badge="Top Review Priority",
)
st.caption(
    "Works are ranked by multidimensional deviation from peer cohort baselines (category & state). "
    "Rankings are prioritization indicators for manual verification, not assertions of wrongdoing."
)

try:
    top_items, _ = api_client.get_anomalies(
        stage="Completed",
        sort_by="rank_in_stage",
        sort_order="asc",
        page=1,
        page_size=10,
    )
    if top_items:
        preview_data = []
        for it in top_items:
            sanction_val = lakh_crore(it.get("sanction_amount"))
            settled_val = lakh_crore(it.get("total_exp_settled"))
            preview_data.append({
                "Priority Rank": f"#{it['rank_in_stage']}",
                "Work ID": it["work_id"],
                "State": it["state"],
                "Constituency": it["constituency"],
                "Work Description": it["work"][:65] + ("..." if len(it["work"]) > 65 else ""),
                "Sanctioned": sanction_val,
                "Settled": settled_val,
                "Peer Tier": it.get("peer_tier", "—"),
                "Key Deviation Indicators": it.get("top_anomalous_factors", "—"),
                "Rule Flags": it.get("n_rule_flags", 0),
            })
        preview_df = pd.DataFrame(preview_data)
        styled_table(preview_df)
    else:
        empty_state("No priority works found in completed cohort.")
except Exception as e:
    st.info(f"Priority preview currently unavailable: {e}")
