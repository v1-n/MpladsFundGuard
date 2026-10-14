import io
import pandas as pd
import streamlit as st

def sanitize_cell_value(val):
    """
    Neutralize spreadsheet formula injection by prepending a single quote
    if the string begins with =, +, -, @, tab, or carriage return.
    """
    if isinstance(val, str) and len(val) > 0:
        if val[0] in ("=", "+", "-", "@", "\t", "\r"):
            return f"'{val}"
    return val

def sanitize_dataframe_for_export(df: pd.DataFrame) -> pd.DataFrame:
    """
    Sanitize all cells of a DataFrame to prevent formula injection.
    """
    clean_df = df.copy()
    for col in clean_df.columns:
        if clean_df[col].dtype == object or pd.api.types.is_string_dtype(clean_df[col]):
            clean_df[col] = clean_df[col].apply(sanitize_cell_value)
    return clean_df

def render_csv_download_button(
    df: pd.DataFrame,
    filename: str,
    button_label: str = "📥 Export Filtered Table to CSV",
    key: str = None
):
    """
    Renders a sanitized CSV download button.
    """
    if df is None or len(df) == 0:
        st.button(button_label, disabled=True, key=key)
        return

    safe_df = sanitize_dataframe_for_export(df)
    csv_bytes = safe_df.to_csv(index=False).encode("utf-8")
    
    st.download_button(
        label=button_label,
        data=csv_bytes,
        file_name=filename,
        mime="text/csv",
        key=key,
        help="Downloads table as CSV with sanitized cells (formula injection neutralized)."
    )
