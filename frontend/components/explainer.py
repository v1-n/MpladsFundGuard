"""
Methodology explainer component for MPLADS FundGuard.
Provides standardized contextual guidance across charts and tables.
"""

from typing import Optional
import streamlit as st


def render_explanation(
    what: str,
    why: str,
    look_for: str,
    label: str = "Methodology & Review Guidance",
    expanded: bool = False,
) -> None:
    """
    Renders an expander explaining what a view shows, why it matters,
    and what human reviewers should inspect.
    """
    with st.expander(f"📘 {label}", expanded=expanded):
        st.markdown(
            f"""
**What this shows:**  
{what}

**Why it matters:**  
{why}

**What reviewers should look for:**  
{look_for}
            """
        )
