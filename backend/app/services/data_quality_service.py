from typing import Optional
import pandas as pd
from backend.app.repositories.data_repository import data_repo
from backend.app.schemas.data_quality import QualitySummary, QualityCheckItem, RuleFindingItem
from backend.app.core.config import settings

FLAG_COL_MAP = {
    "duplicate_payment": "Flag_Duplicate_Payment",
    "same_day_bulk": "Flag_Same_Day_Bulk_Payment",
    "ghost_completion": "Flag_Ghost_Completion",
    "stalled_unpaid": "Flag_Stalled_Unpaid",
    "missing_photo": "Missing_Photo_Proof",
    "orphan_payment": "Flag_Orphan_Payment",
    "cost_cap": "Integrity_Cost_Cap_Violation",
    "date_sequence": "Integrity_Date_Sequence_Violation"
}

REASON_MAP = {
    "Flag_Duplicate_Payment": "Identical [Work ID + Vendor + Amount + Date] ledger rows",
    "Flag_Same_Day_Bulk_Payment": "8+ near-equal works (<=Rs 5L) to one vendor on same date",
    "Flag_Ghost_Completion": "Completed project with Rs 0 settled and Rs 0 pending expenditure",
    "Flag_Stalled_Unpaid": "Sanctioned > 180 days ago with Rs 0 disbursed",
    "Missing_Photo_Proof": "Completed project lacking completion image (post-May 2026 cutoff)",
    "Flag_Orphan_Payment": "Payment record with no corresponding Sanction order",
    "Integrity_Cost_Cap_Violation": "Settled payments exceeded sanctioned amount by >1%",
    "Integrity_Date_Sequence_Violation": "Chronological violation across recommendation, sanction, or payment dates"
}

class DataQualityService:
    @staticmethod
    def get_summary() -> QualitySummary:
        raw_rep = data_repo.get_data_quality_report()
        summary = raw_rep.get("summary", {})
        checks_data = raw_rep.get("checks", [])
        
        checks = [
            QualityCheckItem(
                check_number=c.get("check_number", 0),
                check_name=c.get("check_name", "Check"),
                status=c.get("status", "PASS"),
                message=c.get("message", ""),
                detail=c.get("detail", None),
                count=c.get("count", None),
                is_output_gate=c.get("is_output_gate", False)
            )
            for c in checks_data
        ]
        
        return QualitySummary(
            total_checks=summary.get("total_checks", len(checks)),
            passed=summary.get("passed", 0),
            warnings=summary.get("warnings", 0),
            failures=summary.get("failures", 0),
            input_warnings=summary.get("input_warnings", 0),
            output_warnings=summary.get("output_warnings", 0),
            overall_status=summary.get("overall_status", "WARN"),
            checks=checks
        )

    @staticmethod
    def get_findings(
        flag_type: Optional[str] = None,
        state: Optional[str] = None,
        category: Optional[str] = None,
        sort_by: str = "Sanction_Amount",
        sort_order: str = "desc",
        page: int = 1,
        page_size: int = 50
    ) -> tuple[list[RuleFindingItem], int]:
        master = data_repo.get_master_df().copy()
        page_size = min(page_size, settings.PAGE_SIZE_MAX)
        
        # Build filter condition
        if flag_type and flag_type in FLAG_COL_MAP:
            target_col = FLAG_COL_MAP[flag_type]
            if target_col == "Missing_Photo_Proof":
                cond = (master["Missing_Photo_Proof"] == 1) & (master.get("Post_Photo_Cutoff", 1) == 1)
            else:
                cond = master[target_col] == 1
            filtered = master[cond].copy()
            filtered["_primary_flag"] = target_col
        else:
            # Any rule flag firing
            flag_cols = [
                "Flag_Duplicate_Payment", "Flag_Same_Day_Bulk_Payment",
                "Flag_Ghost_Completion", "Flag_Stalled_Unpaid"
            ]
            cond = pd.Series(False, index=master.index)
            for fc in flag_cols:
                if fc in master.columns:
                    cond = cond | (master[fc] == 1)
            # Add post-cutoff photo missing
            if "Missing_Photo_Proof" in master.columns and "Post_Photo_Cutoff" in master.columns:
                cond = cond | ((master["Missing_Photo_Proof"] == 1) & (master["Post_Photo_Cutoff"] == 1))
            
            filtered = master[cond].copy()
            
            # Assign primary flag label
            def find_primary(row):
                for fc in flag_cols:
                    if row.get(fc, 0) == 1:
                        return fc
                if row.get("Missing_Photo_Proof", 0) == 1 and row.get("Post_Photo_Cutoff", 0) == 1:
                    return "Missing_Photo_Proof"
                return "Rule_Flag"
            filtered["_primary_flag"] = filtered.apply(find_primary, axis=1)
            
        if state:
            filtered = filtered[filtered["State"].str.upper() == state.upper()]
        if category:
            filtered = filtered[filtered["Work category"].str.upper() == category.upper()]
            
        total_records = len(filtered)
        if total_records == 0:
            return [], 0
            
        # Sorting
        ascending = (sort_order.lower() == "asc")
        if sort_by in filtered.columns:
            filtered = filtered.sort_values(by=sort_by, ascending=ascending)
        else:
            filtered = filtered.sort_values(by="Sanction_Amount", ascending=False)
            
        # Pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paged = filtered.iloc[start_idx:end_idx]
        
        findings = []
        for _, r in paged.iterrows():
            prim = r["_primary_flag"]
            findings.append(RuleFindingItem(
                work_id=str(r.get("Work ID", "")),
                state=str(r.get("State", "")),
                constituency=str(r.get("Constituency", "")),
                mp_name=str(r.get("Hon'ble Members of Parliament", "")),
                work=str(r.get("Work", "")),
                sanction_amount=float(r["Sanction_Amount"]) if pd.notna(r.get("Sanction_Amount")) else None,
                total_exp_settled=float(r["Total_Exp_Settled"]) if pd.notna(r.get("Total_Exp_Settled")) else None,
                rule_flag_type=prim,
                reason=REASON_MAP.get(prim, "Irregularity screening flag"),
                installments=int(r.get("Payment_Installments_Count", 0)) if pd.notna(r.get("Payment_Installments_Count")) else 0,
                vendors=int(r.get("Unique_Vendors_Count", 0)) if pd.notna(r.get("Unique_Vendors_Count")) else 0,
                primary_vendor=str(r.get("Primary_Vendor", "Unknown")),
                completion_date=str(r.get("Completion Date", "")) if pd.notna(r.get("Completion Date")) else None
            ))
            
        return findings, total_records
