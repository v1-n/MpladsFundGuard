"""
Integrity scorecard component for MPLADS FundGuard.
Presents pipeline integrity checks with clear PASS/WARN/FAIL counts.
Strictly avoids inventing arbitrary 0-100 scores.
"""

import html
from typing import Any
import streamlit as st
from frontend.components.metrics import metric_grid


def integrity_scorecard(report: dict[str, Any]) -> None:
    """
    Renders an integrity scorecard reflecting passed, warned, and failed pipeline checks.
    """
    if not report:
        st.info("No integrity report available.")
        return

    passed = report.get("passed", 0)
    warnings = report.get("warnings", 0)
    failures = report.get("failures", 0)
    total = report.get("total_checks", passed + warnings + failures)
    status = report.get("overall_status", "UNKNOWN").upper()

    status_badge_variant = "pass"
    if failures > 0:
        status_badge_variant = "fail"
    elif warnings > 0:
        status_badge_variant = "warn"

    items = [
        {
            "label": "Pipeline Status",
            "value": status,
            "subtext": f"{total} validation gates evaluated",
            "badge": "Active",
            "badge_variant": status_badge_variant,
        },
        {
            "label": "Passed Checks",
            "value": str(passed),
            "subtext": "Zero-defect criteria met",
            "badge": "Pass",
            "badge_variant": "pass",
        },
        {
            "label": "Warnings",
            "value": str(warnings),
            "subtext": "Soft anomaly / review needed",
            "badge": "Warn" if warnings > 0 else "Clean",
            "badge_variant": "warn" if warnings > 0 else "pass",
        },
        {
            "label": "Failures",
            "value": str(failures),
            "subtext": "Structural gate breaches",
            "badge": "Fail" if failures > 0 else "None",
            "badge_variant": "fail" if failures > 0 else "pass",
        },
    ]

    metric_grid(items, cols=4)
