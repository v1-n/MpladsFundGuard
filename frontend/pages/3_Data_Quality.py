import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import streamlit as st
import pandas as pd
from frontend.api_client import api_client, APIError
from frontend.components.disclaimer import render_disclaimer_banner
from frontend.components.export import render_csv_download_button

st.set_page_config(page_title="Data Quality & Ledger Rules | MPLADS FundGuard", page_icon="🔍", layout="wide")

st.title("🔍 Data Quality Audit & Ledger Rules")
render_disclaimer_banner()

tab1, tab2 = st.tabs(["📋 14-Point Quality Audit Suite", "🚨 Rule-Based Irregularities Browser"])

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

    st.subheader("Data Pipeline Quality & Audit Verification")
    
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Total Checks", quality_summary.get("total_checks", 0))
    k2.metric("Passed Checks", quality_summary.get("passed", 0))
    k3.metric("Input Warnings", quality_summary.get("input_warnings", 0), help="Expected public data quirks (e.g. legacy missing photos, missing start dates)")
    k4.metric("Output Warnings", quality_summary.get("output_warnings", 0), help="Output verification alerts")
    k5.metric("Failures", quality_summary.get("failures", 0))

    if quality_summary.get("failures", 0) == 0:
        st.success("✅ **Quality Gate Status: PASS** — All output integrity gates, foreign key constraints, and accounting cost-caps passed validation.")
    else:
        st.error("❌ **Quality Gate Failures Detected**")

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
                "Type": gate_type,
                "Status": badge,
                "Message": c.get("message", ""),
                "Detail / Count": str(c.get("count", "")) if c.get("count") is not None else str(c.get("detail", ""))
            })
        st.dataframe(pd.DataFrame(checks_data), use_container_width=True)

# ----------------- TAB 2: Rule-Based Irregularities Browser -----------------
with tab2:
    st.subheader("Rule-Based Irregularity Screening")
    st.caption("Browse projects flagged by deterministic rules for payment, completion, or vendor irregularities.")

    # Filter bar
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
            }[x]
        )
    with fcol2:
        state_filter = st.text_input("Filter by State (Optional)", placeholder="e.g. Rajasthan, Uttar Pradesh")
    with fcol3:
        category_filter = st.text_input("Filter by Work Category (Optional)", placeholder="e.g. Drinking Water, Roads")
    with fcol4:
        sort_order = st.selectbox("Sort Order", options=["desc", "asc"], format_func=lambda x: "Highest Sanction First" if x == "desc" else "Lowest Sanction First")

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
            page_size=int(page_size)
        )
        total_records = pagination.get("total_records", 0)
        total_pages = pagination.get("total_pages", 0)
        
        st.write(f"Showing **{len(findings)}** of **{total_records:,}** matching works (Page {page_num} of {max(1, total_pages)}):")

        if findings:
            table_df = pd.DataFrame(findings)
            
            # Format currency and clean up display columns
            display_df = pd.DataFrame({
                "Work ID": table_df["work_id"],
                "State": table_df["state"],
                "Constituency": table_df["constituency"],
                "MP Name": table_df["mp_name"],
                "Work Description": table_df["work"],
                "Sanctioned (₹)": table_df["sanction_amount"].apply(lambda x: f"₹{x:,.0f}" if pd.notna(x) else "—"),
                "Settled Exp (₹)": table_df["total_exp_settled"].apply(lambda x: f"₹{x:,.0f}" if pd.notna(x) else "—"),
                "Triggered Rule": table_df["rule_flag_type"],
                "Irregularity Reason": table_df["reason"],
                "Installments": table_df["installments"],
                "Vendors": table_df["vendors"],
                "Primary Vendor": table_df["primary_vendor"],
                "Completion Date": table_df["completion_date"].fillna("—")
            })

            st.dataframe(display_df, use_container_width=True)

            # Export button with formula injection protection
            render_csv_download_button(
                df=display_df,
                filename=f"rule_findings_{flag_type_opt}_page{page_num}.csv",
                button_label="📥 Export These Findings to Sanitized CSV"
            )
        else:
            st.info("No works found matching the selected filter criteria.")

    except Exception as e:
        st.error(f"Error loading findings: {e}")
