from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
PAGES_DIR = FRONTEND_DIR / "pages"


def test_app_home_smoke():
    at = AppTest.from_file(str(FRONTEND_DIR / "app.py"))
    at.run(timeout=10)
    assert not at.exception, f"app.py raised exception: {at.exception}"


def test_all_pages_smoke():
    page_files = sorted(list(PAGES_DIR.glob("*.py")))
    assert len(page_files) >= 8, f"Expected at least 8 pages, found {len(page_files)}"

    for page_path in page_files:
        at = AppTest.from_file(str(page_path))
        at.run(timeout=10)
        assert not at.exception, f"Page {page_path.name} raised exception: {at.exception}"
