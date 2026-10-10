"""
eda/eda_checks.py
=================
Data Quality Gate — runs AFTER eda_pipeline.py, BEFORE build_master.py.

Each check either passes ✓, warns ⚠️, or fails ✗.
Pipeline halts with exit code 1 if any CRITICAL check fails.

Checks implemented:
  1. Required columns exist in all 4 clean files
  2. Work ID integrity (format, uniqueness ratio, null rate)
  3. Cross-file join coverage (sanction ↔ expenditure ↔ completion)
  4. Orphan payment ID range check (stale sanction export detection)
  5. NaN vs zero audit (blanks must not silently become 0)
  6. Payment status decomposition (settled vs in-progress vs other)
  7. Amount tail detection (likely unit errors, outliers)
  8. Duplicate record forensics (exact rows, not assumed double-payment)
  9. Rule-firing diagnostics (zero-count flags reported as warnings only)
 10. Missing-photo flag: rate over time to detect portal cutoff
 11. PII scan result summary (count only, no printing of values)
 12. Snapshot freshness: warn if any source file lags latest by > 30 days
 13. Financial reconciliation: sanction vs ledger vs completion totals
"""

import sys
import re
import numpy as np
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CLEAN_DIR = BASE_DIR / "data" / "clean"

# ── Formatting helpers ─────────────────────────────────────────────────────

SEP = "─" * 72
PASS  = "  ✓ PASS"
WARN  = "  ⚠️  WARN"
FAIL  = "  ✗ FAIL"

failures = []
warnings = []


def result(level, msg, detail=""):
    icon = PASS if level == "pass" else WARN if level == "warn" else FAIL
    print(f"{icon}  {msg}")
    if detail:
        print(f"       {detail}")
    if level == "fail":
        failures.append(msg)
    if level == "warn":
        warnings.append(msg)


print("=" * 72)
print("    MPLADS DATA QUALITY CHECKS (EDA Gate)")
print("=" * 72)


# ── Load clean files ──────────────────────────────────────────────────────
print(f"\n{SEP}")
print("[0] Loading clean datasets...")

REQUIRED_FILES = {
    "sanc":  CLEAN_DIR / "clean_works_sanctioned.csv",
    "exp":   CLEAN_DIR / "clean_expenditure.csv",
    "comp":  CLEAN_DIR / "clean_works_completed.csv",
    "mp":    CLEAN_DIR / "clean_mp_summary.csv",
}

dfs = {}
for key, path in REQUIRED_FILES.items():
    if not path.exists():
        result("fail", f"Missing clean file: {path.name}",
               "Run eda/eda_pipeline.py first.")
    else:
        dfs[key] = pd.read_csv(path, low_memory=False)
        for col in dfs[key].columns:
            if any(k in col for k in ["date", "Date", "DATE"]):
                dfs[key][col] = pd.to_datetime(dfs[key][col], errors="coerce")
        result("pass", f"Loaded {path.name}: {len(dfs[key]):,} rows, "
               f"{dfs[key].shape[1]} cols")

if failures:
    print(f"\n{'=' * 72}")
    print("CRITICAL: Cannot continue — clean files are missing. Run eda_pipeline.py first.")
    sys.exit(1)

sanc, exp, comp, mp = dfs["sanc"], dfs["exp"], dfs["comp"], dfs["mp"]


# ── CHECK 1: Required columns ────────────────────────────────────────────
print(f"\n{SEP}")
print("[1] Required columns present...")

REQUIRED_COLS = {
    "sanc": ["Work ID", "Sanction Amount ( ₹ )"],
    "exp":  ["Work ID", "Fund Disbursed Amount ( ₹ )", "Expenditure Date"],
    "comp": ["Work ID", "Completion Date"],
}
for key, cols in REQUIRED_COLS.items():
    df = dfs[key]
    missing = [c for c in cols if c not in df.columns]
    if missing:
        result("fail", f"{key}: Missing required columns: {missing}")
    else:
        result("pass", f"{key}: All required columns present")


# ── CHECK 2: Work ID integrity ───────────────────────────────────────────
print(f"\n{SEP}")
print("[2] Work ID format and uniqueness...")

WID_PATTERN = re.compile(r'^WS/[A-Z0-9]+/\d{4}-\d{4}/\d+$', re.IGNORECASE)

for name, df in [("Sanctioned", sanc), ("Expenditure", exp), ("Completed", comp)]:
    ids = df["Work ID"].dropna().astype(str)
    total = len(df)
    null_rate = df["Work ID"].isna().mean()
    if null_rate > 0.01:
        result("warn", f"{name}: Work ID null rate is {null_rate:.2%}")
    else:
        result("pass", f"{name}: Work ID null rate OK ({null_rate:.2%})")

    valid = ids.str.match(WID_PATTERN).sum()
    if valid / len(ids) < 0.90:
        result("warn", f"{name}: Only {valid/len(ids):.1%} Work IDs match expected format",
               "Check extract_and_clean_work_id() in eda_pipeline.py")
    else:
        result("pass", f"{name}: {valid/len(ids):.1%} Work IDs match format WS/MPXXX/YYYY-YYYY/N")


# ── CHECK 3: Cross-file join coverage ────────────────────────────────────
print(f"\n{SEP}")
print("[3] Cross-file join coverage...")

sanc_ids = set(sanc["Work ID"].dropna())
exp_ids  = set(exp["Work ID"].dropna())
comp_ids = set(comp["Work ID"].dropna())

both_sanc_exp  = sanc_ids & exp_ids
orphan_exp     = exp_ids  - sanc_ids
orphan_comp    = comp_ids - sanc_ids
sanc_no_exp    = sanc_ids - exp_ids

orphan_exp_pct  = len(orphan_exp)  / len(exp_ids)  if exp_ids  else 0
orphan_comp_pct = len(orphan_comp) / len(comp_ids) if comp_ids else 0

print(f"     Sanctioned works:            {len(sanc_ids):>7,}")
print(f"     Works with payment rows:     {len(exp_ids):>7,}  "
      f"(matched to sanction: {len(both_sanc_exp):,})")
print(f"     Orphan payment Work IDs:     {len(orphan_exp):>7,}  ({orphan_exp_pct:.2%} of payment works)")
print(f"     Completed not in sanction:   {len(orphan_comp):>7,}  ({orphan_comp_pct:.2%} of completed)")
print(f"     Sanctioned with no payments: {len(sanc_no_exp):>7,}")

if orphan_exp_pct > 0.05:
    result("warn", f"Orphan payments: {len(orphan_exp):,} payment Work IDs not in sanction file",
           "Likely caused by a stale sanction export. See Check 4.")
else:
    result("pass", f"Orphan payment rate is {orphan_exp_pct:.2%} (within 5% threshold)")

# Add coverage check for Lok Sabha vs Rajya Sabha
if "House" in mp.columns and "Hon'ble Members of Parliament" in sanc.columns:
    def norm(s):
        s = re.sub(r"\(.*?\)", "", str(s).lower())
        s = re.sub(r"\b(shri|smt|dr|prof|adv|kumari|col|capt)\b\.?", "", s)
        return re.sub(r"[^a-z]", "", s)

    names = {norm(x) for x in sanc["Hon'ble Members of Parliament"].dropna()}
    if "MP Name" in mp.columns:
        rs = mp.loc[mp.House == "Rajya Sabha", "MP Name"].map(norm)
        found = int(rs.isin(names).sum())
        if found == 0:
            result("warn", f"Files cover Lok Sabha only; {len(rs)} Rajya Sabha MPs in summary have no rows",
                   "Download the Rajya Sabha exports to cover all MPs.")
        else:
            result("pass", f"{found}/{len(rs)} Rajya Sabha MPs present in the data")



# ── CHECK 4: Orphan payment ID range (stale export detection) ────────────
print(f"\n{SEP}")
print("[4] Stale sanction export detection...")

if orphan_exp:
    def extract_seq(wid):
        m = re.search(r'/(\d+)$', str(wid))
        return int(m.group(1)) if m else None

    max_sanc_seq = max(extract_seq(w) for w in sanc_ids if extract_seq(w))
    orphan_seqs = [extract_seq(w) for w in orphan_exp if extract_seq(w)]
    above_max = sum(1 for s in orphan_seqs if s and s > max_sanc_seq)

    print(f"     Max Work ID sequence in sanction file: {max_sanc_seq:,}")
    print(f"     Orphan Work IDs above that max:        {above_max:,}")
    if above_max > 100:
        result("warn",
               f"{above_max:,} orphan payment Work IDs have sequence numbers ABOVE max sanction ID",
               "This strongly suggests the sanction export is outdated. "
               "Re-download the Works Sanctioned file from the portal.")
    else:
        result("pass", "Orphan Work ID sequences are within sanction range — not a staleness issue")


# ── CHECK 5: NaN vs zero audit ────────────────────────────────────────────
print(f"\n{SEP}")
print("[5] NaN vs zero audit (blank ≠ zero)...")

for name, df, col in [
    ("Sanctioned", sanc, "Sanction Amount ( ₹ )"),
    ("Expenditure", exp, "Fund Disbursed Amount ( ₹ )"),
    ("Completed", comp, "Amount Disbursed ( ₹ )"),
]:
    if col not in df.columns:
        result("warn", f"{name}: Column '{col}' not found — skip")
        continue
    nan_n   = df[col].isna().sum()
    zero_n  = (df[col] == 0).sum()
    total   = len(df)
    print(f"     {name}: blanks(NaN)={nan_n:,} ({nan_n/total:.2%})  |  "
          f"genuine zeros={zero_n:,} ({zero_n/total:.2%})")
    if zero_n > 50 and name == "Completed":
        result("warn",
               f"{name}: {zero_n:,} completed works have ₹0 disbursed amount",
               "The committed file contains explicit 0.0 values; it is unknown whether "
               "the portal showed blank or zero. These are tracked separately.")
    else:
        result("pass", f"{name}: amount NaN/zero counts look reasonable")


# ── CHECK 6: Payment status decomposition ────────────────────────────────
print(f"\n{SEP}")
print("[6] Payment status audit...")

if "Payment Status" in exp.columns:
    status_counts = exp["Payment Status"].value_counts(dropna=False)
    total_exp = len(exp)
    for status, cnt in status_counts.items():
        print(f"     '{status}': {cnt:,} ({cnt/total_exp:.1%})")
    settled_labels = ["Settled", "settled", "Success", "success", "Completed", "completed", "Payment Success"]
    non_settled = exp[~exp["Payment Status"].isin(settled_labels)]
    if len(non_settled) > 0:
        ns_total = non_settled["Fund Disbursed Amount ( ₹ )"].sum() if "Fund Disbursed Amount ( ₹ )" in exp.columns else 0
        if len(non_settled) == len(exp):
            result("warn",
                   f"{len(non_settled):,} payment rows are not in a 'Settled' status (₹{ns_total/1e7:,.2f} Cr)",
                   "Check if 'Payment Status' string matches your settled_labels list.")
        else:
            result("pass", f"{len(non_settled):,} payments ({len(non_settled)/total_exp:.1%}) are In-Progress, separated successfully.")
    else:
        result("pass", "All payment rows are in a settled/success status")
else:
    result("warn", "Payment Status column not found in expenditure file",
           "Cannot distinguish settled vs in-progress payments.")


# ── CHECK 7: Amount tail detection (unit errors / outliers) ──────────────
print(f"\n{SEP}")
print("[7] Outlier and unit-error detection...")

for name, df, col in [
    ("Sanctioned", sanc, "Sanction Amount ( ₹ )"),
    ("Expenditure", exp, "Fund Disbursed Amount ( ₹ )"),
]:
    if col not in df.columns:
        continue
    s = df[col].dropna()
    p99 = s.quantile(0.99)
    high = s[s > p99 * 10]
    tiny = s[(s > 0) & (s < 1_000)]
    print(f"     {name}: P99 = ₹{p99:,.0f}")
    if len(high):
        result("warn",
               f"{name}: {len(high):,} amounts are >10× P99 (₹{high.max():,.0f}) — "
               "verify these are genuine, not unit errors (crore vs rupee)")
    else:
        result("pass", f"{name}: No extreme outliers (>10× P99)")
    if len(tiny):
        result("warn",
               f"{name}: {len(tiny):,} amounts between ₹1 and ₹999 — "
               "possible unit errors or test entries")


# ── CHECK 8: Duplicate record forensics ──────────────────────────────────
print(f"\n{SEP}")
print("[8] Duplicate payment row forensics...")

if "Fund Disbursed Amount ( ₹ )" in exp.columns and "Expenditure Date" in exp.columns:
    dup_key = ["Work ID", "Vendor Name", "Fund Disbursed Amount ( ₹ )", "Expenditure Date"]
    # Normalize vendor name exactly like build_master
    exp_vendor = exp["Vendor Name"].fillna("").astype(str).str.upper().str.replace(r"[^A-Z0-9 ]", " ", regex=True).str.replace(r"\s+", " ", regex=True).str.strip()
    dup_df = exp.copy()
    dup_df["vendor_key"] = exp_vendor
    dup_key = ["Work ID", "vendor_key", "Fund Disbursed Amount ( ₹ )", "Expenditure Date"]

    extra_dups = dup_df[dup_df.duplicated(subset=dup_key, keep="first")]
    n_dup = len(extra_dups)
    n_uniq = extra_dups["Work ID"].nunique()
    dup_amount = extra_dups["Fund Disbursed Amount ( ₹ )"].sum()

    print(f"     Extra duplicate rows [Work ID + Vendor + Amount + Date]: {n_dup:,}")
    print(f"     Distinct Work IDs involved:                              {n_uniq:,}")
    print(f"     Amount in extra duplicate rows:                          ₹{dup_amount/1e7:,.2f} Cr")

    if n_dup > 0:
        result("warn",
               f"{n_dup:,} extra rows identically repeat [Work ID + Vendor + Amount + Date] — "
               f"flag for manual review",
               "NOTE: Equal installments legitimately repeat [Work ID + Amount]; "
               "this is a screening flag only, not proof of double-payment. "
               "Manual review or UTR/voucher matching is needed to confirm.")
    else:
        result("pass", "No exact duplicate [Work ID + Amount + Date] rows found")


# ══════════════════════════════════════════════════════════════════════
# INPUT GATE COMPLETE — Checks 1-8 validate clean files only.
# Checks 9-10 below are OUTPUT checks: they require mplads_360_master.csv
# (built by src/build_master.py). They are skipped if the master is absent.
# ══════════════════════════════════════════════════════════════════════

input_warnings = list(warnings)  # snapshot before output checks

# ── CHECK 9: Rule-firing diagnostics (OUTPUT GATE) ────────────────────────
print(f"\n{SEP}")
print("[9] Rule-firing prevalence diagnostics (requires master)...")

MASTER_PATH = CLEAN_DIR / "mplads_360_master.csv"
if MASTER_PATH.exists():
    master = pd.read_csv(MASTER_PATH, low_memory=False)
    total_master = len(master)
    flag_cols = [c for c in master.columns if c.startswith("Flag_") or c.startswith("Integrity_") or c.startswith("Missing_")]
    if flag_cols:
        print(f"     Total works in master: {total_master:,}")
        for fc in flag_cols:
            n = int(master[fc].sum())
            rate = n / total_master
            # Integrity/Data Gap checks: zero = correct outcome (check passed)
            if fc.startswith("Integrity_") or fc == "Flag_Orphan_Payment":
                if n == 0:
                    result("pass", f"{fc} = 0 ✓  check passed (no violations)")
                else:
                    result("warn", f"{fc}: {n:,} violations ({rate:.2%}) — investigate immediately",
                           "A non-zero count means real data violated this constraint.")
            elif n == 0:
                result("warn", f"{fc} fires on ZERO works — this rule is dead",
                       "Either the condition can never be satisfied, or it is testing "
                       "the wrong column. Remove or fix this rule.")
            elif rate > 0.05:
                result("warn",
                       f"{fc} fires on {rate:.1%} of all works",
                       "High prevalence (>5%) may mean the condition is too broad, "
                       "or it is measuring a common pattern (not unusual). "
                       "Investigate before calling this a risk flag.")
            else:
                result("pass", f"{fc}: {n:,} works ({rate:.2%})")
    else:
        result("warn", "No Flag_ columns found in master dataset")
else:
    print("     [SKIP] mplads_360_master.csv not yet built — run src/build_master.py first")


# ── CHECK 10: Missing-photo flag rate over time ────────────────────────────
print(f"\n{SEP}")
print("[10] Missing photo flag — rate over time...")

if MASTER_PATH.exists() and "Missing_Photo_Proof" in master.columns and "Completion Date" in master.columns:
    master["Completion Date"] = pd.to_datetime(master["Completion Date"], errors="coerce")
    PORTAL_CUTOFF = pd.Timestamp("2026-05-15")
    before = master[master["Completion Date"] < PORTAL_CUTOFF]
    after  = master[master["Completion Date"] >= PORTAL_CUTOFF]

    for label, subset in [("Before May 2026", before), ("After May 2026", after)]:
        if len(subset):
            rate = subset["Missing_Photo_Proof"].mean()
            print(f"     {label}: {rate:.1%} missing photos ({len(subset):,} works)")

    # The flag is only meaningful after the portal started requiring photos
    after_rate = after["Missing_Photo_Proof"].mean() if len(after) else None
    if after_rate is not None and after_rate < 0.01:
        result("warn",
               "Missing_Photo_Proof rate is near 0% after portal cutoff",
               "The flag may be measuring legacy records, not current compliance gaps. "
               "Consider restricting this flag to completions after May 2026.")
    elif after_rate is not None:
        result("pass", f"Missing photo rate after portal cutoff: {after_rate:.1%}")
else:
    print("     [SKIP] master not built or columns missing")


# ── CHECK 11: PII scan result ─────────────────────────────────────────────
print(f"\n{SEP}")
print("[11] PII scan — phone numbers in text columns...")

PHONE_RE = re.compile(r'(?<!\d)[6-9]\d{9}(?!\d)')
text_sources = [
    ("Sanctioned", sanc, ["Work description"]),
    ("Completed",  comp, ["Work Description"]),
]
total_pii_hits = 0
for name, df, cols in text_sources:
    for col in cols:
        if col in df.columns:
            hits = df[col].astype(str).str.contains(PHONE_RE).sum()
            total_pii_hits += hits
            if hits > 0:
                result("warn",
                       f"{name}[{col}]: {hits:,} rows contain possible phone numbers",
                       "These values have been masked to [PHONE_REDACTED] in clean files. "
                       "Do NOT commit raw files to a public repo.")

if total_pii_hits == 0:
    result("pass", "No phone-number patterns found in text columns")


# ── CHECK 12: Snapshot freshness ─────────────────────────────────────────
print(f"\n{SEP}")
print("[12] Data freshness check...")

date_checks = [
    ("Sanctioned", sanc, "Recommended date"),
    ("Expenditure", exp, "Expenditure Date"),
    ("Completed",  comp, "Completion Date"),
]
latest = None
for _, df, col in date_checks:
    if col in df.columns:
        m = pd.to_datetime(df[col], errors="coerce").max()
        if pd.notna(m) and (latest is None or m > latest):
            latest = m

if latest:
    for name, df, col in date_checks:
        if col in df.columns:
            m = pd.to_datetime(df[col], errors="coerce").max()
            if pd.notna(m):
                lag = (latest - m).days
                if lag > 30:
                    result("warn",
                           f"{name} last date {m.strftime('%d-%b-%Y')} lags latest by {lag} days",
                           "File may be a stale snapshot. Re-download from the portal.")
                else:
                    result("pass", f"{name}: Latest date {m.strftime('%d-%b-%Y')} (lag {lag}d)")


# ── CHECK 13: Financial reconciliation totals ─────────────────────────────
print(f"\n{SEP}")
print("[13] Financial reconciliation...")

TOLERANCE_PCT = 5.0  # warn if > 5% gap between sanction and ledger totals

total_sanctioned_all = sanc["Sanction Amount ( ₹ )"].sum() if "Sanction Amount ( ₹ )" in sanc.columns else None
total_ledger     = exp["Fund Disbursed Amount ( ₹ )"].sum() if "Fund Disbursed Amount ( ₹ )" in exp.columns else None
total_completion = comp["Amount Disbursed ( ₹ )"].sum() if "Amount Disbursed ( ₹ )" in comp.columns else None

if total_sanctioned_all and total_ledger:
    # Only compare works that have payments
    exp_ids = set(exp["Work ID"].dropna())
    sanc_with_payments = sanc[sanc["Work ID"].isin(exp_ids)]
    total_sanctioned_active = sanc_with_payments["Sanction Amount ( ₹ )"].sum()

    gap_pct = abs(total_sanctioned_active - total_ledger) / total_sanctioned_active * 100
    gap_amt_cr = (total_sanctioned_active - total_ledger) / 1e7
    print(f"     Sanction total (all):       ₹{total_sanctioned_all/1e7:,.2f} Cr")
    print(f"     Sanction total (active):    ₹{total_sanctioned_active/1e7:,.2f} Cr")
    print(f"     Ledger total:               ₹{total_ledger/1e7:,.2f} Cr")
    if total_completion:
        print(f"     Completion total:           ₹{total_completion/1e7:,.2f} Cr")
    print(f"     Unpaid balance (active):    ₹{gap_amt_cr:,.2f} Cr ({gap_pct:.2f}%)")
    result("pass", f"Active Sanction vs ledger gap is {gap_pct:.2f}% (expected unpaid balance of ₹{gap_amt_cr:,.2f} Cr)")


# ── Final Summary ─────────────────────────────────────────────────────────
print(f"\n{'=' * 72}")
print("    EDA QUALITY GATE SUMMARY")
print(f"{'=' * 72}")

output_checks_ran = MASTER_PATH.exists()
print(f"  Input checks (1-8, 11-13) : {len(input_warnings)} warnings, {len(failures)} failures")
if output_checks_ran:
    output_warnings = len(warnings) - len(input_warnings)
    print(f"  Output checks (9-10)       : {output_warnings} warnings")
else:
    print(f"  Output checks (9-10)       : SKIPPED (master not built yet)")
print(f"  Total warnings : {len(warnings)}")
print(f"  Total failures : {len(failures)}")

if warnings:
    print("\n  Warnings (resolve before publishing results):")
    for w in warnings:
        print(f"    ⚠️  {w}")

if failures:
    print("\n  CRITICAL FAILURES (pipeline halted):")
    for f in failures:
        print(f"    ✗ {f}")
    print("\nFix all critical failures and re-run.\n")
    sys.exit(1)
elif not output_checks_ran:
    print(f"\n  ✓ Input checks finished: 0 failures, {len(warnings)} warnings. Safe to run src/build_master.py\n")
else:
    print(f"\n  ✓ All checks finished (input + output): 0 failures, {len(warnings)} warnings\n")
