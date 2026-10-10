#!/usr/bin/env python3
"""
src/build_ml_features.py — Unsupervised Anomaly Scoring (Isolation Forest) with Peer Normalization.
Detects statistical cost and execution outliers relative to peer projects in the same State & Work category.

IMPORTANT: The scored cohort is restricted to works with at least one SETTLED payment.
Works with only in-progress payments are excluded because they dominate the anomaly
rankings trivially (log_paid = 0, peer ratio ≈ −13) and are not real anomalies.
"""
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.ensemble import IsolationForest

# Paths
DATA = Path(__file__).resolve().parent.parent / "data"
CLEAN_DIR = DATA / "clean"

print("=" * 85)
print("     MPLADS UNSUPERVISED ANOMALY SCORING & PEER BENCHMARKING ENGINE")
print("=" * 85)

# 1. Load Master Dataset
master_path = CLEAN_DIR / "mplads_360_master.csv"
if not master_path.exists():
    raise FileNotFoundError(f"Master file not found at {master_path}. Run src/build_master.py first.")

df = pd.read_csv(master_path, low_memory=False)
print(f"Loaded Master Dataset: {len(df):,} total works.")

# 2. Score only works with SETTLED payments.
# Works with only in-progress payments are NOT scored: their log_paid = 0 and
# paid_vs_peer_log ≈ −13 make them trivial outliers that crowd out real anomalies.
all_paying = df[(df.Is_Sanctioned == 1) & (df.Has_Payments == 1) & (df.Sanction_Amount > 0)].copy()
base = all_paying[all_paying.Total_Exp_Settled > 0].copy()
excluded = len(all_paying) - len(base)
print(f"All paying works: {len(all_paying):,}")
print(f"  Excluded (zero settled, pending-only): {excluded:,}")
print(f"  Active Scored Cohort: {len(base):,} works.")

# 3. Peer Normalization: Compare each work with similar works (same Work category + State)
g = base.groupby(["Work category", "State"])["Total_Exp_Settled"]
base["peer_n"] = g.transform("size")
base["paid_vs_peer_log"] = np.log1p(base.Total_Exp_Settled) - np.log1p(g.transform("median"))
base.loc[base.peer_n < 20, "paid_vs_peer_log"] = np.nan

# 4. Assemble Independent ML Features (NO rule flags — avoids circular reasoning)
feat = pd.DataFrame(index=base.index)
feat["log_sanction"] = np.log1p(base.Sanction_Amount)
feat["log_paid"] = np.log1p(base.Total_Exp_Settled)
feat["log_in_progress"] = np.log1p(base.Total_Exp_In_Progress)
feat["utilization"] = base.Utilization_Ratio.clip(0, 5)

feat["n_settled"] = base.Settled_Count
feat["n_in_progress"] = base.In_Progress_Count
feat["n_vendors"] = base.Unique_Vendors_Count
feat["is_completed"] = base.Is_Completed

for c in ["Sanction_Approval_Days", "Execution_Duration_Days", "First_Payment_Lag_Days"]:
    if c in base.columns:
        feat[c.lower()] = base[c]

feat["paid_vs_peer_log"] = base["paid_vs_peer_log"]
feat.insert(0, "Work ID", base["Work ID"])

# Save ML features with pure NaNs preserved on disk
out_feat = CLEAN_DIR / "ml_features.csv"
feat.to_csv(out_feat, index=False)
print(f"Saved Clean ML Features (NaN preserved on disk) -> {out_feat}")

# 5. Isolation Forest Anomaly Scoring (Median-filled inside model input only)
X = feat.drop(columns="Work ID")
X_imputed = X.fillna(X.median())

iso = IsolationForest(
    n_estimators=300,
    contamination="auto",
    random_state=42,
    n_jobs=-1
)
iso.fit(X_imputed)

# Higher score = more statistically anomalous/unusual
base["anomaly_score"] = -iso.score_samples(X_imputed)

# 6. Evaluate Overlap against Rule Flags (Consistency Check)
flags = [c for c in df.columns if c.startswith("Flag_") or c.startswith("Missing_")]
base["n_rule_flags"] = base[flags].sum(axis=1)

out = base.sort_values("anomaly_score", ascending=False)[
    ["Work ID", "State", "Constituency", "Hon'ble Members of Parliament", "Work", 
     "Sanction_Amount", "Total_Exp_Settled", "Total_Exp_In_Progress", "paid_vs_peer_log",
     "anomaly_score", "n_rule_flags", "Is_Completed"] + flags
]

out_scores = CLEAN_DIR / "anomaly_scores.csv"
out.to_csv(out_scores, index=False)
print(f"Saved Anomaly Rankings -> {out_scores}")

# 7. Print Validation Diagnostics (Per-Flag Lift Table)
top = out.head(500)
print("\n" + "=" * 85)
print(f"Total Scored Works: {len(out):,}  (excluded {excluded:,} pending-only works)")
print("=" * 85)

# Sanity: what does the top-500 look like?
top_settled_zero = (top["Total_Exp_Settled"] == 0).sum()
top_completed = (top.get("Is_Completed", pd.Series(dtype=int)) == 1).sum() if "Is_Completed" in base.columns else "n/a"
base_completed_pct = base["Is_Completed"].mean() if "Is_Completed" in base.columns else 0
print(f"  Top-500 zero-settled: {top_settled_zero}  (should be 0 after exclusion)")
print(f"  Top-500 completed: {top_completed} ({top_completed/500:.1%} vs base {base_completed_pct:.1%})")

print("\n  ML VALIDATION: ISOLATION FOREST LIFT vs RULE-BASED FLAGS")
print("  (If the ML model finds structural anomalies, its top-scored works")
print("  should have a higher concentration of rule-flags than the base population,")
print("  despite never seeing the rules during training.)")
print("-" * 85)

print(f"{'Flag Category':<35} | {'Base Rate':<10} | {'Top 500 Rate':<15} | {'Lift'}")
print("-" * 85)
for f in flags:
    base_rate = out[f].mean()
    if base_rate == 0:
        continue
    top_rate = top[f].mean()
    lift = top_rate / base_rate if base_rate > 0 else 0
    print(f"{f:<35} | {base_rate:>9.1%} | {top_rate:>13.1%} | {lift:>5.1f}x")

print("-" * 85)
any_base = (out.n_rule_flags > 0).mean()
any_top = (top.n_rule_flags > 0).mean()
any_lift = any_top / any_base if any_base > 0 else 0
print(f"{'Any >=1 Rule Flag':<35} | {any_base:>9.1%} | {any_top:>13.1%} | {any_lift:>5.1f}x")
print("=" * 85)

print("\nTop 10 Most Anomalous Projects Identified by Isolation Forest:")
print(top[["Work ID", "State", "Sanction_Amount", "Total_Exp_Settled",
           "paid_vs_peer_log", "anomaly_score", "n_rule_flags"]].head(10).to_string(index=False))
print("=" * 85)
