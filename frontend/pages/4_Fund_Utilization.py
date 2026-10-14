import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pandas as pd
import plotly.express as px
import streamlit as st
from frontend.api_client import api_client, APIError
from frontend.theme import inject_css, apply_dark_theme, CHART_PALETTE
from frontend.components.disclaimer import render_disclaimer_banner
from frontend.components.formatters import lakh_crore, pct, compact
from frontend.components.metrics import metric_grid
from frontend.components.cards import section_header, empty_state
from frontend.components.dataframe import styled_table
from frontend.components.export import render_csv_download_button
from frontend.components.explainer import render_explanation

st.set_page_config(
    page_title="Fund Utilization | MPLADS FundGuard",
    page_icon="🏛️",
    layout="wide",
)

inject_css()

st.title("🏛️ Fund Utilization & Allocation Analysis")
render_disclaimer_banner(include_scope=True)

try:
    summary = api_client.get_fund_utilization_summary()
except APIError as e:
    st.error(f"Error loading utilization summary: {e.message}")
    st.stop()
except Exception as e:
    st.error(f"Failed to connect to backend: {e}")
    st.stop()

# 1. Macro Utilization Overview
section_header(
    title="1. Macro Utilization & Expenditure Scale",
    subtitle="Aggregate fund allocations and burn-down rates across the 18th Lok Sabha ledger",
)
macro_items = [
    {
        "label": "Total Sanctioned",
        "value": lakh_crore(summary.get("total_sanctioned")),
        "subtext": "Approved project allocations",
        "badge": "Approved",
        "badge_variant": "neutral",
    },
    {
        "label": "Settled Expenditure",
        "value": lakh_crore(summary.get("total_settled")),
        "subtext": "Verified disbursements",
        "badge": "Disbursed",
        "badge_variant": "pass",
    },
    {
        "label": "In-Progress Disbursing",
        "value": lakh_crore(summary.get("total_in_progress")),
        "subtext": "Active ongoing disbursements",
        "badge": "In-Flight",
        "badge_variant": "warn",
    },
    {
        "label": "Overall Utilization Rate",
        "value": pct(summary.get("overall_utilization_pct"), decimals=1, is_ratio=False),
        "subtext": "Settled / Sanctioned ratio",
        "badge": "Ratio",
        "badge_variant": "pass" if (summary.get("overall_utilization_pct", 0) >= 60) else "warn",
    },
]
metric_grid(macro_items, cols=4)

sub_items = [
    {
        "label": "Completed Works Utilization",
        "value": pct(summary.get("completed_utilization_pct"), decimals=1, is_ratio=False),
        "subtext": "Physically completed works",
        "badge": "Completed",
        "badge_variant": "pass",
    },
    {
        "label": "In-Progress Utilization",
        "value": pct(summary.get("in_progress_utilization_pct"), decimals=1, is_ratio=False),
        "subtext": "Active disbursing works",
        "badge": "Active",
        "badge_variant": "warn",
    },
    {
        "label": "Active Spending Projects",
        "value": compact(summary.get("total_active_works")),
        "subtext": "Works with settled payments > ₹0",
        "badge": "Active Works",
        "badge_variant": "neutral",
    },
]
metric_grid(sub_items, cols=3)

tab_state, tab_cat = st.tabs([
    "🗺️ State-Level Utilization Breakdown",
    "📂 Work Category Allocations & Peer Tiers",
])

# ----------------- TAB 1: State Breakdown -----------------
with tab_state:
    section_header(
        title="State-Level Allocation & Utilization Breakdown",
        subtitle="Aggregated spending patterns across States/UTs (non-evaluative summary)",
    )

    min_works = st.slider(
        "Minimum Works in State/UT to Display",
        min_value=1,
        max_value=500,
        value=10,
        step=10,
    )

    try:
        state_data = api_client.get_fund_utilization_by_state(min_works=min_works)
        if state_data:
            s_df = pd.DataFrame(state_data)

            # Chart: Sanctioned vs Settled
            fig_state = px.bar(
                s_df.head(20),
                x="state",
                y=["sanctioned_amount", "settled_amount"],
                barmode="group",
                labels={"value": "Amount (₹)", "state": "State", "variable": "Budget Type"},
                title="Top 20 States: Sanctioned vs Settled Expenditure",
                color_discrete_map={
                    "sanctioned_amount": "#2563EB",
                    "settled_amount": "#10B981",
                },
            )
            fig_state.update_layout(xaxis_tickangle=-45)
            apply_dark_theme(fig_state)
            st.plotly_chart(fig_state, use_container_width=True)

            # Table
            display_state_df = pd.DataFrame({
                "State / UT": s_df["state"],
                "Total Works": s_df["works_count"].apply(lambda x: f"{x:,}"),
                "Sanctioned": s_df["sanctioned_amount"].apply(lambda x: lakh_crore(x)),
                "Settled": s_df["settled_amount"].apply(lambda x: lakh_crore(x)),
                "In-Progress": s_df["in_progress_amount"].apply(lambda x: lakh_crore(x)),
                "Utilization %": s_df["utilization_pct"].apply(lambda x: f"{x:.1f}%"),
            })
            styled_table(display_state_df)

            render_csv_download_button(
                df=display_state_df,
                filename="state_fund_utilization.csv",
                button_label="📥 Export State Utilization Table to Sanitized CSV",
            )
        else:
            empty_state("No state data available matching threshold.")
    except Exception as e:
        st.error(f"Error loading state breakdown: {e}")

    render_explanation(
        what="State-level aggregates of approved budget versus disbursed expenditure.",
        why="Expenditure rates vary substantially due to local administrative guidelines, monsoon seasonality, and state treasury disbursement schedules.",
        look_for="States with large differences between sanctioned budget and settled expenditure.",
    )

# ----------------- TAB 2: Category Breakdown -----------------
with tab_cat:
    section_header(
        title="Sectoral Category Allocations & Peer Tiers",
        subtitle="Budget allocation across official development categories with ML peer benchmark coverage",
    )

    try:
        cat_data = api_client.get_fund_utilization_by_category()
        if cat_data:
            c_df = pd.DataFrame(cat_data)

            # Chart: Category expenditure
            fig_cat = px.bar(
                c_df.head(15),
                x="category",
                y="settled_amount",
                labels={"settled_amount": "Settled Expenditure (₹)", "category": "Work Category"},
                title="Settled Expenditure by Top Work Categories",
                color="utilization_pct",
                color_continuous_scale="Purples",
            )
            fig_cat.update_layout(xaxis_tickangle=-45)
            apply_dark_theme(fig_cat)
            st.plotly_chart(fig_cat, use_container_width=True)

            # Table
            display_cat_df = pd.DataFrame({
                "Work Category": c_df["category"],
                "Total Works": c_df["works_count"].apply(lambda x: f"{x:,}"),
                "Sanctioned": c_df["sanctioned_amount"].apply(lambda x: lakh_crore(x)),
                "Settled": c_df["settled_amount"].apply(lambda x: lakh_crore(x)),
                "Utilization %": c_df["utilization_pct"].apply(lambda x: f"{x:.1f}%"),
                "Peer Tiers Breakdown": c_df["peer_benchmark_tier_distribution"].apply(
                    lambda d: ", ".join([f"{k}: {v}" for k, v in d.items()])
                ),
            })
            styled_table(display_cat_df)

            render_csv_download_button(
                df=display_cat_df,
                filename="category_fund_utilization.csv",
                button_label="📥 Export Category Utilization Table to Sanitized CSV",
            )
        else:
            empty_state("No category data available.")
    except Exception as e:
        st.error(f"Error loading category breakdown: {e}")

    render_explanation(
        what="Sectoral breakdown across development sectors (e.g., Drinking Water, Roads, Community Halls) and assigned peer tiers.",
        why="Peer tiers ensure that an anomaly detector compares a road work against other road works in similar geographic areas, preventing small works from being misclassified.",
        look_for="Check whether categories have sufficient volume across peer tiers for reliable baseline estimation.",
    )
