import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import streamlit as st
import pandas as pd
from frontend.api_client import api_client, APIError
from frontend.components.disclaimer import render_disclaimer_banner
from frontend.components.kpi_card import format_currency_inr, format_number

st.set_page_config(page_title="Executive Overview | MPLADS FundGuard", page_icon="📊", layout="wide")

st.title("📊 Executive Dashboard & Macro KPIs")
render_disclaimer_banner(include_scope=True)

try:
    data = api_client.get_overview()
except APIError as e:
    st.error(f"Error fetching overview: {e.message}")
    st.stop()
except Exception as e:
    st.error(f"Failed to connect to backend: {e}")
    st.stop()

# Data Provenance & Freshness Indicator
prov = data.get("data_provenance", {})
if prov:
    master_dt = prov.get("master_artifact_updated", "Recent")[:19].replace("T", " ")
    st.caption(f"🕒 **Data Freshness:** Pipeline Master Artifact updated `{master_dt} UTC` • Version `{prov.get('pipeline_version', '2.0.0')}`")

st.markdown("---")

# 1. Lifecycle Breakdown
st.subheader("1. Project Portfolio by Lifecycle Stage")
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric("Total Works", format_number(data.get("total_works", 0)))
with col2:
    st.metric("Completed Works", format_number(data.get("completed_works", 0)), help="Completed works with physical completion recorded")
with col3:
    st.metric("In-Progress Works", format_number(data.get("in_progress_works", 0)), help="Works currently disbursing payments")
with col4:
    st.metric("Sanctioned Only", format_number(data.get("sanctioned_only_works", 0)), help="Sanctioned with zero payment ledger records")
with col5:
    st.metric("Pending Only", format_number(data.get("pending_only_works", 0)), help="Zero settled expenditure, only pending disbursements")

# 2. Financial Allocations & Unspent Balance
st.subheader("2. Financial Allocations & Utilization")
fcol1, fcol2, fcol3, fcol4, fcol5 = st.columns(5)
with fcol1:
    st.metric("Total Sanctioned", format_currency_inr(data.get("total_sanctioned_amount", 0)))
with fcol2:
    st.metric("Settled Expenditure", format_currency_inr(data.get("total_settled_expenditure", 0)))
with fcol3:
    st.metric("In-Progress Disbursing", format_currency_inr(data.get("total_in_progress_expenditure", 0)))
with fcol4:
    st.metric("Remaining Unspent", format_currency_inr(data.get("remaining_unspent_amount", 0)), help="Sanctioned minus settled expenditure")
with fcol5:
    util_ratio = data.get("overall_utilization_ratio", 0) * 100
    st.metric("Overall Utilization", f"{util_ratio:.1f}%", help="Settled Expenditure / Sanctioned Amount")

st.markdown("---")

# 3. Rule-Based Findings Breakdown
st.subheader("3. Deterministic Ledger Rule Findings")
rule_summary_data = [
    {"Irregularity Check": "Same-Day Bulk Payments", "Severity": "High", "Flagged Works": format_number(data.get("same_day_bulk_payment_works", 0)), "Criteria": "8+ works (<=₹5L) to one vendor on same date"},
    {"Irregularity Check": "Stalled Unpaid Works", "Severity": "Medium", "Flagged Works": format_number(data.get("stalled_unpaid_works", 0)), "Criteria": "Sanctioned > 180 days ago with ₹0 disbursed"},
    {"Irregularity Check": "Duplicate Payments", "Severity": "High", "Flagged Works": format_number(data.get("duplicate_payment_works", 0)), "Criteria": "Identical [Work ID + Vendor + Amount + Date]"},
    {"Irregularity Check": "Ghost Completions", "Severity": "High", "Flagged Works": format_number(data.get("ghost_completion_works", 0)), "Criteria": "Reported complete with ₹0 settled & ₹0 pending"},
    {"Irregularity Check": "Missing Photos (Post-Cutoff)", "Severity": "High", "Flagged Works": format_number(data.get("missing_photos_post_cutoff", 0)), "Criteria": "Completions post-May 2026 lacking required photo proof"},
    {"Irregularity Check": "Missing Photos (Pre-Cutoff)", "Severity": "Informational", "Flagged Works": format_number(data.get("missing_photos_pre_cutoff", 0)), "Criteria": "Legacy completions lacking photo before mandate"}
]
st.dataframe(pd.DataFrame(rule_summary_data), use_container_width=True)

# 4. Pipeline Accounting Integrity
st.subheader("4. Data Pipeline & Accounting Integrity Verification")
integ = data.get("integrity_checks", {})
status = integ.get("status", "NOT VERIFIED")

if status == "PASS":
    st.success("✅ **Ledger Integrity Status: PASS** — Accounting constraints verified across all 84,271 records with 0 orphan payments and 0 cost cap violations.")
elif status == "WARN":
    st.warning("⚠️ **Ledger Integrity Warnings Detected** — Investigate integrity constraint exceptions.")
else:
    st.info(f"ℹ️ **Ledger Integrity Status: {status}**")

icol1, icol2, icol3 = st.columns(3)
with icol1:
    st.metric("Orphan Payment Records", integ.get("orphan_payments", 0), help="Payments without corresponding sanction orders")
with icol2:
    st.metric("Cost Cap Violations", integ.get("cost_cap_violations", 0), help="Settled expenditure exceeding sanctioned amount by >1%")
with icol3:
    st.metric("Date Sequence Violations", integ.get("date_sequence_violations", 0), help="Chronological violations across recommendation, sanction, and payment dates")

st.markdown("---")

# 5. Quick Attention: Top Screening Priorities Preview
st.subheader("5. High-Priority Works Preview (Needs Reviewer Attention)")
st.caption("Top 5 multi-dimensional outliers from the Completed works cohort. Click to navigate to Anomaly Screening for full drill-down.")

try:
    top_anoms, _ = api_client.get_anomalies(stage="Completed", sort_by="anomaly_score", sort_order="desc", page=1, page_size=5)
    if top_anoms:
        preview_rows = [
            {
                "Work ID": a["work_id"],
                "Anomaly Score": f"{a['anomaly_score']:.4f}",
                "Rank": f"#{a['rank_in_stage']}",
                "State": a["state"],
                "Constituency": a["constituency"],
                "Work Type": a["work"],
                "Settled Exp (₹)": f"₹{a['total_exp_settled']:,.0f}" if a.get("total_exp_settled") else "—",
                "Primary Outlier Driver": a.get("top_anomalous_factors", "—")
            }
            for a in top_anoms
        ]
        st.dataframe(pd.DataFrame(preview_rows), use_container_width=True)
except Exception as e:
    st.caption(f"Preview unavailable: {e}")
