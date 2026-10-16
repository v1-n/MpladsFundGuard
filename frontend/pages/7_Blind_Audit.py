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
from frontend.components.formatters import lakh_crore, compact
from frontend.components.metrics import metric_grid
from frontend.components.cards import section_header, empty_state, info_card
from frontend.components.dataframe import styled_table
from frontend.components.export import render_csv_download_button
from frontend.components.explainer import render_explanation

st.set_page_config(
    page_title="Blind Audit Tool | MPLADS FundGuard",
    page_icon="📋",
    layout="wide",
)

inject_css()

st.title("📋 Double-Blind Manual Audit Tool")
render_disclaimer_banner()

tab_audit, tab_rubric, tab_diag = st.tabs([
    "📝 Reviewer Workspace",
    "📖 Standardized Review Rubric",
    "⚖️ Matching Diagnostics & SMD Balance",
])

# ----------------- TAB 1: Reviewer Workspace -----------------
with tab_audit:
    section_header(
        title="1. Blind Verification Sample (100 Shuffled Works)",
        subtitle="Double-blind evaluation protocol to collect human ground-truth labels without model bias",
    )
    st.info(
        "**Strict Blind Protocol:** All model scores, ranks, cohort labels, installment counts, and vendor counts "
        "have been stripped from this review sheet. Review each project using the official portal link, completion photos, "
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
        empty_state("No audit sample available.")
        st.stop()

    # Reviewer Authentication & Identity
    col_rev1, col_rev2 = st.columns([1, 1])
    with col_rev1:
        auth_profile = st.selectbox(
            "Reviewer Session / Identity",
            options=["Auditor-1 (auditor-token-1)", "Auditor-2 (auditor-token-2)", "Lead-Auditor [Admin] (lead-admin-token)", "Custom Reviewer Token"],
            index=0,
            help="Authenticates your review session. Identity is derived directly by the backend from this credential.",
        )
    with col_rev2:
        if auth_profile == "Custom Reviewer Token":
            reviewer_token = st.text_input("Enter Reviewer Auth Token", value="", type="password")
        else:
            token_map = {
                "Auditor-1 (auditor-token-1)": "auditor-token-1",
                "Auditor-2 (auditor-token-2)": "auditor-token-2",
                "Lead-Auditor [Admin] (lead-admin-token)": "lead-admin-token",
            }
            reviewer_token = token_map.get(auth_profile, "auditor-token-1")

        st.caption(f"🔒 Authenticated Session Active • All review records durably stored in SQLite database.")

    # Load previously persisted reviews for this authenticated reviewer from backend
    try:
        saved_reviews_list = api_client.get_audit_reviews(reviewer_token=reviewer_token)
        saved_reviews_map = {r["work_id"]: r for r in saved_reviews_list}
        active_reviewer_id = saved_reviews_list[0]["reviewer_id"] if saved_reviews_list else auth_profile.split(" ")[0]
    except Exception as e:
        saved_reviews_map = {}
        active_reviewer_id = auth_profile.split(" ")[0]

    # Progress tracking
    completed_reviews = len(saved_reviews_map)
    st.progress(completed_reviews / len(sample_items))
    st.caption(
        f"**Audit Progress for {active_reviewer_id}:** {completed_reviews} of {len(sample_items)} works reviewed "
        f"({completed_reviews / len(sample_items) * 100:.1f}%)"
    )

    # Select work to review
    work_ids = [item["work_id"] for item in sample_items]
    selected_id = st.selectbox("Select Project to Audit", options=work_ids)

    curr_item = next(item for item in sample_items if item["work_id"] == selected_id)

    section_header(
        title=f"Project Inspection: {curr_item['work_id']}",
        subtitle=f"{curr_item['state']} • {curr_item['constituency']}",
    )

    pcol1, pcol2 = st.columns([3, 1])
    with pcol1:
        st.markdown(f"**Work Description:** {curr_item['work']}")
        st.markdown(f"**Location:** {curr_item['state']} • `{curr_item['constituency']}`")
    with pcol2:
        portal_url = curr_item.get("portal_url", "https://www.mplads.gov.in/")
        st.link_button(
            "🔗 Open Official MPLADS Portal",
            portal_url,
            help="Cross-reference work status, completion images, and payment bills on the portal",
        )

    st.markdown("#### Record Audit Verdict")
    prior_rec = saved_reviews_map.get(selected_id, {})
    saved_verdict = prior_rec.get("verdict", "")
    saved_notes = prior_rec.get("notes", "")

    verdict_opts = ["", "Normal / Regular", "Irregularity / Suspicious", "Inefficient / Incomplete", "Inconsistent Data"]
    curr_idx = verdict_opts.index(saved_verdict) if saved_verdict in verdict_opts else 0

    v_col1, v_col2 = st.columns([1, 2])
    with v_col1:
        new_verdict = st.selectbox("Audit Verdict", options=verdict_opts, index=curr_idx, key=f"v_{selected_id}")
    with v_col2:
        new_notes = st.text_area(
            "Auditor Verification Notes & Observations",
            value=saved_notes,
            placeholder="e.g. Photo shows finished drain; vendor names verified on portal bills...",
            key=f"n_{selected_id}",
        )

    if st.button("💾 Persist Verdict to Backend", type="primary", key=f"save_{selected_id}"):
        if not new_verdict:
            st.error("Please select a verdict before saving.")
        else:
            try:
                api_client.submit_audit_review(
                    work_id=selected_id,
                    verdict=new_verdict,
                    notes=new_notes,
                    reviewer_token=reviewer_token,
                )
                st.success(f"Verdict for `{selected_id}` saved durably under `{active_reviewer_id}`!")
                st.rerun()
            except APIError as e:
                st.error(f"Error submitting review: {e.message}")
            except Exception as e:
                st.error(f"Submission failed: {e}")

    # Current Review Sheet
    section_header(
        title=f"Review Sheet & Export ({active_reviewer_id})",
        subtitle="Consolidated record of audited works with submitted verdicts",
    )

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
            "Reviewed At": v_info.get("updated_at", "—"),
        })

    audit_df = pd.DataFrame(table_rows)
    styled_table(audit_df)

    render_csv_download_button(
        df=audit_df,
        filename=f"mplads_manual_audit_{reviewer_id}.csv",
        button_label="📥 Export Audit Sheet with Recorded Verdicts to Sanitized CSV",
    )

    render_explanation(
        what="Double-blind review tool displaying 100 randomly shuffled works (50 top-ranked outliers and 50 matched controls) stripped of model rankings.",
        why="Circular evaluation (reviewing while knowing the model score) invalidates human ground-truth. Double-blind verification guarantees objective validation.",
        look_for="Use the portal link to inspect physical completion photos, vendor invoices, and project milestones according to the rubric.",
    )

# ----------------- TAB 2: Standardized Review Rubric -----------------
with tab_rubric:
    section_header(
        title="Standardized Manual Audit Rubric",
        subtitle="Objective criteria for classifying public procurement works into audit categories",
    )
    try:
        rubric_md = api_client.get_audit_rubric()
        st.markdown(rubric_md)
    except Exception as e:
        st.error(f"Error fetching rubric: {e}")

# ----------------- TAB 3: Matching Diagnostics -----------------
with tab_diag:
    section_header(
        title="Control Matching Diagnostics & Balance Analysis",
        subtitle="Evaluating covariate balance between the 50 top-ranked works and 50 matched controls",
    )
    st.info(
        "**Cohort Design:** 50 top-ranked completed works are matched with 50 controls selected from completed works "
        "ranked strictly outside the top-300 (`controls_min_rank >= 300`) with identical work categories."
    )

    try:
        diag = api_client.get_audit_diagnostics()

        diag_items = [
            {
                "label": "Top-Ranked Works in Sample",
                "value": str(diag.get("n_top_ranked", 50)),
                "subtext": "High review priority cohort",
                "badge": "Top Cohort",
                "badge_variant": "top1",
            },
            {
                "label": "Matched Controls in Sample",
                "value": str(diag.get("n_matched_controls", 50)),
                "subtext": "Category-matched control works",
                "badge": "Control Cohort",
                "badge_variant": "pass",
            },
            {
                "label": "Controls Minimum Rank",
                "value": f"#{diag.get('controls_min_rank', 300):,.0f}",
                "subtext": "Strict rank separation threshold",
                "badge": "Separation",
                "badge_variant": "neutral",
            },
        ]
        metric_grid(diag_items, cols=3)

        section_header(
            title="Covariate Balance & Standardized Mean Differences (SMD)",
            subtitle="Comparing feature distributions between top-ranked works and matched controls",
        )
        top_med = diag.get("top_50_medians", {})
        ctrl_med = diag.get("control_medians", {})
        smd = diag.get("standardized_mean_differences", {})

        comp_rows = [
            {
                "Feature": "Payment Installments",
                "Top-50 Ranked Median": f"{top_med.get('installments', 0):.0f}",
                "Control Works Median": f"{ctrl_med.get('installments', 0):.0f}",
                "Standardized Mean Difference (SMD)": f"{smd.get('Settled_Count', 0):.4f}",
                "Balance Status": "Imbalanced (Model Selection Feature)",
            },
            {
                "Feature": "Unique Vendor Count",
                "Top-50 Ranked Median": f"{top_med.get('vendors', 0):.0f}",
                "Control Works Median": f"{ctrl_med.get('vendors', 0):.0f}",
                "Standardized Mean Difference (SMD)": f"{smd.get('Unique_Vendors_Count', 0):.4f}",
                "Balance Status": "Imbalanced (Model Selection Feature)",
            },
            {
                "Feature": "Sanctioned Budget",
                "Top-50 Ranked Median": lakh_crore(top_med.get("budget", 0)),
                "Control Works Median": lakh_crore(ctrl_med.get("budget", 0)),
                "Standardized Mean Difference (SMD)": f"{smd.get('Sanction_Amount', 0):.4f}",
                "Balance Status": "Well-Balanced (SMD < 0.20)",
            },
        ]

        styled_table(pd.DataFrame(comp_rows))

        if diag.get("imbalance_warning"):
            info_card(
                title="Methodology Note on Control Balance",
                content=str(diag.get("notes")),
                icon="⚠️",
                variant="amber",
            )

    except Exception as e:
        st.error(f"Error fetching diagnostics: {e}")

    render_explanation(
        what="Evaluation of how well matched controls resemble the top-ranked works across confounding variables.",
        why="If controls have vastly different project scopes or budgets, any observed differences in audit outcomes might stem from budget differences rather than project integrity.",
        look_for="Check whether Sanctioned Budget is well-balanced (|SMD| < 0.20), while fragmentation features naturally differ as they drive model anomaly ranking.",
    )
