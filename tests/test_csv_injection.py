from backend.app.core.errors import sanitize_csv_cell

def test_sanitize_csv_cell_neutralizes_formulas():
    # Formulas that could trigger code execution in Excel / Google Sheets
    assert sanitize_csv_cell("=1+1") == "'=1+1"
    assert sanitize_csv_cell("+cmd|' /C calc'!A0") == "'+cmd|' /C calc'!A0"
    assert sanitize_csv_cell("-2+3") == "'-2+3"
    assert sanitize_csv_cell("@SUM(A1:A10)") == "'@SUM(A1:A10)"
    assert sanitize_csv_cell("\tmalicious") == "'\tmalicious"
    assert sanitize_csv_cell("\rmalicious") == "'\rmalicious"

def test_sanitize_csv_cell_leaves_benign_values():
    assert sanitize_csv_cell("Road Construction Work") == "Road Construction Work"
    assert sanitize_csv_cell("WS/MP18170/2024-2025/156350") == "WS/MP18170/2024-2025/156350"
    assert sanitize_csv_cell(12345) == 12345
    assert sanitize_csv_cell(None) is None
    assert sanitize_csv_cell(500000.0) == 500000.0
