import numpy as np
import pandas as pd
from backend.app.repositories.data_repository import data_repo
from backend.app.schemas.fund_utilization import (
    UtilizationSummary, StateUtilizationItem, CategoryUtilizationItem
)

class FundUtilizationService:
    @staticmethod
    def get_summary() -> UtilizationSummary:
        master = data_repo.get_master_df()
        
        sanc = float(master["Sanction_Amount"].fillna(0).sum())
        settled = float(master["Total_Exp_Settled"].fillna(0).sum())
        in_prog = float(master["Total_Exp_In_Progress"].fillna(0).sum())
        
        overall_util = (settled / sanc * 100) if sanc > 0 else 0.0
        
        comp_df = master[master["Is_Completed"] == 1]
        comp_sanc = float(comp_df["Sanction_Amount"].fillna(0).sum())
        comp_settled = float(comp_df["Total_Exp_Settled"].fillna(0).sum())
        comp_util = (comp_settled / comp_sanc * 100) if comp_sanc > 0 else 0.0
        
        prog_df = master[master["Lifecycle_Stage"] == "In-Progress / Disbursing"]
        prog_sanc = float(prog_df["Sanction_Amount"].fillna(0).sum())
        prog_settled = float(prog_df["Total_Exp_Settled"].fillna(0).sum())
        prog_util = (prog_settled / prog_sanc * 100) if prog_sanc > 0 else 0.0
        
        active_count = int((master["Total_Exp_Settled"] > 0).sum())
        
        return UtilizationSummary(
            total_sanctioned=sanc,
            total_settled=settled,
            total_in_progress=in_prog,
            overall_utilization_pct=round(overall_util, 2),
            completed_utilization_pct=round(comp_util, 2),
            in_progress_utilization_pct=round(prog_util, 2),
            total_active_works=active_count
        )

    @staticmethod
    def get_by_state(min_works: int = 1) -> list[StateUtilizationItem]:
        master = data_repo.get_master_df()
        
        grp = master.groupby("State").agg(
            works_count=("Work ID", "count"),
            sanctioned_amount=("Sanction_Amount", "sum"),
            settled_amount=("Total_Exp_Settled", "sum"),
            in_progress_amount=("Total_Exp_In_Progress", "sum")
        ).reset_index()
        
        grp = grp[grp["works_count"] >= min_works]
        grp["utilization_pct"] = np.where(
            grp["sanctioned_amount"] > 0,
            (grp["settled_amount"] / grp["sanctioned_amount"]) * 100,
            0.0
        )
        grp = grp.sort_values(by="sanctioned_amount", ascending=False)
        
        items = []
        for _, r in grp.iterrows():
            items.append(StateUtilizationItem(
                state=str(r["State"]),
                works_count=int(r["works_count"]),
                sanctioned_amount=float(round(r["sanctioned_amount"], 2)),
                settled_amount=float(round(r["settled_amount"], 2)),
                in_progress_amount=float(round(r["in_progress_amount"], 2)),
                utilization_pct=float(round(r["utilization_pct"], 2))
            ))
        return items

    @staticmethod
    def get_by_category() -> list[CategoryUtilizationItem]:
        master = data_repo.get_master_df()
        scores = data_repo.get_anomaly_scores_df()
        
        # Merge peer_tier if present
        if "peer_tier" in scores.columns:
            m = master.merge(scores[["Work ID", "peer_tier"]], on="Work ID", how="left")
        else:
            m = master.copy()
            m["peer_tier"] = "Tier 1 (Work x State)"
            
        grp = m.groupby("Work category").agg(
            works_count=("Work ID", "count"),
            sanctioned_amount=("Sanction_Amount", "sum"),
            settled_amount=("Total_Exp_Settled", "sum"),
        ).reset_index()
        
        grp["utilization_pct"] = np.where(
            grp["sanctioned_amount"] > 0,
            (grp["settled_amount"] / grp["sanctioned_amount"]) * 100,
            0.0
        )
        grp = grp.sort_values(by="sanctioned_amount", ascending=False)
        
        items = []
        for _, r in grp.iterrows():
            cat = str(r["Work category"])
            cat_df = m[m["Work category"] == cat]
            tier_dist = cat_df["peer_tier"].fillna("Not Scored / Fallback").value_counts().to_dict()
            items.append(CategoryUtilizationItem(
                category=cat,
                works_count=int(r["works_count"]),
                sanctioned_amount=float(round(r["sanctioned_amount"], 2)),
                settled_amount=float(round(r["settled_amount"], 2)),
                utilization_pct=float(round(r["utilization_pct"], 2)),
                peer_benchmark_tier_distribution=tier_dist
            ))
        return items
