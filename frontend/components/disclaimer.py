import streamlit as st

MANDATORY_DISCLAIMER = (
    "Flags and ranks are screening signals for manual review. "
    "They are not evidence of fraud or wrongdoing."
)

SCOPE_NOTICE = (
    "**Scope & Coverage:** Lok Sabha only (543 MPs, 18th Lok Sabha public ledger). "
    "This platform performs exploratory irregularity audits and multi-dimensional outlier screening "
    "to assist manual public expenditure verification. No constituency or MP blame rankings are generated."
)

def render_disclaimer_banner(include_scope: bool = False):
    """
    Renders the required screening signal disclaimer across pages.
    """
    st.warning(f"⚠️ **Screening Notice:** {MANDATORY_DISCLAIMER}")
    if include_scope:
        st.info(f"ℹ️ {SCOPE_NOTICE}")
