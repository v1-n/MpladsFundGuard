import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pandas as pd
import streamlit as st
from frontend.api_client import api_client, APIError
from frontend.theme import inject_css, apply_dark_theme
from frontend.components.disclaimer import render_disclaimer_banner
from frontend.components.formatters import lakh_crore, pct, compact
from frontend.components.metrics import metric_grid
from frontend.components.cards import section_header, empty_state
from frontend.components.charts import donut_chart, horizontal_bar_chart
from frontend.components.dataframe import styled_table
from frontend.components.explainer import render_explanation

st.set_page_config(
    page_title="Executive Overview | MPLADS FundGuard",
    page_icon="📊",
    layout="wide",
)

inject_css()

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
    st.caption(
        f"🕒 **Data Provenance:** Pipeline Master Artifact updated `{master_dt} UTC` • "
        f"Pipeline Version `{prov.get('pipeline_version', '2.0.0')}` • "
        f"Ledger Source: 18th Lok Sabha Official Portal"
    )

# 1. Lifecycle & Scale KPIs
section_header(
    title="1. Portfolio Scale & Lifecycle Breakdown",
    subtitle="Distribution of works across lifecycle stages in the 18th Lok Sabha ledger",
)
lifecycle_items = [
    {
        "label": "Total Works Monitored",
        "value": compact(data.get("total_works")),
        "subtext": "Ingested procurement records",
        "badge": "Portfolio",
        "badge_variant": "neutral",
    },
    {
        "label": "Completed Works",
        "value": compact(data.get("completed_works")),
        "subtext": f"{pct(data.get('completed_works', 0) / max(1, data.get('total_works', 1)), decimals=1, is_ratio=True)} of portfolio",
        "badge": "Completed",
        "badge_variant": "pass",
    },
    {
        "label": "In-Progress Works",
        "value": compact(data.get("in_progress_works")),
        "subtext": f"{pct(data.get('in_progress_works', 0) / max(1, data.get('total_works', 1)), decimals=1, is_ratio=True)} of portfolio",
        "badge": "Active",
        "badge_variant": "warn",
    },
    {
        "label": "Sanctioned Only",
        "value": compact(data.get("sanctioned_only_works")),
        "subtext": "Approved, ₹0 disbursed yet",
        "badge": "Unstarted",
        "badge_variant": "neutral",
    },
]
metric_grid(lifecycle_items, cols=4)

# 2. Financial Allocations & Burn Down
section_header(
    title="2. Financial Allocations & Fund Utilization",
    subtitle="Macro expenditure figures across sanctioned and disbursed public funds",
)
util_ratio = data.get("overall_utilization_ratio", 0)
finance_items = [
    {
        "label": "Total Sanctioned",
        "value": lakh_crore(data.get("total_sanctioned_amount")),
        "subtext": "Cumulative budget approved",
        "badge": "Sanctioned",
        "badge_variant": "neutral",
    },
    {
        "label": "Settled Expenditure",
        "value": lakh_crore(data.get("total_settled_expenditure")),
        "subtext": "Verified completed disbursements",
        "badge": "Settled",
        "badge_variant": "pass",
    },
    {
        "label": "In-Progress Disbursed",
        "value": lakh_crore(data.get("total_in_progress_expenditure")),
        "subtext": "Active ongoing disbursements",
        "badge": "In-Flight",
        "badge_variant": "warn",
    },
    {
        "label": "Overall Utilization Ratio",
        "value": pct(util_ratio, decimals=1, is_ratio=True),
        "subtext": f"Unspent Balance: {lakh_crore(data.get('remaining_unspent_amount'))}",
        "badge": "Utilization",
        "badge_variant": "pass" if util_ratio >= 0.6 else "warn",
    },
]
metric_grid(finance_items, cols=4)

# Visual Portfolio Charts
c_chart1, c_chart2 = st.columns(2)
with c_chart1:
    fig_donut = donut_chart(
        labels=["Completed", "In-Progress", "Sanctioned Only", "Pending Only"],
        values=[
            data.get("completed_works", 0),
            data.get("in_progress_works", 0),
            data.get("sanctioned_only_works", 0),
            data.get("pending_only_works", 0),
        ],
        title="Works Portfolio by Lifecycle Stage",
        colors=["#10B981", "#8B5CF6", "#F59E0B", "#6B7280"],
    )
    st.plotly_chart(fig_donut, use_container_width=True)

with c_chart2:
    fig_fin = donut_chart(
        labels=["Settled Expenditure", "In-Progress Disbursed", "Unspent Balance"],
        values=[
            max(0, data.get("total_settled_expenditure", 0)),
            max(0, data.get("total_in_progress_expenditure", 0)),
            max(0, data.get("remaining_unspent_amount", 0)),
        ],
        title="Financial Allocation Breakdown",
        colors=["#10B981", "#8B5CF6", "#F97316"],
    )
    st.plotly_chart(fig_fin, use_container_width=True)

# 3. Deterministic Ledger Rule Findings Breakdown
section_header(
    title="3. Deterministic Ledger Rule Screening Findings",
    subtitle="Summary of works triggered across 8 deterministic audit rules",
)
rule_summary_data = [
    {
        "Rule Audit Check": "Same-Day Bulk Payments",
        "Severity": "Screening Alert",
        "Flagged Works": f"{data.get('same_day_bulk_payment_works', 0):,}",
        "Definition & Screening Threshold": "≥8 works (each ≤₹5L) paid to a single vendor on the exact same date",
    },
    {
        "Rule Audit Check": "Stalled Unpaid Works",
        "Severity": "Review Signal",
        "Flagged Works": f"{data.get('stalled_unpaid_works', 0):,}",
        "Definition & Screening Threshold": "Sanctioned > 180 days ago with zero expenditure disbursed",
    },
    {
        "Rule Audit Check": "Duplicate Payment Rows",
        "Severity": "Screening Alert",
        "Flagged Works": f"{data.get('duplicate_payment_works', 0):,}",
        "Definition & Screening Threshold": "Exact duplicate records matching [Work ID + Vendor + Amount + Date]",
    },
    {
        "Rule Audit Check": "Ghost Completions",
        "Severity": "Screening Alert",
        "Flagged Works": f"{data.get('ghost_completion_works', 0):,}",
        "Definition & Screening Threshold": "Recorded as Completed on portal with ₹0 settled & ₹0 pending expenditure",
    },
    {
        "Rule Audit Check": "Missing Photos (Post-Cutoff)",
        "Severity": "Mandate Alert",
        "Flagged Works": f"{data.get('missing_photos_post_cutoff', 0):,}",
        "Definition & Screening Threshold": "Completed post-May 2026 lacking mandatory geotagged physical asset photos",
    },
    {
        "Rule Audit Check": "Missing Photos (Pre-Cutoff)",
        "Severity": "Informational",
        "Flagged Works": f"{data.get('missing_photos_pre_cutoff', 0):,}",
        "Definition & Screening Threshold": "Historical completions prior to mandatory photographic upload requirement",
    },
]
styled_table(pd.DataFrame(rule_summary_data))

# 4. Pipeline & Accounting Integrity Verification
section_header(
    title="4. Pipeline & Accounting Integrity Verification",
    subtitle="Validation gate checks ensuring foreign-key consistency and budget cap adherence",
)
integ = data.get("integrity_checks", {})
integ_status = integ.get("status", "NOT VERIFIED")
integ_variant = "pass" if integ_status == "PASS" else ("warn" if integ_status == "WARN" else "fail")

integrity_items = [
    {
        "label": "Master Integrity Status",
        "value": integ_status,
        "subtext": "Pipeline constraint gate",
        "badge": "Integrity Gate",
        "badge_variant": integ_variant,
    },
    {
        "label": "Orphan Payments",
        "value": str(integ.get("orphan_payments", 0)),
        "subtext": "Payments without parent sanction",
        "badge": "Foreign Key",
        "badge_variant": "pass" if integ.get("orphan_payments", 0) == 0 else "fail",
    },
    {
        "label": "Cost Cap Violations",
        "value": str(integ.get("cost_cap_violations", 0)),
        "subtext": "Settled > Sanctioned by >1%",
        "badge": "Budget Cap",
        "badge_variant": "pass" if integ.get("cost_cap_violations", 0) == 0 else "fail",
    },
    {
        "label": "Date Sequence Violations",
        "value": str(integ.get("date_sequence_violations", 0)),
        "subtext": "Chronological order inconsistencies",
        "badge": "Timeline",
        "badge_variant": "pass" if integ.get("date_sequence_violations", 0) == 0 else "warn",
    },
]
metric_grid(integrity_items, cols=4)

# 5. Geographic State-Level Distribution
section_header(
    title="5. Geographic Distribution Across States",
    subtitle="Total works and expenditure volume by State/UT",
)
try:
    state_data = api_client.get_fund_utilization_by_state(min_works=10)
    if state_data:
        sdf = pd.DataFrame(state_data)
        top_states = sdf.sort_values(by="total_works", ascending=False).head(15)
        top_states["Sanctioned (Cr)"] = top_states["total_sanctioned_amount"] / 1e7
        top_states["Settled (Cr)"] = top_states["total_settled_expenditure"] / 1e7

        fig_states = horizontal_bar_chart(
            df=top_states,
            x_col="total_works",
            y_col="state",
            title="Top 15 States by Ingested Works Volume",
            text_col="total_works",
        )
        st.plotly_chart(fig_states, use_container_width=True)
except Exception as e:
    st.info(f"State breakdown visualization unavailable: {e}")

# Reviewer Explainer
render_explanation(
    what="Macro overview of the 18th Lok Sabha MPLADS public procurement ledger, financial burn down, and deterministic screening findings.",
    why="Establishes portfolio-wide context and verifies data integrity before granular investigation.",
    look_for="Check for unexpected concentrations of stalled works or orphan payment warnings that indicate underlying data reporting gaps.",
)
