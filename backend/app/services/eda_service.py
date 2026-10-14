import numpy as np
import pandas as pd
from backend.app.repositories.data_repository import data_repo
from backend.app.schemas.eda import (
    EDASummary, DatasetMetric, MissingValuesResponse, MissingValueItem,
    EDADistributions, DistributionHistogram
)

class EDAService:
    @staticmethod
    def get_summary() -> EDASummary:
        master = data_repo.get_master_df()
        sanc = data_repo.get_clean_sanc_df()
        exp = data_repo.get_clean_exp_df()
        comp = data_repo.get_clean_comp_df()
        mp = data_repo.get_clean_mp_df()
        
        datasets = [
            DatasetMetric(name="clean_works_sanctioned.csv", rows=len(sanc), columns=sanc.shape[1], column_names=list(sanc.columns)),
            DatasetMetric(name="clean_expenditure.csv", rows=len(exp), columns=exp.shape[1], column_names=list(exp.columns)),
            DatasetMetric(name="clean_works_completed.csv", rows=len(comp), columns=comp.shape[1], column_names=list(comp.columns)),
            DatasetMetric(name="clean_mp_summary.csv", rows=len(mp), columns=mp.shape[1], column_names=list(mp.columns)),
            DatasetMetric(name="mplads_360_master.csv", rows=len(master), columns=master.shape[1], column_names=list(master.columns)),
        ]
        
        lifecycle = master["Lifecycle_Stage"].value_counts().to_dict() if "Lifecycle_Stage" in master else {}
        work_status = master["Work_Status"].fillna("Unknown").value_counts().head(10).to_dict() if "Work_Status" in master else {}
        top_cats = master["Work category"].fillna("Unknown").value_counts().head(10).to_dict() if "Work category" in master else {}
        top_states = master["State"].fillna("Unknown").value_counts().head(10).to_dict() if "State" in master else {}
        
        return EDASummary(
            datasets=datasets,
            lifecycle_breakdown=lifecycle,
            work_status_breakdown=work_status,
            work_category_top_10=top_cats,
            state_top_10=top_states
        )

    @staticmethod
    def get_missing_values(dataset_name: str = "master") -> MissingValuesResponse:
        if dataset_name == "sanctioned":
            df = data_repo.get_clean_sanc_df()
            actual_name = "clean_works_sanctioned.csv"
        elif dataset_name == "expenditure":
            df = data_repo.get_clean_exp_df()
            actual_name = "clean_expenditure.csv"
        elif dataset_name == "completed":
            df = data_repo.get_clean_comp_df()
            actual_name = "clean_works_completed.csv"
        elif dataset_name == "mp":
            df = data_repo.get_clean_mp_df()
            actual_name = "clean_mp_summary.csv"
        else:
            df = data_repo.get_master_df()
            actual_name = "mplads_360_master.csv"
            
        tot = len(df)
        items = []
        for col in df.columns:
            miss = int(df[col].isna().sum())
            if miss > 0:
                pct = round(miss / tot * 100, 2)
                items.append(MissingValueItem(
                    column=col,
                    missing_count=miss,
                    missing_pct=pct,
                    total_count=tot
                ))
        items.sort(key=lambda x: x.missing_count, reverse=True)
        return MissingValuesResponse(dataset_name=actual_name, missing_fields=items)

    @staticmethod
    def _compute_histogram(series: pd.Series, feature_name: str, num_bins: int = 20) -> DistributionHistogram:
        s = series.dropna()
        if len(s) == 0:
            return DistributionHistogram(
                feature=feature_name,
                bins=[0.0, 1.0],
                counts=[0],
                min_val=0.0,
                max_val=0.0,
                mean_val=0.0,
                median_val=0.0
            )
        counts, bin_edges = np.histogram(s, bins=num_bins)
        return DistributionHistogram(
            feature=feature_name,
            bins=[float(round(b, 2)) for b in bin_edges],
            counts=[int(c) for c in counts],
            min_val=float(round(s.min(), 2)),
            max_val=float(round(s.max(), 2)),
            mean_val=float(round(s.mean(), 2)),
            median_val=float(round(s.median(), 2))
        )

    @staticmethod
    def get_distributions() -> EDADistributions:
        master = data_repo.get_master_df()
        
        # Sanction amount clipped at 99th percentile for clean plotting
        sanc = master["Sanction_Amount"].dropna()
        if len(sanc):
            p99 = sanc.quantile(0.99)
            sanc = sanc[sanc <= p99]
        hist_sanc = EDAService._compute_histogram(sanc, "Sanction_Amount (<=P99)")
        
        # Settled expenditure clipped at 99th percentile
        settled = master["Total_Exp_Settled"].dropna()
        settled = settled[settled > 0]
        if len(settled):
            p99 = settled.quantile(0.99)
            settled = settled[settled <= p99]
        hist_settled = EDAService._compute_histogram(settled, "Total_Exp_Settled (>0, <=P99)")
        
        # Execution duration days
        dur = master["Execution_Duration_Days"].dropna()
        dur = dur[(dur >= 0) & (dur <= 1000)]
        hist_dur = EDAService._compute_histogram(dur, "Execution_Duration_Days (0-1000d)")
        
        # Utilization ratio
        util = master["Utilization_Ratio"].dropna()
        util = util[(util >= 0) & (util <= 2.0)]
        hist_util = EDAService._compute_histogram(util, "Utilization_Ratio (0-2)")
        
        return EDADistributions(
            sanction_amount=hist_sanc,
            settled_expenditure=hist_settled,
            execution_duration_days=hist_dur,
            utilization_ratio=hist_util
        )
