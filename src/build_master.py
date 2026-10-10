"""
src/build_master.py
===================
Builds the MPLADS 360° Master Dataset by joining Works Sanctioned,
Expenditure, and Works Completed on canonical Work ID.

Flags generated here are SCREENING INDICATORS for manual review.
They do not constitute proof of fraud or financial misconduct.
"""
import re
import numpy as np
import pandas as pd
from pathlib import Path

# Setup Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


def get_clean_filepath(filename):
    """Finds the file in data/clean/ or data/."""
    p_clean = DATA_DIR / "clean" / filename
    if p_clean.exists():
        return p_clean
    p_direct = DATA_DIR / filename
    if p_direct.exists():
        return p_direct
    return DATA_DIR / "clean" / filename


print("=" * 80)
print("   BUILDING MPLADS 360° MASTER DATASET & FORENSIC AUDIT FEATURES")
print("=" * 80)

# ====================================================================
# 1. Load Datasets
# ====================================================================
print("\n[1/5] Loading cleaned datasets...")
df_sanc = pd.read_csv(get_clean_filepath("clean_works_sanctioned.csv"), low_memory=False)
df_exp  = pd.read_csv(get_clean_filepath("clean_expenditure.csv"),       low_memory=False)
df_comp = pd.read_csv(get_clean_filepath("clean_works_completed.csv"),   low_memory=False)

# Parse dates — ISO format first (clean files), portal format fallback
def parse_dates(df, cols):
    for c in cols:
        if c in df.columns:
            s = df[c].astype("string").str.strip()
            out = pd.to_datetime(s, errors="coerce", format="%Y-%m-%d")
            miss = out.isna() & s.notna() & (s != "")
            if miss.any():
                out[miss] = pd.to_datetime(s[miss], errors="coerce", format="%d-%b-%Y")
            df[c] = out
    return df

df_sanc = parse_dates(df_sanc, ["Recommended date", "Sanction Date"])
df_exp  = parse_dates(df_exp,  ["Expenditure Date"])
df_comp = parse_dates(df_comp, ["Completion Date"])

# Provenance markers — set from file membership, not date logic
df_sanc["_in_sanc"] = 1
df_comp["_in_comp"] = 1

# ====================================================================
# 2. Aggregate Multi-Transaction Expenditure (Many-to-1)
# ====================================================================
print("\n[2/5] Aggregating multi-payment expenditure per Work ID...")

AMT = "Fund Disbursed Amount ( ₹ )"

# ── Vendor key normalisation ────────────────────────────────────────
df_exp["vendor_key"] = (
    df_exp["Vendor Name"]
    .fillna("")
    .astype(str)
    .str.upper()
    .str.replace(r"[^A-Z0-9 ]", " ", regex=True)
    .str.replace(r"\s+", " ", regex=True)
    .str.strip()
)

# ── Duplicate payment detection ────────────────────────────────────
# Same [Work ID + vendor + amount + date] is a screening flag only.
# Equal installments legitimately repeat amount; UTR/voucher matching
# is needed to confirm real double-payment.
df_exp["is_dup_copy"] = df_exp.duplicated(
    subset=["Work ID", "vendor_key", AMT, "Expenditure Date"], keep="first"
)
df_exp["dup_amount"] = df_exp[AMT].where(df_exp["is_dup_copy"], 0.0)

# ── Payment status segmentation ────────────────────────────────────
# "Payment Success" = settled; "Payment In-Progress" = pending.
# We keep BOTH totals so downstream code can use either.
SUCCESS_STATUS = "Payment Success"
df_exp["settled_amount"]     = df_exp[AMT].where(df_exp["Payment Status"].eq(SUCCESS_STATUS), 0.0)
df_exp["in_progress_amount"] = df_exp[AMT].where(~df_exp["Payment Status"].eq(SUCCESS_STATUS), 0.0)

print(f"  • Sanctioned records:    {len(df_sanc):,}")
print(f"  • Expenditure rows:      {len(df_exp):,}  "
      f"(Success: {df_exp['Payment Status'].eq(SUCCESS_STATUS).sum():,}  "
      f"| In-Progress: {(~df_exp['Payment Status'].eq(SUCCESS_STATUS)).sum():,})")
print(f"  • Exact duplicate rows:  {df_exp['is_dup_copy'].sum():,}  "
      "(screening flag only — equal installments also match this pattern)")
print(f"  • Completed records:     {len(df_comp):,}")

def get_primary_vendor(vendors):
    v_clean = vendors.dropna().tolist()
    if not v_clean:
        return "Unknown"
    mode_val = pd.Series(v_clean).mode()
    return mode_val.iloc[0] if not mode_val.empty else "Unknown"

def first_valid(series):
    s_clean = series.dropna()
    return s_clean.iloc[0] if not s_clean.empty else np.nan

df_exp_agg = df_exp.groupby("Work ID").agg(
    Exp_State                = ("State",                  first_valid),
    Exp_Constituency         = ("Constituency",           first_valid),
    Exp_IDA                  = ("IDA",                    first_valid),
    Exp_MP                   = ("Hon'ble Members of Parliament", first_valid),
    Exp_Work                 = ("Work",                   first_valid),
    # ── Financial totals — all three variants kept ───────────────────
    Total_Exp_Disbursed      = (AMT,                      "sum"),   # all rows
    Total_Exp_Settled        = ("settled_amount",         "sum"),   # success only
    Total_Exp_In_Progress    = ("in_progress_amount",     "sum"),   # pending
    # ────────────────────────────────────────────────────────────────
    Payment_Installments_Count = (AMT,                   "size"),   # total row count
    Settled_Count            = ("settled_amount",         lambda s: (s > 0).sum()),
    In_Progress_Count        = ("in_progress_amount",     lambda s: (s > 0).sum()),
    Unique_Vendors_Count     = ("vendor_key",             "nunique"),
    Primary_Vendor           = ("vendor_key",             get_primary_vendor),
    Dup_Payment_Count        = ("is_dup_copy",            "sum"),
    Dup_Payment_Amount       = ("dup_amount",             "sum"),
    First_Payment_Date       = ("Expenditure Date",       "min"),
    Last_Payment_Date        = ("Expenditure Date",       "max"),
    Has_Pending_Payment      = ("Payment Status",
                                lambda s: s.astype(str)
                                .str.contains("Progress|Pending", case=False, na=False)
                                .any()),
).reset_index()
df_exp_agg["_in_exp"] = 1

print(f"  • Aggregated {len(df_exp):,} transactions → {len(df_exp_agg):,} unique works.")

# ====================================================================
# 3. Clean & Prepare Completion Data
# ====================================================================
print("\n[3/5] Processing Completion dataset...")
df_comp_prep = df_comp.copy()
rename_map = {
    "Amount Disbursed ( ₹ )":               "Comp_Reported_Disbursed",
    "Work Description":                      "Comp_Work_Description",
    "Work":                                  "Comp_Work",
    "Work Category":                         "Comp_Work_Category",
    "Work category":                         "Comp_Work_Category",
    "Image":                                 "Comp_Image",
    "State":                                 "Comp_State",
    "Constituency":                          "Comp_Constituency",
    "IDA":                                   "Comp_IDA",
    "Hon'ble Members of Parliament":         "Comp_MP",
}
df_comp_prep = df_comp_prep.rename(
    columns={k: v for k, v in rename_map.items() if k in df_comp_prep.columns}
)

# Photo Proof Flag — only meaningful for completions after portal cutoff
PHOTO_CUTOFF = pd.Timestamp("2026-05-15")
df_comp_prep["Missing_Photo_Proof"] = df_comp_prep["Comp_Image"].apply(
    lambda x: 1 if (pd.isna(x) or str(x).strip().upper() in ["N/A", "NONE", "", "NAN"]) else 0
)
# Track whether this completion is in the post-cutoff regime
df_comp_prep["Post_Photo_Cutoff"] = (df_comp_prep["Completion Date"] >= PHOTO_CUTOFF).astype(int)

# ====================================================================
# 4. Merge Lifecycle & Coalesce Metadata
# ====================================================================
print("\n[4/5] Merging Sanction → Expenditure → Completion...")

master = pd.merge(df_sanc,    df_exp_agg,   on="Work ID", how="outer")
master = pd.merge(master,     df_comp_prep, on="Work ID", how="outer")

# Coalesce metadata
master["State"]          = master["State"].combine_first(master["Exp_State"]).combine_first(master["Comp_State"])
master["Constituency"]   = master["Constituency"].combine_first(master["Exp_Constituency"]).combine_first(master["Comp_Constituency"])
master["IDA"]            = master["IDA"].combine_first(master["Exp_IDA"]).combine_first(master["Comp_IDA"])
master["Hon'ble Members of Parliament"] = (
    master["Hon'ble Members of Parliament"]
    .combine_first(master["Exp_MP"])
    .combine_first(master["Comp_MP"])
)
master["Work category"]  = master["Work category"].combine_first(master["Comp_Work_Category"]).fillna("Others / Unspecified")
master["Work"]           = master["Work"].combine_first(master["Exp_Work"]).combine_first(master["Comp_Work"]).fillna("Unspecified Work")

if "Work description" in master.columns and "Comp_Work_Description" in master.columns:
    master["Work_Description_Final"] = master["Work description"].combine_first(master["Comp_Work_Description"]).fillna(master["Work"])
elif "Work description" in master.columns:
    master["Work_Description_Final"] = master["Work description"].fillna(master["Work"])
else:
    master["Work_Description_Final"] = master["Work"]

# ====================================================================
# 5. Financials & Lifecycle Integrity
# ====================================================================
print("\n[5/5] Engineering Anomaly & Risk Indicators...")

master["Sanction_Amount"]      = master.get("Sanction Amount ( ₹ )", pd.Series(dtype=float))
master["Total_Exp_Disbursed"]  = master["Total_Exp_Disbursed"].fillna(0.0)
master["Total_Exp_Settled"]    = master["Total_Exp_Settled"].fillna(0.0)
master["Total_Exp_In_Progress"]= master["Total_Exp_In_Progress"].fillna(0.0)
master["Dup_Payment_Amount"]   = master["Dup_Payment_Amount"].fillna(0.0)
master["Dup_Payment_Count"]    = master["Dup_Payment_Count"].fillna(0).astype(int)

# Lifecycle provenance markers
master["Is_Sanctioned"] = master["_in_sanc"].fillna(0).astype(int)
master["Has_Payments"]  = master["_in_exp"].fillna(0).astype(int)
master["Is_Completed"]  = master["_in_comp"].fillna(0).astype(int)

master["Lifecycle_Stage"] = np.select(
    [master.Is_Completed == 1, master.Has_Payments == 1, master.Is_Sanctioned == 1],
    ["Completed", "In-Progress / Disbursing", "Sanctioned Only"],
    default="Unknown"
)
san = master["Is_Sanctioned"] == 1

# ── Derived financial metrics ────────────────────────────────────────
# Cost_Variance = Settled payments minus Sanction, for sanctioned works only.
# Using settled (success-only) amount ensures in-progress payments don't
# create false overruns.
master["Cost_Variance"]     = np.where(
    san,
    master["Total_Exp_Settled"] - master["Sanction_Amount"],
    np.nan
)
master["Utilization_Ratio"] = np.where(
    san & (master["Sanction_Amount"] > 0),
    master["Total_Exp_Settled"] / master["Sanction_Amount"],
    np.nan
)

# ── FIX: Flag_Cost_Overrun ───────────────────────────────────────────
# Previous version used Total_Exp_Disbursed (all rows) vs Sanction_Amount.
# Max utilization using all payments was exactly 1.0 → flag never fired.
# Fix: compare SETTLED payments only against Sanction, with a 1% tolerance
# to ignore rounding differences. Still a screening indicator — it does not
# prove misappropriation without source documents.
master["Integrity_Cost_Cap_Violation"] = (
    san
    & (master["Sanction_Amount"] > 0)
    & (master["Total_Exp_Settled"] > master["Sanction_Amount"] * 1.01)  # >1% overrun
).astype(int)

# ── Flag_Orphan_Payment ─────────────────────────────────────────────
# Data gap flag: payment rows with no sanction record found.
# Likely caused by a stale sanction export — NOT an automatic fraud signal.
master["Flag_Orphan_Payment"] = (
    (master["Has_Payments"] == 1) & ~san
).astype(int)

# ── Flag_Ghost_Completion ────────────────────────────────────────────
# Completed work with ZERO settled amount, zero in-progress amount,
# AND zero reported completion amount. If it has a reported completion
# amount but no ledger payments, it's a reconciliation discrepancy.
master["Flag_Ghost_Completion"] = (
    (master["Is_Completed"] == 1)
    & (master["Total_Exp_Settled"] == 0)
    & (master["Total_Exp_In_Progress"] == 0)
    & (master["Comp_Reported_Disbursed"].fillna(0) == 0)
).astype(int)

# ── Flag_Duplicate_Payment ───────────────────────────────────────────
# Screening flag for identical [Work ID + vendor + amount + date] rows.
# Equal installments also match this pattern; manual UTR review is needed.
master["Flag_Duplicate_Payment"] = (master["Dup_Payment_Count"] > 0).astype(int)

# ── FIX: Flag_Temporal_Anomaly ───────────────────────────────────────
# Previous version compared dates that were often NaT after date-parsing bugs.
# Fix 1: date parsing now uses explicit formats (no dayfirst swap).
# Fix 2: the comparison explicitly handles NaT — pd.Series < value is False
#        when either side is NaT, but the OR chain could still give False.
#        We check each condition independently on rows where both dates are valid.
#
# Signals (each only fires where both dates are non-null):
#   A. Recommended date > Sanction Date (approval before recommendation — clerical anomaly)
#   B. Sanction Date > Completion Date (completed before sanctioned — impossible)
#   C. Sanction Date > First Payment Date (paid before formally sanctioned)
#
# We do NOT flag negative Execution_Duration_Days alone — some works are
# completed on the same day as sanction, which is valid for small works.

def safe_negative(a, b):
    """Returns True where a and b are both non-null and a > b (i.e. b - a < 0)."""
    mask_valid = a.notna() & b.notna()
    return mask_valid & (a > b)

cond_A = safe_negative(master["Recommended date"], master["Sanction Date"])
cond_B = safe_negative(master["Sanction Date"],    master["Completion Date"])
cond_C = safe_negative(master["Sanction Date"],    master["First_Payment_Date"])

master["Integrity_Date_Sequence_Violation"] = (cond_A | cond_B | cond_C).astype(int)

# Temporal duration metrics (NaN when either date is missing)
master["Sanction_Approval_Days"]  = (master["Sanction Date"] - master["Recommended date"]).dt.days
master["Execution_Duration_Days"] = (master["Completion Date"] - master["Sanction Date"]).dt.days
master["First_Payment_Lag_Days"]  = (master["First_Payment_Date"] - master["Sanction Date"]).dt.days

# ── Flag_Stalled_Unpaid ─────────────────────────────────────────────
# Sanctioned work with zero payments for > 180 days since sanction date.
snapshot = pd.concat([
    master["Sanction Date"].dropna(),
    master["Last_Payment_Date"].dropna(),
    master["Completion Date"].dropna()
]).max()
master["Flag_Stalled_Unpaid"] = (
    san
    & (master["Has_Payments"] == 0)
    & master["Sanction Date"].notna()
    & (master["Sanction Date"] < snapshot - pd.Timedelta(days=180))
).astype(int)

# ── FIX: Flag_Tender_Splitting_Risk ────────────────────────────────
# Previous rule: MP + vendor + first-payment-date, CV ≤ 0.25, n ≥ 4.
# Fired on 26.9% of works — too broad (catches bulk purchasing).
# Fix: also require vendor amount to be close to MPLADS sub-threshold
# (≤ ₹5 lakh per work) AND at least 8 works in cluster (not just 4).
# Still a SCREENING indicator — it does not prove procurement violation.
GOV_RE = r"\b(?:PANCHAYAT|NIGAM|DEPARTMENT|DEPT|BOARD|PWD|PCCD|UPSIC|KRIDL|MUNICIPAL|PALIKA|SAMITI|ZILLA)\b"
cand = master[
    (master["Has_Payments"] == 1)
    & (master["Total_Exp_Settled"] > 0)  # Exclude zero-settled amounts to avoid NaN CV
    & master["Primary_Vendor"].notna()   # Exclude missing vendors
    & (master["Primary_Vendor"].str.strip() != "")
    & master["Primary_Vendor"].fillna("").str.upper().str.contains(GOV_RE, regex=True).eq(False)
    & master["Sanction_Amount"].notna()
    & (master["Sanction_Amount"] <= 500_000)   # works at or below ₹5 lakh
].copy()

cand["mp_code"] = cand["Work ID"].str.extract(r"MP(\d+)/")[0]
grp = cand.groupby(["mp_code", "Primary_Vendor", "First_Payment_Date"])["Total_Exp_Settled"]
cand["ts_n"]  = grp.transform("size")
cand_mean = grp.transform("mean")
cand_std  = grp.transform("std")
cand["ts_cv"] = np.where(cand_mean > 0, cand_std / cand_mean, np.nan)

split_hit = cand.index[
    (cand["ts_n"] >= 8)
    & (cand["ts_cv"].notna())
    & (cand["ts_cv"] <= 0.15)
]
master["Flag_Same_Day_Bulk_Payment"] = master.index.isin(split_hit).astype(int)

# ── Missing photo — restricted to post-cutoff completions ───────────
# Before portal cutoff (May 2026): 31.3% missing — normal legacy data.
# After cutoff: ~0.3% missing — meaningful compliance gap.
# We report both but only recommend investigating post-cutoff flags.
master["Post_Photo_Cutoff"] = master["Post_Photo_Cutoff"].fillna(0).astype(int)

# ====================================================================
# 6. Cleanup & Column Ordering
# ====================================================================
drop_cols = [
    "Exp_State", "Exp_Constituency", "Exp_IDA", "Exp_MP", "Exp_Work",
    "Comp_State", "Comp_Constituency", "Comp_IDA", "Comp_MP", "Comp_Work",
    "Comp_Work_Category", "Comp_Image", "Comp_Work_Description", "Work description",
    "Sr. No.", "Sr. No._x", "Sr. No._y", "Sanction Amount ( ₹ )",
    "_in_sanc", "_in_exp", "_in_comp",
]
master = master.drop(columns=[c for c in drop_cols if c in master.columns], errors="ignore")

master["Primary_Vendor"]             = master["Primary_Vendor"].fillna("No Vendor (Unpaid)")
master["Has_Pending_Payment"]        = master["Has_Pending_Payment"].fillna(False).astype(bool)
master["Payment_Installments_Count"] = master["Payment_Installments_Count"].fillna(0).astype(int)
master["Unique_Vendors_Count"]       = master["Unique_Vendors_Count"].fillna(0).astype(int)

if "Work Status" in master.columns:
    master = master.rename(columns={"Work Status": "Work_Status"})

# Column ordering
first_cols = [
    "Work ID", "Lifecycle_Stage", "Work_Status", "State", "Constituency", "IDA",
    "Hon'ble Members of Parliament", "Work category", "Work", "Work_Description_Final",
    "Sanction_Amount", "Total_Exp_Settled", "Total_Exp_In_Progress", "Total_Exp_Disbursed",
    "Cost_Variance", "Utilization_Ratio",
    "Recommended date", "Sanction Date", "Completion Date",
    "Payment_Installments_Count", "Settled_Count", "In_Progress_Count",
    "Unique_Vendors_Count", "Primary_Vendor", "Missing_Photo_Proof", "Post_Photo_Cutoff",
]
remaining_cols = [c for c in master.columns if c not in first_cols]
all_cols = [c for c in first_cols if c in master.columns] + remaining_cols
master = master[all_cols]

# ====================================================================
# 7. Export
# ====================================================================
CLEAN_DIR = DATA_DIR / "clean"
CLEAN_DIR.mkdir(parents=True, exist_ok=True)
out_file = CLEAN_DIR / "mplads_360_master.csv"
master.to_csv(out_file, index=False)

# ====================================================================
# 8. Summary Report
# ====================================================================
print("\n" + "=" * 80)
print(f"  360° Master Dataset — {len(master):,} unique works, {master.shape[1]} columns")
print("=" * 80)

tot = len(master)
print(f"\n  Lifecycle Breakdown:")
print(f"    Completed:                {master['Is_Completed'].sum():>7,}  ({master['Is_Completed'].mean():.1%})")
print(f"    In-Progress / Disbursing: {(master['Lifecycle_Stage']=='In-Progress / Disbursing').sum():>7,}")
print(f"    Sanctioned Only:          {(master['Lifecycle_Stage']=='Sanctioned Only').sum():>7,}")

print(f"\n  Financial Totals (settled payments only):")
print(f"    Sanction Total:           ₹{master['Sanction_Amount'].sum()/1e7:>9,.2f} Cr")
print(f"    Settled Payment Total:    ₹{master['Total_Exp_Settled'].sum()/1e7:>9,.2f} Cr")
print(f"    In-Progress Total:        ₹{master['Total_Exp_In_Progress'].sum()/1e7:>9,.2f} Cr")

print(f"\n  Screening Flags (for manual review — not proof of fraud):")
flags = [
    ("Integrity_Cost_Cap_Violation",     "0 = portal enforces cap ✓ | >0 = settled exceeded sanction"),
    ("Integrity_Date_Sequence_Violation","0 = all dates valid ✓     | >0 = payment before sanction"),
    ("Flag_Orphan_Payment",              "Payment with no Sanction record (likely stale export)"),
    ("Flag_Ghost_Completion",            "Completed with ₹0 settled and ₹0 in-progress"),
    ("Flag_Duplicate_Payment",           "Identical [Work+Vendor+Amount+Date] rows"),
    ("Flag_Stalled_Unpaid",              "Sanctioned >180 days ago, zero payments"),
    ("Flag_Same_Day_Bulk_Payment",       "8+ near-equal works, same vendor+MP+day, ≤₹5L each"),
    ("Missing_Photo_Proof",              "No photo proof (post-cutoff completions: note separately)"),
]
for col, desc in flags:
    if col in master.columns:
        n = int(master[col].sum())
        pct = n / tot * 100
        print(f"    {col:<30}  {n:>6,}  ({pct:.2f}%)  — {desc}")

# Post-cutoff photo flag
if "Post_Photo_Cutoff" in master.columns and "Missing_Photo_Proof" in master.columns:
    post = master[master["Post_Photo_Cutoff"] == 1]
    if len(post):
        n_post_miss = int(post["Missing_Photo_Proof"].sum())
        print(f"\n    Missing photos (post-cutoff only): {n_post_miss:,} of {len(post):,} "
              f"post-cutoff completions ({n_post_miss/len(post):.1%})")

print(f"\n  Saved to: {out_file}")
print("=" * 80)
