import streamlit as st
import pandas as pd
import plotly.express as px
from frontend.api_client import api_client, APIError
from frontend.components.disclaimer import render_disclaimer_banner
from frontend.components.kpi_card import format_currency_inr, format_number
from frontend.components.export import render_csv_download_button

st.set_page_config(page_title="Fund Utilization | MPLADS FundGuard", page_icon="🏛️", layout="wide")

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

# 1. Macro Utilization KPIs
st.subheader("1. Macro Utilization Overview")
k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Sanctioned", format_currency_inr(summary.get("total_sanctioned", 0)))
k2.metric("Total Settled Expenditure", format_currency_inr(summary.get("total_settled", 0)))
k3.metric("Total In-Progress / Disbursing", format_currency_inr(summary.get("total_in_progress", 0)))
k4.metric("Overall Utilization Rate", f"{summary.get('overall_utilization_pct', 0):.1f}%")

c1, c2, c3 = st.columns(3)
c1.metric("Completed Works Utilization", f"{summary.get('completed_utilization_pct', 0):.1f}%", help="Settled / Sanctioned for physically completed works")
c2.metric("In-Progress Works Utilization", f"{summary.get('in_progress_utilization_pct', 0):.1f}%", help="Settled / Sanctioned for works currently disbursing")
c3.metric("Active Spending Projects", format_number(summary.get("total_active_works", 0)), help="Works with settled disbursements > ₹0")

st.markdown("---")

tab_state, tab_cat = st.tabs(["🗺️ State-Level Utilization Breakdown", "📂 Work Category Allocations"])

# ----------------- TAB 1: State Breakdown -----------------
with tab_state:
    st.subheader("State-Level Allocation & Utilization Breakdown")
    st.caption("Aggregated spending patterns across States/UTs. Sorted by total sanctioned budget (non-evaluative summary).")

    min_works = st.slider("Minimum Works in State to Display", min_value=1, max_value=500, value=10, step=10)

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
                color_discrete_map={"sanctioned_amount": "#1f77b4", "settled_amount": "#2ca02c"}
            )
            fig_state.update_layout(xaxis_tickangle=-45, margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(fig_state, use_container_width=True)

            # Table
            display_state_df = pd.DataFrame({
                "State / UT": s_df["state"],
                "Total Works": s_df["works_count"].apply(lambda x: f"{x:,}"),
                "Sanctioned (Cr)": (s_df["sanctioned_amount"] / 1e7).apply(lambda x: f"₹{x:,.2f} Cr"),
                "Settled (Cr)": (s_df["settled_amount"] / 1e7).apply(lambda x: f"₹{x:,.2f} Cr"),
                "In-Progress (Cr)": (s_df["in_progress_amount"] / 1e7).apply(lambda x: f"₹{x:,.2f} Cr"),
                "Utilization %": s_df["utilization_pct"].apply(lambda x: f"{x:.1f}%")
            })
            st.dataframe(display_state_df, use_container_width=True)

            render_csv_download_button(
                df=display_state_df,
                filename="state_fund_utilization.csv",
                button_label="📥 Export State Utilization Table to CSV"
            )
        else:
            st.info("No state data available.")
    except Exception as e:
        st.error(f"Error loading state breakdown: {e}")

# ----------------- TAB 2: Category Breakdown -----------------
with tab_cat:
    st.subheader("Work Category Allocations & Peer Tiers")
    st.caption("Budget allocation across official MPLADS development categories with ML peer benchmark coverage.")

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
                color_continuous_scale="Viridis"
            )
            fig_cat.update_layout(xaxis_tickangle=-45, margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(fig_cat, use_container_width=True)

            # Table
            display_cat_df = pd.DataFrame({
                "Work Category": c_df["category"],
                "Total Works": c_df["works_count"].apply(lambda x: f"{x:,}"),
                "Sanctioned (Cr)": (c_df["sanctioned_amount"] / 1e7).apply(lambda x: f"₹{x:,.2f} Cr"),
                "Settled (Cr)": (c_df["settled_amount"] / 1e7).apply(lambda x: f"₹{x:,.2f} Cr"),
                "Utilization %": c_df["utilization_pct"].apply(lambda x: f"{x:.1f}%"),
                "Peer Tiers Breakdown": c_df["peer_benchmark_tier_distribution"].apply(lambda d: ", ".join([f"{k}: {v}" for k, v in d.items()]))
            })
            st.dataframe(display_cat_df, use_container_width=True)

            render_csv_download_button(
                df=display_cat_df,
                filename="category_fund_utilization.csv",
                button_label="📥 Export Category Utilization Table to CSV"
            )
        else:
            st.info("No category data available.")
    except Exception as e:
        st.error(f"Error loading category breakdown: {e}")
