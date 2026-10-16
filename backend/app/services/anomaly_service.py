from typing import Optional
import pandas as pd
from backend.app.repositories.data_repository import data_repo
from backend.app.schemas.anomalies import AnomalyItem, AnomalyDetail
from backend.app.core.errors import NotFoundException
from backend.app.core.config import settings

SORT_COLUMN_MAPPING: dict[str, str] = {
    "rank_in_stage": "rank_in_stage",
    "anomaly_score": "anomaly_score",
    "sanction_amount": "Sanction_Amount",
    "total_exp_settled": "Total_Exp_Settled",
    "total_exp_in_progress": "Total_Exp_In_Progress",
    "paid_vs_peer_log": "paid_vs_peer_log",
    "work_id": "Work ID",
    "state": "State",
    "constituency": "Constituency",
    "n_rule_flags": "n_rule_flags",
}


class AnomalyService:
    @staticmethod
    def get_anomalies(
        stage: Optional[str] = None,
        state: Optional[str] = None,
        category: Optional[str] = None,
        min_score: Optional[float] = None,
        max_score: Optional[float] = None,
        search: Optional[str] = None,
        sort_by: str = "rank_in_stage",
        sort_order: str = "asc",
        page: int = 1,
        page_size: int = 50
    ) -> tuple[list[AnomalyItem], int]:
        scores = data_repo.get_anomaly_scores_df().copy()
        page_size = min(page_size, settings.PAGE_SIZE_MAX)
        
        # Filtering
        if stage:
            scores = scores[scores["Stage"].str.upper() == stage.upper()]
        if state:
            scores = scores[scores["State"].str.upper() == state.upper()]
        if category:
            scores = scores[scores["Work"].str.contains(category, case=False, na=False)]
        if min_score is not None:
            scores = scores[scores["anomaly_score"] >= min_score]
        if max_score is not None:
            scores = scores[scores["anomaly_score"] <= max_score]
        if search:
            q = search.strip()
            scores = scores[
                scores["Work ID"].str.contains(q, case=False, na=False) |
                scores["Work"].str.contains(q, case=False, na=False) |
                scores["Constituency"].str.contains(q, case=False, na=False) |
                scores["Hon'ble Members of Parliament"].str.contains(q, case=False, na=False)
            ]
            
        total_records = len(scores)
        if total_records == 0:
            return [], 0
            
        # Sorting strictly against allowlisted columns
        ascending = (sort_order.lower() == "asc")
        sort_col = SORT_COLUMN_MAPPING.get(sort_by, "rank_in_stage")
        if sort_col in scores.columns:
            scores = scores.sort_values(by=sort_col, ascending=ascending)
        else:
            scores = scores.sort_values(by="rank_in_stage", ascending=True)
            
        # Pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paged = scores.iloc[start_idx:end_idx]
        
        flag_cols = [c for c in scores.columns if c.startswith("Flag_") or c.startswith("Missing_")]
        
        items = []
        for _, r in paged.iterrows():
            flags_dict = {fc: int(r[fc]) for fc in flag_cols if pd.notna(r.get(fc))}
            ext_feat = str(r.get("extreme_feature_indicators", ""))
            top_fac = str(r.get("top_anomalous_factors", ext_feat))
            
            items.append(AnomalyItem(
                work_id=str(r["Work ID"]),
                stage=str(r["Stage"]),
                rank_in_stage=int(r["rank_in_stage"]),
                anomaly_score=float(round(r["anomaly_score"], 4)),
                extreme_feature_indicators=ext_feat,
                top_anomalous_factors=top_fac,
                state=str(r.get("State", "")),
                constituency=str(r.get("Constituency", "")),
                mp_name=str(r.get("Hon'ble Members of Parliament", "")),
                work=str(r.get("Work", "")),
                sanction_amount=float(r["Sanction_Amount"]) if pd.notna(r.get("Sanction_Amount")) else None,
                total_exp_settled=float(r["Total_Exp_Settled"]) if pd.notna(r.get("Total_Exp_Settled")) else None,
                total_exp_in_progress=float(r["Total_Exp_In_Progress"]) if pd.notna(r.get("Total_Exp_In_Progress")) else None,
                paid_vs_peer_log=float(round(r["paid_vs_peer_log"], 4)) if pd.notna(r.get("paid_vs_peer_log")) else None,
                peer_tier=str(r.get("peer_tier", "Tier 1 (Work x State)")),
                peer_median_settled=float(r["peer_median_settled"]) if pd.notna(r.get("peer_median_settled")) else None,
                n_rule_flags=int(r.get("n_rule_flags", 0)) if pd.notna(r.get("n_rule_flags")) else 0,
                flags=flags_dict
            ))
            
        return items, total_records

    @staticmethod
    def get_anomaly_detail(work_id: str) -> AnomalyDetail:
        scores = data_repo.get_anomaly_scores_df()
        row_score = scores[scores["Work ID"] == work_id]
        
        if row_score.empty:
            # Check master if work exists but was not scored
            master = data_repo.get_master_df()
            row_master = master[master["Work ID"] == work_id]
            if row_master.empty:
                raise NotFoundException("Work ID", work_id)
            # Work is in master but was un-scored (e.g. 0 payment or pending only)
            r = row_master.iloc[0]
            stage = str(r.get("Lifecycle_Stage", "Not Scored"))
            flag_cols = [c for c in master.columns if c.startswith("Flag_") or c.startswith("Missing_") or c.startswith("Integrity_")]
            flags_dict = {fc: int(r[fc]) for fc in flag_cols if pd.notna(r.get(fc))}
            missing_photo = bool(r.get("Missing_Photo_Proof") == 1) if pd.notna(r.get("Missing_Photo_Proof")) else False
            post_cutoff = bool(r.get("Post_Photo_Cutoff") == 1) if pd.notna(r.get("Post_Photo_Cutoff")) else False
            if missing_photo:
                photo_status = "NON-COMPLIANT (Post-April 2023 mandate, missing photo proof)" if post_cutoff else "EXEMPT (Pre-April 2023 sanction date, photo advisory only)"
            else:
                photo_status = "COMPLIANT (Photographic documentation uploaded)"
            return AnomalyDetail(
                work_id=work_id,
                stage=stage,
                rank_in_stage=-1,
                percentile_in_stage=None,
                anomaly_score=0.0,
                extreme_feature_indicators="Not scored (cohort has zero settled expenditure)",
                top_anomalous_factors="Not scored (cohort has zero settled expenditure)",
                state=str(r.get("State", "")),
                constituency=str(r.get("Constituency", "")),
                mp_name=str(r.get("Hon'ble Members of Parliament", "")),
                work=str(r.get("Work", "")),
                work_description=str(r.get("Work_Description_Final", "")),
                work_category=str(r.get("Work category", "")),
                sanction_amount=float(r["Sanction_Amount"]) if pd.notna(r.get("Sanction_Amount")) else None,
                total_exp_settled=float(r["Total_Exp_Settled"]) if pd.notna(r.get("Total_Exp_Settled")) else None,
                total_exp_in_progress=float(r["Total_Exp_In_Progress"]) if pd.notna(r.get("Total_Exp_In_Progress")) else None,
                utilization_ratio=float(round(r["Utilization_Ratio"], 4)) if pd.notna(r.get("Utilization_Ratio")) else None,
                cost_variance=float(round(r["Cost_Variance"], 2)) if pd.notna(r.get("Cost_Variance")) else None,
                paid_vs_peer_log=None,
                peer_tier="Not Scored",
                peer_median_settled=None,
                recommended_date=str(r.get("Recommended date", "")),
                sanction_date=str(r.get("Sanction Date", "")),
                completion_date=str(r.get("Completion Date", "")),
                sanction_approval_days=float(r["Sanction_Approval_Days"]) if pd.notna(r.get("Sanction_Approval_Days")) else None,
                execution_duration_days=float(r["Execution_Duration_Days"]) if pd.notna(r.get("Execution_Duration_Days")) else None,
                first_payment_lag_days=float(r["First_Payment_Lag_Days"]) if pd.notna(r.get("First_Payment_Lag_Days")) else None,
                installments_count=int(r.get("Payment_Installments_Count", 0)),
                settled_count=int(r.get("Settled_Count", 0)),
                in_progress_count=int(r.get("In_Progress_Count", 0)),
                vendors_count=int(r.get("Unique_Vendors_Count", 0)),
                primary_vendor=str(r.get("Primary_Vendor", "Unknown")),
                photo_compliance_status=photo_status,
                portal_url="https://www.mplads.gov.in/",
                rule_flags=flags_dict,
                methodology_note="This work has zero settled payments and was excluded from ML anomaly scoring. Flags are derived strictly from deterministic ledger rules."
            )
            
        r_sc = row_score.iloc[0]
        master = data_repo.get_master_df()
        r_m = master[master["Work ID"] == work_id].iloc[0]
        
        flag_cols = [c for c in master.columns if c.startswith("Flag_") or c.startswith("Missing_") or c.startswith("Integrity_")]
        flags_dict = {fc: int(r_m[fc]) for fc in flag_cols if pd.notna(r_m.get(fc))}
        
        ext_feat = str(r_sc.get("extreme_feature_indicators", ""))
        top_fac = str(r_sc.get("top_anomalous_factors", ext_feat))

        total_in_stage = len(scores[scores["Stage"] == str(r_sc["Stage"])])
        rank_val = int(r_sc["rank_in_stage"])
        percentile_val = round((1.0 - (rank_val - 1) / max(1, total_in_stage)) * 100.0, 2)

        missing_photo = bool(r_m.get("Missing_Photo_Proof") == 1) if pd.notna(r_m.get("Missing_Photo_Proof")) else False
        post_cutoff = bool(r_m.get("Post_Photo_Cutoff") == 1) if pd.notna(r_m.get("Post_Photo_Cutoff")) else False
        if missing_photo:
            photo_status = "NON-COMPLIANT (Post-April 2023 mandate, missing photo proof)" if post_cutoff else "EXEMPT (Pre-April 2023 sanction date, photo advisory only)"
        else:
            photo_status = "COMPLIANT (Photographic documentation uploaded)"
        
        return AnomalyDetail(
            work_id=work_id,
            stage=str(r_sc["Stage"]),
            rank_in_stage=rank_val,
            percentile_in_stage=percentile_val,
            anomaly_score=float(round(r_sc["anomaly_score"], 4)),
            extreme_feature_indicators=ext_feat,
            top_anomalous_factors=top_fac,
            state=str(r_sc.get("State", "")),
            constituency=str(r_sc.get("Constituency", "")),
            mp_name=str(r_sc.get("Hon'ble Members of Parliament", "")),
            work=str(r_sc.get("Work", "")),
            work_description=str(r_m.get("Work_Description_Final", "")),
            work_category=str(r_m.get("Work category", "")),
            sanction_amount=float(r_sc["Sanction_Amount"]) if pd.notna(r_sc.get("Sanction_Amount")) else None,
            total_exp_settled=float(r_sc["Total_Exp_Settled"]) if pd.notna(r_sc.get("Total_Exp_Settled")) else None,
            total_exp_in_progress=float(r_sc["Total_Exp_In_Progress"]) if pd.notna(r_sc.get("Total_Exp_In_Progress")) else None,
            utilization_ratio=float(round(r_m["Utilization_Ratio"], 4)) if pd.notna(r_m.get("Utilization_Ratio")) else None,
            cost_variance=float(round(r_m["Cost_Variance"], 2)) if pd.notna(r_m.get("Cost_Variance")) else None,
            paid_vs_peer_log=float(round(r_sc["paid_vs_peer_log"], 4)) if pd.notna(r_sc.get("paid_vs_peer_log")) else None,
            peer_tier=str(r_sc.get("peer_tier", "Tier 1 (Work x State)")),
            peer_median_settled=float(r_sc["peer_median_settled"]) if pd.notna(r_sc.get("peer_median_settled")) else None,
            recommended_date=str(r_m.get("Recommended date", "")),
            sanction_date=str(r_m.get("Sanction Date", "")),
            completion_date=str(r_m.get("Completion Date", "")),
            sanction_approval_days=float(r_m["Sanction_Approval_Days"]) if pd.notna(r_m.get("Sanction_Approval_Days")) else None,
            execution_duration_days=float(r_m["Execution_Duration_Days"]) if pd.notna(r_m.get("Execution_Duration_Days")) else None,
            first_payment_lag_days=float(r_m["First_Payment_Lag_Days"]) if pd.notna(r_m.get("First_Payment_Lag_Days")) else None,
            installments_count=int(r_m.get("Payment_Installments_Count", 0)),
            settled_count=int(r_m.get("Settled_Count", 0)),
            in_progress_count=int(r_m.get("In_Progress_Count", 0)),
            vendors_count=int(r_m.get("Unique_Vendors_Count", 0)),
            primary_vendor=str(r_m.get("Primary_Vendor", "Unknown")),
            photo_compliance_status=photo_status,
            portal_url="https://www.mplads.gov.in/",
            rule_flags=flags_dict,
            methodology_note=(
                "The anomaly score reflects multi-dimensional distance from peers using an Isolation Forest ensemble (10 seeds, max_samples=1024). "
                "Works with high scores primarily reflect unusually fragmented payment structures (high installments and vendor counts) "
                "or extreme costs relative to peer medians. Scores are exploratory screening rankings, not evidence of wrongdoing."
            )
        )
