"""
Pipeline tracker component for MPLADS FundGuard.
Visualizes the 8 methodology steps dynamically based on verified backend metadata.
Uses zero-indent single-block HTML strings to avoid Markdown code-block interpretation.
"""

import html
from typing import Any, Optional
import streamlit as st

FALLBACK_STEPS = [
    {"stage_number": 1, "name": "Raw Ingestion", "description": "Raw portal exports", "status": "NOT VERIFIED"},
    {"stage_number": 2, "name": "Schema Normalization", "description": "Types, dates & IDs", "status": "NOT VERIFIED"},
    {"stage_number": 3, "name": "Integrity Screening", "description": "8 canonical rules", "status": "NOT VERIFIED"},
    {"stage_number": 4, "name": "Indicator Extraction", "description": "Engineered signals", "status": "NOT VERIFIED"},
    {"stage_number": 5, "name": "Cohort Stratification", "description": "Completed vs In-Progress", "status": "NOT VERIFIED"},
    {"stage_number": 6, "name": "Unsupervised Scoring", "description": "IForest 10-seed ensemble", "status": "NOT VERIFIED"},
    {"stage_number": 7, "name": "Diagnostic Balancing", "description": "SMD matched controls", "status": "NOT VERIFIED"},
    {"stage_number": 8, "name": "Human Blind Audit", "description": "Double-blind review protocol", "status": "NOT VERIFIED"},
]


def pipeline_tracker(steps: Optional[list[dict[str, Any]]] = None) -> None:
    """
    Renders the 8-step methodology pipeline progress bar based on live backend metadata.
    """
    actual_steps = steps or FALLBACK_STEPS

    cols = st.columns(len(actual_steps))
    for i, step in enumerate(actual_steps):
        raw_status = str(step.get("status", "NOT VERIFIED")).upper()
        num = step.get("stage_number", step.get("num", i + 1))
        name = html.escape(step.get("name", ""))
        desc = html.escape(step.get("description", step.get("desc", "")))

        if raw_status in ("COMPLETED", "PASS"):
            icon = "✓"
            bg = "rgba(16, 185, 129, 0.15)"
            color = "#10B981"
            border = "rgba(16, 185, 129, 0.3)"
            status_label = "Verified"
        elif raw_status == "ACTIVE":
            icon = "●"
            bg = "rgba(139, 92, 246, 0.2)"
            color = "#A78BFA"
            border = "rgba(139, 92, 246, 0.4)"
            status_label = "Active"
        elif raw_status in ("WARN", "WARNING"):
            icon = "⚠️"
            bg = "rgba(245, 158, 11, 0.15)"
            color = "#F59E0B"
            border = "rgba(245, 158, 11, 0.3)"
            status_label = "Warning"
        else:
            icon = "○"
            bg = "rgba(255, 255, 255, 0.05)"
            color = "#9CA3AF"
            border = "rgba(255, 255, 255, 0.08)"
            status_label = "Not Verified"

        html_box = (
            f'<div style="background: {bg}; border: 1px solid {border}; border-radius: 6px; padding: 0.6rem 0.5rem; text-align: center; height: 100%;">'
            f'<div style="font-size: 0.72rem; font-weight: 700; color: {color}; margin-bottom: 0.2rem;">{icon} Step {num} • {status_label}</div>'
            f'<div style="font-size: 0.78rem; font-weight: 600; color: #E8EDF5; line-height: 1.2;">{name}</div>'
            f'<div style="font-size: 0.68rem; color: #9CA3AF; margin-top: 0.25rem;">{desc}</div>'
            f'</div>'
        )
        with cols[i]:
            st.markdown(html_box, unsafe_allow_html=True)
