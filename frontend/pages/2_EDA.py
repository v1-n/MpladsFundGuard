import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from frontend.api_client import api_client, APIError
from frontend.components.disclaimer import render_disclaimer_banner

st.set_page_config(page_title="EDA & Data Exploration | MPLADS FundGuard", page_icon="📈", layout="wide")

st.title("📈 Exploratory Data Analysis (EDA)")
render_disclaimer_banner()

tab1, tab2, tab3 = st.tabs(["📁 Dataset Catalog & Breakdown", "🔍 Missing Value Diagnostics", "📊 Feature Distributions"])

# ----------------- TAB 1: Catalog & Breakdown -----------------
with tab1:
    try:
        eda_summary = api_client.get_eda_summary()
    except APIError as e:
        st.error(f"Error loading EDA summary: {e.message}")
        st.stop()
    except Exception as e:
        st.error(f"Failed to connect to backend: {e}")
        st.stop()

    st.subheader("1. Pipeline Clean Datasets")
    datasets = eda_summary.get("datasets", [])
    if datasets:
        cat_df = pd.DataFrame([
            {
                "Dataset File": d["name"],
                "Row Count": f"{d['rows']:,}",
                "Columns Count": d["columns"],
                "Key Columns": ", ".join(d["column_names"][:5]) + ("..." if len(d["column_names"]) > 5 else "")
            }
            for d in datasets
        ])
        st.dataframe(cat_df, use_container_width=True)

    st.markdown("---")
    st.subheader("2. Work Classification Distributions")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Lifecycle Stages")
        lifecycle = eda_summary.get("lifecycle_breakdown", {})
        if lifecycle:
            fig_life = px.pie(
                names=list(lifecycle.keys()),
                values=list(lifecycle.values()),
                hole=0.4,
                title="Proportion of Works by Lifecycle Stage"
            )
            fig_life.update_traces(textposition="inside", textinfo="percent+label")
            st.plotly_chart(fig_life, use_container_width=True)

    with col2:
        st.markdown("#### Top 10 Work Categories")
        cats = eda_summary.get("work_category_top_10", {})
        if cats:
            cat_series = pd.Series(cats).sort_values(ascending=True)
            fig_cat = px.bar(
                x=cat_series.values,
                y=cat_series.index,
                orientation="h",
                labels={"x": "Number of Works", "y": "Work Category"},
                title="Top 10 Work Categories by Frequency"
            )
            fig_cat.update_layout(margin=dict(l=10, r=10, t=30, b=10))
            st.plotly_chart(fig_cat, use_container_width=True)

# ----------------- TAB 2: Missing Values -----------------
with tab2:
    st.subheader("Missing Value Audit across Pipeline Tables")
    dataset_choice = st.selectbox(
        "Select Dataset to Inspect",
        options=["master", "sanctioned", "expenditure", "completed", "mp"],
        format_func=lambda x: {
            "master": "mplads_360_master.csv (Enriched 360 View)",
            "sanctioned": "clean_works_sanctioned.csv",
            "expenditure": "clean_expenditure.csv",
            "completed": "clean_works_completed.csv",
            "mp": "clean_mp_summary.csv"
        }[x]
    )

    try:
        miss_data = api_client.get_eda_missing_values(dataset=dataset_choice)
        fields = miss_data.get("missing_fields", [])
        if fields:
            miss_df = pd.DataFrame(fields)
            st.dataframe(
                miss_df.rename(columns={
                    "column": "Column Name",
                    "missing_count": "Missing Rows",
                    "missing_pct": "Missing %",
                    "total_count": "Total Rows"
                }),
                use_container_width=True
            )
            
            # Plot bar of missing %
            fig_miss = px.bar(
                miss_df.head(15),
                x="missing_pct",
                y="column",
                orientation="h",
                labels={"missing_pct": "Missing Percentage (%)", "column": "Field"},
                title=f"Fields with Highest Missingness in {miss_data.get('dataset_name', '')}"
            )
            fig_miss.update_layout(yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig_miss, use_container_width=True)
        else:
            st.success(f"No missing values found in {dataset_choice} dataset!")
    except Exception as e:
        st.error(f"Error fetching missing values: {e}")

# ----------------- TAB 3: Distributions -----------------
with tab3:
    st.subheader("Feature Distributions (Empirical vs Peer Baseline)")
    try:
        dist_data = api_client.get_eda_distributions()
    except Exception as e:
        st.error(f"Error fetching distributions: {e}")
        st.stop()

    def render_histogram(hist_dict, title, x_label):
        bins = hist_dict.get("bins", [])
        counts = hist_dict.get("counts", [])
        if not bins or not counts:
            st.info("No distribution data available.")
            return

        bin_centers = [(bins[i] + bins[i+1]) / 2 for i in range(len(counts))]
        fig = go.Figure(data=[go.Bar(x=bin_centers, y=counts, width=[bins[i+1] - bins[i] for i in range(len(counts))])])
        fig.update_layout(
            title=title,
            xaxis_title=x_label,
            yaxis_title="Count",
            margin=dict(l=10, r=10, t=35, b=10)
        )
        st.plotly_chart(fig, use_container_width=True)
        
        mcol1, mcol2, mcol3, mcol4 = st.columns(4)
        mcol1.metric("Min", f"{hist_dict.get('min_val', 0):,.1f}")
        mcol2.metric("Median", f"{hist_dict.get('median_val', 0):,.1f}")
        mcol3.metric("Mean", f"{hist_dict.get('mean_val', 0):,.1f}")
        mcol4.metric("Max", f"{hist_dict.get('max_val', 0):,.1f}")

    dcol1, dcol2 = st.columns(2)
    with dcol1:
        render_histogram(
            dist_data.get("sanction_amount", {}),
            "Sanction Amount Distribution (Clipped at P99)",
            "Sanction Amount (₹)"
        )
    with dcol2:
        render_histogram(
            dist_data.get("settled_expenditure", {}),
            "Settled Expenditure Distribution (> ₹0, Clipped at P99)",
            "Settled Expenditure (₹)"
        )

    st.markdown("---")
    dcol3, dcol4 = st.columns(2)
    with dcol3:
        render_histogram(
            dist_data.get("execution_duration_days", {}),
            "Execution Duration Days (0 to 1,000 Days)",
            "Duration (Days from Sanction to Completion)"
        )
    with dcol4:
        render_histogram(
            dist_data.get("utilization_ratio", {}),
            "Utilization Ratio Distribution (Settled / Sanctioned)",
            "Ratio (0.0 to 2.0)"
        )
