"""
Dataframe presentation component for MPLADS FundGuard.
Provides consistent styling, column configuration, and safe rendering.
"""

from typing import Any, Optional
import pandas as pd
import streamlit as st
from frontend.components.cards import empty_state


def styled_table(
    df: Optional[pd.DataFrame],
    column_config: Optional[dict[str, Any]] = None,
    hide_index: bool = True,
    height: Optional[int] = None,
) -> None:
    """
    Renders an interactive DataFrame table with standard column configs and clean layout.
    """
    if df is None or df.empty:
        empty_state("No records found matching current criteria.")
        return

    kwargs: dict[str, Any] = {
        "column_config": column_config,
        "hide_index": hide_index,
        "width": "stretch",
    }
    if height is not None:
        kwargs["height"] = height

    st.dataframe(df, **kwargs)
