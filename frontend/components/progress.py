"""
Pipeline tracker component for MPLADS FundGuard.
Visualizes the 8 display-only methodology steps of the screening architecture.
Uses zero-indent single-block HTML strings to avoid Markdown code-block interpretation.
"""

import html
from typing import Any, Optional
import streamlit as st

DEFAULT_STEPS = [
    {"num": 1, "name": "Raw Ingestion", "desc": "86,527 works ingested", "status": "completed"},
    {"num": 2, "name": "Schema Normalization", "desc": "Types, dates & IDs", "status": "completed"},
    {"num": 3, "name": "Integrity Screening", "desc": "8 canonical rules", "status": "completed"},
    {"num": 4, "name": "Indicator Extraction", "desc": "11 descriptive signals", "status": "completed"},
    {"num": 5, "name": "Cohort Stratification", "desc": "Completed vs In-Progress", "status": "completed"},
    {"num": 6, "name": "Unsupervised Scoring", "desc": "IForest + Robust Z", "status": "completed"},
    {"num": 7, "name": "Diagnostic Balancing", "desc": "SMD matched controls", "status": "completed"},
    {"num": 8, "name": "Human Blind Audit", "desc": "Double-blind review", "status": "active"},
]


def pipeline_tracker(steps: Optional[list[dict[str, Any]]] = None) -> None:
    """
    Renders the 8-step methodology pipeline progress bar.
    """
    actual_steps = steps or DEFAULT_STEPS

    cols = st.columns(len(actual_steps))
    for i, step in enumerate(actual_steps):
        status = step.get("status", "completed")
        num = step.get("num", i + 1)
        name = html.escape(step.get("name", ""))
        desc = html.escape(step.get("desc", ""))

        if status == "completed":
            icon = "✓"
            bg = "rgba(16, 185, 129, 0.15)"
            color = "#10B981"
            border = "rgba(16, 185, 129, 0.3)"
        elif status == "active":
            icon = "●"
            bg = "rgba(139, 92, 246, 0.2)"
            color = "#A78BFA"
            border = "rgba(139, 92, 246, 0.4)"
        else:
            icon = "○"
            bg = "rgba(255, 255, 255, 0.05)"
            color = "#9CA3AF"
            border = "rgba(255, 255, 255, 0.08)"

        html_box = (
            f'<div style="background: {bg}; border: 1px solid {border}; border-radius: 6px; padding: 0.6rem 0.5rem; text-align: center; height: 100%;">'
            f'<div style="font-size: 0.75rem; font-weight: 700; color: {color}; margin-bottom: 0.2rem;">{icon} Step {num}</div>'
            f'<div style="font-size: 0.78rem; font-weight: 600; color: #E8EDF5; line-height: 1.2;">{name}</div>'
            f'<div style="font-size: 0.7rem; color: #9CA3AF; margin-top: 0.25rem;">{desc}</div>'
            f'</div>'
        )
        with cols[i]:
            st.markdown(html_box, unsafe_allow_html=True)
