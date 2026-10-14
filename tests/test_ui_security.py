import html
import pytest
import pandas as pd
from frontend.components.metrics import render_metric_card_html
from frontend.components.export import sanitize_cell_value, sanitize_dataframe_for_export


def test_metric_card_html_escaping():
    malicious_input = '<script>alert("xss")</script>'
    card_html = render_metric_card_html(
        label=malicious_input,
        value=malicious_input,
        subtext=malicious_input,
        badge=malicious_input,
    )
    # Ensure unescaped tags are not present
    assert "<script>" not in card_html
    assert html.escape(malicious_input) in card_html


def test_csv_injection_prevention():
    dangerous_payloads = [
        "=CMD('calc')",
        "+12345",
        "-SUM(A1:A10)",
        "@SUM(B1:B10)",
        "\talert",
        "\rcmd",
    ]
    for payload in dangerous_payloads:
        sanitized = sanitize_cell_value(payload)
        assert sanitized.startswith("'"), f"Failed to neutralize: {payload}"

    benign_payloads = ["Regular Text", 12345, None, 84.5]
    for payload in benign_payloads:
        assert sanitize_cell_value(payload) == payload


def test_sanitize_dataframe():
    df = pd.DataFrame({
        "Work ID": ["=1+1", "Normal"],
        "Amount": [100, 200],
        "Notes": ["@cmd", "clean note"]
    })
    safe_df = sanitize_dataframe_for_export(df)
    assert safe_df["Work ID"].iloc[0] == "'=1+1"
    assert safe_df["Work ID"].iloc[1] == "Normal"
    assert safe_df["Notes"].iloc[0] == "'@cmd"
