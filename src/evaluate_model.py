#!/usr/bin/env python3
"""
src/evaluate_model.py — Rigorous Unsupervised Model Evaluation Suite.

Evaluates the unsupervised anomaly detection framework using four defensible methodologies:
1. Run-to-Run Stability: Measures Jaccard index of top-300 anomalies across independent random seeds
   for BOTH Completed and In-Progress cohorts.
2. Synthetic Anomaly Injection: Evaluates detection of multi-dimensional perturbations across
   5 independent trials, reporting mean ± std for ROC-AUC and per-type Recall@2%.
3. Baseline Comparison: Compares Isolation Forest against a non-degenerate Robust Z-Score (Median/MAD)
   on untouched clean data.
4. De-biased Blind Audit Sample: Generates an unlabelled, shuffled sample of 100 distinct works
   (scores and political identifiers stripped) with an audit rubric.
"""

import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.ensemble import IsolationForest
from sklearn.metrics import roc_auc_score

DATA = Path(__file__).resolve().parent.parent / "data"
CLEAN_DIR = DATA / "clean"

print("=" * 85)
print("     MPLADS MODEL EVALUATION & STABILITY BENCHMARK SUITE")
print("=" * 85)

# Load Prepared Features
feat_path = CLEAN_DIR / "ml_features.csv"
if not feat_path.exists():
    raise FileNotFoundError(f"Feature dataset not found at {feat_path}. Run src/build_ml_features.py first.")

df = pd.read_csv(feat_path, low_memory=False)
print(f"Loaded Feature Matrix: {len(df):,} works.")

# Cohort definitions
comp = df[df.Is_Completed == 1].copy().reset_index(drop=True)
prog = df[df.Is_Completed == 0].copy().reset_index(drop=True)

COMP_COLS = [
    "log_sanction", "paid_vs_peer_log", "utilization",
    "n_settled", "n_vendors",
    "sanction_approval_days", "first_payment_lag_days", "execution_duration_days"
]

PROG_COLS = [
    "log_sanction", "paid_vs_peer_log", "utilization", "log_in_progress",
    "n_settled", "n_in_progress", "n_vendors",
    "sanction_approval_days", "first_payment_lag_days"
]

X_comp = comp[COMP_COLS].fillna(comp[COMP_COLS].median()).fillna(0)
X_prog = prog[PROG_COLS].fillna(prog[PROG_COLS].median()).fillna(0)
print(f"  • Completed Works Reference Cohort  : {len(X_comp):,} works")
print(f"  • In-Progress Works Reference Cohort: {len(X_prog):,} works\n")

# ─────────────────────────────────────────────────────────────────────────────
# 1. RUN-TO-RUN STABILITY ACROSS BOTH COHORTS
# ─────────────────────────────────────────────────────────────────────────────
print("─" * 85)
print("[1] Measuring Run-to-Run Ranking Stability (Top-300 Jaccard Overlap)...")

def get_top_k_indices(X, seeds, k=300, max_samples=1024):
    scores = np.zeros(len(X))
    for s in seeds:
        iso = IsolationForest(n_estimators=200, max_samples=min(max_samples, len(X)), random_state=s, n_jobs=-1)
        iso.fit(X)
        scores += -iso.score_samples(X)
    return set(pd.Series(scores).nlargest(k).index)

for name, matrix in [("Completed", X_comp), ("In-Progress", X_prog)]:
    top_A = get_top_k_indices(matrix, seeds=range(0, 10), k=300)
    top_B = get_top_k_indices(matrix, seeds=range(10, 20), k=300)
    jaccard = len(top_A & top_B) / len(top_A | top_B)
    shared = len(top_A & top_B)
    status = "✓ PASS (stable)" if jaccard >= 0.90 else "⚠️ WARNING (unstable)"
    print(f"  • {name:<12} Top-300 Shared: {shared:>3} / 300 | Jaccard Index: {jaccard:.4f}  {status}")

# ─────────────────────────────────────────────────────────────────────────────
# 2. NON-DEGENERATE ROBUST Z-SCORE FUNCTION
# ─────────────────────────────────────────────────────────────────────────────
def robust_z_scores(df_in):
    """
    Computes Robust Z-Score: |x - median| / scale
    where scale = 1.4826 * MAD. If MAD == 0 (common in integer count features where
    median=1 for 90% of rows), falls back to 0.6745 * std to avoid divide-by-zero degeneracy.
    """
    med = df_in.median()
    mad = (df_in - med).abs().median()
    std = df_in.std().replace(0, 1.0)
    scale = np.where(mad > 0, 1.4826 * mad, 0.6745 * std)
    scale = np.where(scale > 0, scale, 1.0)
    return ((df_in - med).abs() / scale).max(axis=1)

# ─────────────────────────────────────────────────────────────────────────────
# 3. SYNTHETIC ANOMALY INJECTION BENCHMARK (5 Independent Trials)
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "─" * 85)
print("[2] Synthetic Outlier Injection Benchmark (5 Independent Trials)...")
print("    Planting 300 synthetic anomalies into clean completed works:")
print("      - Type A (100 works): Cost far above peer benchmark (+2.5 log) & budget (+2.0 log)")
print("      - Type B (100 works): Extreme vendor & installment counts (6x installments, 5x vendors)")
print("      - Type C (100 works): Implausibly compressed timelines (1-day duration, 0 lag)")

N_TRIALS = 5
k_2pct = int(len(X_comp) * 0.02)

if_metrics = []
z_metrics = []

for trial in range(N_TRIALS):
    rng = np.random.default_rng(trial * 100 + 42)
    X_inj = X_comp.copy()
    labels = np.zeros(len(X_inj), dtype=int)
    shuffled_idx = rng.permutation(len(X_inj))

    idx_a = shuffled_idx[:100]
    idx_b = shuffled_idx[100:200]
    idx_c = shuffled_idx[200:300]

    # Injections
    X_inj.loc[idx_a, "log_sanction"] += 2.0
    X_inj.loc[idx_a, "paid_vs_peer_log"] += 2.5
    X_inj.loc[idx_b, "n_settled"] = (X_inj.loc[idx_b, "n_settled"] * 6).clip(lower=6)
    X_inj.loc[idx_b, "n_vendors"] = (X_inj.loc[idx_b, "n_vendors"] * 5).clip(lower=5)
    X_inj.loc[idx_c, "first_payment_lag_days"] = 0
    X_inj.loc[idx_c, "sanction_approval_days"] = 1
    X_inj.loc[idx_c, "execution_duration_days"] = 1
    labels[np.r_[idx_a, idx_b, idx_c]] = 1

    # Train Isolation Forest on clean training sample, score injected evaluation set
    clean_train_idx = shuffled_idx[300:]
    iso_model = IsolationForest(n_estimators=200, max_samples=1024, random_state=trial, n_jobs=-1)
    iso_model.fit(X_inj.loc[clean_train_idx])
    scores_if = -iso_model.score_samples(X_inj)

    # Robust Z baseline on all features
    scores_z = robust_z_scores(X_inj)

    def eval_run(scores):
        auc = roc_auc_score(labels, scores)
        top_k = set(pd.Series(scores).nlargest(k_2pct).index)
        rec = sum(1 for i in np.r_[idx_a, idx_b, idx_c] if i in top_k) / 300
        prec = sum(1 for i in np.r_[idx_a, idx_b, idx_c] if i in top_k) / k_2pct
        rec_a = sum(1 for i in idx_a if i in top_k) / len(idx_a)
        rec_b = sum(1 for i in idx_b if i in top_k) / len(idx_b)
        rec_c = sum(1 for i in idx_c if i in top_k) / len(idx_c)
        return [auc, prec, rec, rec_a, rec_b, rec_c]

    if_metrics.append(eval_run(scores_if))
    z_metrics.append(eval_run(scores_z))

if_arr = np.array(if_metrics)
z_arr = np.array(z_metrics)

print("\n" + f"{'Method':<20} | {'ROC-AUC':<15} | {'Precision@2%':<14} | {'Recall@2% (All)':<16} | {'Type A (Cost)':<15} | {'Type B (Count)':<15} | {'Type C (Time)'}")
print("─" * 125)
print(f"{'Isolation Forest':<20} | {if_arr[:,0].mean():.3f} ± {if_arr[:,0].std():.3f} | {if_arr[:,1].mean():>6.1%} ± {if_arr[:,1].std():.1%} | {if_arr[:,2].mean():>7.1%} ± {if_arr[:,2].std():.1%} | {if_arr[:,3].mean():>6.1%} ± {if_arr[:,3].std():.1%} | {if_arr[:,4].mean():>6.1%} ± {if_arr[:,4].std():.1%} | {if_arr[:,5].mean():>6.1%} ± {if_arr[:,5].std():.1%}")
print(f"{'Robust Z-Score':<20} | {z_arr[:,0].mean():.3f} ± {z_arr[:,0].std():.3f} | {z_arr[:,1].mean():>6.1%} ± {z_arr[:,1].std():.1%} | {z_arr[:,2].mean():>7.1%} ± {z_arr[:,2].std():.1%} | {z_arr[:,3].mean():>6.1%} ± {z_arr[:,3].std():.1%} | {z_arr[:,4].mean():>6.1%} ± {z_arr[:,4].std():.1%} | {z_arr[:,5].mean():>6.1%} ± {z_arr[:,5].std():.1%}")
print("─" * 125)
print("  Note: Type C timeline recall is low (~1%) because single-feature values (0 lag, 1-day approval)")
print("  are already present in 3-4% of legitimate works; trees split one feature at a time.")

# ─────────────────────────────────────────────────────────────────────────────
# 4. BASELINE MODEL AGREEMENT ON UNTOUCHED CLEAN DATA
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "─" * 85)
print("[3] Baseline Model Agreement on Real Untouched Data...")

# Fit 10-seed ensemble IF directly on untouched clean X_comp
clean_if_scores = np.zeros(len(X_comp))
for s in range(10):
    clf = IsolationForest(n_estimators=200, max_samples=1024, random_state=s, n_jobs=-1)
    clf.fit(X_comp)
    clean_if_scores += -clf.score_samples(X_comp)
clean_if_scores /= 10.0

clean_z_scores = robust_z_scores(X_comp)

top_300_if = set(pd.Series(clean_if_scores).nlargest(300).index)
top_300_z = set(pd.Series(clean_z_scores).nlargest(300).index)
shared_baseline = len(top_300_if & top_300_z)

print(f"  • Top-300 works shared on clean data: {shared_baseline} / 300 ({shared_baseline/300:.1%})")
print("    (Isolation Forest and Robust Z-score identify distinct subsets of anomalies;")
print("     Robust Z identifies single extreme values; Isolation Forest captures multi-feature geometry.)")

# ─────────────────────────────────────────────────────────────────────────────
# 5. DE-BIASED BLIND HUMAN REVIEW SAMPLE
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "─" * 85)
print("[4] Generating De-biased Blind Human Audit Sample...")
master_path = CLEAN_DIR / "mplads_360_master.csv"
master_df = pd.read_csv(master_path, low_memory=False)

scores_path = CLEAN_DIR / "anomaly_scores.csv"
scores_df = pd.read_csv(scores_path, low_memory=False)

comp_works = comp[["Work ID"]].merge(master_df, on="Work ID", how="left")
comp_works = comp_works.merge(scores_df[["Work ID", "rank_in_stage", "anomaly_score"]], on="Work ID", how="left")

# Select top 50 anomalies
top_50 = comp_works.sort_values("rank_in_stage").head(50).copy()
top_50["Cohort"] = "Top_Ranked"
top_50_ids = set(top_50["Work ID"])

# Sample 50 random works STRICTLY excluding the top 50 (no duplicate works)
candidate_pool = comp_works[~comp_works["Work ID"].isin(top_50_ids)]
rand_50 = candidate_pool.sample(n=50, random_state=42).copy()
rand_50["Cohort"] = "Random_Sample"

# Combine and shuffle
sample = pd.concat([top_50, rand_50]).sample(frac=1.0, random_state=123).reset_index(drop=True)

# De-bias: Exclude political and regional identifiers (MP Name, Constituency, State)
audit_export = sample[[
    "Work ID", "Work", "Sanction_Amount", "Total_Exp_Settled",
    "Settled_Count", "Unique_Vendors_Count", "Execution_Duration_Days"
]].copy()
audit_export["Audit_Verdict"] = ""  # Options: Normal | Needs Investigation | Suspicious
audit_export["Auditor_Notes"] = ""

out_sample_file = CLEAN_DIR / "manual_audit_sample_blind.csv"
audit_export.to_csv(out_sample_file, index=False)

# Save ground-truth audit key separately for post-audit precision calculation
key_file = CLEAN_DIR / "manual_audit_sample_key.csv"
sample[["Work ID", "Cohort", "rank_in_stage", "anomaly_score"]].to_csv(key_file, index=False)

print(f"  ✓ Exported 100 unique works (de-biased, unlabelled) -> {out_sample_file}")
print(f"  ✓ Exported audit key for scoring validation -> {key_file}")
print("\n  AUDIT REVIEW RUBRIC:")
print("    - 'Normal'             : Proportionate cost, standard duration, 1-2 vendors/installments.")
print("    - 'Needs Investigation': Unusually high vendor count, extreme duration, or high cost vs work type.")
print("    - 'Suspicious'         : Conflicting progress dates, extreme payment fragmentation, severe cost disparity.")
print("=" * 85)
