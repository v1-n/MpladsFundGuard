import streamlit as st
import pandas as pd
from frontend.api_client import api_client, APIError
from frontend.components.disclaimer import render_disclaimer_banner
from frontend.components.kpi_card import format_currency_inr, format_number

st.set_page_config(page_title="Overview | MPLADS FundGuard", page_icon="📊", layout="wide")

st.title("📊 Overview & System Macro KPIs")
render_disclaimer_banner(include_scope=True)

try:
    data = api_client.get_overview()
except APIError as e:
    st.error(f"Error fetching overview: {e.message}")
    st.stop()
except Exception as e:
    st.error(f"Failed to connect to backend: {e}")
    st.stop()

st.markdown("### 1. Work Volume by Lifecycle Stage")
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
    st.metric("Pending Only", format_number(data.get("pending_only_works", 0)), help="Zero settled expenditure, only pending payments")

st.markdown("---")

st.markdown("### 2. Financial Allocations & Overall Utilization")
fcol1, fcol2, fcol3, fcol4 = st.columns(4)
with fcol1:
    st.metric("Total Sanctioned", format_currency_inr(data.get("total_sanctioned_amount", 0)))
with fcol2:
    st.metric("Total Settled Expenditure", format_currency_inr(data.get("total_settled_expenditure", 0)))
with fcol3:
    st.metric("Total In-Progress / Pending", format_currency_inr(data.get("total_in_progress_expenditure", 0)))
with fcol4:
    util_ratio = data.get("overall_utilization_ratio", 0) * 100
    st.metric("Overall Utilization Ratio", f"{util_ratio:.1f}%", help="Total Settled Expenditure / Total Sanctioned Amount")

st.markdown("---")

st.markdown("### 3. Rule-Based Irregularities & Quality Screening")
qcol1, qcol2, qcol3, qcol4 = st.columns(4)
with qcol1:
    st.metric("Duplicate Payments", format_number(data.get("duplicate_payment_works", 0)), help="Exact identical (Work ID, Vendor, Amount, Date) transactions")
with qcol2:
    st.metric("Same-Day Bulk Payments", format_number(data.get("same_day_bulk_payment_works", 0)), help="≥8 works (<=Rs 5L) to a single vendor on the same date")
with qcol3:
    st.metric("Ghost Completions", format_number(data.get("ghost_completion_works", 0)), help="Marked completed with Rs 0 settled and Rs 0 pending expenditure")
with qcol4:
    st.metric("Stalled Unpaid Works", format_number(data.get("stalled_unpaid_works", 0)), help="Sanctioned > 180 days ago with zero disbursements")

col_photo1, col_photo2 = st.columns(2)
with col_photo1:
    st.warning(f"📷 **Post-Cutoff Missing Photos:** **{data.get('missing_photos_post_cutoff', 0)}** completed works sanctioned after May 1, 2026 lack completion photo proof.")
with col_photo2:
    st.info(f"ℹ️ **Pre-Cutoff Missing Photos:** **{data.get('missing_photos_pre_cutoff', 0):,}** completed works prior to May 2026 lack photo proof (legacy guidelines).")

st.markdown("---")

st.markdown("### 4. Data Pipeline & Ledger Integrity Verification")
integ = data.get("integrity_checks", {})
status = integ.get("status", "PASS")

if status == "PASS":
    st.success("✅ **Ledger Integrity Status: PASS** — All payment records strictly bind to valid sanction orders without cap or chronological violations.")
else:
    st.warning("⚠️ **Ledger Integrity Warnings Detected**")

icol1, icol2, icol3 = st.columns(3)
with icol1:
    st.metric("Orphan Payment Records", integ.get("orphan_payments", 0), help="Payments without corresponding sanction orders")
with icol2:
    st.metric("Cost Cap Violations", integ.get("cost_cap_violations", 0), help="Settled expenditure exceeding sanctioned amount by >1%")
with icol3:
    st.metric("Date Sequence Violations", integ.get("date_sequence_violations", 0), help="Chronological violations across recommendation, sanction, and payment dates")

st.caption("These automated integrity checks verify that data transformations preserve accounting constraints.")
