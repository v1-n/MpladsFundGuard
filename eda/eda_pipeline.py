import re
import numpy as np
import pandas as pd
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
CLEAN_DIR = DATA_DIR / "clean"
CLEAN_DIR.mkdir(parents=True, exist_ok=True)
RAW_DIR.mkdir(parents=True, exist_ok=True)

EDA_DIR = BASE_DIR / "eda"
EDA_DIR.mkdir(parents=True, exist_ok=True)


def get_raw_filepath(raw_name, clean_name=None):
    """Finds input file in data/raw/, data/clean/, or data/."""
    if (RAW_DIR / raw_name).exists():
        return RAW_DIR / raw_name
    if clean_name and (CLEAN_DIR / clean_name).exists():
        return CLEAN_DIR / clean_name
    if (DATA_DIR / raw_name).exists():
        return DATA_DIR / raw_name
    if clean_name and (DATA_DIR / clean_name).exists():
        return DATA_DIR / clean_name
    return RAW_DIR / raw_name


# ====================================================================
# FIX 1: Currency Cleaning — preserve blanks as NaN (not ₹0)
# ====================================================================
def clean_currency_series(series):
    """
    Converts currency strings (e.g. '₹1,23,456') to float64.

    IMPORTANT: Blank/unparseable values stay as NaN.
    Never fill blanks with 0.0 here — a missing amount is not the same
    as a zero amount. 75 completed works have genuinely blank amounts
    in the portal; treating them as zero creates ghost-completion false positives.
    """
    cleaned = (
        series.astype(str)
        .str.replace("₹", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.strip()
        .replace({"nan": None, "None": None, "": None})
    )
    result = pd.to_numeric(cleaned, errors="coerce")
    # Report parse failures (not including genuine blanks)
    invalid_mask = result.isna() & series.notna() & (series.astype(str).str.strip() != "")
    if invalid_mask.sum() > 0:
        print(f"  ⚠️  {invalid_mask.sum()} currency values could not be parsed (kept as NaN).")
    return result


# ====================================================================
# FIX 2: Date Parsing — explicit formats, never dayfirst=True on ISO
# ====================================================================
def parse_dates_series(series, column_name=""):
    """
    Parses dates using explicit known formats in priority order:
      1. ISO format: 2024-07-09
      2. Portal format: 09-Jul-2024

    WHY NOT dayfirst=True:
      When raw files already contain ISO dates (YYYY-MM-DD), setting
      dayfirst=True causes pandas to swap day and month for values
      where day <= 12, silently producing wrong dates or NaT for ~63%
      of rows. This makes duplicate detection, stall flags, and temporal
      metrics all incorrect.

    Raises ValueError if unparseable dates remain, so a new date
    format causes an immediate loud failure instead of silent NaT.
    """
    s = series.astype("string").str.strip()

    # Try ISO format first (committed cleaned files use this)
    out = pd.to_datetime(s, errors="coerce", format="%Y-%m-%d")

    # Try portal format for any remaining unparsed non-blank values
    miss = out.isna() & s.notna() & (s != "")
    if miss.any():
        out[miss] = pd.to_datetime(s[miss], errors="coerce", format="%d-%b-%Y")

    # Report any still-unparseable values loudly
    bad = out.isna() & s.notna() & (s != "")
    if bad.any():
        sample = s[bad].head(3).tolist()
        raise ValueError(
            f"[{column_name}] {int(bad.sum())} dates could not be parsed "
            f"with known formats. Sample: {sample}. "
            "Add a new format branch to parse_dates_series()."
        )
    return out


# ====================================================================
# FIX 3: PII Masking — phone numbers in text columns
# ====================================================================
PHONE_RE = re.compile(r'(?<!\d)[6-9]\d{9}(?!\d)')

def mask_pii(series, column_name=""):
    """
    Replaces 10-digit Indian mobile numbers with [PHONE_REDACTED].
    Preserves NaN values correctly using nullable string types.
    """
    str_series = series.astype("string")
    hits = 0
    if str_series.notna().any():
        hits = str_series.str.contains(PHONE_RE, na=False).sum()
        if hits > 0:
            print(f"  ⚠️  PII detected: {hits} phone numbers found in '{column_name}' → masked.")
            return str_series.str.replace(PHONE_RE, "[PHONE_REDACTED]", regex=True)
    return series


# ====================================================================
# Work ID Extraction — shared utility
# ====================================================================
def extract_and_clean_work_id(val):
    """Extracts and standardizes Work ID from raw text."""
    if pd.isna(val):
        return None
    val = str(val).strip()
    match = re.search(r'(WS\s*/\s*[\w`\s]+\s*/\s*\d{4}-\d{4}\s*/\s*\d+)', val, re.IGNORECASE)
    if match:
        extracted = match.group(1)
    elif val.upper().startswith("WS/"):
        extracted = val.split("-")[0]
    else:
        return val
    cleaned = re.sub(r'[`]', '', extracted)
    cleaned = re.sub(r'\s*/\s*', '/', cleaned)
    cleaned = re.sub(r'\s+', '', cleaned).strip()
    return cleaned


def clean_work_description(val):
    """Removes leading Work ID prefix from the Work column."""
    if pd.isna(val):
        return val
    val = str(val).strip()
    cleaned = re.sub(
        r'^WS\s*/\s*[\w`\s]+\s*/\s*\d{4}-\d{4}\s*/\s*\d+\s*-\s*',
        '', val, flags=re.IGNORECASE
    )
    if cleaned.upper().startswith("WS/"):
        parts = cleaned.split("-", 1)
        if len(parts) > 1:
            cleaned = parts[1].strip()
    return cleaned.strip()


# ====================================================================
# MAIN PIPELINE
# ====================================================================
print("=" * 75)
print("       MPLADS DATA CLEANING, TYPE CONVERSION & EDA PIPELINE")
print("=" * 75)

# ---- A. Works Sanctioned ----
print("\n[1/4] Processing 'Works Sanctioned'...")
f_sanc = get_raw_filepath("Works Sanctioned.csv", "clean_works_sanctioned.csv")
df_sanc = pd.read_csv(f_sanc, low_memory=False)

if "Work ID" not in df_sanc.columns and "Work" in df_sanc.columns:
    df_sanc["Work ID"] = df_sanc["Work"].apply(extract_and_clean_work_id)
    df_sanc["Work"] = df_sanc["Work"].apply(clean_work_description)
    df_sanc = df_sanc[["Work ID"] + [c for c in df_sanc.columns if c != "Work ID"]]
else:
    df_sanc["Work ID"] = df_sanc["Work ID"].apply(extract_and_clean_work_id)

orig_len = len(df_sanc)
df_sanc = df_sanc[df_sanc["Work ID"].notna() & (df_sanc["Work ID"].astype(str).str.strip() != "")]
print(f"  • Dropped {orig_len - len(df_sanc)} null Work ID row(s). Active rows: {len(df_sanc):,}")

if "Sanction Amount ( ₹ )" in df_sanc.columns:
    df_sanc["Sanction Amount ( ₹ )"] = clean_currency_series(df_sanc["Sanction Amount ( ₹ )"])
for date_col in ["Recommended date", "Sanction Date"]:
    if date_col in df_sanc.columns:
        df_sanc[date_col] = parse_dates_series(df_sanc[date_col], date_col)

# PII masking on text columns
for col in ["Work description"]:
    if col in df_sanc.columns:
        df_sanc[col] = mask_pii(df_sanc[col], col)


# ---- B. Expenditure ----
print("\n[2/4] Processing 'Expenditure'...")
f_exp = get_raw_filepath(
    "Expenditure on Completed and On-going Works as on Date.csv", "clean_expenditure.csv"
)
df_exp = pd.read_csv(f_exp, low_memory=False)

if "Work ID" in df_exp.columns:
    df_exp["Work ID"] = df_exp["Work ID"].apply(extract_and_clean_work_id)

orig_len = len(df_exp)
df_exp = df_exp[df_exp["Work ID"].notna() & (df_exp["Work ID"].astype(str).str.strip() != "")]
print(f"  • Dropped {orig_len - len(df_exp)} null Work ID row(s). Active rows: {len(df_exp):,}")

if "Fund Disbursed Amount ( ₹ )" in df_exp.columns:
    df_exp["Fund Disbursed Amount ( ₹ )"] = clean_currency_series(df_exp["Fund Disbursed Amount ( ₹ )"])
if "Expenditure Date" in df_exp.columns:
    df_exp["Expenditure Date"] = parse_dates_series(df_exp["Expenditure Date"], "Expenditure Date")

# Payment status audit
if "Payment Status" in df_exp.columns:
    status_counts = df_exp["Payment Status"].value_counts(dropna=False)
    print("  • Payment Status breakdown:")
    for status, count in status_counts.items():
        print(f"    - '{status}': {count:,}")


# ---- C. Works Completed ----
print("\n[3/4] Processing 'Works Completed'...")
f_comp = get_raw_filepath("Works Completed.csv", "clean_works_completed.csv")
df_comp = pd.read_csv(f_comp, low_memory=False)

if "Work ID" not in df_comp.columns and "Work" in df_comp.columns:
    df_comp["Work ID"] = df_comp["Work"].apply(extract_and_clean_work_id)
    df_comp["Work"] = df_comp["Work"].apply(clean_work_description)
    df_comp = df_comp[["Work ID"] + [c for c in df_comp.columns if c != "Work ID"]]
else:
    df_comp["Work ID"] = df_comp["Work ID"].apply(extract_and_clean_work_id)

orig_len = len(df_comp)
df_comp = df_comp[df_comp["Work ID"].notna() & (df_comp["Work ID"].astype(str).str.strip() != "")]
print(f"  • Dropped {orig_len - len(df_comp)} null Work ID row(s). Active rows: {len(df_comp):,}")

if "Amount Disbursed ( ₹ )" in df_comp.columns:
    df_comp["Amount Disbursed ( ₹ )"] = clean_currency_series(df_comp["Amount Disbursed ( ₹ )"])
if "Completion Date" in df_comp.columns:
    df_comp["Completion Date"] = parse_dates_series(df_comp["Completion Date"], "Completion Date")

for col in ["Work Description"]:
    if col in df_comp.columns:
        df_comp[col] = mask_pii(df_comp[col], col)


# ---- D. MP Summary ----
print("\n[4/4] Processing 'MP Summary'...")
f_mp = get_raw_filepath("mplads_mp_summary_2026-10-09.csv")
df_mp = pd.read_csv(f_mp, low_memory=False)

n_all = len(df_mp)
df_mp = df_mp[df_mp["House"] == "Lok Sabha"].copy()
print(f"  • Scope: Lok Sabha only. Kept {len(df_mp)} of {n_all} MPs "
      f"(dropped {n_all - len(df_mp)} Rajya Sabha).")

for col in df_mp.columns:
    if any(k in col for k in ["₹", "Amount", "Cost", "Fund", "Expenditure"]):
        df_mp[col] = clean_currency_series(df_mp[col])


# ====================================================================
# FIX 4: Save Cleaned Datasets
# ====================================================================
print("\n" + "=" * 75)
print("Saving cleaned datasets to data/clean/ ...")

df_sanc.to_csv(CLEAN_DIR / "clean_works_sanctioned.csv", index=False)
df_exp.to_csv(CLEAN_DIR / "clean_expenditure.csv", index=False)
df_comp.to_csv(CLEAN_DIR / "clean_works_completed.csv", index=False)
df_mp.to_csv(CLEAN_DIR / "clean_mp_summary.csv", index=False)

print(f"  ✓ clean_works_sanctioned.csv ({len(df_sanc):,} rows)")
print(f"  ✓ clean_expenditure.csv ({len(df_exp):,} rows)")
print(f"  ✓ clean_works_completed.csv ({len(df_comp):,} rows)")
print(f"  ✓ clean_mp_summary.csv ({len(df_mp):,} rows)")


# ====================================================================
# FIX 5: Statistical EDA Report (informational, not pass/fail)
# ====================================================================
print("\n" + "=" * 75)
print("                     EXPLORATORY DATA ANALYSIS REPORT")
print("=" * 75)


def print_dataset_eda(name, df, date_cols, amount_cols):
    print(f"\n📊 DATASET: {name}")
    print(f"   • Total Records: {len(df):,}")
    print(f"   • Columns ({len(df.columns)}): {', '.join(df.columns[:6])}...")

    nulls = df.isnull().sum()
    nulls = nulls[nulls > 0]
    if not nulls.empty:
        print("   • Missing Values:")
        for c, n in nulls.items():
            print(f"     - {c}: {n:,} ({n/len(df)*100:.2f}%)")
    else:
        print("   • Missing Values: None")

    for ac in amount_cols:
        if ac in df.columns:
            s = df[ac].dropna()
            total = len(df[ac])
            print(f"   • Financial Metric [{ac}]:")
            print(f"     - Total Sum: ₹{s.sum():,.2f}")
            print(f"     - Mean: ₹{s.mean():,.2f} | Median: ₹{s.median():,.2f}")
            print(f"     - Min: ₹{s.min():,.2f} | Max: ₹{s.max():,.2f}")
            print(f"     - Blank/NaN count: {df[ac].isna().sum():,} ({df[ac].isna().sum()/total*100:.2f}%)")
            print(f"     - Genuine ₹0 count: {(s == 0).sum():,} ({(s == 0).sum()/total*100:.2f}%)")
            tiny = s[s < 1000]
            if len(tiny):
                print(f"     ⚠️  Possible unit errors (< ₹1,000): {len(tiny):,} rows (min: ₹{tiny.min():,.2f})")

    for dc in date_cols:
        if dc in df.columns and pd.api.types.is_datetime64_any_dtype(df[dc]):
            valid_dates = df[dc].dropna()
            nat_count = df[dc].isna().sum()
            if not valid_dates.empty:
                print(f"   • Date Range [{dc}]: "
                      f"{valid_dates.min().strftime('%d-%b-%Y')} → "
                      f"{valid_dates.max().strftime('%d-%b-%Y')} "
                      f"(NaT: {nat_count:,} = {nat_count/len(df)*100:.2f}%)")


print_dataset_eda("Works Sanctioned", df_sanc, ["Recommended date", "Sanction Date"], ["Sanction Amount ( ₹ )"])
print_dataset_eda("Expenditure", df_exp, ["Expenditure Date"], ["Fund Disbursed Amount ( ₹ )"])
print_dataset_eda("Works Completed", df_comp, ["Completion Date"], ["Amount Disbursed ( ₹ )"])


# ====================================================================
# FIX 6: Cross-File Financial Reconciliation (strongest correctness proof)
# ====================================================================
print("\n" + "=" * 75)
print("  CROSS-FILE FINANCIAL RECONCILIATION")
print("=" * 75)

total_sanctioned = df_sanc["Sanction Amount ( ₹ )"].sum()
total_ledger = df_exp["Fund Disbursed Amount ( ₹ )"].sum()
total_completion = df_comp["Amount Disbursed ( ₹ )"].sum()

print(f"  • Sanction file total:       ₹{total_sanctioned/1e7:,.2f} Cr  ({len(df_sanc):,} works)")
print(f"  • Ledger (payment) total:    ₹{total_ledger/1e7:,.2f} Cr  ({len(df_exp):,} rows)")
print(f"  • Completion-reported total: ₹{total_completion/1e7:,.2f} Cr  ({len(df_comp):,} works)")


# ====================================================================
# FIX 7: Snapshot Freshness (stale export warning)
# ====================================================================
print("\n" + "=" * 75)
print("  DATA FRESHNESS CHECK")
print("=" * 75)

date_maxes = {
    "Works Sanctioned (Recommended date)": df_sanc["Recommended date"].max() if "Recommended date" in df_sanc else None,
    "Expenditure (Expenditure Date)": df_exp["Expenditure Date"].max() if "Expenditure Date" in df_exp else None,
    "Works Completed (Completion Date)": df_comp["Completion Date"].max() if "Completion Date" in df_comp else None,
}
latest_date = max(v for v in date_maxes.values() if v is not None)
for label, d in date_maxes.items():
    if d:
        lag = (latest_date - d).days
        flag = " ⚠️  STALE" if lag > 30 else " ✓"
        print(f"  • {label}: {d.strftime('%d-%b-%Y')} (lags latest by {lag} days){flag}")


print("\n" + "=" * 75)
print("EDA Pipeline complete. Run eda/eda_checks.py before build_master.py.")
print("=" * 75)
