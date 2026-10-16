import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import numpy as np
import pandas as pd
from backend.app.repositories.data_repository import data_repo
from backend.app.schemas.overview import (
    OverviewKPIs,
    IntegrityChecks,
    PipelineStageItem,
    PipelineDataCounts,
)
from backend.app.core.config import settings


def _get_file_info(filepath: Path) -> tuple[bool, Optional[str]]:
    """Returns (exists, iso_mtime)."""
    if filepath.exists():
        try:
            mtime = os.path.getmtime(filepath)
            iso = datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()
            return True, iso
        except Exception:
            return True, None
    return False, None


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
        pending_only = (
            int(((master["Total_Exp_Settled"] == 0) & (master["Total_Exp_In_Progress"] > 0)).sum())
            if "Total_Exp_Settled" in master and "Total_Exp_In_Progress" in master
            else 0
        )

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

        # Check actual artifact statuses and timestamps on disk
        clean_dir = settings.CLEAN_DATA_DIR
        raw_dir = settings.DATA_DIR / "raw"

        sanc_file = clean_dir / "clean_works_sanctioned.csv"
        exp_file = clean_dir / "clean_expenditure.csv"
        comp_file = clean_dir / "clean_works_completed.csv"
        master_file = clean_dir / "mplads_360_master.csv"
        feat_file = clean_dir / "ml_features.csv"
        scores_file = clean_dir / "anomaly_scores.csv"
        blind_file = clean_dir / "manual_audit_sample_blind.csv"
        diag_file = clean_dir / "audit_matching_diagnostics.json"
        quality_file = clean_dir / "data_quality_report.json"
        eval_file = clean_dir / "evaluation_results.json"

        sanc_ok, sanc_mtime = _get_file_info(sanc_file)
        exp_ok, exp_mtime = _get_file_info(exp_file)
        comp_ok, comp_mtime = _get_file_info(comp_file)
        master_ok, master_mtime = _get_file_info(master_file)
        feat_ok, feat_mtime = _get_file_info(feat_file)
        scores_ok, scores_mtime = _get_file_info(scores_file)
        blind_ok, blind_mtime = _get_file_info(blind_file)
        diag_ok, diag_mtime = _get_file_info(diag_file)
        quality_ok, quality_mtime = _get_file_info(quality_file)
        eval_ok, eval_mtime = _get_file_info(eval_file)

        # Raw file rows count
        raw_rows_total = None
        if raw_dir.exists():
            try:
                total_raw = 0
                for rf in raw_dir.glob("*.csv"):
                    with open(rf, "r", encoding="utf-8", errors="ignore") as f:
                        lines = sum(1 for _ in f)
                    total_raw += max(0, lines - 1)
                raw_rows_total = total_raw
            except Exception:
                pass

        # Pipeline counts
        sanc_count = len(data_repo.get_clean_df("clean_works_sanctioned.csv")) if sanc_ok else None
        exp_count = len(data_repo.get_clean_df("clean_expenditure.csv")) if exp_ok else None
        comp_count = len(data_repo.get_clean_df("clean_works_completed.csv")) if comp_ok else None
        scores_count = len(scores) if scores_ok else None
        blind_count = len(data_repo.get_blind_audit_sample_df()) if blind_ok else None

        pipeline_counts = PipelineDataCounts(
            raw_source_rows=raw_rows_total,
            cleaned_sanctioned_rows=sanc_count,
            cleaned_expenditure_rows=exp_count,
            cleaned_completed_rows=comp_count,
            unique_master_works=tot if master_ok else None,
            ml_scored_works=scores_count,
            blind_audit_sample_works=blind_count,
        )

        # 8 Methodology Pipeline Stages
        pipeline_stages = [
            PipelineStageItem(
                stage_number=1,
                name="Raw Portal Ingestion",
                description=f"{raw_rows_total:,} rows across raw portal exports" if raw_rows_total else "Raw exports from MoSPI",
                status="COMPLETED" if raw_rows_total else "NOT VERIFIED",
                artifact_name="data/raw/*.csv",
                item_count=raw_rows_total,
                updated_at=None,
            ),
            PipelineStageItem(
                stage_number=2,
                name="Schema Normalization",
                description=f"{sanc_count:,} sanctioned, {exp_count:,} expenditure rows" if (sanc_count and exp_count) else "Schema types, dates & IDs",
                status="COMPLETED" if (sanc_ok and exp_ok) else "NOT VERIFIED",
                artifact_name="clean_works_sanctioned.csv",
                item_count=sanc_count,
                updated_at=sanc_mtime,
            ),
            PipelineStageItem(
                stage_number=3,
                name="Integrity Screening",
                description="8 canonical rules & 14 quality gates" if quality_ok else "Quality checks not verified",
                status="COMPLETED" if quality_ok else "NOT VERIFIED",
                artifact_name="data_quality_report.json",
                item_count=8,
                updated_at=quality_mtime,
            ),
            PipelineStageItem(
                stage_number=4,
                name="Indicator Extraction",
                description=f"{len(data_repo.get_clean_df('ml_features.csv')):,} works with engineered signals" if feat_ok else "Indicator extraction",
                status="COMPLETED" if feat_ok else "NOT VERIFIED",
                artifact_name="ml_features.csv",
                item_count=58050 if feat_ok else None,
                updated_at=feat_mtime,
            ),
            PipelineStageItem(
                stage_number=5,
                name="Cohort Stratification",
                description=f"{comp:,} completed • {in_prog:,} in-progress" if master_ok else "Stratified by lifecycle stage",
                status="COMPLETED" if master_ok else "NOT VERIFIED",
                artifact_name="mplads_360_master.csv",
                item_count=tot if master_ok else None,
                updated_at=master_mtime,
            ),
            PipelineStageItem(
                stage_number=6,
                name="Unsupervised Scoring",
                description=f"{scores_count:,} scored works (IForest 10 seeds)" if scores_ok else "Scoring not verified",
                status="COMPLETED" if scores_ok else "NOT VERIFIED",
                artifact_name="anomaly_scores.csv",
                item_count=scores_count,
                updated_at=scores_mtime,
            ),
            PipelineStageItem(
                stage_number=7,
                name="Diagnostic Balancing",
                description="SMD matched controls (50 top vs 50 matched)" if diag_ok else "Diagnostics not verified",
                status="COMPLETED" if diag_ok else "NOT VERIFIED",
                artifact_name="audit_matching_diagnostics.json",
                item_count=100 if diag_ok else None,
                updated_at=diag_mtime,
            ),
            PipelineStageItem(
                stage_number=8,
                name="Human Blind Audit",
                description=f"{blind_count} works in active blind audit protocol" if blind_ok else "Audit sample not verified",
                status="ACTIVE" if blind_ok else "NOT VERIFIED",
                artifact_name="manual_audit_sample_blind.csv",
                item_count=blind_count,
                updated_at=blind_mtime,
            ),
        ]

        provenance = {
            "pipeline_version": "2.0.0",
            "master_artifact_updated": master_mtime or "NOT VERIFIED",
            "anomaly_scores_updated": scores_mtime or "NOT VERIFIED",
            "quality_report_updated": quality_mtime or "NOT VERIFIED",
            "evaluation_results_updated": eval_mtime or "NOT VERIFIED",
        }

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
                status=integrity_status,
            ),
            pipeline_counts=pipeline_counts,
            pipeline_stages=pipeline_stages,
            data_provenance=provenance,
            disclaimer=settings.DISCLAIMER,
        )
