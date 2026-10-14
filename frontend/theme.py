"""
Theme and Design Tokens for MPLADS FundGuard.
Provides consistent colors, typography, CSS injection, and Plotly styling.
"""

import streamlit as st

# Color Tokens
BG_COLOR = "#0B0F19"
SURFACE_COLOR = "rgba(16, 21, 35, 0.75)"
SURFACE_SOLID = "#111827"
SIDEBAR_COLOR = "#12162A"
BORDER_COLOR = "rgba(255, 255, 255, 0.08)"
TEXT_COLOR = "#E8EDF5"
TEXT_MUTED = "#9CA3AF"

# Accent & Functional Semantics
ACCENT_COLOR = "#F97316"   # Saffron
NAVY_COLOR = "#1F3864"     # Dark Navy
BLUE_COLOR = "#2563EB"     # Royal Blue
PURPLE_COLOR = "#8B5CF6"   # Review priority & unsupervised ML signals
GREEN_COLOR = "#10B981"    # Integrity PASS, clean status
AMBER_COLOR = "#F59E0B"    # Integrity WARN, attention needed
RED_COLOR = "#EF4444"      # Integrity FAIL, rule flags count only

# Plotly Palette
CHART_PALETTE = [
    "#F97316",  # Saffron
    "#8B5CF6",  # Purple
    "#2563EB",  # Blue
    "#10B981",  # Green
    "#F59E0B",  # Amber
    "#EC4899",  # Pink
    "#06B6D4",  # Cyan
    "#6366F1",  # Indigo
]

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Outfit:wght@500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    color: #E8EDF5;
}

h1, h2, h3, h4, .font-heading {
    font-family: 'Outfit', sans-serif !important;
    font-weight: 600;
    letter-spacing: -0.02em;
}

/* Glassmorphic card containers */
.glass-card {
    background: rgba(16, 21, 35, 0.75);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    padding: 1.25rem;
    backdrop-filter: blur(8px);
    margin-bottom: 1rem;
}

.kpi-card {
    background: rgba(16, 21, 35, 0.75);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    padding: 1rem 1.15rem;
    height: 100%;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
}

.kpi-label {
    font-size: 0.78rem;
    color: #9CA3AF;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-weight: 600;
    margin-bottom: 0.35rem;
}

.kpi-value {
    font-family: 'Outfit', sans-serif;
    font-size: 1.85rem;
    font-weight: 700;
    color: #E8EDF5;
    line-height: 1.2;
}

.kpi-subtext {
    font-size: 0.78rem;
    color: #9CA3AF;
    margin-top: 0.35rem;
}

/* Review Priority Badges */
.badge-priority-top1 {
    background: rgba(139, 92, 246, 0.25);
    color: #C4B5FD;
    border: 1px solid rgba(139, 92, 246, 0.5);
    padding: 3px 8px;
    border-radius: 4px;
    font-weight: 600;
    font-size: 0.75rem;
    display: inline-block;
}

.badge-priority-top5 {
    background: rgba(139, 92, 246, 0.18);
    color: #DDD6FE;
    border: 1px solid rgba(139, 92, 246, 0.35);
    padding: 3px 8px;
    border-radius: 4px;
    font-weight: 500;
    font-size: 0.75rem;
    display: inline-block;
}

.badge-priority-top10 {
    background: rgba(139, 92, 246, 0.12);
    color: #EDE9FE;
    border: 1px solid rgba(139, 92, 246, 0.25);
    padding: 3px 8px;
    border-radius: 4px;
    font-size: 0.75rem;
    display: inline-block;
}

/* Status Badges */
.badge-pass {
    background: rgba(16, 185, 129, 0.15);
    color: #6EE7B7;
    border: 1px solid rgba(16, 185, 129, 0.3);
    padding: 2px 7px;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 600;
}

.badge-warn {
    background: rgba(245, 158, 11, 0.15);
    color: #FCD34D;
    border: 1px solid rgba(245, 158, 11, 0.3);
    padding: 2px 7px;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 600;
}

.badge-fail {
    background: rgba(239, 68, 68, 0.15);
    color: #FCA5A5;
    border: 1px solid rgba(239, 68, 68, 0.3);
    padding: 2px 7px;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 600;
}

.badge-neutral {
    background: rgba(156, 163, 175, 0.15);
    color: #D1D5DB;
    border: 1px solid rgba(156, 163, 175, 0.25);
    padding: 2px 7px;
    border-radius: 4px;
    font-size: 0.75rem;
}

/* Subtle Streamlit widget styling */
div[data-testid="stMetricValue"] {
    font-family: 'Outfit', sans-serif !important;
}
</style>
"""


def inject_css() -> None:
    """Injects custom design tokens and styles into the Streamlit session."""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def apply_dark_theme(fig):
    """
    Applies the MPLADS FundGuard dark theme to a Plotly figure.
    Sets clean typography, transparent background, and subdued grid lines.
    """
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color=TEXT_COLOR, size=12),
        title_font=dict(family="Outfit, sans-serif", size=15, color=TEXT_COLOR),
        margin=dict(l=40, r=20, t=40, b=40),
        legend=dict(
            bgcolor="rgba(16, 21, 35, 0.8)",
            bordercolor="rgba(255, 255, 255, 0.08)",
            borderwidth=1,
            font=dict(color=TEXT_COLOR, size=11),
        ),
        hoverlabel=dict(
            bgcolor=SURFACE_SOLID,
            font_size=12,
            font_family="Inter, sans-serif",
            bordercolor=BORDER_COLOR,
        ),
    )
    fig.update_xaxes(
        gridcolor="rgba(255, 255, 255, 0.06)",
        zerolinecolor="rgba(255, 255, 255, 0.12)",
        tickfont=dict(color=TEXT_MUTED, size=10),
        title_font=dict(color=TEXT_COLOR, size=11),
    )
    fig.update_yaxes(
        gridcolor="rgba(255, 255, 255, 0.06)",
        zerolinecolor="rgba(255, 255, 255, 0.12)",
        tickfont=dict(color=TEXT_MUTED, size=10),
        title_font=dict(color=TEXT_COLOR, size=11),
    )
    return fig
