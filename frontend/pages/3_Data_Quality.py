import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pandas as pd
import streamlit as st
from frontend.api_client import api_client, APIError
from frontend.theme import inject_css
from frontend.components.disclaimer import render_disclaimer_banner
from frontend.components.formatters import lakh_crore, inr, compact
from frontend.components.cards import section_header, info_card, empty_state
from frontend.components.scorecard import integrity_scorecard
from frontend.components.dataframe import styled_table
from frontend.components.export import render_csv_download_button
from frontend.components.explainer import render_explanation

st.set_page_config(
    page_title="Data Quality & Ledger Rules | MPLADS FundGuard",
    page_icon="🔍",
    layout="wide",
)

inject_css()

st.title("🔍 Data Quality Audit & Ledger Rules")
render_disclaimer_banner()

tab1, tab2, tab3 = st.tabs([
    "📋 14-Point Quality Audit Suite",
    "🚨 Rule-Based Irregularities Browser",
    "📖 Rule Definitions & Benign Explanations",
])

# ----------------- TAB 1: 14-Point Quality Audit Suite -----------------
with tab1:
    try:
        quality_summary = api_client.get_data_quality_summary()
    except APIError as e:
        st.error(f"Error fetching data quality summary: {e.message}")
        st.stop()
    except Exception as e:
        st.error(f"Failed to connect to backend: {e}")
        st.stop()

    section_header(
        title="1. Pipeline Integrity Scorecard",
        subtitle="Verification status across 14 input quality audits and output integrity gates",
    )
    integrity_scorecard(quality_summary)

    section_header(
        title="2. Quality Gate Results Detail",
        subtitle="Detailed log of all automated checks executed during the pipeline build",
    )
    checks = quality_summary.get("checks", [])
    if checks:
        checks_data = []
        for c in checks:
            status = c.get("status", "PASS")
            badge = "🟢 PASS" if status == "PASS" else ("🟡 WARN" if status == "WARN" else "🔴 FAIL")
            gate_type = "Output Integrity Gate" if c.get("is_output_gate") else "Input Quality Audit"
            checks_data.append({
                "#": c.get("check_number", 0),
                "Audit Check Name": c.get("check_name", ""),
                "Gate Type": gate_type,
                "Status": badge,
                "Message": c.get("message", ""),
                "Finding Detail / Count": str(c.get("count", "")) if c.get("count") is not None else str(c.get("detail", "—")),
            })
        styled_table(pd.DataFrame(checks_data))

    render_explanation(
        what="The 14-point audit evaluates data cleanliness (input audits) and strict database constraints (output integrity gates).",
        why="Output integrity gates prevent data leakage, orphan foreign keys, and cost cap violations before models are trained.",
        look_for="Check whether any output gates failed. Input warnings (e.g. legacy missing photos before mandate) are normal in public ledgers.",
    )

# ----------------- TAB 2: Rule-Based Irregularities Browser -----------------
with tab2:
    section_header(
        title="Deterministic Rule Screening Browser",
        subtitle="Inspect individual works flagged by deterministic criteria for payment or timeline irregularities",
    )

    fcol1, fcol2, fcol3, fcol4 = st.columns(4)
    with fcol1:
        flag_type_opt = st.selectbox(
            "Filter by Rule Flag",
            options=[
                "all",
                "duplicate_payment",
                "same_day_bulk",
                "ghost_completion",
                "stalled_unpaid",
                "missing_photo",
                "orphan_payment",
                "cost_cap",
                "date_sequence",
            ],
            format_func=lambda x: {
                "all": "All Rule-Flagged Works (8 Rules)",
                "duplicate_payment": "Duplicate Payment Rows",
                "same_day_bulk": "Same-Day Bulk Payments (≥8 works)",
                "ghost_completion": "Ghost Completions (₹0 Settled)",
                "stalled_unpaid": "Stalled Unpaid (>180 Days)",
                "missing_photo": "Missing Photo Proof (Post-May 2026)",
                "orphan_payment": "Orphan Payments (No Sanction Order)",
                "cost_cap": "Cost Cap Violations (>1% over sanction)",
                "date_sequence": "Date Sequence Violations (Chronological)",
            }[x],
        )
    with fcol2:
        state_filter = st.text_input("Filter by State (Optional)", placeholder="e.g. Maharashtra, Uttar Pradesh")
    with fcol3:
        category_filter = st.text_input("Filter by Work Category (Optional)", placeholder="e.g. Drinking Water, Roads")
    with fcol4:
        sort_order = st.selectbox(
            "Sort by Sanction Amount",
            options=["desc", "asc"],
            format_func=lambda x: "Highest Sanction First" if x == "desc" else "Lowest Sanction First",
        )

    pcol1, pcol2 = st.columns(2)
    with pcol1:
        page_size = st.selectbox("Page Size", options=[25, 50, 100, 200], index=1)
    with pcol2:
        page_num = st.number_input("Page Number", min_value=1, value=1, step=1)

    flag_param = None if flag_type_opt == "all" else flag_type_opt
    state_param = state_filter.strip() if state_filter else None
    cat_param = category_filter.strip() if category_filter else None

    try:
        findings, pagination = api_client.get_data_quality_findings(
            flag_type=flag_param,
            state=state_param,
            category=cat_param,
            sort_by="Sanction_Amount",
            sort_order=sort_order,
            page=int(page_num),
            page_size=int(page_size),
        )
        total_records = pagination.get("total_records", 0)
        total_pages = pagination.get("total_pages", 0)

        st.caption(
            f"Showing **{len(findings)}** of **{total_records:,}** matching works "
            f"(Page {page_num} of {max(1, total_pages)}):"
        )

        if findings:
            table_df = pd.DataFrame(findings)
            display_df = pd.DataFrame({
                "Work ID": table_df["work_id"],
                "State": table_df["state"],
                "Constituency": table_df["constituency"],
                "MP Name": table_df["mp_name"],
                "Work Description": table_df["work"],
                "Sanctioned": table_df["sanction_amount"].apply(lambda x: lakh_crore(x) if pd.notna(x) else "—"),
                "Settled Exp": table_df["total_exp_settled"].apply(lambda x: lakh_crore(x) if pd.notna(x) else "—"),
                "Triggered Rule": table_df["rule_flag_type"],
                "Screening Reason": table_df["reason"],
                "Installments": table_df["installments"],
                "Vendors": table_df["vendors"],
                "Primary Vendor": table_df["primary_vendor"],
                "Completion Date": table_df["completion_date"].fillna("—"),
            })

            styled_table(display_df)

            # Export button with formula injection protection
            render_csv_download_button(
                df=display_df,
                filename=f"rule_findings_{flag_type_opt}_page{page_num}.csv",
                button_label="📥 Export Filtered Findings to Sanitized CSV",
            )
        else:
            empty_state("No works match the selected criteria.")

    except Exception as e:
        st.error(f"Error loading rule findings: {e}")

# ----------------- TAB 3: Rule Definitions & Benign Explanations -----------------
with tab3:
    section_header(
        title="Canonical Rule Definitions & Possible Benign Explanations",
        subtitle="Contextual reference to prevent misinterpreting administrative artifacts as wrongdoing",
    )

    rules_context = [
        {
            "rule": "Same-Day Bulk Payments",
            "threshold": "≥8 works (each ≤₹5 Lakh) paid to a single vendor on the exact same calendar date.",
            "benign": "District Treasuries frequently process batches of petty works (e.g. school benches, handpumps) on a single administrative payment day to optimize clerical workflow.",
            "check": "Verify whether the works were physically executed across separate physical locations despite clustered payment voucher dates.",
        },
        {
            "rule": "Stalled Unpaid Works",
            "threshold": "Sanctioned > 180 days ago with zero expenditure disbursed in the payment ledger.",
            "benign": "Land acquisition, contractor retendering, or seasonal delays (e.g. monsoon) commonly postpone civil works start dates.",
            "check": "Review administrative sanction file for tender status, revised execution orders, or contractor cancellation notices.",
        },
        {
            "rule": "Duplicate Payment Rows",
            "threshold": "Exact duplicate ledger rows sharing identical Work ID, Vendor Name, Amount, and Date.",
            "benign": "Portal double-entry glitches or accidental re-submissions by district operators without financial duplication at the bank level.",
            "check": "Inspect bank payment transaction IDs (UTR numbers) on the public portal to verify whether actual funds were debited twice.",
        },
        {
            "rule": "Ghost Completions",
            "threshold": "Work marked 'Completed' on portal with ₹0 settled and ₹0 pending expenditure.",
            "benign": "Data entry clerk prematurely toggled status flag upon administrative sanction, or work was merged into another scheme.",
            "check": "Check physical site inspection photos or completion certificates on the portal.",
        },
        {
            "rule": "Missing Photo Proof (Post-Cutoff)",
            "threshold": "Work completed after May 2026 lacking required geotagged physical asset photograph.",
            "benign": "Photographs may have been taken offline by district engineers but pending upload due to portal file size limits.",
            "check": "Request physical completion report with timestamped photographs from the District Planning Office.",
        },
        {
            "rule": "Cost Cap Violations",
            "threshold": "Settled expenditure exceeds the sanctioned amount by more than 1%.",
            "benign": "Approved cost escalation or revised administrative sanction orders not yet updated in the summary table.",
            "check": "Inspect revised administrative approvals uploaded in portal documents.",
        },
    ]

    for r in rules_context:
        with st.expander(f"📌 {r['rule']}"):
            st.markdown(f"**Screening Threshold:** {r['threshold']}")
            st.markdown(f"**Possible Benign Operational Reason:** {r['benign']}")
            st.markdown(f"**Verification Guidance for Reviewers:** {r['check']}")
