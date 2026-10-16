import json
import logging
from pathlib import Path
from pydantic import model_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

class Settings(BaseSettings):
    PROJECT_NAME: str = "MPLADS FundGuard API"
    VERSION: str = "2.0.0"
    API_V1_PREFIX: str = "/api/v1"
    API_V1_STR: str = "/api/v1"
    
    # Paths
    BASE_DIR: Path = BASE_DIR
    DATA_DIR: Path = BASE_DIR / "data"
    CLEAN_DATA_DIR: Path = BASE_DIR / "data" / "clean"
    AUDIT_DB_PATH: Path = BASE_DIR / "data" / "manual_audit_reviews.db"
    
    # Server / Security
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: list[str] = [
        "http://localhost:8501",
        "http://127.0.0.1:8501",
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]
    LOG_LEVEL: str = "INFO"
    IS_TESTING: bool = False
    
    # Audit Security & Authentication
    AUDIT_AUTH_ENABLED: bool = True
    AUDIT_REVIEWER_TOKENS: str = ""
    REVIEWER_TOKENS: dict[str, dict[str, str]] = {}
    
    # Pagination
    PAGE_SIZE_DEFAULT: int = 50
    PAGE_SIZE_MAX: int = 200
    
    # App semantics
    REBUILD_COMMAND: str = "python -m src.rebuild"
    DISCLAIMER: str = (
        "Flags and ranks are screening signals for manual review. "
        "They are not evidence of fraud or wrongdoing."
    )
    
    @model_validator(mode="after")
    def parse_tokens(self) -> "Settings":
        raw = (self.AUDIT_REVIEWER_TOKENS or "").strip()
        if raw:
            if raw.startswith("{"):
                try:
                    parsed = json.loads(raw)
                    if isinstance(parsed, dict):
                        self.REVIEWER_TOKENS = parsed
                except Exception as e:
                    logger.error(f"Failed to parse AUDIT_REVIEWER_TOKENS as JSON: {e}")
            else:
                tokens_dict = {}
                for entry in raw.split(","):
                    parts = entry.strip().split(":")
                    if len(parts) >= 2:
                        tok = parts[0].strip()
                        rev_id = parts[1].strip()
                        role = parts[2].strip() if len(parts) >= 3 else "reviewer"
                        if tok and rev_id:
                            tokens_dict[tok] = {"reviewer_id": rev_id, "role": role}
                if tokens_dict:
                    self.REVIEWER_TOKENS = tokens_dict
        return self

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }

settings = Settings()
