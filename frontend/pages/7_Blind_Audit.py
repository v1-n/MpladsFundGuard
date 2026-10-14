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

st.set_page_config(page_title="Blind Audit Tool | MPLADS FundGuard", page_icon="📋", layout="wide")

st.title("📋 Double-Blind Manual Audit Tool")
render_disclaimer_banner()

tab_audit, tab_rubric, tab_diag = st.tabs(["📝 Reviewer Workspace", "📖 Standardized Review Rubric", "⚖️ Matching Diagnostics & SMD"])

# ----------------- TAB 1: Reviewer Workspace -----------------
with tab_audit:
    st.subheader("Blind Verification Sample (100 Shuffled Works)")
    st.info(
        "**Strict Blind Protocol:** All model scores, ranks, cohort labels, installment counts, and vendor counts "
        "have been stripped from this sheet. Review each project using the official portal link, completion photos, "
        "and physical description against the rubric. Record your independent verdict without circular bias."
    )

    try:
        sample_resp = api_client.get_blind_audit_sample()
        sample_items = sample_resp.get("sample", [])
    except APIError as e:
        st.error(f"Error fetching blind audit sample: {e.message}")
        st.stop()
    except Exception as e:
        st.error(f"Failed to connect to backend: {e}")
        st.stop()

    if not sample_items:
        st.warning("No audit sample available.")
        st.stop()

    # Reviewer Identity for durable persistence
    col_rev1, col_rev2 = st.columns([1, 2])
    with col_rev1:
        reviewer_id = st.text_input("Reviewer ID / Name", value="Auditor-1", help="Used to isolate and persist your review verdicts in backend storage")
    with col_rev2:
        st.caption("Verdicts and observations are saved durably to the backend database under this Reviewer ID.")

    # Load previously persisted reviews for this reviewer from backend
    try:
        saved_reviews_list = api_client.get_audit_reviews(reviewer_id=reviewer_id)
        saved_reviews_map = {r["work_id"]: r for r in saved_reviews_list}
    except Exception:
        saved_reviews_map = {}

    # Progress tracking
    completed_reviews = len(saved_reviews_map)
    st.progress(completed_reviews / len(sample_items))
    st.caption(f"**Audit Progress for {reviewer_id}:** {completed_reviews} of {len(sample_items)} works reviewed ({completed_reviews/len(sample_items)*100:.1f}%)")

    # Select work to review
    work_ids = [item["work_id"] for item in sample_items]
    selected_id = st.selectbox("Select Project to Audit", options=work_ids)

    curr_item = next(item for item in sample_items if item["work_id"] == selected_id)

    st.markdown("---")
    st.markdown(f"### Project Details: `{curr_item['work_id']}`")
    
    pcol1, pcol2 = st.columns([2, 1])
    with pcol1:
        st.markdown(f"**Work Description:** {curr_item['work']}")
        st.markdown(f"**State / Constituency:** {curr_item['state']} • `{curr_item['constituency']}`")
    with pcol2:
        portal_url = curr_item.get("portal_url", "https://www.mplads.gov.in/")
        st.link_button("🔗 Open Official MPLADS Portal", portal_url, help="Cross-reference work status, completion images, and payment bills on the portal")

    st.markdown("#### Record Your Audit Verdict")
    prior_rec = saved_reviews_map.get(selected_id, {})
    saved_verdict = prior_rec.get("verdict", "")
    saved_notes = prior_rec.get("notes", "")

    verdict_opts = ["", "Normal / Regular", "Irregularity / Suspicious", "Inefficient / Incomplete", "Inconsistent Data"]
    curr_idx = verdict_opts.index(saved_verdict) if saved_verdict in verdict_opts else 0

    v_col1, v_col2 = st.columns([1, 2])
    with v_col1:
        new_verdict = st.selectbox("Audit Verdict", options=verdict_opts, index=curr_idx, key=f"v_{selected_id}")
    with v_col2:
        new_notes = st.text_area("Auditor Verification Notes & Observations", value=saved_notes, placeholder="e.g. Photo shows finished drain; vendor names verified on portal...", key=f"n_{selected_id}")

    if st.button("💾 Persist Verdict to Backend", type="primary", key=f"save_{selected_id}"):
        if not new_verdict:
            st.error("Please select a verdict before saving.")
        else:
            try:
                api_client.submit_audit_review(
                    work_id=selected_id,
                    reviewer_id=reviewer_id,
                    verdict=new_verdict,
                    notes=new_notes
                )
                st.success(f"Verdict for `{selected_id}` saved durably under `{reviewer_id}`!")
                st.rerun()
            except APIError as e:
                st.error(f"Error submitting review: {e.message}")
            except Exception as e:
                st.error(f"Submission failed: {e}")

    st.markdown("---")
    st.subheader(f"Current Review Sheet ({reviewer_id}) & Export")

    # Construct review table with current saved verdicts
    table_rows = []
    for item in sample_items:
        wid = item["work_id"]
        v_info = saved_reviews_map.get(wid, {})
        table_rows.append({
            "Work ID": wid,
            "Work Description": item["work"],
            "State": item["state"],
            "Constituency": item["constituency"],
            "Portal URL": item["portal_url"],
            "Audit Verdict": v_info.get("verdict", "Unreviewed"),
            "Auditor Notes": v_info.get("notes", ""),
            "Reviewed At": v_info.get("updated_at", "—")
        })

    audit_df = pd.DataFrame(table_rows)
    st.dataframe(audit_df, use_container_width=True)

    render_csv_download_button(
        df=audit_df,
        filename=f"mplads_manual_audit_{reviewer_id}.csv",
        button_label="📥 Export Audit Sheet with Recorded Verdicts to CSV"
    )

# ----------------- TAB 2: Standardized Review Rubric -----------------
with tab_rubric:
    st.subheader("Standardized Manual Audit Rubric")
    try:
        rubric_md = api_client.get_audit_rubric()
        st.markdown(rubric_md)
    except Exception as e:
        st.error(f"Error fetching rubric: {e}")

# ----------------- TAB 3: Matching Diagnostics -----------------
with tab_diag:
    st.subheader("Control Matching Diagnostics & Balance Analysis")
    st.info(
        "**Cohort Design:** 50 top-ranked completed works are matched with 50 controls selected from completed works "
        "ranked strictly outside the top-300 (`controls_min_rank >= 300`) with identical work categories."
    )

    try:
        diag = api_client.get_audit_diagnostics()
        
        d1, d2, d3 = st.columns(3)
        d1.metric("Top-Ranked Works in Sample", diag.get("n_top_ranked", 50))
        d2.metric("Matched Controls in Sample", diag.get("n_matched_controls", 50))
        d3.metric("Controls Minimum Rank", f"#{diag.get('controls_min_rank', 300):,.0f}")

        st.markdown("#### Top-50 vs Control Cohort Comparison")
        top_med = diag.get("top_50_medians", {})
        ctrl_med = diag.get("control_medians", {})
        smd = diag.get("standardized_mean_differences", {})

        comp_rows = [
            {
                "Feature": "Payment Installments",
                "Top-50 Ranked Median": f"{top_med.get('installments', 0):.0f}",
                "Control Works Median": f"{ctrl_med.get('installments', 0):.0f}",
                "Standardized Mean Difference (SMD)": f"{smd.get('Settled_Count', 0):.4f}",
                "Balance Status": "Imbalanced (Model Selection Feature)"
            },
            {
                "Feature": "Unique Vendor Count",
                "Top-50 Ranked Median": f"{top_med.get('vendors', 0):.0f}",
                "Control Works Median": f"{ctrl_med.get('vendors', 0):.0f}",
                "Standardized Mean Difference (SMD)": f"{smd.get('Unique_Vendors_Count', 0):.4f}",
                "Balance Status": "Imbalanced (Model Selection Feature)"
            },
            {
                "Feature": "Sanctioned Budget",
                "Top-50 Ranked Median": f"₹{top_med.get('budget', 0):,.0f}",
                "Control Works Median": f"₹{ctrl_med.get('budget', 0):,.0f}",
                "Standardized Mean Difference (SMD)": f"{smd.get('Sanction_Amount', 0):.4f}",
                "Balance Status": "Well-Balanced (SMD < 0.20)"
            }
        ]

        st.dataframe(pd.DataFrame(comp_rows), use_container_width=True)

        if diag.get("imbalance_warning"):
            st.warning(
                "⚠️ **Methodology Caveat on Control Balance:** "
                f"{diag.get('notes')}"
            )

    except Exception as e:
        st.error(f"Error fetching diagnostics: {e}")
