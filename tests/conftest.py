import pytest
from fastapi.testclient import TestClient
from backend.app.core.config import settings

# Test credentials configured strictly for test execution
TEST_TOKENS = {
    "auditor-test-token": {"reviewer_id": "Auditor-Test-Alpha", "role": "reviewer"},
    "auditor-beta-token": {"reviewer_id": "Auditor-Test-Beta", "role": "reviewer"},
    "lead-admin-token": {"reviewer_id": "Lead-Auditor", "role": "admin"},
}

@pytest.fixture(scope="session", autouse=True)
def configure_test_environment(tmp_path_factory):
    settings.IS_TESTING = True
    settings.REVIEWER_TOKENS.update(TEST_TOKENS)
    test_db = tmp_path_factory.mktemp("audit_db") / "manual_audit_reviews_test.db"
    settings.AUDIT_DB_PATH = test_db
    from backend.app.services.audit_service import audit_service
    audit_service.db_path = test_db
    audit_service._init_sqlite_db()

@pytest.fixture(scope="session")
def client():
    from backend.app.main import app
    with TestClient(app) as c:
        yield c
