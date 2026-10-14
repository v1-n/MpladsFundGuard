"""
Metric grid and KPI card components for MPLADS FundGuard.
Provides consistent glassmorphic metric cards across all dashboard pages.
"""

import html
from typing import Any, Optional
import streamlit as st


def render_metric_card_html(
    label: str,
    value: str,
    subtext: Optional[str] = None,
    badge: Optional[str] = None,
    badge_variant: str = "neutral",
) -> str:
    """Generates the HTML for an individual KPI card."""
    safe_label = html.escape(str(label))
    safe_val = html.escape(str(value))
    sub_html = f'<div class="kpi-subtext">{html.escape(str(subtext))}</div>' if subtext else ""

    badge_html = ""
    if badge:
        cls_map = {
            "pass": "badge-pass",
            "warn": "badge-warn",
            "fail": "badge-fail",
            "top1": "badge-priority-top1",
            "top5": "badge-priority-top5",
            "top10": "badge-priority-top10",
        }
        b_cls = cls_map.get(badge_variant, "badge-neutral")
        badge_html = f'<span class="{b_cls}" style="float: right;">{html.escape(str(badge))}</span>'

    return f"""
    <div class="kpi-card">
        <div>
            <div class="kpi-label">{safe_label}{badge_html}</div>
            <div class="kpi-value">{safe_val}</div>
        </div>
        {sub_html}
    </div>
    """


def metric_grid(items: list[dict[str, Any]], cols: int = 4) -> None:
    """
    Renders a grid of KPI cards across a specified number of columns.
    items: list of dicts with keys: 'label', 'value', and optional 'subtext', 'badge', 'badge_variant'.
    """
    if not items:
        return

    # Split into chunks of `cols`
    for i in range(0, len(items), cols):
        chunk = items[i : i + cols]
        row_cols = st.columns(cols)
        for col_idx, item in enumerate(chunk):
            with row_cols[col_idx]:
                card_html = render_metric_card_html(
                    label=item.get("label", ""),
                    value=item.get("value", "—"),
                    subtext=item.get("subtext"),
                    badge=item.get("badge"),
                    badge_variant=item.get("badge_variant", "neutral"),
                )
                st.markdown(card_html, unsafe_allow_html=True)
