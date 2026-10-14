from pathlib import Path
import pytest

FORBIDDEN_PHRASES = [
    "fraud probability",
    "fraud score",
    "accuracy of fraud detection",
    "culprit",
    "leaderboard",
]

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


def test_no_forbidden_words_in_frontend():
    py_files = list(FRONTEND_DIR.rglob("*.py"))
    assert len(py_files) > 0, "No frontend python files found"

    violations = []
    for file_path in py_files:
        content = file_path.read_text(encoding="utf-8").lower()
        for phrase in FORBIDDEN_PHRASES:
            if phrase in content:
                violations.append(f"{file_path.name}: contains forbidden phrase '{phrase}'")

    assert not violations, "\n".join(violations)
