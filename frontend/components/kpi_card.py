import streamlit as st

def render_metric_card(title: str, value: str, delta: str = None, help_text: str = None):
    """
    Renders a clean metric card using Streamlit's native st.metric.
    """
    st.metric(label=title, value=value, delta=delta, help=help_text)

def format_currency_inr(amount: float) -> str:
    """
    Format large INR figures into Crores (Cr) or Lakhs (L).
    """
    if amount is None or amount == 0:
        return "₹0"
    abs_amt = abs(amount)
    if abs_amt >= 1e7:
        cr = amount / 1e7
        return f"₹{cr:,.2f} Cr"
    elif abs_amt >= 1e5:
        lakh = amount / 1e5
        return f"₹{lakh:,.2f} L"
    else:
        return f"₹{amount:,.0f}"

def format_number(val: int) -> str:
    """
    Format integer count with thousands commas.
    """
    if val is None:
        return "0"
    return f"{val:,}"
