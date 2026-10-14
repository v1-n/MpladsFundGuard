import os
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd
from backend.app.repositories.data_repository import data_repo
from backend.app.schemas.overview import OverviewKPIs, IntegrityChecks
from backend.app.core.config import settings

class OverviewService:
    @staticmethod
    def get_overview_kpis() -> OverviewKPIs:
        master = data_repo.get_master_df()
        scores = data_repo.get_anomaly_scores_df()
        
        tot = len(master)
        comp = int(master["Is_Completed"].sum()) if "Is_Completed" in master else 0
        in_prog = int((master["Lifecycle_Stage"] == "In-Progress / Disbursing").sum()) if "Lifecycle_Stage" in master else 0
        sanc_only = int((master["Lifecycle_Stage"] == "Sanctioned Only").sum()) if "Lifecycle_Stage" in master else 0
        
        # Pending only = works with payments where settled == 0 and in_progress > 0
        pending_only = int(((master["Total_Exp_Settled"] == 0) & (master["Total_Exp_In_Progress"] > 0)).sum()) if "Total_Exp_Settled" in master and "Total_Exp_In_Progress" in master else 0
        
        sanc_tot = float(master["Sanction_Amount"].fillna(0).sum()) if "Sanction_Amount" in master else 0.0
        settled_tot = float(master["Total_Exp_Settled"].fillna(0).sum()) if "Total_Exp_Settled" in master else 0.0
        prog_tot = float(master["Total_Exp_In_Progress"].fillna(0).sum()) if "Total_Exp_In_Progress" in master else 0.0
        remaining_unspent = max(0.0, round(sanc_tot - settled_tot, 2))
        overall_util = (settled_tot / sanc_tot) if sanc_tot > 0 else 0.0
        
        stalled = int(master["Flag_Stalled_Unpaid"].fillna(0).sum()) if "Flag_Stalled_Unpaid" in master else 0
        dup = int(master["Flag_Duplicate_Payment"].fillna(0).sum()) if "Flag_Duplicate_Payment" in master else 0
        ghost = int(master["Flag_Ghost_Completion"].fillna(0).sum()) if "Flag_Ghost_Completion" in master else 0
        bulk = int(master["Flag_Same_Day_Bulk_Payment"].fillna(0).sum()) if "Flag_Same_Day_Bulk_Payment" in master else 0
        
        # Missing photos
        post_cutoff_mask = master["Post_Photo_Cutoff"] == 1 if "Post_Photo_Cutoff" in master else pd.Series(False, index=master.index)
        missing_photo_mask = master["Missing_Photo_Proof"] == 1 if "Missing_Photo_Proof" in master else pd.Series(False, index=master.index)
        
        missing_post = int((post_cutoff_mask & missing_photo_mask).sum())
        missing_pre = int((~post_cutoff_mask & missing_photo_mask & (master["Is_Completed"] == 1)).sum())
        
        # Anomaly counts in top 300 per stage
        top_comp = int(((scores["Stage"] == "Completed") & (scores["rank_in_stage"] <= 300)).sum()) if "rank_in_stage" in scores else 0
        top_prog = int(((scores["Stage"] == "In-Progress") & (scores["rank_in_stage"] <= 300)).sum()) if "rank_in_stage" in scores else 0
        
        # Evidence-based integrity checks
        has_orphan = "Flag_Orphan_Payment" in master.columns
        has_cost_cap = "Integrity_Cost_Cap_Violation" in master.columns
        has_date_seq = "Integrity_Date_Sequence_Violation" in master.columns

        orphan = int(master["Flag_Orphan_Payment"].fillna(0).sum()) if has_orphan else 0
        cost_cap = int(master["Integrity_Cost_Cap_Violation"].fillna(0).sum()) if has_cost_cap else 0
        date_seq = int(master["Integrity_Date_Sequence_Violation"].fillna(0).sum()) if has_date_seq else 0

        if not (has_orphan and has_cost_cap and has_date_seq):
            integrity_status = "NOT VERIFIED"
        elif orphan == 0 and cost_cap == 0 and date_seq == 0:
            integrity_status = "PASS"
        else:
            integrity_status = "WARN"

        # Artifact provenance
        provenance = {}
        try:
            master_file = settings.CLEAN_DATA_DIR / "mplads_360_master.csv"
            if master_file.exists():
                mtime = os.path.getmtime(master_file)
                provenance["master_artifact_updated"] = datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()
            scores_file = settings.CLEAN_DATA_DIR / "anomaly_scores.csv"
            if scores_file.exists():
                stime = os.path.getmtime(scores_file)
                provenance["anomaly_scores_updated"] = datetime.fromtimestamp(stime, tz=timezone.utc).isoformat()
            provenance["pipeline_version"] = "2.0.0"
        except Exception:
            pass

        return OverviewKPIs(
            total_works=tot,
            completed_works=comp,
            in_progress_works=in_prog,
            sanctioned_only_works=sanc_only,
            pending_only_works=pending_only,
            total_sanctioned_amount=sanc_tot,
            total_settled_expenditure=settled_tot,
            total_in_progress_expenditure=prog_tot,
            remaining_unspent_amount=remaining_unspent,
            overall_utilization_ratio=round(overall_util, 4),
            stalled_unpaid_works=stalled,
            duplicate_payment_works=dup,
            ghost_completion_works=ghost,
            same_day_bulk_payment_works=bulk,
            missing_photos_post_cutoff=missing_post,
            missing_photos_pre_cutoff=missing_pre,
            completed_anomalies_top_300=top_comp,
            in_progress_anomalies_top_300=top_prog,
            integrity_checks=IntegrityChecks(
                orphan_payments=orphan,
                cost_cap_violations=cost_cap,
                date_sequence_violations=date_seq,
                status=integrity_status
            ),
            data_provenance=provenance,
            disclaimer=settings.DISCLAIMER
        )
