import pandas as pd
from frontend.components.export import sanitize_cell_value, sanitize_dataframe_for_export

def test_sanitize_cell_value_formulas():
    assert sanitize_cell_value("=cmd|'/C calc'!A0") == "'=cmd|'/C calc'!A0"
    assert sanitize_cell_value("+12345") == "'+12345"
    assert sanitize_cell_value("-12345") == "'-12345"
    assert sanitize_cell_value("@SUM(A1)") == "'@SUM(A1)"
    assert sanitize_cell_value("\ttab_val") == "'\ttab_val"
    assert sanitize_cell_value("\rreturn_val") == "'\rreturn_val"

def test_sanitize_dataframe_export():
    df = pd.DataFrame({
        "Work ID": ["WS/1", "WS/2"],
        "Formula Col": ["=1+1", "Normal text"],
        "Numeric Col": [100, 200]
    })
    safe_df = sanitize_dataframe_for_export(df)
    assert safe_df["Formula Col"].iloc[0] == "'=1+1"
    assert safe_df["Formula Col"].iloc[1] == "Normal text"
    assert safe_df["Numeric Col"].iloc[0] == 100
