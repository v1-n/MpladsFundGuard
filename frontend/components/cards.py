"""
Card, header, and state display components for MPLADS FundGuard.
Strictly escapes HTML content to prevent XSS.
Uses zero-indent single-block HTML strings to avoid Markdown code-block interpretation.
"""

import html
from typing import Optional
import streamlit as st


def section_header(title: str, subtitle: Optional[str] = None, badge: Optional[str] = None) -> None:
    """
    Renders a unified section header with an optional subtitle and badge.
    """
    safe_title = html.escape(title)
    badge_html = f'<span class="badge-neutral" style="margin-left: 0.5rem; vertical-align: middle;">{html.escape(badge)}</span>' if badge else ""
    sub_html = f'<div style="color: #9CA3AF; font-size: 0.85rem; margin-top: 0.2rem;">{html.escape(subtitle)}</div>' if subtitle else ""

    html_content = (
        f'<div style="margin-top: 1.5rem; margin-bottom: 0.85rem;">'
        f'<h3 class="font-heading" style="margin: 0; font-size: 1.25rem; color: #E8EDF5; display: inline-block;">{safe_title}</h3>'
        f'{badge_html}'
        f'{sub_html}'
        f'</div>'
    )
    st.markdown(html_content, unsafe_allow_html=True)


def info_card(title: str, content: str, icon: Optional[str] = None, variant: str = "default") -> None:
    """
    Renders a glassmorphic info card with optional icon and accent variant.
    """
    safe_title = html.escape(title)
    safe_content = html.escape(content)
    icon_html = f'<span style="margin-right: 0.4rem;">{html.escape(icon)}</span>' if icon else ""

    border_color = "rgba(255, 255, 255, 0.08)"
    if variant == "purple":
        border_color = "rgba(139, 92, 246, 0.3)"
    elif variant == "accent":
        border_color = "rgba(249, 115, 22, 0.3)"
    elif variant == "amber":
        border_color = "rgba(245, 158, 11, 0.3)"

    html_content = (
        f'<div class="glass-card" style="border-color: {border_color};">'
        f'<div style="font-weight: 600; color: #E8EDF5; font-size: 0.95rem; margin-bottom: 0.4rem;">{icon_html}{safe_title}</div>'
        f'<div style="color: #9CA3AF; font-size: 0.85rem; line-height: 1.5;">{safe_content}</div>'
        f'</div>'
    )
    st.markdown(html_content, unsafe_allow_html=True)


def empty_state(message: str, icon: str = "🔍") -> None:
    """
    Renders an empty state indicator with a message and icon.
    """
    safe_msg = html.escape(message)
    safe_icon = html.escape(icon)
    html_content = (
        f'<div class="glass-card" style="text-align: center; padding: 2.5rem 1rem;">'
        f'<div style="font-size: 2.2rem; margin-bottom: 0.5rem;">{safe_icon}</div>'
        f'<div style="color: #9CA3AF; font-size: 0.9rem;">{safe_msg}</div>'
        f'</div>'
    )
    st.markdown(html_content, unsafe_allow_html=True)


def error_state(title: str, message: str) -> None:
    """
    Renders an error callout box with a title and explanation.
    """
    safe_title = html.escape(title)
    safe_msg = html.escape(message)
    html_content = (
        f'<div class="glass-card" style="border-color: rgba(239, 68, 68, 0.4); background: rgba(239, 68, 68, 0.05);">'
        f'<div style="color: #F87171; font-weight: 600; font-size: 0.95rem; margin-bottom: 0.3rem;">⚠️ {safe_title}</div>'
        f'<div style="color: #D1D5DB; font-size: 0.85rem; line-height: 1.4;">{safe_msg}</div>'
        f'</div>'
    )
    st.markdown(html_content, unsafe_allow_html=True)
