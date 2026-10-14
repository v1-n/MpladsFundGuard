"""
Plotly chart generators with unified dark theme styling.
"""

from typing import Any, Optional
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from frontend.theme import apply_dark_theme, CHART_PALETTE, ACCENT_COLOR, PURPLE_COLOR


def donut_chart(
    labels: list[str],
    values: list[float | int],
    title: str = "",
    hole: float = 0.6,
    colors: Optional[list[str]] = None,
) -> go.Figure:
    """Creates a donut chart styled with dark theme."""
    palette = colors or CHART_PALETTE
    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=hole,
                marker=dict(colors=palette, line=dict(color="#111827", width=1.5)),
                textinfo="label+percent",
                hoverinfo="label+value+percent",
            )
        ]
    )
    if title:
        fig.update_layout(title=title)
    return apply_dark_theme(fig)


def horizontal_bar_chart(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: str = "",
    color_col: Optional[str] = None,
    text_col: Optional[str] = None,
    color_sequence: Optional[list[str]] = None,
) -> go.Figure:
    """Creates a horizontal bar chart sorted ascending by value."""
    seq = color_sequence or [ACCENT_COLOR]
    fig = px.bar(
        df,
        x=x_col,
        y=y_col,
        orientation="h",
        color=color_col,
        text=text_col,
        color_discrete_sequence=seq,
        title=title,
    )
    if text_col:
        fig.update_traces(textposition="outside")
    fig.update_layout(yaxis=dict(autorange="reversed"))
    return apply_dark_theme(fig)


def histogram_chart(
    df: pd.DataFrame,
    col: str,
    title: str = "",
    log_x: bool = False,
    nbins: int = 30,
    color: Optional[str] = None,
) -> go.Figure:
    """Creates a histogram for feature distributions with optional log-scale toggle."""
    fill_color = color or ACCENT_COLOR
    fig = px.histogram(
        df,
        x=col,
        nbins=nbins,
        title=title,
        log_x=log_x,
        color_discrete_sequence=[fill_color],
    )
    fig.update_traces(marker_line_width=1, marker_line_color="#111827")
    return apply_dark_theme(fig)


def heatmap_chart(
    z_matrix: list[list[float]],
    x_labels: list[str],
    y_labels: list[str],
    title: str = "",
    colorscale: str = "Viridis",
) -> go.Figure:
    """Creates a correlation or prevalence heatmap."""
    fig = go.Figure(
        data=go.Heatmap(
            z=z_matrix,
            x=x_labels,
            y=y_labels,
            colorscale=colorscale,
            hoverongaps=False,
        )
    )
    if title:
        fig.update_layout(title=title)
    return apply_dark_theme(fig)


def scatter_chart(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: str = "",
    hover_cols: Optional[list[str]] = None,
    color_col: Optional[str] = None,
) -> go.Figure:
    """Creates a scatter plot with optional color grouping and hover metadata."""
    fig = px.scatter(
        df,
        x=x_col,
        y=y_col,
        color=color_col,
        hover_data=hover_cols,
        title=title,
        color_discrete_sequence=CHART_PALETTE,
    )
    fig.update_traces(marker=dict(size=7, opacity=0.8, line=dict(width=0.5, color="#FFFFFF")))
    return apply_dark_theme(fig)
