import sys
from pathlib import Path

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import streamlit as st
from frontend.api_client import api_client, APIError
from frontend.components.disclaimer import render_disclaimer_banner

st.set_page_config(
    page_title="MPLADS FundGuard | Full-Stack Screening Platform",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Sidebar metadata
with st.sidebar:
    st.title("🛡️ MPLADS FundGuard")
    st.caption("v2.0 • Public Procurement Screening & Anomaly Auditing")
    
    # Backend health check indicator
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
    st.info("Select a page from the sidebar above to explore:")
    st.markdown(
        """
        - **1. Overview:** Macro statistics & pipeline integrity
        - **2. EDA:** Dataset shapes, missingness, distributions
        - **3. Data Quality:** 14-point ledger rules & flagged works
        - **4. Fund Utilization:** State & category allocations
        - **5. Anomaly Screening:** Outlier scoring & deep-dives
        - **6. Model Evaluation:** Seed stability & synthetic benchmark
        - **7. Blind Audit:** Unbiased manual verification tool
        """
    )
    st.divider()
    st.caption("Lok Sabha procurement data • 543 Constituencies")

# Main Home Header
st.title("🛡️ MPLADS FundGuard: Screening & Anomaly Review Platform")
render_disclaimer_banner(include_scope=True)

st.markdown("---")

col1, col2 = st.columns([2, 1])

with col1:
    st.markdown(
        """
        ### About the Platform
        **MPLADS FundGuard** is an open-source, reproducible screening platform for public procurement records
        under the **Members of Parliament Local Area Development Scheme (MPLADS)** for the 18th Lok Sabha.
        
        It combines:
        1. **Deterministic Ledger Quality Audits:** Detecting duplicate payments, split invoices, ghost completions, stalled works, and missing completion photos.
        2. **Multi-Dimensional Peer Anomaly Screening:** Scoring works using an Isolation Forest ensemble benchmarked against peer groups (by work category and state) rather than nationwide raw amounts.
        3. **Double-Blind Verification Audit:** Providing an unbiased, matched-control review sheet and standardized rubric for human field verification.

        ---
        ### How to Use This System
        - **Triage & Screening:** Navigate to **Data Quality** or **Anomaly Screening** to inspect works with extreme payment patterns or rule violations.
        - **Granular Investigation:** Expand any work record to inspect primary vendors, installment timelines, and peer comparisons.
        - **Data Export:** Export filtered tables safely with automatic spreadsheet formula injection neutralization.
        """
    )

with col2:
    st.subheader("⚡ Quick Status")
    try:
        overview = api_client.get_overview()
        st.metric("Total Works Monitored", f"{overview.get('total_works', 0):,}")
        st.metric("Total Settled Expenditure", f"₹{overview.get('total_settled_expenditure', 0) / 1e7:,.1f} Cr")
        st.metric("Rule-Flagged Works", f"{overview.get('same_day_bulk_payment_works', 0) + overview.get('stalled_unpaid_works', 0):,}")
        
        integ = overview.get("integrity_checks", {})
        integ_status = integ.get("status", "NOT VERIFIED")
        if integ_status == "PASS":
            st.success("✅ Master Ledger Integrity: PASS (0 Orphans, 0 Over-caps)")
        elif integ_status == "WARN":
            st.warning(f"⚠️ Master Ledger Integrity: WARN ({integ.get('orphan_payments', 0)} Orphans, {integ.get('cost_cap_violations', 0)} Over-caps)")
        else:
            st.info(f"ℹ️ Master Ledger Integrity: {integ_status}")
    except Exception as e:
        st.warning(f"Backend data loading: {e}")

st.markdown("---")
st.info("👈 **Select a page from the left sidebar to begin investigation.**")
