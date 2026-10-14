"""
src/rebuild.py
==============
Automated execution of the entire MPLADS FundGuard data pipeline in sequence:
  1. eda/eda_pipeline.py  (Cleans raw CSVs, parses dates, masks PII)
  2. eda/eda_checks.py    (Input Quality Gate)
  3. src/build_master.py  (Builds 360° Master dataset with forensic flags)
  4. eda/eda_checks.py    (Output Quality Gate, exports data_quality_report.json)
  5. src/build_ml_features.py (Engineers features, runs Isolation Forest scoring)
  6. src/evaluate_model.py (Runs benchmarks, generates audit sample & evaluation_results.json)

Usage:
  python3 -m src.rebuild
"""
import sys
import subprocess
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

PIPELINE_STEPS = [
    ("Step 1: Clean Raw Datasets", [sys.executable, "eda/eda_pipeline.py"]),
    ("Step 2: Input Quality Gate", [sys.executable, "eda/eda_checks.py"]),
    ("Step 3: Build 360° Master", [sys.executable, "src/build_master.py"]),
    ("Step 4: Output Quality Gate", [sys.executable, "eda/eda_checks.py"]),
    ("Step 5: ML Feature & Anomaly Scoring", [sys.executable, "src/build_ml_features.py"]),
    ("Step 6: Evaluation & Blind Audit Suite", [sys.executable, "src/evaluate_model.py"]),
]

def main():
    print("=" * 80)
    print("      MPLADS FUNDGUARD — FULL PIPELINE REBUILD")
    print("=" * 80)
    start_total = time.time()

    for idx, (step_name, cmd) in enumerate(PIPELINE_STEPS, 1):
        print(f"\n[{idx}/{len(PIPELINE_STEPS)}] Executing: {step_name} ({' '.join(cmd)})...")
        step_start = time.time()
        res = subprocess.run(cmd, cwd=str(BASE_DIR))
        elapsed = time.time() - step_start
        if res.returncode != 0:
            print(f"\n❌ Pipeline failed at {step_name} with exit code {res.returncode}")
            sys.exit(res.returncode)
        print(f"✓ {step_name} completed in {elapsed:.1f}s (exit code 0)")

    total_elapsed = time.time() - start_total
    print("\n" + "=" * 80)
    print(f"🎉 All pipeline steps completed successfully in {total_elapsed:.1f}s.")
    print("Clean artifacts and evaluation JSON files are up to date.")
    print("=" * 80)

if __name__ == "__main__":
    main()
