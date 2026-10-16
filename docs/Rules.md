# MPLADS FundGuard — Engineering & Ethical Guidelines

## 1. Ethical & Language Constraints (MANDATORY)
- **Screening, Not Accusation:** Never use terms such as "fraud probability", "fraud score", "accuracy of fraud detection", "culprit", or "guilty".
- **Review Prioritization Only:** Anomaly scores and ranks represent multi-dimensional outlier distances relative to peers, not verified malfeasance.
- **No Competitive Leaderboards:** Do not generate rankings comparing MPs or constituencies by suspicion or risk.
- **Explicit Synthetic Benchmark Labeling:** Never claim real-world audit precision without human ground-truth labels. Label synthetic benchmarks clearly.

## 2. Security Standards
- **Reviewer Authentication:** All audit endpoints require validated bearer tokens.
- **Session Isolation:** Reviewers must not see other reviewers' notes or verdicts.
- **Sanitized Exports:** Never export dataframes without running them through `sanitize_dataframe_export`.
- **Key Quarantine:** Never read or expose `manual_audit_sample_key.csv` in API endpoints.

## 3. Testing & Verification
- Always execute `PYTHONPATH=. pytest -v` before committing code.
- Ensure all Streamlit pages are covered by `AppTest` smoke tests.
- Reconcile monetary sums to 0.00 variance across line-item and master levels.